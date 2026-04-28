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
    for output_name, cfg in output_config.items():
        if cfg.get("type") == ENTITY_TYPE_FAN:
            is_pwm = output_name in PWM_OUTPUTS
            custom_name = cfg.get("name", f"Fan{output_name.upper()}")
            fans.append(
                CresOutputFanEntity(coordinator, output_name, entry, is_pwm, custom_name)
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

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

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

    @property
    def is_on(self):
        if not self.coordinator.data:
            return False
        fan_data = self.coordinator.data.get("fan", {})
        enabled = fan_data.get("enabled", False)
        duty_cycle = fan_data.get("dutyCycle", 0)

        try:
            duty_cycle = float(duty_cycle)
        except (ValueError, TypeError):
            duty_cycle = 0

        return enabled and duty_cycle > 0

    @property
    def percentage(self):
        if not self.coordinator.data:
            return 0
        fan_data = self.coordinator.data.get("fan", {})
        enabled = fan_data.get("enabled", False)
        duty_cycle = fan_data.get("dutyCycle", 0)

        if not enabled:
            return 0

        try:
            return float(duty_cycle)
        except (ValueError, TypeError):
            _LOGGER.error(f"Invalid duty_cycle value: {duty_cycle}")
            return 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        _LOGGER.debug(f"Turning on fan with percentage {percentage}")
        if percentage is None:
            minduty = await self.coordinator.controller.fan.getFanDutyCycleMin()
            await self.coordinator.controller.fan.setFanEnabled(True)
            await self.coordinator.controller.fan.setFanDutyCycle(float(minduty))
        else:
            await self.coordinator.controller.fan.setFanEnabled(True)
            await self.coordinator.controller.fan.setFanDutyCycle(float(percentage))
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Turning off fan")
        await self.coordinator.controller.fan.setFanEnabled(False)
        await self.coordinator.controller.fan.setFanDutyCycle(0)
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        _LOGGER.debug(f"Setting fan percentage to {percentage}")
        if percentage > 0:
            await self.coordinator.controller.fan.setFanEnabled(True)
        else:
            await self.coordinator.controller.fan.setFanEnabled(False)

        await self.coordinator.controller.fan.setFanDutyCycle(float(percentage))
        self.async_write_ha_state()


class CresOutputFanEntity(CoordinatorEntity, FanEntity):
    """Fan entity for CresControl outputs."""

    def __init__(self, coordinator, output_name, entry, is_pwm=False, custom_name=None):
        super().__init__(coordinator)
        self._output_name = output_name
        self._entry = entry
        self._is_pwm = is_pwm
        self._custom_name = custom_name or f"Fan{output_name.upper()}"
        self._device_id = f"{DOMAIN}_output_{output_name}_device"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

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
        if self._is_pwm:
            return (
                FanEntityFeature.SET_SPEED
                | FanEntityFeature.TURN_ON
                | FanEntityFeature.TURN_OFF
            )
        return FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

    @property
    def is_on(self):
        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        return output_data.get("enabled", False)

    @property
    def percentage(self):
        if not self._is_pwm:
            return 100 if self.is_on else 0

        output_data = self.coordinator.data.get("outputs", {}).get(self._output_name, {})
        voltage = output_data.get("voltage", 0)
        try:
            return int((float(voltage) / 10.0) * 100)
        except (ValueError, TypeError):
            return 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is not None and self._is_pwm:
            voltage = (percentage / 100.0) * 10.0
            await self.coordinator.controller.outputs.set_output_voltage(
                self._output_name, voltage
            )
            # Enable PWM for PWM outputs
            await self.coordinator.controller.outputs.set_output_pwm_enabled(
                self._output_name, True
            )

        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, True
        )
        # Update state directly without full refresh
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.outputs.set_output_enabled(
            self._output_name, False
        )
        if self._is_pwm:
            await self.coordinator.controller.outputs.set_output_voltage(
                self._output_name, 0
            )
        # Update state directly without full refresh
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        if not self._is_pwm:
            if percentage > 0:
                await self.async_turn_on()
            else:
                await self.async_turn_off()
            return

        voltage = (percentage / 100.0) * 10.0
        await self.coordinator.controller.outputs.set_output_voltage(
            self._output_name, voltage
        )

        if percentage > 0:
            await self.coordinator.controller.outputs.set_output_enabled(
                self._output_name, True
            )
        else:
            await self.coordinator.controller.outputs.set_output_enabled(
                self._output_name, False
            )

        # Update state directly without full refresh

        self.async_write_ha_state()


class CresSwitchFanEntity(CoordinatorEntity, FanEntity):
    """Fan entity for CresControl power switches with PWM."""

    def __init__(self, coordinator, switch_name, entry, custom_name=None):
        super().__init__(coordinator)
        self._switch_name = switch_name
        self._entry = entry
        self._custom_name = custom_name or f"Fan{switch_name.upper()}"
        self._device_id = f"{DOMAIN}_{switch_name}_device"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

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

    @property
    def is_on(self):
        switch_data = self.coordinator.data.get("switches", {}).get(self._switch_name, {})
        return switch_data.get("enabled", False)

    @property
    def percentage(self):
        switch_data = self.coordinator.data.get("switches", {}).get(self._switch_name, {})
        duty_cycle = switch_data.get("duty-cycle", 0)
        try:
            return int(float(duty_cycle))
        except (ValueError, TypeError):
            return 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is not None:
            await self.coordinator.controller.switches.set_duty_cycle(
                self._switch_name, percentage
            )

        await self.coordinator.controller.switches.set_pwm_enabled(self._switch_name, True)
        await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, True)
        # Update state directly without full refresh
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, False)
        await self.coordinator.controller.switches.set_duty_cycle(self._switch_name, 0)
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        await self.coordinator.controller.switches.set_duty_cycle(
            self._switch_name, percentage
        )

        if percentage > 0:
            await self.coordinator.controller.switches.set_pwm_enabled(self._switch_name, True)
            await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, True)
        else:
            await self.coordinator.controller.switches.set_switch_enabled(self._switch_name, False)

        # Update state directly without full refresh

        self.async_write_ha_state()
