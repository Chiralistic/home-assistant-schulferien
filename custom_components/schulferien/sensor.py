import aiofiles  # Für asynchrone Dateizugriffe / For asynchronous file access
import aiohttp
import json
import logging
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from icalendar import Calendar
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_NAME, CONF_STATE
from .const import API_URL, STANDARD_SPRACHE, STANDARD_LAND

# Initialisiere Logger / Initialize logger
_LOGGER = logging.getLogger(__name__)

CACHE_DATEI = Path(__file__).parent / "ferien_cache.json"
CACHE_GUELTIGKEIT_STUNDEN = 24  # Cache bleibt 24 Stunden gültig
MAX_RETRIES = 3  # Maximale Anzahl von Wiederholungen


async def fetch_holidays(subdivision):
    """
    Fetch holiday data from the OpenHolidays API asynchronously.
    """
    today = datetime.now()
    valid_from = today.strftime("%Y-%m-%d")
    valid_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    params = {
        "countryIsoCode": STANDARD_LAND,
        "subdivisionCode": subdivision,
        "languageIsoCode": STANDARD_SPRACHE,
        "validFrom": valid_from,
        "validTo": valid_to,
    }

    headers = {
        "Accept": "text/calendar",
        "User-Agent": "HomeAssistant-Schulferien-Integration",
    }

    ssl_context = ssl.create_default_context()

    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", API_URL, params)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, params=params, headers=headers, ssl=ssl_context, timeout=10) as response:
                response.raise_for_status()
                _LOGGER.debug("API-Antwort erhalten: %s", response.status)
                return await response.text()
        except aiohttp.ClientError as error:
            _LOGGER.error("API-Anfrage fehlgeschlagen: %s", error)
            raise RuntimeError(f"API-Anfrage fehlgeschlagen: {error}")


async def fetch_holidays_with_retry(subdivision):
    """
    Wiederholt die API-Anfrage bei Fehlern.
    Retries the API request in case of failures.
    """
    retries = 0
    while retries < MAX_RETRIES:
        try:
            return await fetch_holidays(subdivision)
        except RuntimeError as e:
            retries += 1
            _LOGGER.warning("API-Anfrage fehlgeschlagen (Versuch %d von %d): %s", retries, MAX_RETRIES, e)
            await asyncio.sleep(5)  # Wartezeit vor erneutem Versuch
    _LOGGER.error("API-Anfrage nach %d Versuchen fehlgeschlagen.", MAX_RETRIES)
    raise RuntimeError("API konnte nicht erreicht werden")


async def lade_cache():
    """
    Lädt die zwischengespeicherten Ferien-Daten aus der lokalen Datei.
    Loads cached holiday data from the local file.
    """
    if not CACHE_DATEI.exists():
        _LOGGER.warning("Cache-Datei existiert nicht: %s", CACHE_DATEI)
        return None

    try:
        async with aiofiles.open(CACHE_DATEI, "r") as file:
            inhalt = await file.read()
            daten = json.loads(inhalt)

        zeitstempel = datetime.fromisoformat(daten["zeitstempel"])
        if datetime.now() - zeitstempel > timedelta(hours=CACHE_GUELTIGKEIT_STUNDEN):
            _LOGGER.warning("Cache ist abgelaufen (älter als %d Stunden)", CACHE_GUELTIGKEIT_STUNDEN)
            return None

        # Konvertiere die JSON-Daten zurück in `date`-Objekte
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


async def speichere_cache(ferien):
    """
    Speichert die Ferien-Daten in der lokalen Cache-Datei.
    Saves holiday data to the local cache file.
    """
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
        async with aiofiles.open(CACHE_DATEI, "w") as file:
            await file.write(json.dumps(daten, ensure_ascii=False, indent=4))
        _LOGGER.debug("Cache erfolgreich gespeichert: %d Ferieneinträge", len(ferien))
    except IOError as e:
        _LOGGER.error("Fehler beim Speichern des Caches: %s", e)
        raise RuntimeError(f"Fehler beim Speichern des Caches: {e}")


def parse_ical(ical_data):
    """
    Parst iCalendar-Daten und extrahiert Ferien.
    Parses iCalendar data and extracts holidays.
    """
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


async def aktualisiere_ferien(bundesland):
    """
    Aktualisiert Ferieninformationen und speichert sie im Cache.
    Updates holiday information and saves it to the cache.
    """
    try:
        ical_data = await fetch_holidays_with_retry(bundesland)
        holidays = parse_ical(ical_data)
        await speichere_cache(holidays)
        return holidays
    except RuntimeError:
        _LOGGER.warning("Falle auf Cache zurück, da die API nicht erreichbar war.")
        return await lade_cache()


class SchulferienSensor(Entity):
    def __init__(self, name, bundesland):
        self._name = name
        self._bundesland = bundesland
        self._heute_ferientag = None  # Aktueller Status
        self._naechste_ferien_name = None  # Nächste Ferien
        self._naechste_ferien_start = None  # Beginn der nächsten Ferien
        self._naechste_ferien_ende = None  # Ende der nächsten Ferien

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return "Ferientag" if self._heute_ferientag else "Kein Ferientag"

    @property
    def extra_state_attributes(self):
        """
        Zusätzliche Attribute für die Anzeige im Sensor.
        """
        return {
            "Nächste Ferien": self._naechste_ferien_name,
            "Beginn": self._naechste_ferien_start,
            "Ende": self._naechste_ferien_ende,
        }

    async def async_update(self):
        """
        Aktualisiert den Sensor, ruft Ferien ab und prüft, ob heute ein Ferientag ist.
        """
        today = datetime.now().date()
        holidays = await aktualisiere_ferien(self._bundesland)

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


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME, "Schulferien")
    bundesland = config.get(CONF_STATE, "DE-NI")
    async_add_entities([SchulferienSensor(name, bundesland)])
