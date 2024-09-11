from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfTemperature, PERCENTAGE, CONCENTRATION_PARTS_PER_MILLION
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "temperature": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer", "device_class": "temperature"},
    "humidity": {"unit": PERCENTAGE, "icon": "mdi:water-percent", "device_class": "humidity"},
    "vpd": {"unit": "kPa", "icon": "mdi:thermometer", "device_class": None},
    "co2": {"unit": CONCENTRATION_PARTS_PER_MILLION, "icon": "mdi:carbon-dioxide", "device_class": "carbon_dioxide"},
    "voltage": {"unit": "V", "icon": "mdi:flash", "device_class": None},
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    sensors = {}

    _LOGGER.debug(f"Starting setup of sensors. Coordinator data: {coordinator.data}")

    # Loop through all devices and add the appropriate sensors or inputs
    for device in coordinator.controller.devices:
        device_id_normalized = device.device_id.lower()

        # Handle sensor devices (e.g., temperature, humidity, vpd, co2)
        if device.device_type == "sensor":
            _LOGGER.debug(f"Detected sensor device: {device.device_id}")
            for sensor_type in ["temperature", "humidity", "vpd", "co2"]:
                if sensor_type in device.state:
                    entity_id = f"{device_id_normalized}_{sensor_type}"
                    if entity_id not in sensors:
                        sensors[entity_id] = CresSensorEntity(
                            device, sensor_type, coordinator, entry
                        )

        # Handle input devices (e.g., voltage)
        elif device.device_type == "input":
            _LOGGER.debug(f"Detected input device: {device.device_id}")
            entity_id = f"{device_id_normalized}_voltage"
            if entity_id not in sensors:
                sensors[entity_id] = CresInputVoltageEntity(device, coordinator, entry)

    if not sensors:
        _LOGGER.error("No sensors found to add to Home Assistant")

    async_add_entities(sensors.values())
    _LOGGER.debug(f"Sensors added to Home Assistant: {list(sensors.keys())}")

# Sensor Entities for the different sensor types

class CresSensorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, device, sensor_type, coordinator, entry):
        super().__init__(coordinator)
        self._device = device
        self._sensor_type = sensor_type
        self._entry = entry

        _LOGGER.debug(
            f"Initialized CresSensorEntity for {self._device.device_id} with type {self._sensor_type}"
        )

    @property
    def unique_id(self):
        normalized_device_id = self._device.device_id.lower()
        return f"crescontrol_sensor_{normalized_device_id}_{self._sensor_type}_{self._entry.entry_id}"

    @property
    def device_info(self):
        normalized_device_id = self._device.device_id.lower()
        return {
            "identifiers": {(DOMAIN, normalized_device_id)},
            "name": f"{normalized_device_id.capitalize()}",
            "manufacturer": "cre.sience",
            "model": "CresControl Sensor",
            "sw_version": "1.0",
        }

    def _get_state_from_coordinator(self):
        """Fetch the state from the coordinator data."""
        # Fetch sensor data from the coordinator
        sensor_data = self.coordinator.data.get("sensors", {})
        state = sensor_data.get(self._device.device_id, {}).get(self._sensor_type)
        
        if state is None:
            _LOGGER.error(
                f"No state found for sensor {self._device.device_id} of type {self._sensor_type}"
            )
            return None

        _LOGGER.debug(
            f"Fetched state {state} from coordinator for sensor {self._device.device_id} of type {self._sensor_type}"
        )
        return float(state) if state is not None else None

    @property
    def name(self):
        normalized_device_id = self._device.device_id.lower()
        return f"{normalized_device_id.capitalize()} {self._sensor_type.capitalize()}"

    @property
    def state(self):
        # Fetch and return state from the coordinator
        return self._get_state_from_coordinator()

    @property
    def unit_of_measurement(self):
        return SENSOR_TYPES[self._sensor_type]["unit"]

    @property
    def device_class(self):
        return SENSOR_TYPES[self._sensor_type]["device_class"]

    @property
    def icon(self):
        return SENSOR_TYPES[self._sensor_type]["icon"]

    async def async_update(self):
        await self.coordinator.async_request_refresh()
        _LOGGER.debug(
            f"Updating sensor {self._device.device_id} of type {self._sensor_type}"
        )
# Input Voltage Entity

class CresInputVoltageEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, device, coordinator, entry):
        super().__init__(coordinator)
        self._device = device
        self._entry = entry

    @property
    def unique_id(self):
        normalized_device_id = self._device.device_id.lower()
        return f"crescontrol_input_{normalized_device_id}_voltage"

    @property
    def device_info(self):
        normalized_device_id = self._device.device_id.lower()
        return {
            "identifiers": {(DOMAIN, f"{DOMAIN}_input_{normalized_device_id}")},
            "name": f"Input {normalized_device_id.upper()}",
            "manufacturer": "cre.sience",
            "model": "CresControl Input",
            "sw_version": "1.0",
        }

    def _get_state_from_coordinator(self):
        """Fetch the state from the coordinator data."""
        input_data = self.coordinator.data.get("inputs", {})
        state = input_data.get(self._device.device_id, {}).get("voltage")
        _LOGGER.debug(f"State from coordinator for input {self._device.device_id}, state: {state}")
        return state

    @property
    def name(self):
        normalized_device_id = self._device.device_id.lower()
        return f"Input {normalized_device_id.upper()} Voltage"

    @property
    def state(self):
        state = self._get_state_from_coordinator()
        _LOGGER.debug(f"Getting voltage state for {self._device.device_id}, state: {state}")
        return state

    @property
    def unit_of_measurement(self):
        return "V"
