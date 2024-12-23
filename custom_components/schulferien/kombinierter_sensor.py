"""Modul für den kombinierten Sensor,
     der sowohl Schulferien- als auch Feiertagsinformationen bereitstellt."""

import logging
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

class SchulferienFeiertagSensor(Entity):
    """Kombinierter Sensor für Schulferien und Feiertage."""

    def __init__(self, hass, config):
        """Initialisiert den kombinierten Sensor mit Konfigurationsdaten."""
        self._hass = hass
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.schulferien_feiertage")
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = None

    @property
    def name(self):
        """Gibt den Namen des Sensors zurück."""
        return self._name

    @property
    def unique_id(self):
        """Gibt die eindeutige ID des Sensors zurück."""
        return self._unique_id

    @property
    def state(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return "Ferientag/Feiertag" if self._state else "Kein Ferientag/Feiertag"

    async def async_update(self):
        """Kombiniert die Zustände der Schulferien- und Feiertag-Sensoren."""
        schulferien_state = self._hass.states.get(self._entity_ids["schulferien"])
        feiertag_state = self._hass.states.get(self._entity_ids["feiertag"])

        self._state = (
            (schulferien_state and schulferien_state.state == "Ferientag") or
            (feiertag_state and feiertag_state.state == "Feiertag")
        )
