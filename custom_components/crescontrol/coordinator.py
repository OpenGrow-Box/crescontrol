from dataclasses import dataclass
from datetime import timedelta
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from custom_components.crescontrol.cres_control import CresControl, APIAuthError, DeviceType
from custom_components.crescontrol.const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Circuit breaker: after this many consecutive failures, increase poll interval
MAX_CONSECUTIVE_FAILURES = 3
# Maximum poll interval in seconds (5 minutes)
MAX_POLL_INTERVAL = 300


class CresControlCoordinator(DataUpdateCoordinator):
    """Coordinator to manage the integration with the CresControl system."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, controller: CresControl) -> None:
        """Initialize the coordinator."""
        self.host = config_entry.data[CONF_HOST]
        self.base_poll_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._current_poll_interval = self.base_poll_interval
        self._consecutive_failures = 0
        self.controller = controller
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self._current_poll_interval),
        )

    async def async_update_data(self):
        """Fetch data from the API endpoint.
        
        On partial failure, returns previously cached data if available
        to avoid all entities going unavailable.
        Implements circuit breaker: increases poll interval after consecutive failures.
        """
        try:
            _LOGGER.debug("Updating CresControl data from API")

            if not self.controller._initialized:
                try:
                    await self.controller.init_devices()
                except Exception as init_err:
                    _LOGGER.warning(f"Device initialization failed: {init_err}")
                    if self.data:
                        _LOGGER.debug("Using cached data due to initialization failure")
                        return self.data
                    raise

            await self.controller.update_all()

            # Success: reset circuit breaker
            self._consecutive_failures = 0
            if self._current_poll_interval != self.base_poll_interval:
                self._current_poll_interval = self.base_poll_interval
                self.update_interval = timedelta(seconds=self._current_poll_interval)
                _LOGGER.info(
                    "Device reachable again, restored poll interval to %ds",
                    self._current_poll_interval,
                )

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
        except UpdateFailed:
            if self.data:
                self._consecutive_failures += 1
                await self._adjust_poll_interval()
                _LOGGER.debug(
                    "Update failed (consecutive failures: %d), keeping cached data",
                    self._consecutive_failures,
                )
                return self.data
            raise
        except Exception as err:
            self._consecutive_failures += 1
            await self._adjust_poll_interval()
            if self.data:
                _LOGGER.debug(
                    "Communication error (consecutive failures: %d), using cached data",
                    self._consecutive_failures,
                )
                return self.data
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed("Error communicating with API") from err

    async def _adjust_poll_interval(self):
        """Increase poll interval when device is unreachable (circuit breaker)."""
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            new_interval = min(
                self.base_poll_interval * (2 ** (self._consecutive_failures - MAX_CONSECUTIVE_FAILURES + 1)),
                MAX_POLL_INTERVAL,
            )
            if new_interval != self._current_poll_interval:
                self._current_poll_interval = new_interval
                self.update_interval = timedelta(seconds=self._current_poll_interval)
                _LOGGER.warning(
                    "Device unreachable for %d consecutive polls, reduced update frequency to %ds",
                    self._consecutive_failures,
                    self._current_poll_interval,
                )

    @property
    def subsystem_failures(self) -> set[str]:
        """Return set of subsystem names that failed on the last update."""
        return self.controller.subsystem_failures

    async def async_update_single_device(self, device_id: str):
        """Update a specific device by its ID."""
        try:
            _LOGGER.debug(f"Updating device {device_id} from API")

            # Find the corresponding device and update it specifically
            device = self.controller.get_device_by_id(device_id)
            if device:
                if device.device_type == DeviceType.SENSOR:
                    await self.controller.update_sensors()  # Update all sensors
                elif device.device_type == DeviceType.FAN:
                    await self.controller.update_fan()  # Update fan
                elif device.device_type == DeviceType.INPUT:
                    await self.controller.update_inputs()  # Update all inputs
                elif device.device_type == DeviceType.OUTPUT:
                    await self.controller.update_outputs()  # Update all outputs
                elif device.device_type == DeviceType.SWITCH:
                    await self.controller.update_switches()  # Update all switches
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
