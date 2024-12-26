"""Modul für die Verwaltung und den Abruf von Schulferien in Deutschland."""

from datetime import datetime, timedelta
import logging
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.entity import Entity
import aiohttp
from .api_utils import fetch_data, parse_daten
from .const import API_URL_FERIEN, COUNTRIES, REGIONS

_LOGGER = logging.getLogger(__name__)

def get_country_name(code):
    """Gibt den ausgeschriebenen Ländernamen für einen Ländercode zurück."""
    return COUNTRIES.get(code, code)

def get_region_name(country_code, region_code):
    """Gibt den ausgeschriebenen Regionsnamen für einen Regionscode zurück."""
    _LOGGER.debug("Region code: %s", region_code)
    _LOGGER.debug("Regions dictionary: %s", REGIONS)
    return REGIONS.get(country_code, {}).get(region_code, region_code)

class SchulferienSensor(Entity):
    """Sensor für Schulferien und Brückentage."""

    def __init__(self, hass, config):
        """Initialisiert den Schulferien-Sensor mit Konfigurationsdaten."""
        self._hass = hass
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.schulferien")
        self._location = {"land": config["land"], "region": config["region"]}
        self._brueckentage = config.get("brueckentage", [])
        self._last_update_date = None
        self._ferien_info = {
            "heute_ferientag": None,
            "naechste_ferien_name": None,
            "naechste_ferien_beginn": None,
            "naechste_ferien_ende": None,
            "ferien_liste": [],  # <-- Initialisiert als leere Liste
        }

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird."""
        # Initiale Abfrage beim Hinzufügen der Entität
        await self.async_update()
        _LOGGER.debug("Initiale Abfrage beim Hinzufügen der Entität durchgeführt.")

        """Frage die API täglich um drei Uhr morgens ab. """
        # Zeitplan für die tägliche Abfrage um 3 Uhr morgens
        async_track_time_change(self._hass, self.async_update, hour=3, minute=0, second=0)
        _LOGGER.debug("Tägliche Abfrage um 3 Uhr morgens eingerichtet.")

    @property
    def should_poll(self):
        """Deaktiviert automatische Abfragen durch Home Assistant."""
        return False

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
        return "Ferientag" if self._ferien_info.get("heute_ferientag", False) else "Kein Ferientag"



    @property
    def last_update_date(self):
        """Gibt das Datum des letzten Updates zurück."""
        return self._last_update_date

    @last_update_date.setter
    def last_update_date(self, value):
        """Setzt das Datum des letzten Updates."""
        self._last_update_date = value

    @property
    def ferien_info(self):
        """Gibt die aktuellen Ferieninformationen zurück."""
        return self._ferien_info

    @property
    def brueckentage(self):
        """Gibt die konfigurierten Brückentage zurück."""
        return self._brueckentage

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        heute = datetime.now().date()
        aktuelles_ereignis = None
        beginn = None
        ende = None

        # Nutze eine leere Liste, falls 'ferien_liste' fehlt
        ferien_liste = self._ferien_info.get("ferien_liste", [])

        for ferien in ferien_liste:
            if ferien["start_datum"] <= heute <= ferien["end_datum"]:
                aktuelles_ereignis = ferien["name"]
                beginn = ferien["start_datum"].strftime("%d.%m.%Y")
                ende = ferien["end_datum"].strftime("%d.%m.%Y")
                break

        if not aktuelles_ereignis:
            aktuelles_ereignis = self._ferien_info["naechste_ferien_name"]
            beginn = self._ferien_info["naechste_ferien_beginn"]
            ende = self._ferien_info["naechste_ferien_ende"]

        return {
            "Name der Ferien": aktuelles_ereignis,
            "Beginn": beginn,
            "Ende": ende,
            "Land": get_country_name(self._location["land"]),
            "Region": get_region_name(self._location["land"], self._location["region"]),
            "Brückentage": self._brueckentage,
        }

    async def async_update(self, session=None):
        """Aktualisiert die Schulferiendaten durch Abfrage der API."""
        heute = datetime.now().date()

        # Zeitraum erweitern, um laufende Ferien zu erfassen
        startdatum = (heute - timedelta(days=30)).strftime("%Y-%m-%d")
        enddatum = (heute + timedelta(days=365)).strftime("%Y-%m-%d")

        api_parameter = {
            "countryIsoCode": self._location["land"],
            "subdivisionCode": self._location["region"],
            "validFrom": startdatum,  # 30 Tage zurück
            "validTo": enddatum,
            "languageIsoCode": "DE",
        }

        try:
            # API-Daten abrufen
            ferien_daten = await fetch_data(API_URL_FERIEN, api_parameter, session)
            if not ferien_daten:
                _LOGGER.warning("Keine Schulferiendaten von der API erhalten.")
                return

            # Verarbeite die Daten
            ferien_liste = parse_daten(ferien_daten, self._brueckentage)
            self._ferien_info["ferien_liste"] = ferien_liste  # Alle Einträge speichern

            # Aktuelle Ferien prüfen (Zeitraum!)
            aktuelles_ereignis = next(
                (
                    ferien for ferien in ferien_liste
                    if ferien["start_datum"] <= heute <= ferien["end_datum"]
                ),
                None,
            )

            # Setze den Zustand und die Attribute
            if aktuelles_ereignis:
                # Wenn aktuell Ferien, setze den Zustand
                self._ferien_info.update({
                    "heute_ferientag": True,
                    "naechste_ferien_name": aktuelles_ereignis["name"],
                    "naechste_ferien_beginn": aktuelles_ereignis["start_datum"].strftime(
                        "%d.%m.%Y"
                    ),
                    "naechste_ferien_ende": aktuelles_ereignis["end_datum"].strftime(
                        "%d.%m.%Y"
                    ),
                })
            else:
                # Kein aktueller Ferientag
                self._ferien_info["heute_ferientag"] = False

                # Nächste Ferien ermitteln
                zukunftsferien = [
                    ferien for ferien in ferien_liste if ferien["start_datum"] > heute
                ]
                if zukunftsferien:
                    naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                    self._ferien_info.update({
                        "naechste_ferien_name": naechste_ferien["name"],
                        "naechste_ferien_beginn": naechste_ferien["start_datum"].strftime("%d.%m.%Y"),
                        "naechste_ferien_ende": naechste_ferien["end_datum"].strftime("%d.%m.%Y"),
                    })

            self._last_update_date = heute

        except (KeyError, ValueError) as e:
            _LOGGER.error("Fehler beim Verarbeiten der Schulferiendaten: %s", e)
