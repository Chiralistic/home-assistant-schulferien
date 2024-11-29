import aiofiles  # Für asynchrone Dateizugriffe
import aiohttp  # Für HTTP-Anfragen
import json  # Für das Speichern und Laden von JSON-Daten
import logging  # Für das Debugging und Protokollierung
from datetime import datetime, timedelta  # Für Datumsoperationen
from pathlib import Path  # Für Dateipfade
from icalendar import Calendar  # Zum Parsen von iCalendar-Daten
from homeassistant.helpers.entity import Entity  # Basis für Home Assistant Entitäten
from homeassistant.helpers.event import async_track_point_in_time  # Planung von zukünftigen Updates
from homeassistant.util.dt import now as dt_now  # Abrufen des aktuellen Datums/Zeit
from homeassistant.const import CONF_NAME, CONF_STATE  # Standardkonstanten
from .const import API_URL, STANDARD_SPRACHE, STANDARD_LAND  # Konstante Werte aus const.py

_LOGGER = logging.getLogger(__name__)

# Konfiguration von festen Werten
CACHE_GUELTIGKEIT_STUNDEN = 24  # Cache bleibt 24 Stunden gültig
MAX_RETRIES = 3  # Maximale Anzahl von Wiederholungen bei API-Fehlern
CACHE_DATEI = Path(__file__).parent / "ferien_cache.json"  # Speicherort der Cache-Datei


async def fetch_holidays(country_code, subdivision):
    """
    Ruft Ferieninformationen von der OpenHolidays-API ab.
    """
    today = datetime.now()
    valid_from = today.strftime("%Y-%m-%d")  # Aktuelles Datum
    valid_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")  # Ein Jahr in die Zukunft

    params = {
        "countryIsoCode": country_code,
        "subdivisionCode": subdivision,
        "languageIsoCode": STANDARD_SPRACHE,
        "validFrom": valid_from,
        "validTo": valid_to,
    }

    headers = {
        "Accept": "text/calendar",  # Erwartetes Format der API
        "User-Agent": "HomeAssistant-Schulferien",  # Nutzer-Agent
    }

    async with aiohttp.ClientSession() as session:
        for retry in range(MAX_RETRIES):
            try:
                async with session.get(API_URL, params=params, headers=headers, timeout=10) as response:
                    response.raise_for_status()  # Fehler auslösen, wenn der Status nicht 2xx ist
                    return await response.text()  # Inhalt der Antwort zurückgeben
            except aiohttp.ClientError as error:
                _LOGGER.warning("Fehler bei API-Anfrage (Versuch %d): %s", retry + 1, error)
                if retry < MAX_RETRIES - 1:
                    await asyncio.sleep(5)  # Verzögerung vor Wiederholung
        raise RuntimeError("Maximale Anzahl von API-Anfragen erreicht.")


async def lade_cache():
    """
    Lädt zwischengespeicherte Daten aus einer lokalen Datei.
    """
    if not CACHE_DATEI.exists():  # Überprüfen, ob die Datei existiert
        _LOGGER.warning("Cache-Datei existiert nicht.")
        return None

    try:
        async with aiofiles.open(CACHE_DATEI, "r") as file:
            daten = json.loads(await file.read())  # JSON-Daten laden

        # Überprüfen, ob der Cache noch gültig ist
        zeitstempel = datetime.fromisoformat(daten["zeitstempel"])
        if datetime.now() - zeitstempel > timedelta(hours=CACHE_GUELTIGKEIT_STUNDEN):
            _LOGGER.warning("Cache ist abgelaufen.")
            return None

        return daten["ferien"]  # Ferieninformationen zurückgeben
    except (IOError, ValueError, KeyError) as e:
        _LOGGER.error("Fehler beim Laden des Caches: %s", e)
        return None


async def speichere_cache(ferien):
    """
    Speichert die Ferieninformationen in einer Cache-Datei.
    """
    daten = {
        "zeitstempel": datetime.now().isoformat(),  # Zeitstempel hinzufügen
        "ferien": ferien,
    }

    try:
        async with aiofiles.open(CACHE_DATEI, "w") as file:
            await file.write(json.dumps(daten, ensure_ascii=False, indent=4))
            _LOGGER.debug("Cache erfolgreich gespeichert.")
    except IOError as e:
        _LOGGER.error("Fehler beim Speichern des Caches: %s", e)


def parse_ical(ical_data):
    """
    Parst iCalendar-Daten, um Ferieninformationen zu extrahieren.
    """
    holidays = []
    calendar = Calendar.from_ical(ical_data)
    for component in calendar.walk():
        if component.name == "VEVENT":  # Nur "VEVENT"-Einträge verarbeiten
            holidays.append(
                {
                    "name": str(component.get("summary")),
                    "start_date": component.get("dtstart").dt.date(),
                    "end_date": component.get("dtend").dt.date(),
                }
            )
    return holidays


async def aktualisiere_ferien(country_code, subdivision):
    """
    Aktualisiert die Ferieninformationen und nutzt den Cache, wenn möglich.
    """
    try:
        ical_data = await fetch_holidays(country_code, subdivision)
        holidays = parse_ical(ical_data)
        await speichere_cache(holidays)  # Neue Daten zwischenspeichern
        return holidays
    except RuntimeError:
        _LOGGER.warning("API-Anfrage fehlgeschlagen. Fallback auf Cache.")
        return await lade_cache()  # Cache verwenden


class SchulferienSensor(Entity):
    """
    Sensor-Klasse für Schulferien.
    """

    def __init__(self, name, country_code, subdivision):
        self._name = name
        self._country_code = country_code
        self._subdivision = subdivision
        self._heute_ferientag = None
        self._naechste_ferien_name = None
        self._naechste_ferien_start = None
        self._naechste_ferien_ende = None

    @property
    def name(self):
        """Name des Sensors."""
        return self._name

    @property
    def state(self):
        """Status: 'Ferientag' oder 'Kein Ferientag'."""
        return "Ferientag" if self._heute_ferientag else "Kein Ferientag"

    @property
    def extra_state_attributes(self):
        """Zusätzliche Informationen als Attribut."""
        return {
            "Nächste Ferien": self._naechste_ferien_name,
            "Beginn": self._naechste_ferien_start,
            "Ende": self._naechste_ferien_ende,
        }

    async def async_update(self):
        """Aktualisiert die Sensor-Daten."""
        holidays = await aktualisiere_ferien(self._country_code, self._subdivision)
        if holidays is None:
            return

        today = datetime.now().date()

        # Prüfen, ob heute ein Ferientag ist
        self._heute_ferientag = any(
            holiday["start_date"] <= today <= holiday["end_date"] for holiday in holidays
        )

        # Nächste Ferien ermitteln
        future_holidays = [h for h in holidays if h["start_date"] > today]
        if future_holidays:
            next_holiday = min(future_holidays, key=lambda h: h["start_date"])
            self._naechste_ferien_name = next_holiday["name"]
            self._naechste_ferien_start = next_holiday["start_date"].strftime("%d.%m.%Y")
            self._naechste_ferien_ende = next_holiday["end_date"].strftime("%d.%m.%Y")
