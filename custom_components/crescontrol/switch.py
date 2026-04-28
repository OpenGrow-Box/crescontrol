import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from custom_components.crescontrol.const import (
    DOMAIN,
    CONF_OUTPUTS,
    CONF_SWITCHES,
    ENTITY_TYPE_SWITCH,
    PWM_OUTPUTS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CresControl switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    switches = []

    output_config = entry.data.get(CONF_OUTPUTS, {})
    switch_config = entry.data.get(CONF_SWITCHES, {})

    # Create switch entities for outputs configured as switches
    for output_name, cfg in output_config.items():
        if cfg.get("type") == ENTITY_TYPE_SWITCH:
            device_id = f"{DOMAIN}_output_{output_name}_device"
            custom_name = cfg.get("name", f"Output{output_name.upper()}")
            switches.append(
                CresOutputSwitchEntity(coordinator, output_name, entry, device_id, custom_name)
            )
            # Add PWM enabled switch for PWM capable outputs
            if output_name in PWM_OUTPUTS:
                switches.append(
                    CresOutputPWMEnabledEntity(coordinator, output_name, entry, device_id, custom_name)
                )
            _LOGGER.debug(f"Created switch entity: {custom_name}")

    # Create switch entities for power switches configured as switches
    for switch_name, cfg in switch_config.items():
        if cfg.get("type") == ENTITY_TYPE_SWITCH:
            device_id = f"{DOMAIN}_{switch_name}_device"
            custom_name = cfg.get("name", f"Switch{switch_name.upper()}")
            switches.append(
                CresSwitchEntity(coordinator, switch_name, entry, device_id, custom_name)
            )
            switches.append(
                CresSwitchPWMEnabledEntity(coordinator, switch_name, entry, device_id, custom_name)
            )
            _LOGGER.debug(f"Created switch entity: {custom_name}")

    async_add_entities(switches)
    _LOGGER.info(f"Added {len(switches)} switch entities")


class CresOutputSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch entity for CresControl outputs."""

    def __init__(self, coordinator, output_name, entry, device_id, custom_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._device_id = device_id
        self._custom_name = custom_name or f"Output{output_name.upper()}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_switch_{self._entry.entry_id}"

    @property
    def name(self):
        return self._custom_name

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
    def extra_state_attributes(self):
        outputs_data = self.coordinator.data.get("outputs", {}) if self.coordinator.data else {}
        return {
            "output_channel": self._output_name,
            "pwm_frequency": outputs_data.get(self._output_name, {}).get("pwmFrequency", 0),
        }

    @property
    def is_on(self):
        if not self.coordinator.data:
            return False
        outputs_data = self.coordinator.data.get("outputs", {})
        return outputs_data.get(self._output_name, {}).get("enabled", False)

    @property
    def icon(self):
        return "mdi:power-socket"

    async def async_turn_on(self, **kwargs):
        # Enable PWM for PWM-capable outputs (A, B)
        if self._output_name in PWM_OUTPUTS:
            await self.coordinator.controller.outputs.set_output_pwm_enabled(
                self._output_name, True
            )
        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, True
        )
        # Update state directly without full refresh
        self.async_write_ha_state()
        outputs_data = self.coordinator.data.get("outputs", {}) if self.coordinator.data else {}
        _LOGGER.debug(f"Turned on output {self._output_name}, current data: {outputs_data.get(self._output_name)}")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, False
        )
        # Update state directly without full refresh
        self.async_write_ha_state()
        outputs_data = self.coordinator.data.get("outputs", {}) if self.coordinator.data else {}
        _LOGGER.debug(f"Turned off output {self._output_name}, current data: {outputs_data.get(self._output_name)}")


class CresOutputPWMEnabledEntity(CoordinatorEntity, SwitchEntity):
    """PWM enabled switch entity for CresControl outputs."""

    def __init__(self, coordinator, output_name, entry, device_id, custom_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._device_id = device_id
        self._custom_name = custom_name or f"Output{output_name.upper()}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_pwm_enabled_{self._entry.entry_id}"

    @property
    def name(self):
        return f"{self._custom_name}PWM"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._custom_name,
            "manufacturer": "cre.sience",
            "model": "CresControl PWM",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        outputs_data = self.coordinator.data.get("outputs", {}) if self.coordinator.data else {}
        output_info = outputs_data.get(self._output_name, {})
        return {
            "output_channel": self._output_name,
            "pwm_frequency": output_info.get("pwmFrequency", 0),
            "voltage": output_info.get("voltage", 0),
        }

    @property
    def is_on(self):
        if not self.coordinator.data:
            return False
        outputs_data = self.coordinator.data.get("outputs", {})
        return outputs_data.get(self._output_name, {}).get("pwmEnabled", False)

    @property
    def icon(self):
        return "mdi:fan"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_pwm_enabled(
            self._output_name, True
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_pwm_enabled(
            self._output_name, False
        )
        self.async_write_ha_state()


class CresSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch entity for CresControl power switches."""

    def __init__(self, coordinator, switch_name, entry, device_id, custom_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._device_id = device_id
        self._custom_name = custom_name or f"Switch{switch_name.upper()}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_{self._entry.entry_id}"

    @property
    def name(self):
        return self._custom_name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._custom_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Switch",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        switches_data = self.coordinator.data.get("switches", {}) if self.coordinator.data else {}
        return {
            "switch_channel": self._switch_name,
            "pwm_frequency": switches_data.get(self._switch_name, {}).get("pwm-frequency", 0),
        }

    @property
    def is_on(self):
        if not self.coordinator.data:
            return False
        switches_data = self.coordinator.data.get("switches", {})
        return switches_data.get(self._switch_name, {}).get("enabled", False)

    @property
    def icon(self):
        return "mdi:power-socket"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.controller.switches.set_switch_enabled(
            self._switch_name, True
        )
        # Update state directly without full refresh
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.switches.set_switch_enabled(
            self._switch_name, False
        )
        # Update state directly without full refresh
        self.async_write_ha_state()


class CresSwitchPWMEnabledEntity(CoordinatorEntity, SwitchEntity):
    """PWM enabled switch entity for CresControl power switches."""

    def __init__(self, coordinator, switch_name, entry, device_id, custom_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._device_id = device_id
        self._custom_name = custom_name or f"Switch{switch_name.upper()}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_pwm_enabled_{self._entry.entry_id}"

    @property
    def name(self):
        return f"{self._custom_name}PWM"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._custom_name,
            "manufacturer": "cre.sience",
            "model": "CresControl PWM",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        switches_data = self.coordinator.data.get("switches", {}) if self.coordinator.data else {}
        return {
            "duty_cycle": switches_data.get(self._switch_name, {}).get("duty-cycle", 0),
            "switch_channel": self._switch_name,
        }

    @property
    def is_on(self):
        if not self.coordinator.data:
            return False
        switches_data = self.coordinator.data.get("switches", {})
        return switches_data.get(self._switch_name, {}).get("pwm-enabled", False)

    @property
    def icon(self):
        return "mdi:fan"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.controller.switches.set_pwm_enabled(
            self._switch_name, True
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.switches.set_pwm_enabled(
            self._switch_name, False
        )
        self.async_write_ha_state()
