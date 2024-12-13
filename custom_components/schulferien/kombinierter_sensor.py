"""Modul für den kombinierten Sensor,
    der sowohl Schulferien- als auch Feiertagsinformationen bereitstellt."""

import logging
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

class SchulferienFeiertagSensor(Entity):
    """Kombinierter Sensor für Schulferien und Feiertage."""

    def __init__(self, hass, config):
        self._hass = hass
        self._name = config["name"]
        self._schulferien_entity_id = config["schulferien_entity_id"]
        self._feiertag_entity_id = config["feiertag_entity_id"]
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return "sensor.schulferien_feiertag"

    @property
    def state(self):
        return "Ferientag/Feiertag" if self._state else "Kein Ferientag/Feiertag"

    @property
    def extra_state_attributes(self):
        return {
            "Schulferien Sensor": self._schulferien_entity_id,
            "Feiertag Sensor": self._feiertag_entity_id,
        }

    async def async_update(self):
        """Kombiniere die Zustände der Schulferien- und Feiertag-Sensoren."""
        schulferien_state = self._hass.states.get(self._schulferien_entity_id)
        feiertag_state = self._hass.states.get(self._feiertag_entity_id)

        schulferien_zustand = schulferien_state.state if schulferien_state else "None"
        _LOGGER.debug("Schulferien-Sensorzustand: %s", schulferien_zustand)

        feiertag_zustand = feiertag_state.state if feiertag_state else "None"
        _LOGGER.debug("Feiertag-Sensorzustand: %s", feiertag_zustand)

        self._state = (
            (schulferien_state and schulferien_state.state == "Ferientag") or
            (feiertag_state and feiertag_state.state == "Feiertag")
        )

        _LOGGER.debug("Kombinierter Sensorzustand: %s", self.state)
