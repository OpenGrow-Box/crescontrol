import logging
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup fan platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

   
    fan_entity = CresFanEntity(coordinator, entry.entry_id)
    async_add_entities(
        [fan_entity], True
    ) 

    _LOGGER.debug(f"Fan entity {fan_entity.name} added to Home Assistant")


class CresFanEntity(CoordinatorEntity, FanEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_id = f"{DOMAIN}_fan_device" 

    @property
    def unique_id(self):
        return f"crescontrol_fan_{self._entry_id}"

    @property
    def name(self):
        return "CresControl Fan"

    @property
    def device_info(self):
        """Return device information about this entity, ensuring RPM sensor is part of this device."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": "CresControl Fan",
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
        """Check if the fan is on using coordinator data."""
        fan_data = self.coordinator.data.get("fan", {})
        enabled = fan_data.get("enabled", False)
        duty_cycle = fan_data.get("dutyCycle", 0)

        try:
            duty_cycle = float(duty_cycle)
        except (ValueError, TypeError):
            duty_cycle = 0

      
        if not enabled:
            return False

        return enabled and duty_cycle > 0

    @property
    def percentage(self):
        """Return the current speed percentage from coordinator data."""
        fan_data = self.coordinator.data.get("fan", {})
        enabled = fan_data.get("enabled", False)
        duty_cycle = fan_data.get("dutyCycle", 0)


        if enabled == False:
            return 0

        try:
            return float(duty_cycle)
        except (ValueError, TypeError):
            _LOGGER.error(f"Invalid duty_cycle value: {duty_cycle}")
            return 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        """Turn on the fan using the coordinator."""
        _LOGGER.debug(f"Turning on fan with percentage {percentage}")
        if percentage == None:
            minduty =  await self.coordinator.controller.fan.getFanDutyCycleMin()
            await self.coordinator.controller.fan.setFanEnabled(True)
            await self.coordinator.controller.fan.setFanDutyCycle(float(minduty))
            await self.coordinator.async_update_single_device("fan")
            self.async_write_ha_state()

        else:
            await self.coordinator.controller.fan.setFanEnabled(True)
            await self.coordinator.controller.fan.setFanDutyCycle(float(percentage))
            await self.coordinator.async_update_single_device("fan")
            self.async_write_ha_state()


    async def async_turn_off(self, **kwargs):
        """Turn off the fan using the coordinator."""
        _LOGGER.debug("Turning off fan")

        
        await self.coordinator.controller.fan.setFanEnabled(False)
        await self.coordinator.controller.fan.setFanDutyCycle(0)
        await self.coordinator.async_update_single_device("fan")
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        """Set the speed percentage of the fan using the coordinator."""
        _LOGGER.debug(f"Setting fan percentage to {percentage}")

       
        if percentage > 0:
            await self.coordinator.controller.fan.setFanEnabled(True)
        else:
            await self.coordinator.controller.fan.setFanEnabled(False)

        await self.coordinator.controller.fan.setFanDutyCycle(float(percentage))

      
        await self.coordinator.async_update_single_device("fan")
        self.async_write_ha_state()

    async def async_set_value(self, value: float):
        await self.coordinator.async_update_single_device("fan")
        self.async_write_ha_state()
