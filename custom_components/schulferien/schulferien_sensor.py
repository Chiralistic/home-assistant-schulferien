"""Modul für die Verwaltung und den Abruf von Schulferien in Deutschland."""

from datetime import datetime, timedelta
import logging
from homeassistant.helpers.entity import Entity
from .api_utils import fetch_data, parse_daten
from .const import API_URL_FERIEN, COUNTRIES, REGIONS

_LOGGER = logging.getLogger(__name__)

def get_country_name(code):
    """Gibt den ausgeschriebenen Ländernamen für einen Ländercode zurück."""
    return COUNTRIES.get(code, code)

def get_region_name(country_code, region_code):
    """Gibt den ausgeschriebenen Regionsnamen für einen Regionscode zurück."""
    _LOGGER.debug("Region code sfs: %s", region_code)
    _LOGGER.debug("Regions dictionary sfs: %s", REGIONS)  
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

    async def async_update(self, session=None):
        """Aktualisiert die Schulferiendaten durch Abfrage der API."""
        heute = datetime.now().date()
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Schulferien wurde heute bereits abgefragt.")
            return

        api_parameter = {
            "countryIsoCode": self._location["land"],
            "subdivisionCode": self._location["region"],
            "validFrom": datetime.now().strftime("%Y-%m-%d"),
            "validTo": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "languageIsoCode": "DE",
        }

        try:
            ferien_daten = await fetch_data(API_URL_FERIEN, api_parameter, session)
            if not ferien_daten:
                _LOGGER.warning("Keine Schulferiendaten von der API erhalten.")
                return

            _LOGGER.debug("Empfangene Schulferiendaten: %s", ferien_daten)

            ferien_liste = parse_daten(ferien_daten, self._brueckentage)
            _LOGGER.debug("Verarbeitete Schulferiendaten: %s", ferien_liste)

            self._ferien_info["heute_ferientag"] = any(
                ferien["start_datum"] <= heute <= ferien["end_datum"] for ferien in ferien_liste
            )
            _LOGGER.debug("Heute Ferientag: %s", self._ferien_info["heute_ferientag"])

            zukunftsferien = [ferien for ferien in ferien_liste if ferien["start_datum"] > heute]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                self._ferien_info["naechste_ferien_name"] = naechste_ferien["name"]
                self._ferien_info["naechste_ferien_beginn"] = naechste_ferien["start_datum"].strftime("%d.%m.%Y")
                self._ferien_info["naechste_ferien_ende"] = naechste_ferien["end_datum"].strftime("%d.%m.%Y")
                _LOGGER.debug(
                    "Nächste Ferien: %s, Beginn: %s, Ende: %s",
                    self._ferien_info["naechste_ferien_name"],
                    self._ferien_info["naechste_ferien_beginn"],
                    self._ferien_info["naechste_ferien_ende"],
                )
            else:
                self._ferien_info["naechste_ferien_name"] = None
                self._ferien_info["naechste_ferien_beginn"] = None
                self._ferien_info["naechste_ferien_ende"] = None
                _LOGGER.debug("Keine zukünftigen Ferien gefunden.")

            self._last_update_date = heute
        except Exception as e:
            _LOGGER.error("Fehler beim Aktualisieren der Schulferiendaten: %s", e)