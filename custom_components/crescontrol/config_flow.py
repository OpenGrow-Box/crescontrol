import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from custom_components.crescontrol.const import (
    DOMAIN,
    CONF_OUTPUTS,
    CONF_SWITCHES,
    CONF_INPUTS,
    CONF_FAN,
    OUTPUT_CHANNELS,
    SWITCH_CHANNELS,
    INPUT_CHANNELS,
    PWM_OUTPUTS,
    ENTITY_TYPE_NONE,
    ENTITY_TYPE_LIGHT,
    ENTITY_TYPE_SWITCH,
    ENTITY_TYPE_FAN,
    ENTITY_TYPE_NUMBER,
    ENTITY_TYPE_OPTIONS,
    SENSOR_TYPE_NONE,
    SENSOR_TYPE_VOLTAGE,
    INPUT_SENSOR_OPTIONS,
    DEFAULT_OUTPUT_NAMES,
    DEFAULT_SWITCH_NAMES,
    DEFAULT_INPUT_NAMES,
)
from custom_components.crescontrol.cres_control import CresControl
import logging

_LOGGER = logging.getLogger(__name__)


class CresControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CresControl."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._host = None
        self._outputs = {}
        self._switches = {}
        self._inputs = {}
        self._fan = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step - host configuration."""
        errors = {}

        if user_input is None:
            schema = vol.Schema({
                vol.Required(CONF_HOST, description={"suggested_value": "192.168.1.100"}): str
            })
            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                errors=errors,
            )

        host = user_input[CONF_HOST].strip()
        _LOGGER.debug(f"Testing connection to {host}.")

        if not host:
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
                errors=errors,
            )

        try:
            control = CresControl(host)
            connection_successful = await control.test_connection()

            if not connection_successful:
                raise Exception("Connection test failed.")

            _LOGGER.debug(f"Successfully connected to {host}.")
            self._host = host

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            return await self.async_step_outputs()

        except Exception as e:
            _LOGGER.error(f"Failed to connect to {host}: {e}")
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
                errors=errors,
            )

    async def async_step_outputs(self, user_input=None):
        """Handle output configuration step."""
        errors = {}

        if user_input is not None:
            for output in OUTPUT_CHANNELS:
                entity_type = user_input.get(f"output_{output}_type", ENTITY_TYPE_NONE)
                if entity_type != ENTITY_TYPE_NONE:
                    custom_name = user_input.get(f"output_{output}_name", "")
                    # Auto-generate name from type + channel if empty
                    if not custom_name or not custom_name.strip():
                        custom_name = f"{entity_type.capitalize()}{output.upper()}"
                    self._outputs[output] = {
                        "type": entity_type,
                        "name": custom_name.replace(" ", ""),
                    }

            return await self.async_step_switches()

        schema_dict = {}
        for output in OUTPUT_CHANNELS:
            is_pwm = output in PWM_OUTPUTS
            default_type = ENTITY_TYPE_LIGHT if is_pwm else ENTITY_TYPE_NONE

            schema_dict[vol.Optional(f"output_{output}_type", default=default_type)] = vol.In(ENTITY_TYPE_OPTIONS)
            schema_dict[vol.Optional(f"output_{output}_name", default="")] = str

        return self.async_show_form(
            step_id="outputs",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_switches(self, user_input=None):
        """Handle switch configuration step."""
        errors = {}

        if user_input is not None:
            for switch in SWITCH_CHANNELS:
                entity_type = user_input.get(f"switch_{switch}_type", ENTITY_TYPE_NONE)
                if entity_type != ENTITY_TYPE_NONE:
                    custom_name = user_input.get(f"switch_{switch}_name", "")
                    # Auto-generate name from type + channel if empty
                    if not custom_name or not custom_name.strip():
                        custom_name = f"{entity_type.capitalize()}{switch.upper()}"
                    self._switches[switch] = {
                        "type": entity_type,
                        "name": custom_name.replace(" ", ""),
                    }

            return await self.async_step_inputs()

        schema_dict = {}
        for switch in SWITCH_CHANNELS:
            schema_dict[vol.Optional(f"switch_{switch}_type", default=ENTITY_TYPE_NONE)] = vol.In(ENTITY_TYPE_OPTIONS)
            schema_dict[vol.Optional(f"switch_{switch}_name", default="")] = str

        return self.async_show_form(
            step_id="switches",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_inputs(self, user_input=None):
        """Handle input configuration step."""
        errors = {}

        if user_input is not None:
            for input_name in INPUT_CHANNELS:
                sensor_type = user_input.get(f"input_{input_name}_type", SENSOR_TYPE_NONE)
                if sensor_type != SENSOR_TYPE_NONE:
                    custom_name = user_input.get(f"input_{input_name}_name", "")
                    # Auto-generate name from type + channel if empty
                    if not custom_name or not custom_name.strip():
                        custom_name = f"Input{input_name.upper()}"
                    self._inputs[input_name] = {
                        "type": sensor_type,
                        "name": custom_name.replace(" ", ""),
                    }

            return await self.async_step_fan()

        schema_dict = {}
        for input_name in INPUT_CHANNELS:
            schema_dict[vol.Optional(f"input_{input_name}_type", default=SENSOR_TYPE_NONE)] = vol.In(INPUT_SENSOR_OPTIONS)
            schema_dict[vol.Optional(f"input_{input_name}_name", default="")] = str

        return self.async_show_form(
            step_id="inputs",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_fan(self, user_input=None):
        """Handle built-in fan configuration step."""
        errors = {}

        if user_input is not None:
            fan_enabled = user_input.get("fan_enabled", False)
            if fan_enabled:
                self._fan = {
                    "enabled": True,
                    "type": ENTITY_TYPE_FAN,
                    "name": user_input.get("fan_name", "Ventilation").replace(" ", ""),
                }
            else:
                self._fan = {"enabled": False}

            return self.async_create_entry(
                title=f"CresControl ({self._host})",
                data={
                    CONF_HOST: self._host,
                    CONF_OUTPUTS: self._outputs,
                    CONF_SWITCHES: self._switches,
                    CONF_INPUTS: self._inputs,
                    CONF_FAN: self._fan,
                },
            )

        schema_dict = {
            vol.Optional("fan_enabled", default=False): bool,
            vol.Optional("fan_name", default="Ventilation"): str,
        }

        return self.async_show_form(
            step_id="fan",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return CresControlOptionsFlowHandler(config_entry)


class CresControlOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for reconfiguration."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            new_data = dict(self.config_entry.data)

            # Parse outputs
            output_config = {}
            for output in OUTPUT_CHANNELS:
                entity_type = user_input.get(f"output_{output}_type", ENTITY_TYPE_NONE)
                if entity_type != ENTITY_TYPE_NONE:
                    custom_name = user_input.get(f"output_{output}_name", "")
                    if not custom_name or not custom_name.strip():
                        custom_name = f"{entity_type.capitalize()}{output.upper()}"
                    output_config[output] = {
                        "type": entity_type,
                        "name": custom_name.replace(" ", ""),
                    }

            # Parse switches
            switch_config = {}
            for switch in SWITCH_CHANNELS:
                entity_type = user_input.get(f"switch_{switch}_type", ENTITY_TYPE_NONE)
                if entity_type != ENTITY_TYPE_NONE:
                    custom_name = user_input.get(f"switch_{switch}_name", "")
                    if not custom_name or not custom_name.strip():
                        custom_name = f"{entity_type.capitalize()}{switch.upper()}"
                    switch_config[switch] = {
                        "type": entity_type,
                        "name": custom_name.replace(" ", ""),
                    }

            # Parse inputs
            input_config = {}
            for input_name in INPUT_CHANNELS:
                sensor_type = user_input.get(f"input_{input_name}_type", SENSOR_TYPE_NONE)
                if sensor_type != SENSOR_TYPE_NONE:
                    custom_name = user_input.get(f"input_{input_name}_name", "")
                    if not custom_name or not custom_name.strip():
                        custom_name = f"Input{input_name.upper()}"
                    input_config[input_name] = {
                        "type": sensor_type,
                        "name": custom_name.replace(" ", ""),
                    }

            # Parse fan
            fan_enabled = user_input.get("fan_enabled", False)
            if fan_enabled:
                custom_name = user_input.get("fan_name", "")
                if not custom_name or not custom_name.strip():
                    custom_name = "Ventilation"
                fan_config = {
                    "enabled": True,
                    "type": ENTITY_TYPE_FAN,
                    "name": custom_name.replace(" ", ""),
                }
            else:
                fan_config = {"enabled": False}

            new_data[CONF_OUTPUTS] = output_config
            new_data[CONF_SWITCHES] = switch_config
            new_data[CONF_INPUTS] = input_config
            new_data[CONF_FAN] = fan_config

            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        # Build schema with current values
        current_outputs = self.config_entry.data.get(CONF_OUTPUTS, {})
        current_switches = self.config_entry.data.get(CONF_SWITCHES, {})
        current_inputs = self.config_entry.data.get(CONF_INPUTS, {})
        current_fan = self.config_entry.data.get(CONF_FAN, {})

        schema_dict = {}

        # Output fields
        for output in OUTPUT_CHANNELS:
            cfg = current_outputs.get(output, {})
            is_pwm = output in PWM_OUTPUTS
            default_type = cfg.get("type", ENTITY_TYPE_LIGHT if is_pwm else ENTITY_TYPE_NONE)
            default_name = cfg.get("name", "")

            schema_dict[vol.Optional(f"output_{output}_type", default=default_type)] = vol.In(ENTITY_TYPE_OPTIONS)
            schema_dict[vol.Optional(f"output_{output}_name", default=default_name)] = str

        # Switch fields
        for switch in SWITCH_CHANNELS:
            cfg = current_switches.get(switch, {})
            default_type = cfg.get("type", ENTITY_TYPE_NONE)
            default_name = cfg.get("name", "")

            schema_dict[vol.Optional(f"switch_{switch}_type", default=default_type)] = vol.In(ENTITY_TYPE_OPTIONS)
            schema_dict[vol.Optional(f"switch_{switch}_name", default=default_name)] = str

        # Input fields
        for input_name in INPUT_CHANNELS:
            cfg = current_inputs.get(input_name, {})
            default_type = cfg.get("type", SENSOR_TYPE_NONE)
            default_name = cfg.get("name", "")

            schema_dict[vol.Optional(f"input_{input_name}_type", default=default_type)] = vol.In(INPUT_SENSOR_OPTIONS)
            schema_dict[vol.Optional(f"input_{input_name}_name", default=default_name)] = str

        # Fan fields
        fan_enabled = current_fan.get("enabled", False) if isinstance(current_fan, dict) else False
        fan_name = current_fan.get("name", "") if isinstance(current_fan, dict) else ""

        schema_dict[vol.Optional("fan_enabled", default=fan_enabled)] = bool
        schema_dict[vol.Optional("fan_name", default=fan_name)] = str

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
