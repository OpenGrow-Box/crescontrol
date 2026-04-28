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
    for output_name, cfg in output_config.items():
        if cfg.get("type") == ENTITY_TYPE_LIGHT:
            is_dimmable = output_name in PWM_OUTPUTS
            custom_name = cfg.get("name", f"Light{output_name.upper()}")
            lights.append(
                CresOutputLightEntity(
                    coordinator, output_name, entry, is_dimmable, custom_name
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

    async_add_entities(lights)
    _LOGGER.info(f"Added {len(lights)} light entities")


class CresOutputLightEntity(CoordinatorEntity, LightEntity):
    """Light entity for CresControl outputs."""

    def __init__(self, coordinator, output_name, entry, is_dimmable=False, custom_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._is_dimmable = is_dimmable
        self._custom_name = custom_name or f"Light{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        self._attr_is_on = False
        self._attr_brightness = 0

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_light_{self._entry.entry_id}"

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
        return {
            "output_channel": self._output_name,
        }

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS if self._is_dimmable else ColorMode.ONOFF

    @property
    def supported_color_modes(self):
        if self._is_dimmable:
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}

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

    @property
    def is_on(self):
        return self._attr_is_on

    @property
    def brightness(self):
        if not self._is_dimmable:
            return 255 if self.is_on else 0
        return self._attr_brightness

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)

        if self._is_dimmable:
            voltage = (brightness / 255.0) * 10.0
            await self.coordinator.controller.outputs.set_output_voltage(
                self._output_name, voltage
            )
            # Enable PWM for dimmable outputs
            await self.coordinator.controller.outputs.set_output_pwm_enabled(
                self._output_name, True
            )
            self._attr_brightness = brightness

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
        self._attr_is_on = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Turned off output light {self._output_name}")


class CresSwitchLightEntity(CoordinatorEntity, LightEntity):
    """Light entity for CresControl power switches with PWM dimming."""

    def __init__(self, coordinator, switch_name, entry, custom_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._custom_name = custom_name or f"Switch{switch_name.upper()}"
        self._device_id = f"{DOMAIN}_{switch_name}_device"
        self._attr_is_on = False
        self._attr_brightness = 0

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_light_{self._entry.entry_id}"

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
        return {
            "switch_channel": self._switch_name,
        }

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self):
        return {ColorMode.BRIGHTNESS}

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

    @property
    def is_on(self):
        return self._attr_is_on

    @property
    def brightness(self):
        return self._attr_brightness

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

    def __init__(self, coordinator, entry, custom_name=None):
        super().__init__(coordinator)
        self._entry = entry
        self._custom_name = custom_name or "Ventilation"
        self._device_id = f"{DOMAIN}_fan_device"
        self._attr_is_on = False
        self._attr_brightness = 0

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def unique_id(self):
        return f"crescontrol_fan_light_{self._entry.entry_id}"

    @property
    def name(self):
        return self._custom_name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._custom_name,
            "manufacturer": "cre.sience",
            "model": "CresControl Fan",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        return {}

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self):
        return {ColorMode.BRIGHTNESS}

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

    @property
    def is_on(self):
        return self._attr_is_on

    @property
    def brightness(self):
        return self._attr_brightness

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
