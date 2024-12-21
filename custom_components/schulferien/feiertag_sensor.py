"""Modul für die Verwaltung und den Abruf von Feiertagen in Deutschland."""

import logging  # Standardimport zuerst
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_change
from .api_utils import fetch_data, parse_daten
from .const import API_URL_FEIERTAGE, COUNTRIES, REGIONS, CACHE_FILE_FEIERTAGE

_LOGGER = logging.getLogger(__name__)

def get_country_name(code):
    """Gibt den ausgeschriebenen Ländernamen für einen Ländercode zurück."""
    return COUNTRIES.get(code, code)

def get_region_name(country_code, region_code):
    """Gibt den ausgeschriebenen Regionsnamen für einen Regionscode zurück."""
    return REGIONS.get(country_code, {}).get(region_code, region_code)

class FeiertagSensor(Entity):
    """Sensor für Feiertage."""

    def __init__(self, hass, config):
        self._hass = hass
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.feiertag")
        self._land = config["land"]
        self._region = config["region"]
        self._last_update_date = None
        self._heute_feiertag = None
        self._naechster_feiertag = {"name": None, "datum": None}

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird."""
        # Nur die tägliche Abfrage um 3 Uhr morgens einplanen
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
        return "Feiertag" if self._heute_feiertag else "Kein Feiertag"

    @property
    def should_poll(self):
        """Deaktiviert automatische Abfragen durch Home Assistant."""
        return False

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        return {
            "Nächster Feiertag": self._naechster_feiertag["name"],
            "Datum des nächsten Feiertags": self._naechster_feiertag["datum"],
            "Land": get_country_name(self._land),
            "Region": get_region_name(self._land, self._region),
        }
        #_LOGGER.debug("Aktualisierte Feiertag-Attribute: %s", self.extra_state_attributes)

    async def async_update(self, session=None):
        """Aktualisiert die Feiertagsdaten durch Abfrage der API."""
        #_LOGGER.debug("Starte tägliche API-Abfrage für Feiertage.")

        api_parameter = {
            "countryIsoCode": self._land,
            "subdivisionCode": self._region,
            "languageIsoCode": "DE",
            "validFrom": datetime.now().strftime("%Y-%m-%d"),
            "validTo": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        try:
            feiertage_daten = await fetch_data(API_URL_FEIERTAGE, api_parameter, CACHE_FILE_FEIERTAGE, session)
            if not feiertage_daten:
                _LOGGER.warning("Keine Feiertagsdaten von der API erhalten.")
                self._heute_feiertag = None
                self._naechster_feiertag = {"name": None, "datum": None}
                return

            feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")
            #_LOGGER.debug("Verarbeitete Feiertagsdaten: %s", feiertage_liste)

            heute = datetime.now().date()
            self._heute_feiertag = any(
                feiertag["start_datum"] == heute for feiertag in feiertage_liste
            )

            zukunft_feiertage = [feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute]
            if zukunft_feiertage:
                naechster_feiertag = min(zukunft_feiertage, key=lambda f: f["start_datum"])
                self._naechster_feiertag["name"] = naechster_feiertag["name"]
                self._naechster_feiertag["datum"] = naechster_feiertag["start_datum"].strftime(
                    "%d.%m.%Y"
                )
            else:
                self._naechster_feiertag["name"] = None
                self._naechster_feiertag["datum"] = None

            # Aktualisierungsdatum speichern
            self._last_update_date = heute
            _LOGGER.info("Feiertagsdaten erfolgreich aktualisiert.")

        except Exception as e:
            _LOGGER.error("Fehler beim Aktualisieren der Feiertagsdaten: %s", e)
