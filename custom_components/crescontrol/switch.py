import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    switches = []


    for switch_name in ["12v", "24v-a", "24v-b"]:
        device_id = f"{DOMAIN}_{switch_name}_device"
        switches.append(CresSwitchEntity(coordinator, switch_name, entry, device_id))
        switches.append(
            CresSwitchPWMEnabledEntity(coordinator, switch_name, entry, device_id)
        )

    for output_name in ["a", "b", "c", "d", "e", "f"]:
        device_id = f"{DOMAIN}_{output_name}_device"
        if output_name in ["a", "b"]:
            switches.append(
                CresSwitchPWMEnabledOutputEntity(
                    coordinator, output_name, entry, device_id
                )
            )
            switches.append(
                CresOutputSwitchEntity(coordinator, output_name, entry, device_id)
            )
        else:
            switches.append(
                CresOutputSwitchEntity(coordinator, output_name, entry, device_id)
            )

    async_add_entities(switches)


class CresSwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, switch_name, entry, device_id):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._is_on = False
        self._duty_cycle = 0
        self._entry = entry
        self._device_id = device_id

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_{self._entry.entry_id}"

    @property
    def name(self):
        return f"Analog {self._switch_name.capitalize()} Switch"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"CresControl {self._switch_name.capitalize()}",
            "manufacturer": "cre.sience",
            "model": "Switch",
            "sw_version": "1.0",
        }

    @property
    def is_on(self):
       
        return (
            self.coordinator.data["switches"]
            .get(self._switch_name, {})
            .get("enabled", False)
        )

    @property
    def icon(self):
        return "mdi:power-socket"

    @property
    def extra_state_attributes(self):
        return {
            "pwm_frequency": self.coordinator.data["switches"]
            .get(self._switch_name, {})
            .get("pwm-frequency", 0)
        }

    async def async_turn_on(self, **kwargs):
        await self.coordinator.controller.switches.set_switch_enabled(
            self._switch_name, True
        )
        await self.coordinator.async_request_refresh()  
        self.async_write_ha_state()  
        _LOGGER.debug(f"Switch {self._switch_name} turned on.")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.switches.set_switch_enabled(
            self._switch_name, False
        )
        await self.coordinator.async_request_refresh()  
        self.async_write_ha_state()  
        _LOGGER.debug(f"Switch {self._switch_name} turned off.")

    async def async_set_value(self, value: float):
        await self.coordinator.controller.switches.set_duty_cycle(self._switch_name, value)
        await self.coordinator.async_request_refresh()  
        self.async_write_ha_state()  


class CresSwitchPWMEnabledEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, switch_name, entry, device_id):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._device_id = device_id

    @property
    def unique_id(self):
        return (
            f"crescontrol_switch_{self._switch_name}_pwm_enabled_{self._entry.entry_id}"
        )

    @property
    def name(self):
        return f"PWM {self._switch_name.capitalize()} Enabled"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"CresControl {self._switch_name.capitalize()}",
            "manufacturer": "cre.sience",
            "model": "Switch PWM",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        return {
            "duty_cycle": self.coordinator.data["switches"]
            .get(self._switch_name, {})
            .get("duty-cycle", 0),
        }

    @property
    def is_on(self):
        return (
            self.coordinator.data["switches"]
            .get(self._switch_name, {})
            .get("pwm-enabled", False)
        )

    @property
    def icon(self):
        return "mdi:toggle-switch"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.controller.switches.set_pwm_enabled(self._switch_name, True)
        await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, False)
        await self.coordinator.async_request_refresh()  
        self.async_write_ha_state()  
        _LOGGER.debug(f"PWM for switch {self._switch_name} enabled.")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.switches.set_pwm_enabled(self._switch_name, False)
        await self.coordinator.async_request_refresh()  
        self.async_write_ha_state()  
        _LOGGER.debug(f"PWM for switch {self._switch_name} disabled.")

    async def async_set_value(self, value: float):
        await self.coordinator.controller.switches.set_pwm_frequency(self._switch_name, value)
        await self.coordinator.async_update_single_device(self._device_id)
        self.async_write_ha_state()  # Zustand der Entität nach der Änderung aktualisieren


class CresOutputSwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, output_name, entry, device_id):
        super().__init__(coordinator)
        self._switch_name = output_name
        self._entry = entry
        self._device_id = device_id

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._switch_name}_switch_{self._entry.entry_id}"

    @property
    def name(self):
        return f" Analog {self._switch_name.capitalize()} Switch"

    @property
    def device_info(self):
        """Return device information about this entity, grouped with output-related devices."""
        device_id = f"{DOMAIN}_output_{self._switch_name}_device"
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": f"CresControl Output {self._switch_name.capitalize()}",
            "manufacturer": "cre.sience",
            "model": "Output Switch",
            "sw_version": "1.0",
        }

    @property
    def is_on(self):
        return (
            self.coordinator.data["outputs"]
            .get(self._switch_name, {})
            .get("enabled", False)
        )

    @property
    def icon(self):
        return "mdi:power-socket"

    @property
    def extra_state_attributes(self):
        return {
            "pwm_frequency": self.coordinator.data["outputs"]
            .get(self._switch_name, {})
            .get("pwm-frequency", 0)
        }

    async def async_turn_on(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_enabled(
            self._switch_name, True
        )
        await self.coordinator.async_request_refresh()
        _LOGGER.debug(
            f"Turned on output {self._switch_name}, current data: {self.coordinator.data['outputs'].get(self._switch_name)}"
        )

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_enabled(
            self._switch_name, False
        )
        await self.coordinator.async_request_refresh()
        _LOGGER.debug(
            f"Turned off output {self._switch_name}, current data: {self.coordinator.data['outputs'].get(self._switch_name)}"
        )

    async def async_set_value(self, value: float):
        await self.coordinator.async_update_single_device(self._device_id)
        self.async_write_ha_state() 


class CresSwitchPWMEnabledOutputEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, output_name, entry, device_id):
        super().__init__(coordinator)
        self._switch_name = output_name
        self._is_on = False
        self._entry = entry
        self._device_id = device_id

    @property
    def unique_id(self):
        return (
            f"crescontrol_output_{self._switch_name}_pwm_enabled_{self._entry.entry_id}"
        )

    @property
    def name(self):
        return f"PWM {self._switch_name.capitalize()} Enabled"

    @property
    def device_info(self):
        """Return device information about this entity, grouped with output-related devices."""
        device_id = f"{DOMAIN}_output_{self._switch_name}_device"
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": f"CresControl Output {self._switch_name.capitalize()}",
            "manufacturer": "cre.sience",
            "model": "Output PWM",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        return {
            "duty_cycle": self.coordinator.data["outputs"]
            .get(self._switch_name, {})
            .get("duty-cycle", 0)
        }

    @property
    def is_on(self):
        return (
            self.coordinator.data["outputs"]
            .get(self._switch_name, {})
            .get("pwmEnabled", False)
        )

    @property
    def icon(self):
        return "mdi:toggle-switch"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_pwm_enabled(
            self._switch_name, True
        )
        await self.coordinator.async_request_refresh()
        _LOGGER.debug(f"PWM for output {self._switch_name} enabled.")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_pwm_enabled(
            self._switch_name, False
        )
        await self.coordinator.async_request_refresh()
        _LOGGER.debug(f"PWM for output {self._switch_name} disabled.")

    async def async_set_value(self, value: float):
        await self.coordinator.async_update_single_device(self._device_id)
        self.async_write_ha_state()  
