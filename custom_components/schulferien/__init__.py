"""Initialisierung der Schulferien und Feiertags-Integration.

Entry Point für Home Assistant. Forwardet das Setup/Unload an
sensor.py und binary_sensor.py.

Warum beide Entity-Types? Sensoren liefern detaillierte Werte
("ferientag", "kein_ferientag" mit Attributen). BinarySensoren
liefern einfache ON/OFF-Zustände für Automatisierungen.
Beide ergänzen sich und dienen unterschiedlichen Use-Cases.
"""

import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    """Setup der Schulferien-Integration aus einem Config Entry.

    Warum ["sensor", "binary_sensor"] in einem Aufruf? Beide Entity-Types
    werden gleichzeitig geladen — spart einen HA-Call. Die Reihenfolge
    (sensor vor binary_sensor) ist wichtig: BinarySensoren lesen States
    der Sensoren über hass.states.get() und benötigen diese daher zuerst.

    Args:
        hass: Home Assistant Instanz.
        entry: Config entry mit Land/Region-Konfiguration.

    Returns:
        True wenn Setup erfolgreich.
    """
    _LOGGER.debug("Setting up Schulferien entry: %s", entry.title)

    # Beide Entity-Types gleichzeitig laden (sensor vor binary_sensor)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor"])

    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry.

    Warum beide Unloads verknüpft? Beide Entity-Types müssen erfolgreich
    entladen werden. Wenn einer fehlschlägt, bleibt die Integration im
    inkonsistenten Zustand.

    Args:
        hass: Home Assistant Instanz.
        entry: Config entry zum Entladen.

    Returns:
        True wenn beide Unloads erfolgreich waren.
    """
    _LOGGER.debug("Unloading Schulferien entry: %s", entry.title)

    # Lade sowohl Sensor als auch Binary Sensor
    unload_sensors = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    unload_binary_sensors = await hass.config_entries.async_forward_entry_unload(
        entry, "binary_sensor"
    )

    # Beide müssen erfolgreich sein — inkonsistenter Zustand vermeiden
    return unload_sensors and unload_binary_sensors
