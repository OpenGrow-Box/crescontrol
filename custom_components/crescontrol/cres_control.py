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
        """Initialize all devices. Each subsystem is initialized independently.
        
        Failed subsystems are skipped so that working subsystems are still available.
        """
        # Clear previous state to prevent duplicates on re-initialization
        self.devices = []
        init_errors = []
        
        # Sensors Initialization - always available
        try:
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
        except Exception as e:
            _LOGGER.warning(f"Sensor initialization failed: {e}")
            init_errors.append(("sensors", e))

        # Initialize Fan only if enabled
        if self.fan_enabled:
            try:
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
            except Exception as e:
                _LOGGER.warning(f"Fan initialization failed: {e}")
                init_errors.append(("fan", e))

        # Initialize Outputs - only active ones
        if self.outputs.outputList:
            try:
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
            except Exception as e:
                _LOGGER.warning(f"Outputs initialization failed: {e}")
                init_errors.append(("outputs", e))

        # Initialize Inputs - only active ones
        if self.inputs.inputList:
            try:
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
            except Exception as e:
                _LOGGER.warning(f"Inputs initialization failed: {e}")
                init_errors.append(("inputs", e))

        # Initialize Switches - only active ones
        if self.switches.switchList:
            try:
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
            except Exception as e:
                _LOGGER.warning(f"Switches initialization failed: {e}")
                init_errors.append(("switches", e))
        
        # Mark as initialized if at least some devices were created
        if self.devices:
            self._initialized = True
            if init_errors:
                _LOGGER.info(f"Partial initialization: {len(self.devices)} devices initialized, {len(init_errors)} subsystems failed")
        elif init_errors:
            # Only raise if nothing could be initialized
            _LOGGER.error(f"All subsystems failed to initialize: {init_errors}")
            raise UpdateFailed(f"All {len(init_errors)} subsystems failed to initialize") from init_errors[0][1]

    def get_device_by_id(self, device_id):
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None

    async def update_sensors(self):
        try:
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
        except Exception as e:
            _LOGGER.warning(f"Sensors update failed, keeping previous state: {e}")
            raise

    async def update_fan(self):
        if not self.fan_enabled:
            return
        try:
            await self.fan.getAllFanData()
            self.fan_data = {
                "enabled": self.fan.enabled,
                "dutyCycle": self.fan.duty_cycle,
                "minDutyCycle": self.fan.min_duty_cycle,
            }
            fan_device = self.get_device_by_id("fan")
            if fan_device:
                fan_device.state = self.fan_data.copy()
        except Exception as e:
            _LOGGER.warning(f"Fan update failed, keeping previous state: {e}")
            raise

    async def update_inputs(self):
        if not self.inputs.inputList:
            return
        try:
            await self.inputs.getAllInputsData() 
            for device in self.devices:
                if device.device_type == DeviceType.INPUT:
                    device.state = self.inputs.inputs_data.get(device.device_id, {}).copy()
        except Exception as e:
            _LOGGER.warning(f"Inputs update failed, keeping previous state: {e}")
            raise

    async def update_outputs(self):
        if not self.outputs.outputList:
            return
        try:
            self.outputs_data = await self.outputs.getAllOutputsData()
            for device in self.devices:
                if device.device_type == DeviceType.OUTPUT:
                    device.state = self.outputs_data.get(device.device_id, {}).copy()
        except Exception as e:
            _LOGGER.warning(f"Outputs update failed, keeping previous state: {e}")
            raise

    async def update_switches(self):
        if not self.switches.switchList:
            return
        try:
            await self.switches.getAllSwitchData()
            for device in self.devices:
                if device.device_type == DeviceType.SWITCH:
                    device.state = self.switches.switch_data.get(device.device_id, {}).copy()
        except Exception as e:
            _LOGGER.warning(f"Switches update failed, keeping previous state: {e}")
            raise

    async def update_all(self):
        """Update all device data. Each subsystem is updated independently.
        
        Failed subsystems are logged but do not cause other subsystems to fail.
        Only raises if ALL subsystems fail.
        """
        updates = [
            ("sensors", self.update_sensors),
            ("fan", self.update_fan),
            ("inputs", self.update_inputs),
            ("outputs", self.update_outputs),
            ("switches", self.update_switches),
        ]
        
        errors = []
        for name, update_func in updates:
            try:
                await update_func()
            except Exception as e:
                _LOGGER.warning(f"Subsystem '{name}' update failed: {e}")
                errors.append((name, e))
        
        if len(errors) == len(updates):
            _LOGGER.error(f"All {len(updates)} subsystems failed to update")
            raise UpdateFailed(f"All {len(updates)} subsystems failed") from errors[0][1]
        elif errors:
            _LOGGER.info(f"Partial update completed: {len(updates) - len(errors)}/{len(updates)} subsystems OK")

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
