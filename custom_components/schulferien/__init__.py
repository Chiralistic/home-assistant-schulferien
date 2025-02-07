"""Initialisierung der Schulferien und Feiertags-Integration."""

import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    """Set up Schulferien from a config entry."""
    _LOGGER.debug("Setting up Schulferien entry: %s", entry.title)

    # Registriere den Binary Sensor zusätzlich
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor"])

    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading Schulferien entry: %s", entry.title)

    # Lade sowohl Sensor als auch Binary Sensor
    unload_sensors = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    unload_binary_sensors = await hass.config_entries.async_forward_entry_unload(
        entry, "binary_sensor"
    )

    # Beide müssen erfolgreich sein
    return unload_sensors and unload_binary_sensors
