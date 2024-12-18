"""Modul für die Verwaltung und den Abruf von Schulferien in Deutschland."""

from datetime import datetime, timedelta
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_change
from .api_utils import fetch_data, parse_daten
from .const import API_URL_FERIEN, COUNTRIES, REGIONS, CACHE_FILE_SCHULFERIEN

_LOGGER = logging.getLogger(__name__)

def get_country_name(code):
    """Gibt den ausgeschriebenen Ländernamen für einen Ländercode zurück."""
    return COUNTRIES.get(code, code)

def get_region_name(country_code, region_code):
    """Gibt den ausgeschriebenen Regionsnamen für einen Regionscode zurück."""
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
        }

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird."""
        # Initiale Abfrage beim Hinzufügen der Entität
        await self.async_update()
        _LOGGER.debug("Initiale Abfrage beim Hinzufügen der Entität durchgeführt.")

        # Zeitplan für die tägliche Abfrage um 3 Uhr morgens
        async_track_time_change(self._hass, self.async_update, hour=3, minute=0, second=0)
        _LOGGER.debug("Tägliche Abfrage um 3 Uhr morgens eingerichtet.")

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
        return "Ferientag" if self._ferien_info["heute_ferientag"] else "Kein Ferientag"

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
    def should_poll(self):
        """Deaktiviert automatische Abfragen durch Home Assistant."""
        return False

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        return {
            "Nächste Ferien": self._ferien_info["naechste_ferien_name"],
            "Beginn": self._ferien_info["naechste_ferien_beginn"],
            "Ende": self._ferien_info["naechste_ferien_ende"],
            "Land": get_country_name(self._location["land"]),
            "Region": get_region_name(self._location["land"], self._location["region"]),
            "Brückentage": self._brueckentage,
        }
        #_LOGGER.debug("Aktualisierte Schulferien-Attribute: %s", self.extra_state_attributes)

    async def async_update(self, session=None):
        """Aktualisiert die Schulferiendaten durch Abfrage der API."""
        #_LOGGER.debug("Starte tägliche API-Abfrage für Schulferien.")

        api_parameter = {
            "countryIsoCode": self._location["land"],
            "subdivisionCode": self._location["region"],
            "validFrom": datetime.now().strftime("%Y-%m-%d"),
            "validTo": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        try:
            ferien_daten = await fetch_data(API_URL_FERIEN, api_parameter, CACHE_FILE_SCHULFERIEN, session)
            if not ferien_daten:
                _LOGGER.warning("Keine Schulferiendaten von der API erhalten.")
                return

            ferien_liste = parse_daten(ferien_daten, self._brueckentage)
            #_LOGGER.debug("Verarbeitete Schulferiendaten: %s", ferien_liste)

            self._ferien_info["heute_ferientag"] = any(
                ferien["start_datum"] <= datetime.now().date() <= ferien["end_datum"]
                for ferien in ferien_liste
            )

            # Nächste Ferien setzen
            zukunftsferien = [ferien for ferien in ferien_liste if ferien["start_datum"] > datetime.now().date()]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                self._ferien_info["naechste_ferien_name"] = naechste_ferien["name"]
                self._ferien_info["naechste_ferien_beginn"] = naechste_ferien["start_datum"].strftime(
                    "%d.%m.%Y"
                )
                self._ferien_info["naechste_ferien_ende"] = naechste_ferien["end_datum"].strftime(
                    "%d.%m.%Y"
                )
            else:
                self._ferien_info["naechste_ferien_name"] = None
                self._ferien_info["naechste_ferien_beginn"] = None
                self._ferien_info["naechste_ferien_ende"] = None

            # Aktualisierungsdatum speichern
            self._last_update_date = datetime.now().date()
            _LOGGER.info("Schulferiendaten erfolgreich aktualisiert.")

        except Exception as e:
            _LOGGER.error("Fehler beim Aktualisieren der Schulferiendaten: %s", e)
