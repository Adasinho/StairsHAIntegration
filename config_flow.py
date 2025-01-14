"""Config flow for Stairs integration."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DEFAULT_HOST, DEFAULT_NUM_STRIPS, DEFAULT_PORT, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required("led_strips", default=DEFAULT_NUM_STRIPS): int,
    }
)


class StairsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Stairs."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Tutaj możesz dodać walidację danych wejściowych, np.:
            # if not is_valid_host(user_input[CONF_HOST]):
            #     errors["base"] = "invalid_host"
            # if not is_valid_port(user_input[CONF_PORT]):
            #     errors["base"] = "invalid_port"

            if not (user_input[CONF_HOST]):
                errors["base"] = "no_host"

            elif not (0 < user_input[CONF_PORT] < 65536):
                errors["base"] = "no_port"

            elif not (0 < user_input["led_strips"] <= 100):
                errors["base"] = "invalid_strip_number"

            if not errors:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Handle a get options flow for Stairs."""

        return StairsOptionsFlowHandler(config_entry)


class StairsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a options flow for Stairs."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST, default=self.config_entry.data.get(CONF_HOST)
                    ): cv.string,
                    vol.Optional(
                        CONF_PORT, default=self.config_entry.data.get(CONF_PORT)
                    ): cv.port,
                    vol.Optional(
                        "led_strips", default=self.config_entry.data.get("led_strips")
                    ): cv.positive_int,
                }
            ),
        )
