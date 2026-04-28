import asyncio
import aiohttp
from custom_components.crescontrol.cres_system import CresSystem
from custom_components.crescontrol.cres_sensor import CresSensors
from custom_components.crescontrol.cres_fan import CresFan
from custom_components.crescontrol.cres_inputs import CresInputs
from custom_components.crescontrol.cres_outputs import CresOutputs
from custom_components.crescontrol.cres_switch import CresSwitches
from dataclasses import dataclass
from enum import StrEnum
from custom_components.crescontrol.const import sanitize_sensor_id
import logging

_LOGGER = logging.getLogger(__name__)


class DeviceType(StrEnum):
    SENSOR = "sensor"
    FAN = "fan"
    OUTPUT = "output"
    INPUT = "input"
    SWITCH = "switch"
    OTHER = "other"


@dataclass
class Device:
    device_id: int | str
    device_unique_id: str
    device_type: DeviceType
    name: str
    state: dict


class CresControl:
    def __init__(self, reqAddr, config=None, session=None):
        self.reqAddr = reqAddr
        self.config = config or {}
        self._session = session
        self.system = CresSystem(reqAddr, session)
        self.sensors = CresSensors(reqAddr, session)
        self.fan = CresFan(reqAddr, session)
        
        # Only initialize active devices based on config
        active_outputs = list(self.config.get("outputs", {}).keys())
        active_inputs = list(self.config.get("inputs", {}).keys())
        active_switches = list(self.config.get("switches", {}).keys())
        fan_config = self.config.get("fan", {})
        fan_enabled = fan_config.get("enabled", False) if isinstance(fan_config, dict) else False
        
        self.inputs = CresInputs(reqAddr, active_inputs, session)
        self.outputs = CresOutputs(reqAddr, active_outputs, session=session)
        self.switches = CresSwitches(reqAddr, active_switches, session)
        self.devices = []
        self._initialized = False
        
        # Initialize placeholders for data
        self.system_data = None
        self.fan_data = {}  
        self.sensor_data = None
        self.inputs_data = None
        self.outputs_data = None
        self.switches_data = None
        self.fan_enabled = fan_enabled

    async def init_devices(self):
        """Initialize all devices atomically. On failure, devices list is cleared."""
        # Clear previous state to prevent duplicates on re-initialization
        self.devices = []
        
        try:
            # Sensors Initialization - always available
            await self.sensors.get_sensors()  
            await self.sensors.update_sensor_data() 

            for sensor_id, sensor_state in self.sensors.sensor_data.items():
                sanitized_id = sanitize_sensor_id(sensor_id)
                self.devices.append(
                    Device(
                        device_id=sanitized_id,
                        device_unique_id=f"{self.reqAddr}_{sanitized_id}",
                        device_type=DeviceType.SENSOR,
                        name=f"{sanitized_id}",
                        state=sensor_state,
                    )
                )

            # Initialize Fan only if enabled
            if self.fan_enabled:
                await self.fan.getAllFanData()
                self.fan_data = {
                    "enabled": self.fan.enabled,
                    "dutyCycle": self.fan.duty_cycle,
                    "minDutyCycle": self.fan.min_duty_cycle,
                }

                fan_device = self.get_device_by_id("fan")
                if not fan_device:
                    fan_device = Device(
                        device_id="fan",
                        device_unique_id=f"{self.reqAddr}_fan",
                        device_type=DeviceType.FAN,
                        name="fan",
                        state=self.fan_data,
                    )
                    self.devices.append(fan_device)

            # Initialize Outputs - only active ones
            if self.outputs.outputList:
                self.outputs_data = await self.outputs.getAllOutputsData()
                for output_name, output_state in self.outputs_data.items():
                    self.devices.append(
                        Device(
                            device_id=output_name,
                            device_unique_id=f"{self.reqAddr}_O{output_name}",
                            device_type=DeviceType.OUTPUT,
                            name=f"Output-{output_name}",
                            state=output_state,
                        )
                    )

            # Initialize Inputs - only active ones
            if self.inputs.inputList:
                await self.inputs.getAllInputsData()
                for input_name, input_state in self.inputs.inputs_data.items():
                    self.devices.append(
                        Device(
                            device_id=input_name,
                            device_unique_id=f"{self.reqAddr}_I{input_name}",
                            device_type=DeviceType.INPUT,
                            name=f"Input-{input_name}",
                            state=input_state,
                        )
                    )

            # Initialize Switches - only active ones
            if self.switches.switchList:
                await self.switches.getAllSwitchData()
                for switch_name, switch_state in self.switches.switch_data.items():
                    self.devices.append(
                        Device(
                            device_id=switch_name,
                            device_unique_id=f"{self.reqAddr}_Switch_{switch_name}",
                            device_type=DeviceType.SWITCH,
                            name=f"Switch {switch_name.upper()}",
                            state=switch_state,
                        )
                    )
            
            self._initialized = True
            
        except Exception:
            # On failure, clear devices so next refresh will retry
            self.devices = []
            raise

    def get_device_by_id(self, device_id):
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None

    async def update_sensors(self):
        await self.sensors.update_sensor_data()
        # Build sanitized sensor data mapping
        sanitized_sensor_data = {}
        for raw_id, data in self.sensors.sensor_data.items():
            sanitized_id = sanitize_sensor_id(raw_id)
            sanitized_sensor_data[sanitized_id] = data
        
        for device in self.devices:
            if device.device_type == DeviceType.SENSOR:
                sensor_id = device.device_id
                device.state = sanitized_sensor_data.get(sensor_id, {})

    async def update_fan(self):
        if not self.fan_enabled:
            return
        await self.fan.getAllFanData()
        self.fan_data = {
            "enabled": self.fan.enabled,
            "dutyCycle": self.fan.duty_cycle,
            "minDutyCycle": self.fan.min_duty_cycle,
        }
        fan_device = self.get_device_by_id("fan")
        if fan_device:
            fan_device.state = self.fan_data.copy()

    async def update_inputs(self):
        if not self.inputs.inputList:
            return
        await self.inputs.getAllInputsData() 
        for device in self.devices:
            if device.device_type == DeviceType.INPUT:
                device.state = self.inputs.inputs_data.get(device.device_id, {}).copy()

    async def update_outputs(self):
        if not self.outputs.outputList:
            return
        self.outputs_data = await self.outputs.getAllOutputsData()
        for device in self.devices:
            if device.device_type == DeviceType.OUTPUT:
                device.state = self.outputs_data.get(device.device_id, {}).copy()

    async def update_switches(self):
        if not self.switches.switchList:
            return
        await self.switches.getAllSwitchData()
        for device in self.devices:
            if device.device_type == DeviceType.SWITCH:
                device.state = self.switches.switch_data.get(device.device_id, {}).copy()

    async def update_all(self):
        """Update all device data. Runs updates concurrently but propagates exceptions."""
        results = await asyncio.gather(
            self.update_sensors(),
            self.update_fan(),
            self.update_inputs(),
            self.update_outputs(),
            self.update_switches(),
            return_exceptions=True,
        )
        # Check if any update failed and raise the first exception
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            _LOGGER.error(f"Update failed for {len(errors)} subsystems: {errors}")
            raise UpdateFailed(f"Failed to update {len(errors)} subsystems") from errors[0]

    async def fetch_sensor_data(self, sensor_id):
        return self.sensors.sensor_data.get(sensor_id, {})

    async def test_connection(self):
        try:
            system_info = await self.system.getSystemInfo()
            if system_info:
                _LOGGER.info(f"Connection test successful: {system_info}")
                return True
            else:
                _LOGGER.warning(
                    "Connection test failed: No system information received."
                )
                return False
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            return False

    async def get_fan_status(self):
        return str(self.fan)

    async def async_close(self):
        """Close all aiohttp sessions including subsystem sessions."""
        # Close all subsystem request sessions
        subsystems = [self.system, self.sensors, self.fan, self.inputs, self.outputs, self.switches]
        for subsystem in subsystems:
            if hasattr(subsystem, 'req') and subsystem.req:
                await subsystem.req.close()
        
        # Close main session if owned
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def __str__(self):
        return f"""
        Devices: {[str(device) for device in self.devices]}
        """


class APIAuthError(Exception):
    pass


class APIConnectionError(Exception):
    pass


class UpdateFailed(Exception):
    pass
