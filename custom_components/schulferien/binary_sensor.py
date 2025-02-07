import logging
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

_LOGGER = logging.getLogger(__name__)

# Definition der EntityDescription mit Übersetzungsschlüssel
SCHULFERIEN_FEIERTAG_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_feiertag",
    name="Schulferien/Feiertage",
    translation_key="schulferien_feiertag",  # Bezug zur Übersetzung
)

class SchulferienFeiertagBinarySensor(BinarySensorEntity):
    """Kombinierter Binärsensor für Schulferien und Feiertage."""

    def __init__(self, hass, config):
        """Initialisiert den kombinierten Binärsensor mit Konfigurationsdaten."""
        self.entity_description = SCHULFERIEN_FEIERTAG_BINARY_SENSOR
        self._hass = hass
        self._unique_id = config.get("unique_id", "binary_sensor.schulferien_feiertage")
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        """Gibt die eindeutige ID des Sensors zurück."""
        return self._unique_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Kombiniert die Zustände der Schulferien- und Feiertag-Sensoren."""
        schulferien_state = self._hass.states.get(self._entity_ids["schulferien"])
        feiertag_state = self._hass.states.get(self._entity_ids["feiertag"])

        self._state = (
            (schulferien_state and schulferien_state.state == "ferientag") or
            (feiertag_state and feiertag_state.state == "feiertag")
        )


async def async_setup_entry(hass, entry, async_add_entities):
    """Setze den Kombinierten Binary Sensor für Schulferien und Feiertage auf."""
    _LOGGER.debug("Initialisiere kombinierten Binärsensor für Schulferien und Feiertage.")

    # Konfiguration aus dem Eintrag holen
    config = {
        "schulferien_entity_id": "sensor.schulferien",  # Beispiel für Entitäts-ID der Schulferien
        "feiertag_entity_id": "sensor.feiertag",  # Beispiel für Entitäts-ID der Feiertage
        "unique_id": "binary_sensor.schulferien_feiertage"
    }

    # Erstelle den Sensor
    binary_sensor = SchulferienFeiertagBinarySensor(hass, config)

    # Füge den Sensor zu Home Assistant hinzu
    async_add_entities([binary_sensor])
