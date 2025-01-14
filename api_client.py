"""Klient API dla integracji Stairs."""

import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)


class StairsApiClient:
    """Klasa klienta API do komunikacji z API."""

    def __init__(self, host, port, session: aiohttp.ClientSession) -> None:
        """Inicjalizacja klienta API."""
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}/api"
        self.session = session

    async def async_set_solid_color(self, strip_number, rgb):
        """Ustaw jednolity kolor.

        Args:
            strip_number: strip number LED.
            rgb: Krotka z wartościami RGB (czerwony, zielony, niebieski).

        """
        url = f"{self._base_url}/animation/solidcolor"

        payload = {
            "step_number": strip_number,
            "red": rgb[0],
            "green": rgb[1],
            "blue": rgb[2],
        }
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    _LOGGER.info("Ustawiono kolor %s na pasku %s", rgb, strip_number)
                else:
                    _LOGGER.error(
                        "Błąd podczas ustawiania koloru na pasku %s: %s",
                        strip_number,
                        response.status,
                    )
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas ustawiania koloru na pasku %s: %s",
                strip_number,
                e,
            )

    async def async_set_brightness(self, strip_number, brightness):
        """Ustaw jasność paska."""
        url = f"{self._base_url}/brightness"

        payload = {"step_number": strip_number, "brightness": brightness}

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    _LOGGER.info(
                        "Ustawiono jasność %s na pasku %s", brightness, strip_number
                    )
                else:
                    _LOGGER.error(
                        "Błąd podczas ustawiania jasności na pasku %s: %s",
                        strip_number,
                        response.status,
                    )
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas ustawiania jasności na pasku %s: %s",
                strip_number,
                e,
            )

    async def async_check_availability(self):
        """Sprawdza dostępność API."""
        try:
            async with (
                self.session.get(
                    f"{self._base_url}/health",  # Endpoint do sprawdzenia ogólnej dostępności API
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp
            ):
                if resp.status == 200:
                    _LOGGER.debug("API jest dostępne")
                    return True
                _LOGGER.error("API jest niedostępne (status: %s)", resp.status)
                return False
        except (TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas sprawdzania dostępności: %s", e
            )
            return False

    async def async_get_status(self, strip_number):
        """Pobierz dane z API."""
        try:
            async with self.session.get(
                f"{self._base_url}/led/status?strip_number={strip_number}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.info("Otrzymano status: %s", data)
                    return data
                _LOGGER.error(
                    "Błąd podczas pobierania statusu dla paska %s: %s",
                    strip_number,
                    resp.status,
                )
                return None
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas aktualizacji paska %s: %s",
                strip_number,
                e,
            )
            return None

    async def async_turn_on_strip(self, strip_number):
        """Włącz pasek LED."""
        url = f"{self._base_url}/led/turn_on"  # Dostosuj endpoint
        payload = {"step_number": strip_number}
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    _LOGGER.info("Włączono pasek %s", strip_number)
                else:
                    _LOGGER.error(
                        "Błąd podczas włączania paska %s: %s",
                        strip_number,
                        response.status,
                    )
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas włączania paska %s: %s", strip_number, e
            )

    async def async_turn_off_strip(self, strip_number):
        """Wyłącz pasek LED."""
        url = f"{self._base_url}/led/turn_off"  # Dostosuj endpoint
        payload = {"step_number": strip_number}
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    _LOGGER.info("Wyłączono pasek %s", strip_number)
                else:
                    _LOGGER.error(
                        "Błąd podczas wyłączania paska %s: %s",
                        strip_number,
                        response.status,
                    )
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas wyłączania paska %s: %s", strip_number, e
            )

    async def async_set_effect(self, strip_number, effect):
        """Ustaw efekt na pasku."""
        url = f"{self._base_url}/led/effect"
        payload = {"strip_number": strip_number, "effect": effect}
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    _LOGGER.info("Ustawiono efekt %s na pasku %s", effect, strip_number)
                else:
                    _LOGGER.error(
                        "Błąd podczas ustawiania efektu na pasku %s: %s",
                        strip_number,
                        response.status,
                    )
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas ustawiania efektu na pasku %s: %s",
                strip_number,
                e,
            )

    async def async_get_all_statuses(self):
        """Pobiera status wszystkich pasków LED za jednym zapytaniem."""
        try:
            async with self.session.get(f"{self._base_url}/led/status/all") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("Otrzymano status wszystkich pasków: %s", data)
                    return data
                _LOGGER.error(
                    "Błąd podczas pobierania statusu wszystkich pasków: %s", resp.status
                )
                return None
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "Błąd połączenia z API podczas pobierania statusu wszystkich pasków: %s",
                e,
            )
            return None
