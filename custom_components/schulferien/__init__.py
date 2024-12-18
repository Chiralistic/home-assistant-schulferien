"""Initialisierung der Schulferien und Feiertags-Integration."""

import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    """Set up Schulferien from a config entry."""
    _LOGGER.debug("Setting up Schulferien entry: %s", entry.title)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading Schulferien entry: %s", entry.title)
    return await hass.config_entries.async_forward_entry_unloads(entry, ["sensor"])
