from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from custom_components.crescontrol.const import (
    DOMAIN,
    CONF_OUTPUTS,
    CONF_SWITCHES,
    CONF_INPUTS,
    CONF_FAN,
    ENTITY_TYPE_NUMBER,
    PWM_OUTPUTS,
    INPUT_CHANNELS,
    SWITCH_CHANNELS,
)
import logging

_LOGGER = logging.getLogger(__name__)


def _get_configured_name(entry, channel_type, channel_name):
    """Get the configured name for a channel from the config entry."""
    config = entry.data.get(channel_type, {})
    cfg = config.get(channel_name, {})
    return cfg.get("name", f"{channel_type.capitalize()}{channel_name.upper()}")


def _get_output_suffix(entity_type, base_suffix):
    """Get the appropriate suffix for an output number entity based on configured type."""
    if base_suffix == "Voltage":
        if entity_type == "light":
            return "Intensity"
        elif entity_type == "fan":
            return "Duty"
        else:
            return "Voltage"
    elif base_suffix == "PWMFreq":
        if entity_type == "light":
            return "IntensityPWMFreq"
        elif entity_type == "fan":
            return "DutyPWMFreq"
        else:
            return "PWMFreq"
    return base_suffix


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CresControl number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    numbers = []

    output_config = entry.data.get(CONF_OUTPUTS, {})
    switch_config = entry.data.get(CONF_SWITCHES, {})
    input_config = entry.data.get(CONF_INPUTS, {})
    fan_config = entry.data.get(CONF_FAN, {})

    # Number entities for outputs configured as number (manual control)
    for output_name, cfg in output_config.items():
        if cfg.get("type") == ENTITY_TYPE_NUMBER:
            configured_name = _get_configured_name(entry, CONF_OUTPUTS, output_name)
            numbers.append(CresOutputManualNumber(coordinator, output_name, entry, configured_name))

    # Number entities for switches configured as number (manual duty cycle control)
    for switch_name, cfg in switch_config.items():
        if cfg.get("type") == ENTITY_TYPE_NUMBER:
            configured_name = _get_configured_name(entry, CONF_SWITCHES, switch_name)
            numbers.append(CresSwitchManualNumber(coordinator, switch_name, entry, configured_name))

    # Calibration and config numbers for active outputs
    for output_name, cfg in output_config.items():
        entity_type = cfg.get("type", "")
        if entity_type != "none" and entity_type != "":
            configured_name = _get_configured_name(entry, CONF_OUTPUTS, output_name)
            # Only add voltage number for switch/number types (light/fan use brightness/speed)
            if entity_type in ["switch", "number"]:
                numbers.append(CresOutputVoltageNumber(coordinator, output_name, entry, configured_name, entity_type))
            numbers.append(CresOutputCalibOffsetNumber(coordinator, output_name, entry, configured_name))
            numbers.append(CresOutputCalibFactorNumber(coordinator, output_name, entry, configured_name))
            numbers.append(CresOutputThresholdNumber(coordinator, output_name, entry, configured_name))
            if output_name in PWM_OUTPUTS:
                numbers.append(CresOutputPWMFrequencyNumber(coordinator, output_name, entry, configured_name, entity_type))

    # Calibration and config numbers for active switches
    for switch_name, cfg in switch_config.items():
        entity_type = cfg.get("type", "")
        if entity_type != "none" and entity_type != "":
            configured_name = _get_configured_name(entry, CONF_SWITCHES, switch_name)
            numbers.append(CresSwitchDutyCycleNumber(coordinator, switch_name, entry, configured_name))
            numbers.append(CresSwitchPWMFrequencyNumber(coordinator, switch_name, entry, configured_name))

    # Calibration numbers for active inputs
    for input_name, cfg in input_config.items():
        sensor_type = cfg.get("type", "")
        if sensor_type != "none" and sensor_type != "":
            configured_name = _get_configured_name(entry, CONF_INPUTS, input_name)
            numbers.append(CresInputCalibOffsetNumber(coordinator, input_name, entry, configured_name))
            numbers.append(CresInputCalibFactorNumber(coordinator, input_name, entry, configured_name))

    # Fan min duty cycle if fan is enabled
    if fan_config.get("enabled", False):
        configured_name = _get_configured_name(entry, CONF_FAN, "fan")
        numbers.append(CresFanMinDutyCycleNumber(coordinator, "fan", entry, configured_name))

    async_add_entities(numbers)
    _LOGGER.info(f"Added {len(numbers)} number entities")


def safe_float_conversion(value, entity_name, attribute_name):
    """Converts a value to float and logs error if conversion fails."""
    try:
        if value is None or value == "":
            _LOGGER.error(
                f"Empty or None value for {entity_name} {attribute_name}"
            )
            return 0.0

        float_value = float(value)
        if attribute_name == "Voltage" and not (0 <= float_value <= 10):
            _LOGGER.warning(
                f"Value out of range for {entity_name} {attribute_name}: '{value}'. Expected range 0-10."
            )
            return max(0, min(10, float_value))
        elif attribute_name not in ["Voltage", "PWM Frequency", "Calib-Offset", "Calib-Factor", "Threshold"] and not (0 <= float_value <= 100):
            _LOGGER.warning(
                f"Value out of range for {entity_name} {attribute_name}: '{value}'. Expected range 0-100."
            )
            return max(0, min(100, float_value))

        return float_value
    except (ValueError, TypeError) as e:
        _LOGGER.error(
            f"Invalid float conversion value for {entity_name} {attribute_name}: '{value}'. Exception: {e}"
        )
        return 0.0


class CresOutputManualNumber(CoordinatorEntity, NumberEntity):
    """Manual number entity for CresControl outputs."""

    def __init__(self, coordinator, output_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._configured_name = configured_name or f"Output{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        voltage = output_data.get("voltage", 0)
        try:
            self._attr_native_value = float(voltage)
        except (ValueError, TypeError):
            self._attr_native_value = 0

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "outputs" not in self.coordinator.subsystem_failures)

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_manual_{self._entry.entry_id}"

    @property
    def name(self):
        return f"{self._configured_name}Manual"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Manual",
            "sw_version": "1.0",
        }

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 10

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "V"

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} manual voltage to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.outputs.set_output_voltage(
            self._output_name, value
        )
        # Enable PWM for PWM-capable outputs when manually setting voltage
        if self._output_name in ["a", "b"]:
            await self.coordinator.controller.outputs.set_output_pwm_enabled(
                self._output_name, True
            )


class CresSwitchManualNumber(CoordinatorEntity, NumberEntity):
    """Manual number entity for CresControl switches."""

    def __init__(self, coordinator, switch_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._configured_name = configured_name or f"Switch{switch_name.upper()}"
        self._device_id = f"{DOMAIN}_{switch_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        switch_data = self.coordinator.data.get("switches", {}).get(self._switch_name, {})
        duty_cycle = switch_data.get("duty-cycle", 0)
        try:
            self._attr_native_value = float(duty_cycle)
        except (ValueError, TypeError):
            self._attr_native_value = 0

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "switches" not in self.coordinator.subsystem_failures)

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_manual_{self._entry.entry_id}"

    @property
    def name(self):
        return f"{self._configured_name}Manual"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Manual",
            "sw_version": "1.0",
        }

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 100

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "%"

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting switch {self._switch_name} manual duty cycle to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.switches.set_duty_cycle(
            self._switch_name, value
        )


class CresFanMinDutyCycleNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, device_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._device_name = device_name
        self._entry = entry
        self._configured_name = configured_name or "Ventilation"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        fan_data = self.coordinator.data.get("fan", {})
        self._attr_native_value = fan_data.get("minDutyCycle", 0)

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "fan" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}MinDutyCycle"

    @property
    def unique_id(self):
        return f"crescontrol_{self._device_name}_min_duty_cycle_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def device_info(self):
        device_id = f"{DOMAIN}_fan_device"
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Fan",
            "sw_version": "1.0",
        }

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 100

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "%"

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting fan {self._device_name} min duty cycle to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.fan.setFanDutyCycleMin(value)


class CresInputCalibOffsetNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, input_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._input_name = input_name
        self._entry = entry
        self._configured_name = configured_name or f"Input{input_name.upper()}"
        self._device_id = f"{DOMAIN}_input_{input_name}"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        input_data = self.coordinator.data.get("inputs", {}).get(self._input_name, {})
        raw_value = input_data.get("calibOffset", 0)
        self._attr_native_value = safe_float_conversion(raw_value, f"Input {self._input_name}", "Calib-Offset")

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "inputs" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}CalibOffset"

    @property
    def unique_id(self):
        return f"crescontrol_input_{self._input_name}_calib_offset_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 10

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "V"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Input",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting input {self._input_name} calibration offset to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.inputs.set_input_calib_offset(
            self._input_name, value
        )


class CresInputCalibFactorNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, input_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._input_name = input_name
        self._entry = entry
        self._configured_name = configured_name or f"Input{input_name.upper()}"
        self._device_id = f"{DOMAIN}_input_{input_name}"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 1
            return
        input_data = self.coordinator.data.get("inputs", {}).get(self._input_name, {})
        raw_value = input_data.get("calibFactor", 1)
        self._attr_native_value = safe_float_conversion(raw_value, f"Input {self._input_name}", "Calib-Factor")

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "inputs" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}CalibFactor"

    @property
    def unique_id(self):
        return f"crescontrol_input_{self._input_name}_calib_factor_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 1

    @property
    def native_max_value(self):
        return 10

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "x"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Input",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting input {self._input_name} calibration factor to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.inputs.set_input_calib_factor(
            self._input_name, value
        )


class CresOutputVoltageNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, output_name, entry, configured_name=None, entity_type="switch"):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._configured_name = configured_name or f"Output{output_name.upper()}"
        self._entity_type = entity_type
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        # Check if this is a percentage-based control (light/fan) or voltage-based (switch)
        self._is_percentage = entity_type in ["light", "fan"]
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        raw_value = output_data.get("voltage", 0)
        voltage = safe_float_conversion(raw_value, f"Output {self._output_name}", "Voltage")
        if self._is_percentage:
            self._attr_native_value = min(100, max(0, voltage * 10))
        else:
            self._attr_native_value = voltage

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "outputs" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        suffix = _get_output_suffix(self._entity_type, "Voltage")
        return f"{self._configured_name}{suffix}"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_voltage_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 100 if self._is_percentage else 10

    @property
    def native_step(self):
        return 1 if self._is_percentage else 0.1

    @property
    def native_unit_of_measurement(self):
        return "%" if self._is_percentage else "V"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Output",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        if self._is_percentage:
            # Convert percentage back to voltage for the API
            voltage = value / 10.0
            _LOGGER.debug(f"Setting output {self._output_name} intensity to {value}% (voltage: {voltage}V)")
        else:
            voltage = value
            _LOGGER.debug(f"Setting output {self._output_name} voltage to {voltage}V")
        
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.outputs.set_output_voltage(
            self._output_name, voltage
        )


class CresOutputCalibOffsetNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, output_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._configured_name = configured_name or f"Output{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        raw_value = output_data.get("calibOffset", 0)
        self._attr_native_value = safe_float_conversion(raw_value, f"Output {self._output_name}", "Calib-Offset")

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "outputs" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}CalibOffset"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_calib_offset_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 10

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "V"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Output",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} calibration offset to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.outputs.set_output_calib_offset(
            self._output_name, value
        )


class CresOutputCalibFactorNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, output_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._configured_name = configured_name or f"Output{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 1
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        raw_value = output_data.get("calibFactor", 1)
        self._attr_native_value = safe_float_conversion(raw_value, f"Output {self._output_name}", "Calib-Factor")

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "outputs" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}CalibFactor"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_calib_factor_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 1

    @property
    def native_max_value(self):
        return 10

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "x"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Output",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} calibration factor to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.outputs.set_output_calib_factor(
            self._output_name, value
        )


class CresOutputThresholdNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, output_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._configured_name = configured_name or f"Output{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        raw_value = output_data.get("threshold", 0)
        self._attr_native_value = safe_float_conversion(raw_value, f"Output {self._output_name}", "Threshold")

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "outputs" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}Threshold"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_threshold_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 100

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "V"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Output",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} threshold to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.outputs.set_output_threshold(self._output_name, value)


class CresOutputPWMFrequencyNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, output_name, entry, configured_name=None, entity_type="switch"):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._configured_name = configured_name or f"Output{output_name.upper()}"
        self._entity_type = entity_type
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        raw_value = output_data.get("pwmFrequency", 0)
        converted_value = safe_float_conversion(raw_value, f"Output {self._output_name}", "PWM Frequency")
        if converted_value <= 0:
            self._attr_native_value = 0
        else:
            self._attr_native_value = converted_value

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "outputs" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        suffix = _get_output_suffix(self._entity_type, "PWMFreq")
        return f"{self._configured_name}{suffix}"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_pwm_frequency_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 5000

    @property
    def native_step(self):
        return 1

    @property
    def native_unit_of_measurement(self):
        return "Hz"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Output PWM",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} PWM frequency to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.outputs.set_output_pwm_frequency(
            self._output_name, value
        )


class CresSwitchDutyCycleNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, switch_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._configured_name = configured_name or f"Switch{switch_name.upper()}"
        self._device_id = f"{DOMAIN}_{switch_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        switch_data = self.coordinator.data.get("switches", {}).get(self._switch_name, {})
        raw_value = switch_data.get("duty-cycle", 0)
        self._attr_native_value = safe_float_conversion(raw_value, f"Switch {self._switch_name}", "Duty Cycle")

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "switches" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}DutyCycle"

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_duty_cycle_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 100

    @property
    def native_step(self):
        return 0.1

    @property
    def native_unit_of_measurement(self):
        return "%"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Switch",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting switch {self._switch_name} duty cycle to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.switches.set_duty_cycle(
            self._switch_name, value
        )


class CresSwitchPWMFrequencyNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, switch_name, entry, configured_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._configured_name = configured_name or f"Switch{switch_name.upper()}"
        self._device_id = f"{DOMAIN}_{switch_name}_device"
        self._attr_native_value = None

    def _update_from_coordinator(self):
        if not self.coordinator.data:
            self._attr_native_value = 0
            return
        switch_data = self.coordinator.data.get("switches", {}).get(self._switch_name, {})
        raw_value = switch_data.get("pwm-frequency", 0)
        converted_value = safe_float_conversion(raw_value, f"Switch {self._switch_name}", "PWM Frequency")
        if converted_value <= 0:
            self._attr_native_value = 0
        else:
            self._attr_native_value = converted_value

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "switches" not in self.coordinator.subsystem_failures)

    @property
    def name(self):
        return f"{self._configured_name}PWMFreq"

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_pwm_frequency_{self._entry.entry_id}"

    @property
    def native_value(self):
        if self._attr_native_value is not None:
            return self._attr_native_value
        self._update_from_coordinator()
        return self._attr_native_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 5000

    @property
    def native_step(self):
        return 1

    @property
    def native_unit_of_measurement(self):
        return "Hz"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._configured_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Switch PWM",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float):
        _LOGGER.debug(f"Setting switch {self._switch_name} PWM frequency to {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.controller.switches.set_pwm_frequency(
            self._switch_name, value
        )
