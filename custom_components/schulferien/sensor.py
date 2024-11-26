import aiohttp
import asyncio
from datetime import datetime, timedelta
from icalendar import Calendar
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_NAME, CONF_STATE
from .const import (
    DOMAIN,
    API_URL,
    DEFAULT_LANGUAGE,
    DEFAULT_COUNTRY,
)


async def fetch_holidays(subdivision):
    """Asynchronously fetch holiday data from the OpenHolidays API."""
    today = datetime.now()
    valid_from = today.strftime("%Y-%m-%d")
    valid_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    params = {
        "countryIsoCode": DEFAULT_COUNTRY,
        "subdivisionCode": subdivision,
        "languageIsoCode": DEFAULT_LANGUAGE,
        "validFrom": valid_from,
        "validTo": valid_to,
    }
    headers = {"accept": "text/calendar"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, params=params, headers=headers, timeout=10) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as error:
            raise RuntimeError(f"API request failed: {error}")


def parse_ical(ical_data):
    """Parse iCalendar data to extract holidays."""
    holidays = []
    calendar = Calendar.from_ical(ical_data)
    for component in calendar.walk():
        if component.name == "VEVENT":
            start_date = component.get("dtstart").dt
            end_date = component.get("dtend").dt
            name = str(component.get("summary"))
            holidays.append(
                {
                    "name": name,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
    return holidays


class SchoolHolidaySensor(Entity):
    """Sensor to indicate whether today is a school holiday and provide future holiday info."""

    def __init__(self, name, subdivision):
        self._name = name
        self._subdivision = subdivision
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
        return {
            "next_holiday_name": self._next_holiday_name,
            "next_holiday_start": self._next_holiday_start,
            "next_holiday_end": self._next_holiday_end,
        }

    async def async_update(self):
        """Asynchronously update sensor state."""
        today = datetime.now().date()
        try:
            ical_data = await fetch_holidays(self._subdivision)
            holidays = parse_ical(ical_data)
        except RuntimeError as e:
            holidays = []
            self._is_holiday_today = None
            self._next_holiday_name = None
            self._next_holiday_start = None
            self._next_holiday_end = None
            return

        # Check if today is a holiday
        self._is_holiday_today = any(
            holiday["start_date"] <= today <= holiday["end_date"] for holiday in holidays
        )

        # Find the next holiday
        future_holidays = [
            holiday for holiday in holidays if holiday["start_date"] > today
        ]
        if future_holidays:
            next_holiday = min(
                future_holidays, key=lambda h: h["start_date"]
            )
            self._next_holiday_name = next_holiday["name"]
            self._next_holiday_start = next_holiday["start_date"].strftime("%d.%m.%Y")
            self._next_holiday_end = next_holiday["end_date"].strftime("%d.%m.%Y")
        else:
            self._next_holiday_name = None
            self._next_holiday_start = None
            self._next_holiday_end = None


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the SchoolHolidaySensor platform."""
    name = config.get(CONF_NAME, "Schulferien")
    subdivision = config.get(CONF_STATE, "DE-NI")
    async_add_entities([SchoolHolidaySensor(name, subdivision)])
