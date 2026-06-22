import logging
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from custom_components.crescontrol.const import (
    DOMAIN,
    CONF_FAN,
    CONF_OUTPUTS,
    CONF_SWITCHES,
    ENTITY_TYPE_FAN,
    PWM_OUTPUTS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CresControl fan entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    fans = []

    fan_config = entry.data.get(CONF_FAN, {})
    output_config = entry.data.get(CONF_OUTPUTS, {})
    switch_config = entry.data.get(CONF_SWITCHES, {})

    # Create fan entity for built-in fan if configured as fan
    if fan_config.get("enabled", False) and fan_config.get("type") == ENTITY_TYPE_FAN:
        custom_name = fan_config.get("name", "Ventilation")
        fans.append(CresFanEntity(coordinator, entry, custom_name))
        _LOGGER.debug(f"Created fan entity: {custom_name}")

    # Create fan entities for outputs configured as fans
    # All outputs support 0-10V speed control, only A&B have additional PWM
    for output_name, cfg in output_config.items():
        if cfg.get("type") == ENTITY_TYPE_FAN:
            custom_name = cfg.get("name", f"Fan{output_name.upper()}")
            fans.append(
                CresOutputFanEntity(coordinator, output_name, entry, is_pwm=True, custom_name=custom_name)
            )
            _LOGGER.debug(f"Created fan entity: {custom_name}")

    # Create fan entities for switches configured as fans
    for switch_name, cfg in switch_config.items():
        if cfg.get("type") == ENTITY_TYPE_FAN:
            custom_name = cfg.get("name", f"Fan{switch_name.upper()}")
            fans.append(
                CresSwitchFanEntity(coordinator, switch_name, entry, custom_name)
            )
            _LOGGER.debug(f"Created fan entity: {custom_name}")

    async_add_entities(fans, True)
    _LOGGER.info(f"Added {len(fans)} fan entities")


class CresFanEntity(CoordinatorEntity, FanEntity):
    """Fan entity for CresControl built-in fan."""

    def __init__(self, coordinator, entry, custom_name=None):
        super().__init__(coordinator)
        self._entry = entry
        self._custom_name = custom_name or "Ventilation"
        self._device_id = f"{DOMAIN}_fan_device"
        self._attr_is_on = None
        self._attr_percentage = None

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "fan" not in self.coordinator.subsystem_failures)

    @property
    def unique_id(self):
        return f"crescontrol_fan_{self._entry.entry_id}"

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
    def supported_features(self):
        return (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )

    def _update_from_coordinator(self):
        """Update local state from coordinator data."""
        if not self.coordinator.data:
            return
        fan_data = self.coordinator.data.get("fan", {})
        enabled = fan_data.get("enabled", False)
        duty_cycle = fan_data.get("dutyCycle", 0)
        try:
            duty_cycle = float(duty_cycle)
        except (ValueError, TypeError):
            duty_cycle = 0
        self._attr_is_on = enabled and duty_cycle > 0
        self._attr_percentage = float(duty_cycle) if enabled else 0

    @property
    def is_on(self):
        if self._attr_is_on is not None:
            return self._attr_is_on
        if not self.coordinator.data:
            return False
        self._update_from_coordinator()
        return self._attr_is_on if self._attr_is_on is not None else False

    @property
    def percentage(self):
        if self._attr_percentage is not None:
            return self._attr_percentage
        if not self.coordinator.data:
            return 0
        self._update_from_coordinator()
        return self._attr_percentage if self._attr_percentage is not None else 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        _LOGGER.debug(f"Turning on fan with percentage {percentage}")
        if percentage is None:
            # Use cached min duty cycle from coordinator data if available
            fan_data = self.coordinator.data.get("fan", {}) if self.coordinator.data else {}
            minduty = fan_data.get("minDutyCycle", 0)
            if minduty == 0:
                minduty = await self.coordinator.controller.fan.getFanDutyCycleMin()
            await self.coordinator.controller.fan.setFanEnabled(True)
            await self.coordinator.controller.fan.setFanDutyCycle(float(minduty))
            self._attr_is_on = True
            self._attr_percentage = float(minduty)
        else:
            await self.coordinator.controller.fan.setFanEnabled(True)
            await self.coordinator.controller.fan.setFanDutyCycle(float(percentage))
            self._attr_is_on = True
            self._attr_percentage = float(percentage)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Turning off fan")
        await self.coordinator.controller.fan.setFanEnabled(False)
        await self.coordinator.controller.fan.setFanDutyCycle(0)
        self._attr_is_on = False
        self._attr_percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        _LOGGER.debug(f"Setting fan percentage to {percentage}")
        if percentage > 0:
            await self.coordinator.controller.fan.setFanEnabled(True)
            self._attr_is_on = True
        else:
            await self.coordinator.controller.fan.setFanEnabled(False)
            self._attr_is_on = False

        await self.coordinator.controller.fan.setFanDutyCycle(float(percentage))
        self._attr_percentage = float(percentage)
        self.async_write_ha_state()


class CresOutputFanEntity(CoordinatorEntity, FanEntity):
    """Fan entity for CresControl outputs."""

    def __init__(self, coordinator, output_name, entry, is_pwm=False, custom_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        # All outputs support 0-10V speed control
        # Only A & B have additional PWM capability
        self._is_pwm = True  # All outputs can do 0-10V speed control
        self._custom_name = custom_name or f"Fan{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"
        self._attr_is_on = None
        self._attr_percentage = None

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "outputs" not in self.coordinator.subsystem_failures)

    @property
    def unique_id(self):
        return f"crescontrol_output_{self._output_name}_fan_{self._entry.entry_id}"

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
    def supported_features(self):
        # All outputs support 0-10V speed control
        return (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )

    def _update_from_coordinator(self):
        """Update local state from coordinator data."""
        if not self.coordinator.data:
            return
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        enabled = output_data.get("enabled", False)
        voltage = output_data.get("voltage", 0)
        self._attr_is_on = enabled
        # All outputs calculate percentage from voltage (0-10V)
        try:
            self._attr_percentage = int((float(voltage) / 10.0) * 100)
        except (ValueError, TypeError):
            self._attr_percentage = 0

    @property
    def is_on(self):
        if self._attr_is_on is not None:
            return self._attr_is_on
        if not self.coordinator.data:
            return False
        self._update_from_coordinator()
        return self._attr_is_on if self._attr_is_on is not None else False

    @property
    def percentage(self):
        if self._attr_percentage is not None:
            return self._attr_percentage
        if not self.coordinator.data:
            return 0
        self._update_from_coordinator()
        return self._attr_percentage if self._attr_percentage is not None else 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        # Check if PWM mode is enabled in config (only for A & B)
        output_config = self._entry.data.get(CONF_OUTPUTS, {}).get(self._output_name, {})
        pwm_mode = output_config.get("pwm_mode", False)
        
        if percentage is not None:
            voltage = (percentage / 100.0) * 10.0
            await self.coordinator.controller.outputs.set_output_voltage(
                self._output_name, voltage
            )
            # Only enable PWM if explicitly configured AND output supports it (A & B)
            if pwm_mode and self._output_name in PWM_OUTPUTS:
                await self.coordinator.controller.outputs.set_output_pwm_enabled(
                    self._output_name, True
                )
            self._attr_percentage = percentage

        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, True
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, False
        )
        await self.coordinator.controller.outputs.set_output_voltage(
            self._output_name, 0
        )
        self._attr_percentage = 0
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        voltage = (percentage / 100.0) * 10.0
        await self.coordinator.controller.outputs.set_output_voltage(
            self._output_name, voltage
        )

        if percentage > 0:
            await self.coordinator.controller.outputs.set_output_enabled(
                self._output_name, True
            )
            self._attr_is_on = True
        else:
            await self.coordinator.controller.outputs.set_output_enabled(
                self._output_name, False
            )
            self._attr_is_on = False

        self._attr_percentage = percentage
        self.async_write_ha_state()


class CresSwitchFanEntity(CoordinatorEntity, FanEntity):
    """Fan entity for CresControl power switches with PWM."""

    def __init__(self, coordinator, switch_name, entry, custom_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._custom_name = custom_name or f"Fan{switch_name.upper()}"
        self._device_id = f"{DOMAIN}_{switch_name}_device"
        self._attr_is_on = None
        self._attr_percentage = None

    @property
    def available(self) -> bool:
        return (self.coordinator.last_update_success
                and self.coordinator.data is not None
                and "switches" not in self.coordinator.subsystem_failures)

    @property
    def unique_id(self):
        return f"crescontrol_switch_{self._switch_name}_fan_{self._entry.entry_id}"

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
    def supported_features(self):
        return (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )

    def _update_from_coordinator(self):
        """Update local state from coordinator data."""
        if not self.coordinator.data:
            return
        switch_data = self.coordinator.data.get("switches", {}).get(self._switch_name, {})
        enabled = switch_data.get("enabled", False)
        duty_cycle = switch_data.get("duty-cycle", 0)
        self._attr_is_on = enabled
        try:
            self._attr_percentage = int(float(duty_cycle))
        except (ValueError, TypeError):
            self._attr_percentage = 0

    @property
    def is_on(self):
        if self._attr_is_on is not None:
            return self._attr_is_on
        if not self.coordinator.data:
            return False
        self._update_from_coordinator()
        return self._attr_is_on if self._attr_is_on is not None else False

    @property
    def percentage(self):
        if self._attr_percentage is not None:
            return self._attr_percentage
        if not self.coordinator.data:
            return 0
        self._update_from_coordinator()
        return self._attr_percentage if self._attr_percentage is not None else 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is not None:
            await self.coordinator.controller.switches.set_duty_cycle(
                self._switch_name, percentage
            )
            self._attr_percentage = percentage

        await self.coordinator.controller.switches.set_pwm_enabled(self._switch_name, True)
        await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, True)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, False)
        await self.coordinator.controller.switches.set_duty_cycle(self._switch_name, 0)
        self._attr_is_on = False
        self._attr_percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        await self.coordinator.controller.switches.set_duty_cycle(
            self._switch_name, percentage
        )
        self._attr_percentage = percentage

        if percentage > 0:
            await self.coordinator.controller.switches.set_pwm_enabled(self._switch_name, True)
            await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, True)
            self._attr_is_on = True
        else:
            await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, False)
            self._attr_is_on = False

        self.async_write_ha_state()
