# /custom_components/schulferien/sensor.py

import aiohttp
import logging
from datetime import datetime, timedelta
from pathlib import Path
from icalendar import Calendar
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util.dt import now as dt_now
from .const import API_URL, STANDARD_SPRACHE, STANDARD_LAND

_LOGGER = logging.getLogger(__name__)

async def hole_ferien(api_parameter):
    """
    Fragt Ferieninformationen von der API ab.

    :param api_parameter: Dictionary mit API-Parametern.
    :return: iCalendar-Daten als String.
    """
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", API_URL, api_parameter)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                API_URL, params=api_parameter, headers={"Accept": "text/calendar"}
            ) as antwort:
                antwort.raise_for_status()
                daten = await antwort.text()
                _LOGGER.debug("API-Antwort erhalten: %s", antwort.status)
                return daten
        except aiohttp.ClientError as fehler:
            _LOGGER.error("API-Anfrage fehlgeschlagen: %s", fehler)
            raise RuntimeError(f"API-Anfrage fehlgeschlagen: {fehler}")

def parse_ical(ical_daten):
    """
    Verarbeitet die iCalendar-Daten und extrahiert Ferieninformationen.

    :param ical_daten: iCalendar-Daten als String.
    :return: Liste von Ferien mit Name, Start- und Enddatum.
    """
    try:
        kalender = Calendar.from_ical(ical_daten)
        ferien_liste = []
        for eintrag in kalender.walk():
            if eintrag.name == "VEVENT":
                ferien_liste.append({
                    "name": str(eintrag.get("summary")),
                    "start_datum": eintrag.get("dtstart").dt,
                    "end_datum": eintrag.get("dtend").dt,
                })
        _LOGGER.debug("iCalendar erfolgreich geparst: %d Ferieneinträge", len(ferien_liste))
        return ferien_liste
    except Exception as fehler:
        _LOGGER.error("Fehler beim Parsen von iCalendar-Daten: %s", fehler)
        raise RuntimeError("Ungültige iCalendar-Daten erhalten.")

class SchulferienSensor(Entity):
    """Sensor für Schulferien."""

    def __init__(self, name, land, region):
        self._name = name
        self._land = land
        self._region = region
        self._heute_ferientag = None
        self._naechste_ferien_name = None
        self._naechste_ferien_beginn = None
        self._naechste_ferien_ende = None

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
            "Beginn": self._naechste_ferien_beginn,
            "Ende": self._naechste_ferien_ende,
        }

    async def async_update(self):
        """
        Aktualisiert die Ferieninformationen durch Abruf der API.
        """
        heute = datetime.now().date()
        api_parameter = {
            "countryIsoCode": self._land,
            "subdivisionCode": self._region,
            "languageIsoCode": STANDARD_SPRACHE,
            "validFrom": heute.strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        try:
            ical_daten = await hole_ferien(api_parameter)
            ferien_liste = parse_ical(ical_daten)

            # Heute ein Ferientag?
            self._heute_ferientag = any(
                ferien["start_datum"] <= heute <= ferien["end_datum"]
                for ferien in ferien_liste
            )

            # Nächste Ferien
            zukunftsferien = [
                ferien for ferien in ferien_liste if ferien["start_datum"] > heute
            ]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                self._naechste_ferien_name = naechste_ferien["name"]
                self._naechste_ferien_beginn = naechste_ferien["start_datum"].strftime("%d.%m.%Y")
                self._naechste_ferien_ende = naechste_ferien["end_datum"].strftime("%d.%m.%Y")
            else:
                self._naechste_ferien_name = None
                self._naechste_ferien_beginn = None
                self._naechste_ferien_ende = None

        except RuntimeError:
            _LOGGER.warning("API konnte nicht erreicht werden, Daten sind möglicherweise nicht aktuell.")

    async def async_added_to_hass(self):
        """
        Wird aufgerufen, wenn der Sensor zu Home Assistant hinzugefügt wird.
        Hier wird der tägliche Abruf geplant.
        """
        jetzt = dt_now()
        naechste_aktualisierung = jetzt.replace(hour=0, minute=1, second=0, microsecond=0)
        if jetzt >= naechste_aktualisierung:
            naechste_aktualisierung += timedelta(days=1)

        _LOGGER.debug("Nächste Aktualisierung für %s geplant", naechste_aktualisierung)
        async_track_point_in_time(self.hass, self.async_update_callback, naechste_aktualisierung)

    async def async_update_callback(self, zeitpunkt):
        """Callback für geplante Aktualisierungen."""
        _LOGGER.debug("Aktualisierung um %s gestartet", zeitpunkt)
        await self.async_update()

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """
    Einrichtung des Sensors bei Start von Home Assistant.

    :param hass: Home Assistant Instanz.
    :param config: Konfigurationsdaten.
    :param async_add_entities: Funktion zum Hinzufügen von Sensoren.
    """
    name = config.get("name", "Schulferien")
    land = config.get("country_code", STANDARD_LAND)
    region = config.get("region", "DE-NI")
    async_add_entities([SchulferienSensor(name, land, region)])
