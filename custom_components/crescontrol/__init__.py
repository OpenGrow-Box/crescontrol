import logging
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.crescontrol.const import (
    DOMAIN,
    CONF_HOST,
    CONF_OUTPUTS,
    CONF_SWITCHES,
    CONF_INPUTS,
    CONF_FAN,
)
from custom_components.crescontrol.cres_control import CresControl
from custom_components.crescontrol.coordinator import ExampleCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the CresControl integration."""
    _LOGGER.debug("Initializing CresControl Integration")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CresControl from a config entry."""
    _LOGGER.debug("Setup of configuration entries started")

    host = entry.data[CONF_HOST]
    
    # Build config for CresControl
    config = {
        "outputs": entry.data.get(CONF_OUTPUTS, {}),
        "switches": entry.data.get(CONF_SWITCHES, {}),
        "inputs": entry.data.get(CONF_INPUTS, {}),
        "fan": entry.data.get(CONF_FAN, {}),
    }
    
    # Create shared aiohttp session for all subsystems
    session = aiohttp.ClientSession()
    control = CresControl(host, config, session)

    if not await control.test_connection():
        _LOGGER.error(f"Connection test to {host} failed.")
        await control.async_close()
        return False

    coordinator = ExampleCoordinator(hass, entry, control)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "control": control,
        "coordinator": coordinator,
    }

    await coordinator.async_config_entry_first_refresh()

    # Auto-enable PWM for configured PWM outputs (A, B) on startup
    outputs = entry.data.get(CONF_OUTPUTS, {})
    pwm_outputs = ["a", "b"]
    for output_name, output_cfg in outputs.items():
        if output_name in pwm_outputs and output_cfg.get("type") != "none":
            try:
                await control.outputs.set_output_pwm_enabled(output_name, True)
                _LOGGER.debug(f"Auto-enabled PWM for output {output_name}")
            except Exception as e:
                _LOGGER.warning(f"Failed to auto-enable PWM for output {output_name}: {e}")

    # Determine which platforms to load based on configuration
    platforms = set()
    
    outputs = entry.data.get(CONF_OUTPUTS, {})
    switches = entry.data.get(CONF_SWITCHES, {})
    inputs = entry.data.get(CONF_INPUTS, {})
    fan = entry.data.get(CONF_FAN, {})
    
    # Check if this is an old config entry (backward compatibility)
    is_old_config = not (outputs or switches or inputs or fan)
    
    if is_old_config:
        _LOGGER.warning("Old config format detected - loading all platforms for backward compatibility. Please reconfigure the integration.")
        platforms = {"light", "switch", "sensor", "fan", "number"}
    else:
        # Check outputs for entity types
        for output_cfg in outputs.values():
            entity_type = output_cfg.get("type", "")
            if entity_type == "light":
                platforms.add("light")
            elif entity_type == "switch":
                platforms.add("switch")
            elif entity_type == "fan":
                platforms.add("fan")
            elif entity_type == "number":
                platforms.add("number")

        # Check switches for entity types
        for switch_cfg in switches.values():
            entity_type = switch_cfg.get("type", "")
            if entity_type == "light":
                platforms.add("light")
            elif entity_type == "switch":
                platforms.add("switch")
            elif entity_type == "fan":
                platforms.add("fan")
            elif entity_type == "number":
                platforms.add("number")

        # Always load sensor platform for built-in sensors (climate device)
        # Also load if inputs are configured as sensors
        platforms.add("sensor")

        # Built-in fan
        if fan.get("enabled", False):
            fan_type = fan.get("type", "")
            if fan_type == "light":
                platforms.add("light")
            elif fan_type == "fan":
                platforms.add("fan")
            elif fan_type == "number":
                platforms.add("number")

        if not platforms:
            _LOGGER.warning("No platforms configured for CresControl")
            return True

    # Always load number platform for calibration entities
    platforms.add("number")

    await hass.config_entries.async_forward_entry_setups(entry, list(platforms))
    
    for platform in platforms:
        _LOGGER.debug(f"Platform {platform} loaded")

    _LOGGER.debug("CresControl Integration successfully set up")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unloading of an entry."""
    _LOGGER.debug("Unloading configuration entries started")

    # Determine which platforms were loaded
    platforms = set()
    
    outputs = entry.data.get(CONF_OUTPUTS, {})
    switches = entry.data.get(CONF_SWITCHES, {})
    inputs = entry.data.get(CONF_INPUTS, {})
    fan = entry.data.get(CONF_FAN, {})

    for output_cfg in outputs.values():
        entity_type = output_cfg.get("type", "")
        if entity_type in ["light", "switch", "fan", "number"]:
            platforms.add(entity_type if entity_type != "number" else "number")

    for switch_cfg in switches.values():
        entity_type = switch_cfg.get("type", "")
        if entity_type in ["light", "switch", "fan", "number"]:
            platforms.add(entity_type if entity_type != "number" else "number")

    if inputs:
        platforms.add("sensor")

    if fan.get("enabled", False):
        fan_type = fan.get("type", "")
        if fan_type in ["light", "fan", "number"]:
            platforms.add(fan_type if fan_type != "number" else "number")

    platforms.add("number")  # Always unload number platform

    unload_ok = await hass.config_entries.async_unload_platforms(entry, list(platforms))

    if unload_ok:
        # Close shared aiohttp session
        control = hass.data[DOMAIN].get(entry.entry_id, {}).get("control")
        if control:
            await control.async_close()
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("CresControl Integration successfully unloaded")
    else:
        _LOGGER.error("Error unloading CresControl Integration")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
