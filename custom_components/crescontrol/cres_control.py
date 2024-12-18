import asyncio
from .cres_system import CresSystem
from .cres_sensor import CresSensors
from .cres_fan import CresFan
from .cres_inputs import CresInputs
from .cres_outputs import CresOutputs
from .cres_switch import CresSwitches
from dataclasses import dataclass
from enum import StrEnum
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
    def __init__(self, reqAddr):
        self.reqAddr = reqAddr
        self.system = CresSystem(reqAddr)
        self.sensors = CresSensors(reqAddr)
        self.fan = CresFan(reqAddr)
        self.inputs = CresInputs(reqAddr)
        self.outputs = CresOutputs(reqAddr)
        self.switches = CresSwitches(reqAddr)
        self.devices = []

        # Initialize placeholders for data
        self.system_data = None
        self.fan_data = {}  
        self.sensor_data = None
        self.inputs_data = None
        self.outputs_data = None
        self.switches_data = None

    async def init_devices(self):
        # Sensors Initialization
        await self.sensors.get_sensors()  
        await self.sensors.update_sensor_data() 

        for sensor_id, sensor_state in self.sensors.sensor_data.items():
            self.devices.append(
                Device(
                    device_id=sensor_id,
                    device_unique_id=f"{self.reqAddr}_{sensor_id}",
                    device_type=DeviceType.SENSOR,
                    name=f"{sensor_id}",
                    state=sensor_state,
                )
            )

        # Initialize Fan
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
        else:
            pass

        # Initialize Outputs using getAllOutputs
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

        # Initialize Inputs
        await self.inputs.getAllInputsData()  # Verwende die neue getAllInputs-Methode
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

        # Initialize Switches
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

    def get_device_by_id(self, device_id):
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None

    async def update_sensors(self):
        try:
            await self.sensors.update_sensor_data()
            for device in self.devices:
                if device.device_type == DeviceType.SENSOR:
                    sensor_id = device.device_id
                    updated_state = self.sensors.sensor_data.get(sensor_id, {})
                    device.state.update(updated_state)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Aktualisieren der Sensoren: {e}")

    async def update_fan(self):
        try:
            await self.fan.getAllFanData()
            self.fan_data.update(
                {
                    "enabled": self.fan.enabled,
                    "dutyCycle": self.fan.duty_cycle,
                    "minDutyCycle": self.fan.min_duty_cycle,
                }
            )
            fan_device = self.get_device_by_id("fan")
            if fan_device:
                fan_device.state.update(self.fan_data)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Aktualisieren der Lüfterdaten: {e}")

    async def update_inputs(self):
        try:
            await self.inputs.getAllInputsData() 
            for device in self.devices:
                if device.device_type == DeviceType.INPUT:
                    updated_state = self.inputs.inputs_data.get(device.device_id, {})
                    device.state.update(updated_state)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Aktualisieren der Eingabedaten: {e}")

    async def update_outputs(self):
        try:
            # Verwende den Multi-Request für Outputs
            self.outputs_data = await self.outputs.getAllOutputsData()
            for device in self.devices:
                if device.device_type == DeviceType.OUTPUT:
                    updated_state = self.outputs_data.get(device.device_id, {})
                    device.state.update(updated_state)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Aktualisieren der Ausgabedaten: {e}")

    async def update_switches(self):
        try:
            await self.switches.getAllSwitchData()
            for device in self.devices:
                if device.device_type == DeviceType.SWITCH:
                    switch_name = device.device_id
                    updated_state = self.switches.switch_data.get(switch_name, {})
                    device.state.update(updated_state)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Aktualisieren der Switch-Daten: {e}")

    async def update_all(self):
        await self.update_sensors()
        await self.update_fan()
        await self.update_inputs()
        await self.update_outputs()
        await self.update_switches()

    async def fetch_sensor_data(self, sensor_id):
        return self.sensors.sensor_data.get(sensor_id, {})

    async def test_connection(self):
        try:
            system_info = await self.system.getSystemInfo()
            if system_info:
                _LOGGER.info(f"Verbindungstest erfolgreich: {system_info}")
                return True
            else:
                _LOGGER.warning(
                    "Verbindungstest fehlgeschlagen: Keine Systeminformationen empfangen."
                )
                return False
        except Exception as e:
            _LOGGER.error(f"Verbindungstest fehlgeschlagen: {e}")
            return False

    async def get_fan_status(self):
        return str(self.fan)

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
