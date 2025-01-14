"""Main entity instance."""

from datetime import timedelta
import logging

import aiohttp
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    PLATFORM_SCHEMA as LIGHT_PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .api_client import StairsApiClient

_LOGGER = logging.getLogger(__name__)

DOMAIN = "stairs"

# Zmieniamy platform schema, aby uwzględnić wiele pasków LED
LIGHT_PLATFORM_SCHEMA = LIGHT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST, default="127.0.0.1"): cv.string,
        vol.Required(CONF_PORT, default=5000): cv.port,
        vol.Optional("led_strips", default=16): cv.positive_int,  # Liczba pasków LED
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Skonfiguruj platformę światła z wpisu konfiguracyjnego."""
    _LOGGER.info("Uruchamiam async_setup_entry dla light")

    api_client = hass.data[DOMAIN][config_entry.entry_id]
    num_led_strips = config_entry.data["led_strips"]

    async_add_entities([Stairs(hass, api_client, i) for i in range(num_led_strips)])


# async def async_setup_platform(
#     hass: HomeAssistant, config: ConfigType, async_add_entities: AddEntitiesCallback
# ) -> None:
#     """Konfiguracja platformy."""
#     _LOGGER.debug("Uruchamiam async_setup_platform")
#     host = config[CONF_HOST]
#     port = config[CONF_PORT]
#     num_led_strips = config["led_strips"]

#     _LOGGER.debug(
#         "Konfiguruję platformę Stairs dla hosta %s i portu %s, liczba pasków LED: %s",
#         host,
#         port,
#         num_led_strips,
#     )

#     # Tworzymy encje dla każdego paska LED
#     async_add_entities([Stairs(hass, host, port, i) for i in range(num_led_strips)])


# async def async_setup_entry(
#     hass: HomeAssistant,
#     config_entry: ConfigEntry,
#     async_add_entities: AddEntitiesCallback,
# ) -> None:
#     """Skonfiguruj platformę z wpisu konfiguracyjnego."""
#     _LOGGER.info("Uruchamiam async_setup_entry")
#     host = config_entry.data[CONF_HOST]
#     port = config_entry.data[CONF_PORT]
#     num_led_strips = config_entry.data["led_strips"]

#     _LOGGER.info(
#         "Konfiguruję platformę %s dla hosta %s i portu %s, liczba pasków LED: %s",
#         DOMAIN,
#         host,
#         port,
#         num_led_strips,
#     )

#     # session = hass.helpers.aiohttp_client.async_get_clientsession()
#     # api_client = StairsApiClient(host, port, session)

#     async_add_entities(
#         [Stairs(hass, host, port, i) for i in range(num_led_strips)], True
#     )


class Stairs(LightEntity, RestoreEntity):
    """Reprezentacja oświetlenia schodów."""

    def __init__(
        self, hass: HomeAssistant, api_client: StairsApiClient, strip_number: int
    ) -> None:
        """Inicjalizacja."""
        self._api_client = api_client
        # self._host = host
        # self._port = port
        # self._base_url = f"http://{host}:{port}/api"
        self._strip_number = strip_number
        self._state = False
        self._brightness = 255  # Domyślna jasność
        self._name = f"Stairs step {strip_number}"
        self._unique_id = f"{DOMAIN}_{strip_number}"
        self._rgb_color = (255, 255, 255)  # Domyślny kolor bazowy
        # self._color_to_set = (255, 255, 255)
        self._effect_list = ["RAINBOW", "PULSE", "STROBE"]
        self._effect = "STROBE"
        self._stop_update = None
        self.hass = hass
        self._available = False  # Domyślnie ustawiamy jako niedostępny

    async def async_added_to_hass(self) -> None:
        """Przywracanie stanu encji po dodaniu jej do HA."""
        _LOGGER.debug("Uruchamiam async_added_to_hass dla %s", self._unique_id)
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            if state.state == STATE_ON:
                self._state = True
            else:
                self._state = False

            if "brightness" in state.attributes:
                self._brightness = state.attributes.get("brightness", 255)

            if "rgb_color" in state.attributes:
                self._rgb_color = state.attributes.get("rgb_color", (255, 255, 255))

            if "effect" in state.attributes:
                self._effect = state.attributes.get("effect", "STROBE")

        # Pobierz stan z API przy starcie
        await self.async_initialize_state_from_api()

        # Uruchom pętlę aktualizacji
        await self.start_update_loop()

    async def async_will_remove_from_hass(self) -> None:
        """Wywołane przed usunięciem encji z HA."""
        _LOGGER.debug("Uruchamiam async_will_remove_from_hass dla %s", self._unique_id)
        await self.stop_update_loop()

    async def async_initialize_state_from_api(self):
        """Pobiera początkowy stan paska LED z API."""
        try:
            data = await self._api_client.async_get_status(self._strip_number)
            if data:
                _LOGGER.info(
                    "Otrzymano początkowy status dla paska %s: %s",
                    self._strip_number,
                    data,
                )
                self._state = data.get("state") == "ON"
                self._brightness = data.get("brightness", self._brightness)
                self._rgb_color = tuple(data.get("rgb_color", self._rgb_color))
                self._effect = data.get("effect", self._effect)
            else:
                _LOGGER.warning(
                    "Nie udało się pobrać początkowego stanu dla paska %s",
                    self._strip_number,
                )
                self._state = False
        except aiohttp.ClientConnectionError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas pobierania początkowego statusu paska %s: Nie można połączyć się z serwerem: %s",
                self._strip_number,
                e,
            )
            self._state = False
        except aiohttp.InvalidURL as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas pobierania początkowego statusu paska %s: Nieprawidłowy URL: %s",
                self._strip_number,
                e,
            )
            self._state = False
        except aiohttp.ClientResponseError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas pobierania początkowego statusu paska %s: Błąd odpowiedzi HTTP: %s",
                self._strip_number,
                e,
            )
            self._state = False
        except TimeoutError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas pobierania początkowego statusu paska %s: Przekroczono czas oczekiwania: %s",
                self._strip_number,
                e,
            )
            self._state = False
        finally:
            self.async_write_ha_state()

    @property
    def should_poll(self) -> bool:
        """Encja będzie odpytywana."""
        return True

    @property
    def name(self) -> str:
        """Nazwa."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Unikalny ID."""
        return self._unique_id

    @property
    def brightness(self) -> int:
        """Jasność."""
        return self._brightness

    @property
    def is_on(self) -> bool:
        """Stan."""
        return self._state

    @property
    def color_mode(self) -> ColorMode:
        """Tryb koloru."""
        return ColorMode.RGB

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Kolor RGB."""
        return self._rgb_color

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Zwraca zbiór wspieranych trybów kolorów."""
        return {ColorMode.RGB}

    @property
    def effect_list(self) -> list[str]:
        """Lista dostępnych efektów."""
        _LOGGER.debug("Zwracam effect_list: %s", self._effect_list)
        return self._effect_list

    @property
    def effect(self) -> str:
        """Aktualnie wybrany efekt."""
        _LOGGER.debug("Zwracam effect: %s", self._effect)
        return self._effect

    @property
    def available(self) -> bool:
        """Zwraca True, jeśli encja jest dostępna."""
        return self._available

    async def async_turn_on(self, **kwargs: vol.Any) -> None:
        """Włącz oświetlenie."""
        await self._turn_on_online(**kwargs)

    async def _turn_on_online(self, **kwargs):
        """Włączanie oświetlenia w trybie online."""
        _LOGGER.info("Turn on strip: %s", self._strip_number)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        effect = kwargs.get(ATTR_EFFECT)

        # Ustaw jasność, tylko jeśli podano
        if brightness is not None:
            self._brightness = brightness
            _LOGGER.info("Otrzymano jasność: %s", self._brightness)
            # Ustaw jasność na API, tylko jeśli się zmieniła
            await self._api_client.async_set_brightness(
                self._strip_number, self._brightness
            )

        # Ustaw kolor
        if rgb_color is not None:
            _LOGGER.info("Otrzymano kolor RGB: %s", rgb_color)
            self._rgb_color = rgb_color
            await self._api_client.async_set_solid_color(
                self._strip_number, self._rgb_color
            )
            # self._color_to_set = rgb_color

        if effect is not None:
            _LOGGER.debug("Otrzymano efekt: %s", effect)
            self._effect = effect
            await self._api_client.async_set_effect(self._strip_number, effect)
            # Do zrobienia: Wysyłanie żądania do API w celu ustawienia efektu

        if not self._state:
            self._state = True
            await self._api_client.async_turn_on_strip(self._strip_number)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: vol.Any) -> None:
        """Wyłącz oświetlenie."""
        await self._turn_off_online()

    async def _turn_off_online(self):
        """Wyłączanie oświetlenia w trybie online."""
        _LOGGER.info("Turn off strip: %s", self._strip_number)
        self._state = False
        self._effect = None

        # Wyślij żądanie wyłączenia paska do API
        await self._api_client.async_turn_off_strip(self._strip_number)

        self.async_write_ha_state()

    async def start_update_loop(self):
        """Rozpoczęcie pętli aktualizacji."""

        async def update_callback(now):
            await self.async_check_availability()
            if self._available:
                await self.async_update()
            elif self._state != STATE_UNAVAILABLE:
                self._state = STATE_UNAVAILABLE
            self.async_write_ha_state()

        _LOGGER.debug("Uruchamiam pętlę aktualizacji")
        self._stop_update = async_track_time_interval(
            self.hass, update_callback, timedelta(seconds=5)
        )

    async def stop_update_loop(self):
        """Zatrzymanie pętli aktualizacji."""
        if self._stop_update:
            _LOGGER.debug("Zatrzymuję pętlę aktualizacji")
            self._stop_update()
            self._stop_update = None

    async def async_check_availability(self):
        """Sprawdza dostępność paska LED, odpytując API."""
        is_available = await self._api_client.async_check_availability()
        self._available = is_available

        if self._available:
            if not self._available:
                _LOGGER.info("Pasek LED %s jest dostępny", self._strip_number)
        else:
            if self._available:
                _LOGGER.warning("Pasek LED %s jest niedostępny", self._strip_number)
            self._state = STATE_UNAVAILABLE

    async def async_update(self) -> None:
        """Aktualizuj stan encji, pobierając dane z API."""
        data = await self._api_client.async_get_status(self._strip_number)
        if data:
            _LOGGER.info("Otrzymano status: %s", data)
            self._state = data.get("state") == "ON"
            rgb_color = data.get("rgb_color")
            if rgb_color is not None:
                self._rgb_color = tuple(rgb_color)
            self._effect = data.get("effect", self._effect)
        else:
            _LOGGER.error("Błąd podczas aktualizacji paska %s", self._strip_number)
            self._state = False

    async def async_set_solid_color(self, rgb):
        """Ustaw jednolity kolor."""
        await self._api_client.async_set_solid_color(self._strip_number, rgb)

    async def async_set_brightness(self, brightness):
        """Ustaw jasność paska."""
        await self._api_client.async_set_brightness(self._strip_number, brightness)

    async def async_set_effect(self, strip_number, effect):
        """Ustaw efekt na pasku."""
        await self._api_client.async_set_effect(strip_number, effect)
