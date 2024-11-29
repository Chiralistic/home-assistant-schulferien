import aiofiles
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from icalendar import Calendar
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util.dt import now as dt_now
from homeassistant.const import CONF_NAME, CONF_STATE
from .const import API_URL, STANDARD_SPRACHE, STANDARD_LAND

_LOGGER = logging.getLogger(__name__)

CONF_HOUR = "hour"
CONF_MINUTE = "minute"
CONF_CACHE_DURATION = "cache_duration"
CONF_MAX_RETRIES = "max_retries"
CONF_COUNTRY_CODE = "country_code"

DEFAULT_HOUR = 3
DEFAULT_MINUTE = 0
DEFAULT_CACHE_DURATION = 24
DEFAULT_MAX_RETRIES = 3
DEFAULT_COUNTRY_CODE = STANDARD_LAND


async def fetch_holidays(country_code, subdivision):
    """
    Fetch holiday data from the OpenHolidays API asynchronously.
    """
    today = datetime.now()
    valid_from = today.strftime("%Y-%m-%d")
    valid_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    params = {
        "countryIsoCode": country_code,
        "subdivisionCode": subdivision,
        "languageIsoCode": STANDARD_SPRACHE,
        "validFrom": valid_from,
        "validTo": valid_to,
    }

    headers = {
        "Accept": "text/calendar",
        "User-Agent": "HomeAssistant-Schulferien-Integration",
    }

    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", API_URL, params)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, params=params, headers=headers, timeout=10) as response:
                response.raise_for_status()
                _LOGGER.debug("API-Antwort erhalten: %s", response.status)
                return await response.text()
        except aiohttp.ClientError as error:
            _LOGGER.error("API-Anfrage fehlgeschlagen: %s", error)
            raise RuntimeError(f"API-Anfrage fehlgeschlagen: {error}")


async def fetch_holidays_with_retry(country_code, subdivision, max_retries):
    retries = 0
    while retries < max_retries:
        try:
            return await fetch_holidays(country_code, subdivision)
        except RuntimeError as e:
            retries += 1
            _LOGGER.warning("API-Anfrage fehlgeschlagen (Versuch %d von %d): %s", retries, max_retries, e)
            await asyncio.sleep(5)
    _LOGGER.error("API-Anfrage nach %d Versuchen fehlgeschlagen.", max_retries)
    raise RuntimeError("API konnte nicht erreicht werden")


async def lade_cache(cache_file, cache_duration):
    if not cache_file.exists():
        _LOGGER.warning("Cache-Datei existiert nicht: %s", cache_file)
        return None

    try:
        async with aiofiles.open(cache_file, "r") as file:
            inhalt = await file.read()
            daten = json.loads(inhalt)

        zeitstempel = datetime.fromisoformat(daten["zeitstempel"])
        if datetime.now() - zeitstempel > timedelta(hours=cache_duration):
            _LOGGER.warning("Cache ist abgelaufen (älter als %d Stunden)", cache_duration)
            return None

        ferien = [
            {
                "name": urlaub["name"],
                "start_date": datetime.strptime(urlaub["start_date"], "%Y-%m-%d").date(),
                "end_date": datetime.strptime(urlaub["end_date"], "%Y-%m-%d").date(),
            }
            for urlaub in daten["ferien"]
        ]
        _LOGGER.debug("Cache erfolgreich geladen: %d Ferieneinträge", len(ferien))
        return ferien
    except (IOError, ValueError, KeyError) as e:
        _LOGGER.error("Fehler beim Laden des Caches: %s", e)
        raise RuntimeError(f"Fehler beim Laden des Caches: {e}")


async def speichere_cache(cache_file, ferien):
    ferien_serialisiert = [
        {
            "name": urlaub["name"],
            "start_date": urlaub["start_date"].strftime("%Y-%m-%d"),
            "end_date": urlaub["end_date"].strftime("%Y-%m-%d"),
        }
        for urlaub in ferien
    ]

    daten = {
        "zeitstempel": datetime.now().isoformat(),
        "ferien": ferien_serialisiert,
    }

    try:
        async with aiofiles.open(cache_file, "w") as file:
            await file.write(json.dumps(daten, ensure_ascii=False, indent=4))
        _LOGGER.debug("Cache erfolgreich gespeichert: %d Ferieneinträge", len(ferien))
    except IOError as e:
        _LOGGER.error("Fehler beim Speichern des Caches: %s", e)
        raise RuntimeError(f"Fehler beim Speichern des Caches: {e}")


def parse_ical(ical_data):
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
    _LOGGER.debug("iCalendar erfolgreich geparst: %d Ferieneinträge", len(holidays))
    return holidays


async def aktualisiere_ferien(country_code, bundesland, cache_file, cache_duration, max_retries):
    try:
        ical_data = await fetch_holidays_with_retry(country_code, bundesland, max_retries)
        holidays = parse_ical(ical_data)
        await speichere_cache(cache_file, holidays)
        return holidays
    except RuntimeError:
        _LOGGER.warning("Falle auf Cache zurück, da die API nicht erreichbar war.")
        return await lade_cache(cache_file, cache_duration)


class SchulferienSensor(Entity):
    def __init__(self, name, country_code, bundesland, hour, minute, cache_duration, max_retries):
        self._name = name
        self._country_code = country_code
        self._bundesland = bundesland
        self._hour = hour
        self._minute = minute
        self._cache_duration = cache_duration
        self._max_retries = max_retries
        self._heute_ferientag = None
        self._naechste_ferien_name = None
        self._naechste_ferien_start = None
        self._naechste_ferien_ende = None
        self._next_update_scheduled = False

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return "Ferientag" if self._heute_ferientag else "Kein Ferientag"

    @property
    def extra_state_attributes(self):
        return {
            "Nächste Ferien": self._naechste_ferien_name,
            "Beginn": self._naechste_ferien_start,
            "Ende": self._naechste_ferien_ende,
        }

    async def async_schedule_update(self, hass):
        now = dt_now()
        next_update = now.replace(hour=self._hour, minute=self._minute, second=0, microsecond=0)
        if now >= next_update:
            next_update += timedelta(days=1)

        _LOGGER.debug("Nächste Aktualisierung für %s geplant", next_update)
        async_track_point_in_time(hass, self.async_update_callback, next_update)
        self._next_update_scheduled = True

    async def async_update_callback(self, time):
        _LOGGER.debug("Aktualisierung um %s gestartet", time)
        await self.async_update()
        self._next_update_scheduled = False

    async def async_update(self):
        today = datetime.now().date()
        cache_file = Path(__file__).parent / "ferien_cache.json"
        holidays = await aktualisiere_ferien(
            self._country_code, self._bundesland, cache_file, self._cache_duration, self._max_retries
        )

        if holidays is None:
            self._heute_ferientag = None
            self._naechste_ferien_name = None
            self._naechste_ferien_start = None
            self._naechste_ferien_ende = None
            _LOGGER.warning("Keine Ferieninformationen verfügbar.")
            return

        self._heute_ferientag = any(
            holiday["start_date"] <= today <= holiday["end_date"] for holiday in holidays
        )

        future_holidays = [
            holiday for holiday in holidays if holiday["start_date"] > today
        ]
        if future_holidays:
            next_holiday = min(
                future_holidays, key=lambda holiday: holiday["start_date"]
            )
            self._naechste_ferien_name = next_holiday["name"]
            self._naechste_ferien_start = next_holiday["start_date"].strftime(
                "%d.%m.%Y"
            )
            self._naechste_ferien_ende = next_holiday["end_date"].strftime(
                "%d.%m.%Y"
            )
        else:
            self._naechste_ferien_name = None
            self._naechste_ferien_start = None
            self._naechste_ferien_ende = None

        _LOGGER.debug(
            "Sensor aktualisiert: Heute Ferientag: %s, Nächste Ferien: %s",
            self._heute_ferientag,
            self._naechste_ferien_name,
        )

        if not self._next_update_scheduled:
            await self.async_schedule_update(self.hass)

    async def async_added_to_hass(self):
        _LOGGER.debug("SchulferienSensor hinzugefügt.")
        await self.async_schedule_update(self.hass)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME, "Schulferien")
    country_code = config.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE)
    bundesland = config.get(CONF_STATE, "DE-NI")
    hour = config.get(CONF_HOUR, DEFAULT_HOUR)
    minute = config.get(CONF_MINUTE, DEFAULT_MINUTE)
    cache_duration = config.get(CONF_CACHE_DURATION, DEFAULT_CACHE_DURATION)
    max_retries = config.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)
    async_add_entities(
        [
            SchulferienSensor(
                name, country_code, bundesland, hour, minute, cache_duration, max_retries
            )
        ]
    )
