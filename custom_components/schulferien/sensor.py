import logging
from datetime import datetime
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, REGION_TO_API, COUNTRY_TO_API

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Schulferien sensor from a config entry."""
    name = entry.title
    country_code = entry.data["country_code"]
    state_code = entry.data["state"]

    async_add_entities([SchulferienSensor(name, country_code, state_code)])


class SchulferienSensor(Entity):
    """Representation of the Schulferien sensor."""

    def __init__(self, name: str, country_code: str, state_code: str):
        self._name = name
        self._country_code = country_code
        self._state_code = state_code
        self._is_holiday_today = None
        self._next_holiday_name = None
        self._next_holiday_start = None
        self._next_holiday_end = None

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return "Ferientag" if self._is_holiday_today else "Kein Ferientag"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        country_name = COUNTRY_TO_API.get(self._country_code, self._country_code)
        region_name = REGION_TO_API.get(self._country_code, {}).get(self._state_code, self._state_code)

        return {
            "Nächste Ferien": self._next_holiday_name,
            "Beginn": self._next_holiday_start,
            "Ende": self._next_holiday_end,
            "Land": f"{country_name} ({self._country_code})",
            "Region": f"{region_name} ({self._state_code})",
        }

    async def async_update(self):
        """Update the sensor state."""
        today = datetime.now().date()

        try:
            # Simulate loading holiday data from API (replace with real API logic)
            holidays = [
                {"name": "Weihnachtsferien", "start_date": datetime(2024, 12, 23).date(), "end_date": datetime(2025, 1, 6).date()},
                {"name": "Osterferien", "start_date": datetime(2025, 3, 29).date(), "end_date": datetime(2025, 4, 12).date()},
            ]

            # Check if today is a holiday
            self._is_holiday_today = any(
                holiday["start_date"] <= today <= holiday["end_date"] for holiday in holidays
            )

            # Find the next holiday
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

        except Exception as e:
            _LOGGER.error(f"Fehler beim Laden der Daten: {e}")
            self._is_holiday_today = None
