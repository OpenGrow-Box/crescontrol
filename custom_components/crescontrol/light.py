"""Light platform for CresControl integration."""
import logging
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from custom_components.crescontrol.const import (
    DOMAIN,
    CONF_OUTPUTS,
    CONF_SWITCHES,
    CONF_FAN,
    ENTITY_TYPE_LIGHT,
    PWM_OUTPUTS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CresControl light entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    lights = []

    output_config = entry.data.get(CONF_OUTPUTS, {})
    switch_config = entry.data.get(CONF_SWITCHES, {})
    fan_config = entry.data.get(CONF_FAN, {})

    # Create light entities for outputs configured as lights
    # All outputs support 0-10V dimming, only A&B have additional PWM
    for output_name, cfg in output_config.items():
        if cfg.get("type") == ENTITY_TYPE_LIGHT:
            custom_name = cfg.get("name", f"Light{output_name.upper()}")
            lights.append(
                CresOutputLightEntity(
                    coordinator, output_name, entry, is_dimmable=True, custom_name=custom_name
                )
            )
            _LOGGER.debug(f"Created light entity: {custom_name}")

    # Create light entities for switches configured as lights
    for switch_name, cfg in switch_config.items():
        if cfg.get("type") == ENTITY_TYPE_LIGHT:
            custom_name = cfg.get("name", f"Switch{switch_name.upper()}")
            lights.append(
                CresSwitchLightEntity(coordinator, switch_name, entry, custom_name)
            )
            _LOGGER.debug(f"Created light entity: {custom_name}")

    # Create light entity for fan if configured as light
    if fan_config.get("enabled", False) and fan_config.get("type") == ENTITY_TYPE_LIGHT:
        custom_name = fan_config.get("name", "Ventilation")
        lights.append(CresFanLightEntity(coordinator, entry, custom_name))
        _LOGGER.debug(f"Created light entity for fan: {custom_name}")

    async_add_entities(lights, True)
    _LOGGER.info(f"Added {len(lights)} light entities")


class CresOutputLightEntity(CoordinatorEntity, LightEntity):
    """Light entity for CresControl outputs."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator, output_name, entry, is_dimmable=False, custom_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._is_dimmable = is_dimmable
        self._attr_unique_id = f"crescontrol_output_{output_name}_light_{entry.entry_id}"
        self._attr_name = custom_name or f"Light{output_name.upper()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{DOMAIN}_output_{output_name}_device")},
            "name": custom_name or f"Light{output_name.upper()}",
            "manufacturer": "cre.sience",
            "model": "CresControl Output",
            "sw_version": "1.0",
        }
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_extra_state_attributes = {"output_channel": output_name}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    def _update_from_coordinator(self):
        """Update local state from coordinator data."""
        if not self.coordinator.data:
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        enabled = output_data.get("enabled", False)
        voltage = output_data.get("voltage", 0)
        self._attr_is_on = enabled
        if self._is_dimmable:
            try:
                self._attr_brightness = int((float(voltage) / 10.0) * 255)
            except (ValueError, TypeError):
                self._attr_brightness = 0
        else:
            self._attr_brightness = 255 if enabled else 0

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)

        if self._is_dimmable:
            voltage = (brightness / 255.0) * 10.0
            await self.coordinator.controller.outputs.set_output_voltage(
                self._output_name, voltage
            )
            # Only enable PWM if explicitly configured in output settings
            output_config = self._entry.data.get(CONF_OUTPUTS, {}).get(self._output_name, {})
            if output_config.get("pwm_mode", False):
                await self.coordinator.controller.outputs.set_output_pwm_enabled(
                    self._output_name, True
                )
            self._attr_brightness = brightness
            
            # Update coordinator data immediately so all sensors update
            if self.coordinator.data and "outputs" in self.coordinator.data:
                if self._output_name in self.coordinator.data["outputs"]:
                    new_data = dict(self.coordinator.data)
                    new_data["outputs"] = dict(new_data["outputs"])
                    new_data["outputs"][self._output_name] = dict(new_data["outputs"][self._output_name])
                    new_data["outputs"][self._output_name]["voltage"] = voltage
                    new_data["outputs"][self._output_name]["enabled"] = True
                    self.coordinator.async_set_updated_data(new_data)

        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, True
        )
        self._attr_is_on = True
        self.async_write_ha_state()
        _LOGGER.debug(f"Turned on output light {self._output_name}")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, False
        )
        if self._is_dimmable:
            await self.coordinator.controller.outputs.set_output_voltage(
                self._output_name, 0
            )
            self._attr_brightness = 0
            # Update coordinator data immediately so all sensors update
            if self.coordinator.data and "outputs" in self.coordinator.data:
                if self._output_name in self.coordinator.data["outputs"]:
                    new_data = dict(self.coordinator.data)
                    new_data["outputs"] = dict(new_data["outputs"])
                    new_data["outputs"][self._output_name] = dict(new_data["outputs"][self._output_name])
                    new_data["outputs"][self._output_name]["voltage"] = 0
                    new_data["outputs"][self._output_name]["enabled"] = False
                    self.coordinator.async_set_updated_data(new_data)
        self._attr_is_on = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Turned off output light {self._output_name}")


class CresSwitchLightEntity(CoordinatorEntity, LightEntity):
    """Light entity for CresControl power switches with PWM dimming."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator, switch_name, entry, custom_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._attr_unique_id = f"crescontrol_switch_{switch_name}_light_{entry.entry_id}"
        self._attr_name = custom_name or f"Switch{switch_name.upper()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{DOMAIN}_{switch_name}_device")},
            "name": custom_name or f"Switch{switch_name.upper()}",
            "manufacturer": "cre.sience",
            "model": "CresControl Switch",
            "sw_version": "1.0",
        }
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_extra_state_attributes = {"switch_channel": switch_name}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    def _update_from_coordinator(self):
        """Update local state from coordinator data."""
        if not self.coordinator.data:
            return
        switch_data = self.coordinator.data.get("switches", {}).get(self._switch_name, {})
        enabled = switch_data.get("enabled", False)
        duty_cycle = switch_data.get("duty-cycle", 0)
        self._attr_is_on = enabled
        try:
            self._attr_brightness = int((float(duty_cycle) / 100.0) * 255)
        except (ValueError, TypeError):
            self._attr_brightness = 0

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        duty_cycle = (brightness / 255.0) * 100.0

        await self.coordinator.controller.switches.set_pwm_enabled(self._switch_name, True)
        await self.coordinator.controller.switches.set_duty_cycle(self._switch_name, duty_cycle)
        await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, True)
        self._attr_is_on = True
        self._attr_brightness = brightness
        self.async_write_ha_state()
        _LOGGER.debug(f"Turned on switch light {self._switch_name} at {duty_cycle}%")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, False)
        await self.coordinator.controller.switches.set_duty_cycle(self._switch_name, 0)
        self._attr_is_on = False
        self._attr_brightness = 0
        self.async_write_ha_state()
        _LOGGER.debug(f"Turned off switch light {self._switch_name}")


class CresFanLightEntity(CoordinatorEntity, LightEntity):
    """Light entity for CresControl fan output (used as dimmable light)."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator, entry, custom_name=None):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"crescontrol_fan_light_{entry.entry_id}"
        self._attr_name = custom_name or "Ventilation"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{DOMAIN}_fan_device")},
            "name": custom_name or "Ventilation",
            "manufacturer": "cre.sience",
            "model": "CresControl Fan",
            "sw_version": "1.0",
        }
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_extra_state_attributes = {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    def _update_from_coordinator(self):
        """Update local state from coordinator data."""
        if not self.coordinator.data:
            return
        fan_data = self.coordinator.data.get("fan", {})
        enabled = fan_data.get("enabled", False)
        duty_cycle = fan_data.get("dutyCycle", 0)
        self._attr_is_on = enabled
        try:
            self._attr_brightness = int((float(duty_cycle) / 100.0) * 255)
        except (ValueError, TypeError):
            self._attr_brightness = 0

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        duty_cycle = (brightness / 255.0) * 100.0

        await self.coordinator.controller.fan.setFanEnabled(True)
        await self.coordinator.controller.fan.setFanDutyCycle(duty_cycle)
        self._attr_is_on = True
        self._attr_brightness = brightness
        self.async_write_ha_state()
        _LOGGER.debug(f"Turned on fan light at {duty_cycle}%")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.fan.setFanEnabled(False)
        await self.coordinator.controller.fan.setFanDutyCycle(0)
        self._attr_is_on = False
        self._attr_brightness = 0
        self.async_write_ha_state()
        _LOGGER.debug("Turned off fan light")