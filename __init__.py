import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .cres_control import CresControl
from .coordinator import ExampleCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the CresControl integration."""
    _LOGGER.debug("Initialisiere CresControl Integration")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setup der Konfigurationseinträge gestartet")

    host = entry.data["host"]
    control = CresControl(host)

    if not await control.test_connection():
        _LOGGER.error(f"Verbindungstest zu {host} fehlgeschlagen.")
        return False

    coordinator = ExampleCoordinator(hass, entry, control)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "control": control,
        "coordinator": coordinator,
    }

    await coordinator.async_config_entry_first_refresh()

    platforms = ["fan", "sensor", "switch", "number"]
    for platform in platforms:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )
        _LOGGER.debug(f"Plattform {platform} wird geladen")

    _LOGGER.debug("CresControl Integration erfolgreich eingerichtet")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unloading of an entry."""
    _LOGGER.debug("Entladen der Konfigurationseinträge gestartet")

    platforms = ["fan", "sensor", "switch", "number"]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("CresControl Integration erfolgreich entladen")
    else:
        _LOGGER.error("Fehler beim Entladen der CresControl Integration")

    return unload_ok
