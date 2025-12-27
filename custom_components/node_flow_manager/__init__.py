import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NodeRedApiClient
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_VERIFY_SSL, CONF_PUBLIC_URL, CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import NodeRedCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.TEXT, Platform.NUMBER, Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Node-RED Flow Manager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Merge data and options
    config = {**entry.data, **entry.options}

    _LOGGER.setLevel(config.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper())

    session = async_get_clientsession(hass)
    client = NodeRedApiClient(
        host=config[CONF_HOST],
        port=config.get(CONF_PORT, DEFAULT_PORT),
        username=config.get(CONF_USERNAME),
        password=config.get(CONF_PASSWORD),
        session=session,
        verify_ssl=config.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        public_url=config.get(CONF_PUBLIC_URL)
    )

    coordinator = NodeRedCoordinator(
        hass, 
        client, 
        scan_interval_seconds=config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entry when options change
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
