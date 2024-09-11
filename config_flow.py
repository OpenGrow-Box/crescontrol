import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from .const import DOMAIN
from .cres_control import CresControl  # Stellen Sie sicher, dass CresControl importiert wird
import logging

_LOGGER = logging.getLogger(__name__)

class CresControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is None:
            schema = vol.Schema({
                vol.Required(CONF_HOST): str
            })
            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                errors=errors,
                description_placeholders={
                    "host": "10.1.1.122"
                }
            )

        host = user_input[CONF_HOST]
        _LOGGER.debug(f"Testing connection to {host}.")

        try:
            control = CresControl(host)  # Instanziieren der CresControl mit dem Host
            connection_successful = await control.test_connection()  # Verwenden von CresControl zum Testen der Verbindung

            if not connection_successful:
                raise Exception("Connection test failed.")

            _LOGGER.debug(f"Successfully connected to {host}.")
        except Exception as e:
            _LOGGER.error(f"Failed to connect to {host}: {e}")
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): str
                }),
                errors=errors,
                description_placeholders={
                    "host": "10.1.1.122"
                }
            )

        return self.async_create_entry(title=f"CresControl ({host})", data={"host": host})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CresControlOptionsFlowHandler(config_entry)

class CresControlOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({
               
                })
            )
        return self.async_create_entry(title="", data=user_input)
