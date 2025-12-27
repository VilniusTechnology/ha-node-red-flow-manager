import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from homeassistant.core import callback
from .api import NodeRedApiClient
from .const import (
    DOMAIN, 
    DEFAULT_PORT, 
    DEFAULT_VERIFY_SSL, 
    CONF_PUBLIC_URL, 
    CONF_LOG_LEVEL, 
    DEFAULT_LOG_LEVEL, 
    LOG_LEVELS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

class NodeRedFlowManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Node-RED Flow Manager."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NodeRedFlowManagerOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = NodeRedApiClient(
                host=user_input[CONF_HOST],
                port=user_input.get(CONF_PORT, DEFAULT_PORT),
                username=user_input.get(CONF_USERNAME),
                password=user_input.get(CONF_PASSWORD),
                session=session,
                verify_ssl=user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            )

            valid = await client.authenticate()
            if not valid:
                errors["base"] = "invalid_auth"
            else:
                try:
                    await client.get_flows()
                except Exception:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=f"Node-RED ({user_input[CONF_HOST]})", 
                        data=user_input
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str,
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                vol.Optional(CONF_PUBLIC_URL): str,
            }),
            errors=errors
        )

class NodeRedFlowManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle Node-RED options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Default values comes from options if set, otherwise data
        # Default values comes from options if set, otherwise data
        data = {**self._config_entry.data, **self._config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=data.get(CONF_HOST)): str,
                vol.Optional(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_USERNAME, default=data.get(CONF_USERNAME, "")): str,
                vol.Optional(CONF_PASSWORD, default=data.get(CONF_PASSWORD, "")): str,
                vol.Optional(CONF_VERIFY_SSL, default=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)): bool,
                vol.Optional(CONF_PUBLIC_URL, default=data.get(CONF_PUBLIC_URL, "")): str,
                vol.Optional(CONF_LOG_LEVEL, default=data.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL)): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"label": label, "value": value} 
                            for value, label in LOG_LEVELS.items()
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_SCAN_INTERVAL, default=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=5)),
            })
        )
