from dataclasses import dataclass
from datetime import timedelta
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .cres_control import CresControl, APIAuthError, DeviceType
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ExampleCoordinator(DataUpdateCoordinator):
    """Coordinator to manage the integration with the CresControl system."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, controller: CresControl) -> None:
        """Initialize the coordinator."""
        self.host = config_entry.data[CONF_HOST]
        self.poll_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self.controller = controller
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
        )

    async def async_update_data(self):
        """Fetch data from the API endpoint."""
        try:
            _LOGGER.debug("Updating CresControl data from API")

            # Initialize devices only if they haven't been initialized
            if not self.controller.devices:
                await self.controller.init_devices()

            # Update all devices with consolidated requests
            await self.controller.update_all()

            # Collect and organize data
            data = {
                "fan": self.collect_fan_data(),
                "switches": self.collect_switch_data(),
                "inputs": self.collect_input_data(),
                "outputs": self.collect_output_data(),
                "sensors": self.collect_sensor_data(),
            }

            _LOGGER.debug("Fetched data from CresControl: %s", data)
            return data

        except APIAuthError as err:
            _LOGGER.error("API Auth Error: %s", err)
            raise UpdateFailed("Authentication Error") from err
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed("Error communicating with API") from err

    async def async_update_single_device(self, device_id: str):
        """Update a specific device by its ID."""
        try:
            _LOGGER.debug(f"Updating device {device_id} from API")

            # Finde das entsprechende Gerät und aktualisiere es gezielt
            device = self.controller.get_device_by_id(device_id)
            if device:
                if device.device_type == DeviceType.SENSOR:
                    await self.controller.update_sensors()  # Aktualisiere alle Sensoren
                elif device.device_type == DeviceType.FAN:
                    await self.controller.update_fan()  # Aktualisiere den Lüfter
                elif device.device_type == DeviceType.INPUT:
                    await self.controller.update_inputs()  # Aktualisiere alle Eingaben
                elif device.device_type == DeviceType.OUTPUT:
                    await self.controller.update_outputs()  # Aktualisiere alle Ausgaben
                elif device.device_type == DeviceType.SWITCH:
                    await self.controller.update_switches()  # Aktualisiere alle Schalter
                else:
                    _LOGGER.warning(f"Device type {device.device_type} not recognized")
                return {device.device_id: device.state}
            else:
                _LOGGER.warning(f"Device with ID {device_id} not found")
                return {}
        except Exception as err:
            _LOGGER.error(f"Error updating device {device_id}: {err}")
            raise UpdateFailed(f"Error updating device {device_id}") from err

    def collect_fan_data(self):
        """Collect fan data from the CresControl object."""
        fan_device = self.controller.get_device_by_id("fan")
        if fan_device:
            return fan_device.state
        return {}

    def collect_switch_data(self):
        """Collect switch data from the CresControl object."""
        switches = {}
        for device in self.controller.devices:
            if device.device_type == DeviceType.SWITCH:
                switch_name = device.device_id
                switches[switch_name] = device.state
        return switches

    def collect_input_data(self):
        """Collect input data from the CresControl object."""
        inputs = {}
        for device in self.controller.devices:
            if device.device_type == DeviceType.INPUT:
                inputs[device.device_id] = device.state
        return inputs

    def collect_output_data(self):
        """Collect output data from the CresControl object."""
        outputs = {}
        for device in self.controller.devices:
            if device.device_type == DeviceType.OUTPUT:
                outputs[device.device_id] = device.state
        return outputs

    def collect_sensor_data(self):
        """Collect sensor data from the CresControl object."""
        sensors = {}
        for device in self.controller.devices:
            if device.device_type == DeviceType.SENSOR:
                sensors[device.device_id] = device.state
        return sensors
