"""Łączy się z API i parsuje dane."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import StairsApiClient
from .const import DOMAIN
from .light import Stairs

_LOGGER = logging.getLogger(__name__)

# List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LIGHT]

# Create ConfigEntry type alias with API object
# Rename type alias and update all entry annotations
type StairsConfigEntry = ConfigEntry[Stairs]  # noqa: F821


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StairsConfigEntry,
) -> bool:
    """Skonfiguruj platformę z wpisu konfiguracyjnego."""
    _LOGGER.info("Uruchamiam async_setup_entry")
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    num_led_strips = entry.data["led_strips"]

    _LOGGER.info(
        "Konfiguruję platformę %s dla hosta %s i portu %s, liczba pasków LED: %s",
        DOMAIN,
        host,
        port,
        num_led_strips,
    )

    session = async_get_clientsession(hass)
    api_client = StairsApiClient(host, port, session)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = api_client

    # entry.runtime_data = Stairs(hass, api_client, 0)

    # hass.data[DOMAIN][config_entry.entry_id] = api_client

    # async_add_entities([Stairs(hass, host, port, i) for i in range(num_led_strips)])

    await hass.config_entries.async_forward_entry_setup(entry, "light")

    return True


# Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: StairsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
