from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    numbers = []

    # Only calibration-related number entities for Inputs
    for input_name in coordinator.controller.inputs.devices:
        numbers.append(CresInputCalibOffsetNumber(coordinator, input_name, entry))
        numbers.append(CresInputCalibFactorNumber(coordinator, input_name, entry))

    # Setup Number entities for Outputs
    for output_name in coordinator.controller.outputs.devices:
        numbers.append(CresOutputVoltageNumber(coordinator, output_name, entry))
        numbers.append(CresOutputCalibOffsetNumber(coordinator, output_name, entry))
        numbers.append(CresOutputCalibFactorNumber(coordinator, output_name, entry))
        numbers.append(CresOutputThresholdNumber(coordinator,output_name,entry))
        
        # Add PWM-specific numbers only for 'a' and 'b'
        if output_name in ["a", "b"]:
            numbers.append(
                CresOutputPWMFrequencyNumber(coordinator, output_name, entry)
            )

    # Setup Number entities for Switches
    for switch_name in ["12v", "24v-a", "24v-b"]:
        numbers.append(CresSwitchDutyCycleNumber(coordinator, switch_name, entry))
        numbers.append(CresSwitchPWMFrequencyNumber(coordinator, switch_name, entry))

    # Add MinDutyCycle for Fan directly
    numbers.append(CresFanMinDutyCycleNumber(coordinator, "fan", entry))

    async_add_entities(numbers)


class CresControlNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, device_name, entry, device_type):
        super().__init__(coordinator)
        self._device_name = device_name.lower()  
        self._entry = entry
        self._device_type = device_type

    @property
    def device_info(self):
        """Return device information about this entity."""
        device_id_normalized = self._device_name.lower()  

        if self._device_type == "input":
            device_id = f"{DOMAIN}_input_{device_id_normalized}"
            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": f"Input {device_id_normalized.upper()}",
                "manufacturer": "cre.sience",
                "model": "CresControl Input",
                "sw_version": "1.0",
            }
        elif self._device_type == "switch":
            device_id = f"{DOMAIN}_{device_id_normalized}_device"
            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": f"Switch {device_id_normalized.capitalize()}",
                "manufacturer": "cre.sience",
                "model": "CresControl Switch",
                "sw_version": "1.0",
            }
        elif self._device_type == "fan":
            device_id = f"{DOMAIN}_fan_device"
            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": "CresControl Fan",
                "manufacturer": "cre.sience",
                "model": "Fan",
                "sw_version": "1.0",
            }
        elif self._device_type == "output":
            device_id = f"{DOMAIN}_{self._device_type}_{device_id_normalized}_device"
            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": f"{self._device_type.capitalize()} {device_id_normalized.capitalize()}",
                "manufacturer": "cre.sience",
                "model": f"CresControl {self._device_type.capitalize()}",
                "sw_version": "1.0",
            }            
        else:
            device_id = f"{DOMAIN}_{self._device_type}_{device_id_normalized}_device"
            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": f"{self._device_type.capitalize()} {device_id_normalized.capitalize()}",
                "manufacturer": "cre.sience",
                "model": f"CresControl {self._device_type.capitalize()}",
                "sw_version": "1.0",
            }

    @property
    def unique_id(self):
        return f"crescontrol_{self._device_type}_{self._device_name}_number"

def safe_float_conversion(value, entity_name, attribute_name):
    """Converts a value to float and logs error if conversion fails."""
    try:
        if value is None or value == "":
            _LOGGER.error(
                f"Empty or None value for {entity_name} {attribute_name}, no default value will be used."
            )
            raise ValueError(f"No valid value for {entity_name} {attribute_name}")

        float_value = float(value)
        if attribute_name in ["Voltage"] and not (0 <= float_value <= 10):
            _LOGGER.error(
                f"Value out of range for {entity_name} {attribute_name}: '{value}'. Expected range 0-10."
            )
            raise ValueError(f"Value out of range for {entity_name} {attribute_name}")
        elif attribute_name not in ["Voltage"] and not (0 <= float_value <= 100):
            _LOGGER.error(
                f"Value out of range for {entity_name} {attribute_name}: '{value}'. Expected range 0-100."
            )
            raise ValueError(f"Value out of range for {entity_name} {attribute_name}")

        return float_value
    except (ValueError, TypeError) as e:
        _LOGGER.error(
            f"Invalid float conversion value for {entity_name} {attribute_name}: '{value}'. Exception: {e}"
        )
        raise

class CresFanMinDutyCycleNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, device_name, entry):
        super().__init__(coordinator)
        self._device_name = device_name
        self._entry = entry

    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting fan {self._device_name} min duty cycle to {value}")
        await self.coordinator.controller.fan.setFanDutyCycleMin(value)
        await self.coordinator.async_update_single_device("fan")
        self.async_write_ha_state()
        
        
    @property
    def name(self):
        return f"DutyCycle Min "

    @property
    def unique_id(self):
        return f"crescontrol_{self._device_name}_min_duty_cycle"

    @property
    def value(self):
        # Zugreifen auf die neuesten Fan-Daten vom Coordinator
        raw_value = self.coordinator.data["fan"].get("minDutyCycle", 0)
        return raw_value


    @property
    def device_info(self):
        """Return device information about this entity."""
        device_id = f"{DOMAIN}_fan_device"
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": "CresControl Fan",
            "manufacturer": "cre.sience",
            "model": "CresControl Fan",
            "sw_version": "1.0",
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100
    
    @property
    def step(self):
        return 0.1
    
    @property
    def unit_of_measurement(self):
        return "%"

class CresInputCalibOffsetNumber(CresControlNumber):
    def __init__(self, coordinator, input_name, entry):
        super().__init__(coordinator, input_name, entry, "input")
        self._input_name = input_name

    @property
    def name(self):
        return f"Input {self._input_name} Calib-Offset"

    @property
    def unique_id(self):
        return f"crescontrol_input_{self._input_name}_calib_offset"

    @property
    def value(self):
        raw_value = self.coordinator.controller.inputs.inputs_data[self._input_name][
            "calibOffset"
        ]
        return safe_float_conversion(
            raw_value, f"Input {self._input_name}", "Calib-Offset"
        )

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 10
    
    @property
    def step(self):
        return 0.1

    @property
    def unit_of_measurement(self):
        return "V"


    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting input {self._input_name} calibration offset to {value}")
        await self.coordinator.controller.inputs.set_input_calib_offset(
            self._input_name, value
        )
        await self.coordinator.async_request_refresh()

class CresInputCalibFactorNumber(CresControlNumber):
    def __init__(self, coordinator, input_name, entry):
        super().__init__(coordinator, input_name, entry, "input")
        self._input_name = input_name

    @property
    def name(self):
        return f"Input {self._input_name} Calib-Factor"

    @property
    def unique_id(self):
        return f"crescontrol_input_{self._input_name}_calib_factor"

    @property
    def value(self):
        raw_value = self.coordinator.controller.inputs.inputs_data[self._input_name][
            "calibFactor"
        ]
        return safe_float_conversion(
            raw_value, f"Input {self._input_name}", "Calib-Factor"
        )

    @property
    def min_value(self):
        return 1

    @property
    def max_value(self):
        return 10
    
    @property
    def step(self):
        return 0.1
    
    
    @property
    def unit_of_measurement(self):
        return "x"


    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting input {self._input_name} calibration factor to {value}")
        await self.coordinator.controller.inputs.set_input_calib_factor(
            self._input_name, value
        )
        await self.coordinator.async_request_refresh()

class CresOutputVoltageNumber(CresControlNumber):
    def __init__(self, coordinator, output_name, entry):
        super().__init__(coordinator, output_name, entry, "output")
        self._output_name = output_name

    @property
    def name(self):
        return f"Output {self._output_name} Voltage"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_voltage"

    @property
    def value(self):
        raw_value = self.coordinator.controller.outputs.outputs_data[self._output_name][
            "voltage"
        ]
        return safe_float_conversion(
            raw_value, f"Output {self._output_name}", "Voltage"
        )

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 10

    @property
    def step(self):
        return 0.1

    @property
    def unit_of_measurement(self):
        return "V"

    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} voltage to {value}")
        await self.coordinator.controller.outputs.set_output_voltage(
            self._output_name, value
        )
        await self.coordinator.async_request_refresh()

class CresOutputCalibOffsetNumber(CresControlNumber):
    def __init__(self, coordinator, output_name, entry):
        super().__init__(coordinator, output_name, entry, "output")
        self._output_name = output_name

    @property
    def name(self):
        return f"Output {self._output_name} Calib-Offset"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_calib_offset"

    @property
    def value(self):
        raw_value = self.coordinator.controller.outputs.outputs_data[self._output_name][
            "calibOffset"
        ]
        return safe_float_conversion(
            raw_value, f"Output {self._output_name}", "Calib-Offset"
        )

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 10

    @property
    def step(self):
        return 0.1

    @property
    def unit_of_measurement(self):
        return "V"

    @property
    def step(self):
        return 0.1

    async def async_set_value(self, value: float):
        _LOGGER.debug(
            f"Setting output {self._output_name} calibration offset to {value}"
        )
        await self.coordinator.controller.outputs.set_output_calib_offset(
            self._output_name, value
        )
        await self.coordinator.async_request_refresh()

class CresOutputCalibFactorNumber(CresControlNumber):
    def __init__(self, coordinator, output_name, entry):
        super().__init__(coordinator, output_name, entry, "output")
        self._output_name = output_name

    @property
    def name(self):
        return f"Output {self._output_name} Calib-Factor"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_calib_factor"

    @property
    def value(self):
        raw_value = self.coordinator.controller.outputs.outputs_data[
            self._output_name
        ].get("calibFactor", "")
        return safe_float_conversion(
            raw_value, f"Output {self._output_name}", "Calib-Factor"
        )

    @property
    def min_value(self):
        return 1  

    @property
    def max_value(self):
        return 10  

    @property
    def step(self):
        return 0.1

    @property
    def unit_of_measurement(self):
        return "x"

    async def async_set_value(self, value: float):
        _LOGGER.debug(
            f"Setting output {self._output_name} calibration factor to {value}"
        )
        await self.coordinator.controller.outputs.set_output_calib_factor(
            self._output_name, value
        )
        await self.coordinator.async_request_refresh()

class CresSwitchDutyCycleNumber(CresControlNumber):
    def __init__(self, coordinator, switch_name, entry):
        super().__init__(coordinator, switch_name, entry, "switch")
        self._switch_name = switch_name

    @property
    def name(self):
        return f"Switch {self._switch_name} Duty Cycle"

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_duty_cycle"

    @property
    def value(self):
        raw_value = self.coordinator.controller.switches.switch_data[
            self._switch_name
        ]["duty-cycle"]
        return safe_float_conversion(
            raw_value, f"Switch {self._switch_name}", "Duty Cycle"
        )

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def unit_of_measurement(self):
        return "%"

    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting switch {self._switch_name} duty cycle to {value}")
        await self.coordinator.controller.switches.set_duty_cycle(
            self._switch_name, value
        )
        await self.coordinator.async_request_refresh()

class CresOutputPWMFrequencyNumber(CresControlNumber):
    def __init__(self, coordinator, output_name, entry):
        super().__init__(coordinator, output_name, entry, "output")
        self._output_name = output_name

    @property
    def name(self):
        return f"Output {self._output_name} PWM Frequency"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_pwm_frequency"

    @property
    def value(self):
        raw_value = self.coordinator.controller.outputs.outputs_data[
            self._output_name
        ].get("pwmFrequency", 0)
        
        
        converted_value = safe_float_conversion(
            raw_value, f"Output {self._output_name}", "PWM Frequency"
        )
        
        
        if converted_value < self.min_value:
            _LOGGER.warning(
                f"PWM Frequency für Output {self._output_name} ist unter dem minimalen Wert {self.min_value} Hz. Setze auf {self.min_value} Hz."
            )
            return self.min_value
        
        return converted_value

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 1000

    @property
    def step(self):
        return 1

    @property
    def unit_of_measurement(self):
        return "Hz"

    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} PWM frequency to {value}")
        await self.coordinator.controller.outputs.set_output_pwm_frequency(
            self._output_name, value
        )
        await self.coordinator.async_request_refresh()

class CresSwitchPWMFrequencyNumber(CresControlNumber):
    def __init__(self, coordinator, switch_name, entry):
        super().__init__(coordinator, switch_name, entry, "switch")
        self._switch_name = switch_name

    @property
    def name(self):
        return f"Switch {self._switch_name} PWM Frequency"

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_pwm_frequency"

    @property
    def value(self):
        raw_value = self.coordinator.controller.switches.switch_data[
            self._switch_name
        ].get("pwm-frequency", 0)
        
       
        converted_value = safe_float_conversion(
            raw_value, f"Switch {self._switch_name}", "PWM Frequency"
        )
        
        
        if converted_value < self.min_value:
            _LOGGER.warning(
                f"PWM Frequency für Switch {self._switch_name} ist unter dem minimalen Wert {self.min_value} Hz. Setze auf {self.min_value} Hz."
            )
            return self.min_value
        
        return converted_value

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 1000
    
    @property
    def step(self):
        return 1

    @property
    def unit_of_measurement(self):
        return "Hz"

    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting switch {self._switch_name} PWM frequency to {value}")
        await self.coordinator.controller.switches.set_pwm_frequency(
            self._switch_name, value
        )
        await self.coordinator.async_request_refresh()

class CresSwitchPWMEnabledNumber(CresControlNumber):
    def __init__(self, coordinator, switch_name, entry):
        super().__init__(coordinator, switch_name, entry, "switch")
        self._switch_name = switch_name

    @property
    def name(self):
        return f"Switch {self._switch_name} PWM Enabled"

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_pwm_enabled"

    @property
    def value(self):
        raw_value = self.coordinator.controller.switches.switch_data[
            self._switch_name
        ].get("pwm-enabled", 0)
        return safe_float_conversion(
            raw_value, f"Switch {self._switch_name}", "PWM Enabled"
        )

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 1

    async def async_set_value(self, value: float):
        pwm_enabled = value > 0.5
        _LOGGER.debug(
            f"Setting switch {self._switch_name} PWM enabled to {pwm_enabled}"
        )
        await self.coordinator.controller.switches.set_pwm_enabled(
            self._switch_name, pwm_enabled
        )
        await self.coordinator.async_request_refresh()

class CresOutputThresholdNumber(CresControlNumber):
    def __init__(self, coordinator, output_name, entry):
        super().__init__(coordinator, output_name, entry, "output")
        self._output_name = output_name

    @property
    def name(self):
        return f"Output {self._output_name} Threshold"

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_threshold"

    @property
    def value(self):
        
        raw_value = self.coordinator.controller.outputs.outputs_data[self._output_name].get(
            "threshold", 0
        )
        return safe_float_conversion(
            raw_value, f"Output {self._output_name}", "Threshold"
        )

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100
    
    @property
    def step(self):
        return 0.1

    @property
    def unit_of_measurement(self):
        return "V"

    async def async_set_value(self, value: float):
        _LOGGER.debug(f"Setting output {self._output_name} threshold to {value}")
        await self.coordinator.controller.outputs.set_output_threshold(self._output_name, value)
        await self.coordinator.async_request_refresh()
