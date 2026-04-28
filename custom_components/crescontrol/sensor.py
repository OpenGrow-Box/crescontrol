from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfTemperature, PERCENTAGE, CONCENTRATION_PARTS_PER_MILLION
from custom_components.crescontrol.const import (
    DOMAIN,
    CONF_INPUTS,
    CONF_OUTPUTS,
    SENSOR_TYPE_NONE,
    PWM_OUTPUTS,
)
import logging

_LOGGER = logging.getLogger(__name__)

# Sensor type configurations
SENSOR_CONFIGS = {
    "voltage": {"unit": "V", "icon": "mdi:flash", "device_class": "voltage"},
    "temperature": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer", "device_class": "temperature"},
    "humidity": {"unit": PERCENTAGE, "icon": "mdi:water-percent", "device_class": "humidity"},
    "pressure": {"unit": "hPa", "icon": "mdi:gauge", "device_class": "pressure"},
    "co2": {"unit": CONCENTRATION_PARTS_PER_MILLION, "icon": "mdi:molecule-co2", "device_class": "carbon_dioxide"},
    "ec": {"unit": "mS/cm", "icon": "mdi:water-opacity", "device_class": None},
    "ph": {"unit": "pH", "icon": "mdi:ph", "device_class": None},
}

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CresControl sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    sensors = []

    input_config = entry.data.get(CONF_INPUTS, {})

    # Create sensors for built-in sensor devices (temperature, humidity, vpd, co2)
    # Only create sensor entities if the sensor actually has data for that type
    for device in coordinator.controller.devices:
        if device.device_type == "sensor":
            _LOGGER.debug(f"Detected sensor device: {device.device_id}")
            # Check what data this sensor actually has
            sensor_data = coordinator.controller.sensors.sensor_data.get(device.device_id, {})
            for sensor_type in ["temperature", "humidity", "vpd", "co2"]:
                # Only create entity if sensor has actual data for this type
                if sensor_type in sensor_data and sensor_data[sensor_type] is not None:
                    entity_id = f"{device.device_id.lower()}_{sensor_type}"
                    if entity_id not in [s.unique_id for s in sensors]:
                        sensors.append(
                            CresSensorEntity(device, sensor_type, coordinator, entry)
                        )

    # Create sensors for input devices based on configuration
    for input_name, cfg in input_config.items():
        configured_type = cfg.get("type", SENSOR_TYPE_NONE)
        if configured_type == SENSOR_TYPE_NONE:
            continue

        custom_name = cfg.get("name", f"Input{input_name.upper()}")

        _LOGGER.debug(f"Creating sensor for input {input_name} as {configured_type}")
        sensors.append(
            CresInputSensorEntity(
                input_name, configured_type, coordinator, entry, custom_name
            )
        )

    # Create status sensors for outputs configured as light or fan
    output_config = entry.data.get(CONF_OUTPUTS, {})
    for output_name, cfg in output_config.items():
        entity_type = cfg.get("type", "")
        if entity_type in ["light", "fan"]:
            custom_name = cfg.get("name", f"{entity_type.capitalize()}{output_name.upper()}")
            sensors.append(
                CresOutputStatusSensor(
                    output_name, entity_type, coordinator, entry, custom_name
                )
            )
            _LOGGER.debug(f"Creating status sensor for output {output_name} as {entity_type}")

    async_add_entities(sensors)
    _LOGGER.info(f"Added {len(sensors)} sensor entities")


class CresSensorEntity(CoordinatorEntity, SensorEntity):
    """Sensor entity for CresControl built-in sensors."""

    def __init__(self, device, sensor_type, coordinator, entry):
        super().__init__(coordinator)
        self._device = device
        self._sensor_type = sensor_type
        self._entry = entry
        normalized_device_id = device.device_id.lower()
        self._device_id = f"{DOMAIN}_{normalized_device_id}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        normalized_device_id = self._device.device_id.lower()
        return f"crescontrol_sensor_{normalized_device_id}_{self._sensor_type}_{self._entry.entry_id}"

    @property
    def name(self):
        normalized_device_id = self._device.device_id.lower()
        return f"{normalized_device_id.capitalize()}_{self._sensor_type.capitalize()}"

    @property
    def device_info(self):
        normalized_device_id = self._device.device_id.lower()
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"{normalized_device_id.capitalize()}",
            "manufacturer": "cre.sience",
            "model": "CresControl Sensor",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        return {
            "sensor_type": self._sensor_type,
        }

    def _get_state_from_coordinator(self):
        if not self.coordinator.data:
            return None
        sensor_data = self.coordinator.data.get("sensors", {})
        state = sensor_data.get(self._device.device_id, {}).get(self._sensor_type)
        if state is None:
            return None
        try:
            return float(state)
        except (ValueError, TypeError):
            return None

    @property
    def state(self):
        return self._get_state_from_coordinator()

    @property
    def unit_of_measurement(self):
        if self._sensor_type == "temperature":
            return UnitOfTemperature.CELSIUS
        elif self._sensor_type == "humidity":
            return PERCENTAGE
        elif self._sensor_type == "co2":
            return CONCENTRATION_PARTS_PER_MILLION
        elif self._sensor_type == "vpd":
            return "kPa"
        return None

    @property
    def icon(self):
        icons = {
            "temperature": "mdi:thermometer",
            "humidity": "mdi:water-percent",
            "vpd": "mdi:water",
            "co2": "mdi:molecule-co2",
        }
        return icons.get(self._sensor_type, "mdi:help-circle")


class CresInputSensorEntity(CoordinatorEntity, SensorEntity):
    """Sensor entity for CresControl analog inputs."""

    def __init__(self, input_name, sensor_type, coordinator, entry, custom_name=None):
        super().__init__(coordinator)
        self._input_name = input_name
        self._sensor_type = sensor_type
        self._entry = entry
        self._config = SENSOR_CONFIGS.get(sensor_type, SENSOR_CONFIGS["voltage"])
        self._custom_name = custom_name or f"Input{input_name.upper()}"
        self._device_id = f"{DOMAIN}_input_{input_name}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_input_{self._input_name}_{self._sensor_type}_{self._entry.entry_id}"

    @property
    def name(self):
        return f"{self._custom_name}{self._sensor_type.capitalize()}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._custom_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Input",
            "sw_version": "1.0",
        }

    def _get_raw_voltage(self):
        if not self.coordinator.data:
            return 0.0
        input_data = self.coordinator.data.get("inputs", {})
        voltage = input_data.get(self._input_name, {}).get("voltage", 0)
        try:
            return float(voltage)
        except (ValueError, TypeError):
            return 0.0

    @property
    def state(self):
        voltage = self._get_raw_voltage()
        # Apply conversion factors based on sensor type
        conversion_factors = {
            "voltage": 1.0,
            "temperature": 10.0,
            "humidity": 10.0,
            "pressure": 100.0,
            "co2": 200.0,
            "ec": 1.0,
            "ph": 1.4,
        }
        factor = conversion_factors.get(self._sensor_type, 1.0)
        value = voltage * factor
        return round(value, 2)

    @property
    def unit_of_measurement(self):
        return self._config.get("unit", "V")

    @property
    def device_class(self):
        return self._config.get("device_class")

    @property
    def icon(self):
        return self._config.get("icon", "mdi:flash")

    @property
    def extra_state_attributes(self):
        return {
            "input_channel": self._input_name,
            "raw_voltage": self._get_raw_voltage(),
            "sensor_type": self._sensor_type,
        }


class CresOutputStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity showing current intensity/duty for light/fan outputs."""

    def __init__(self, output_name, entity_type, coordinator, entry, custom_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entity_type = entity_type
        self._entry = entry
        self._custom_name = custom_name or f"{entity_type.capitalize()}{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        suffix = "intensity" if self._entity_type == "light" else "dutycycle"
        return f"crescontrol_output_{self._output_name}_{suffix}_{self._entry.entry_id}"

    @property
    def name(self):
        if self._entity_type == "light":
            return "Intensity"
        else:
            return "DutyCycle"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._custom_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Output",
            "sw_version": "1.0",
        }

    @property
    def unit_of_measurement(self):
        return "%"

    @property
    def icon(self):
        if self._entity_type == "light":
            return "mdi:brightness-6"
        return "mdi:fan"

    @property
    def state(self):
        if not self.coordinator.data:
            return 0
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        voltage = output_data.get("voltage", 0)
        enabled = output_data.get("enabled", False)
        
        if not enabled:
            return 0
            
        try:
            return min(100, max(0, float(voltage) * 10))
        except (ValueError, TypeError):
            return 0

    @property
    def extra_state_attributes(self):
        return {
            "output_channel": self._output_name,
            "entity_type": self._entity_type,
            "voltage": self.coordinator.data.get("outputs", {}).get(self._output_name, {}).get("voltage", 0) if self.coordinator.data else 0,
        }
