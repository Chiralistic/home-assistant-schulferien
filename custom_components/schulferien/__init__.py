from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Globale Variable zur Verwaltung der Integration
PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """
    Wird aufgerufen, wenn Home Assistant startet.
    Diese Methode ist notwendig, um YAML-Konfigurationen zu unterstützen.
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Setzt die Integration basierend auf einer UI-Konfiguration auf.
    """
    hass.data.setdefault(DOMAIN, {})

    # Plattformen (z. B. Sensoren) laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Entfernt die Integration, wenn sie deaktiviert wird.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
