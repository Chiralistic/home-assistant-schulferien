import logging
from datetime import datetime
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """
    Setzt die Sensoren basierend auf einer Konfigurationseintragung auf.
    """
    # Hole die Konfigurationsdaten
    name = entry.data.get("name", "Schulferien")
    country_code = entry.data.get("country_code", "DE")
    state = entry.data.get("state", "DE-NI")

    # Sensor erstellen und hinzufügen
    async_add_entities([SchulferienSensor(name, country_code, state)])


class SchulferienSensor(Entity):
    """
    Sensor-Klasse für die Schulferien.
    """

    def __init__(self, name: str, country_code: str, state: str):
        self._name = name
        self._country_code = country_code
        self._state = state
        self._is_holiday_today = None
        self._next_holiday_name = None
        self._next_holiday_start = None
        self._next_holiday_end = None

    @property
    def name(self):
        """Name des Sensors."""
        return self._name

    @property
    def state(self):
        """Aktueller Status: 'Ferientag' oder 'Kein Ferientag'."""
        return "Ferientag" if self._is_holiday_today else "Kein Ferientag"

    @property
    def extra_state_attributes(self):
        """
        Zusätzliche Attribute, die im Sensor angezeigt werden.
        """
        return {
            "Nächste Ferien": self._next_holiday_name,
            "Beginn": self._next_holiday_start,
            "Ende": self._next_holiday_end,
        }

    async def async_update(self):
        """
        Aktualisiert die Sensor-Daten.
        """
        today = datetime.now().date()

        # Dummy-Daten für Tests (ersetze dies durch API-Aufruf in einer echten Integration)
        holidays = [
            {"name": "Weihnachtsferien", "start_date": datetime(2024, 12, 23).date(), "end_date": datetime(2025, 1, 6).date()},
            {"name": "Osterferien", "start_date": datetime(2025, 3, 29).date(), "end_date": datetime(2025, 4, 12).date()},
        ]

        # Prüfen, ob heute ein Ferientag ist
        self._is_holiday_today = any(
            holiday["start_date"] <= today <= holiday["end_date"] for holiday in holidays
        )

        # Nächste Ferien ermitteln
        future_holidays = [h for h in holidays if h["start_date"] > today]
        if future_holidays:
            next_holiday = min(future_holidays, key=lambda h: h["start_date"])
            self._next_holiday_name = next_holiday["name"]
            self._next_holiday_start = next_holiday["start_date"].strftime("%d.%m.%Y")
            self._next_holiday_end = next_holiday["end_date"].strftime("%d.%m.%Y")
        else:
            self._next_holiday_name = None
            self._next_holiday_start = None
            self._next_holiday_end = None
