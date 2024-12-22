"""Modul für die Verwaltung und den Abruf von Feiertagen in Deutschland."""

import logging
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from .api_utils import fetch_data, parse_daten
from .const import API_URL_FEIERTAGE, COUNTRIES, REGIONS

_LOGGER = logging.getLogger(__name__)

def get_country_name(code):
    """Gibt den ausgeschriebenen Ländernamen für einen Ländercode zurück."""
    return COUNTRIES.get(code, code)

def get_region_name(country_code, region_code):
    """Gibt den ausgeschriebenen Regionsnamen für einen Regionscode zurück."""
    _LOGGER.debug("Region code fts: %s", region_code)
    _LOGGER.debug("Regions dictionary fts: %s", REGIONS)
    return REGIONS.get(country_code, {}).get(region_code, region_code)

class FeiertagSensor(Entity):
    """Sensor für Feiertage."""

    def __init__(self, hass, config):
        """Initialisiert den Feiertag-Sensor mit Konfigurationsdaten."""
        self._hass = hass
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.feiertag")
        self._location = {"land": config["land"], "region": config["region"]}
        self._last_update_date = None
        self._feiertags_info = {
            "heute_feiertag": None,
            "naechster_feiertag_name": None,
            "naechster_feiertag_datum": None,
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
        return "Feiertag" if self._feiertags_info["heute_feiertag"] else "Kein Feiertag"

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        return {
            "Nächster Feiertag": self._feiertags_info["naechster_feiertag_name"],
            "Datum des nächsten Feiertags": self._feiertags_info["naechster_feiertag_datum"],
            "Land": get_country_name(self._location["land"]),
            "Region": get_region_name(
                self._location["land"], self._location["region"]
            ),
        }

    async def async_update(self, session=None):
        """Aktualisiert die Feiertagsdaten."""
        heute = datetime.now().date()
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Feiertage wurde heute bereits abgefragt.")
            return

        api_parameter = {
            "countryIsoCode": self._location["land"],
            "subdivisionCode": self._location["region"],
            "validFrom": datetime.now().strftime("%Y-%m-%d"),
            "validTo": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "languageIsoCode": "DE",
        }

        feiertage_daten = await fetch_data(API_URL_FEIERTAGE, api_parameter, session)
        feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")

        self._feiertags_info["heute_feiertag"] = any(
            feiertag["start_datum"] == heute for feiertag in feiertage_liste
        )

        zukunft_feiertage = [
            feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute
        ]
        if zukunft_feiertage:
            naechster_feiertag = min(zukunft_feiertage, key=lambda f: f["start_datum"])
            self._feiertags_info["naechster_feiertag_name"] = naechster_feiertag["name"]
            self._feiertags_info["naechster_feiertag_datum"] = naechster_feiertag["start_datum"].strftime(
                "%d.%m.%Y"
            )
        else:
            self._feiertags_info["naechster_feiertag_name"] = None
            self._feiertags_info["naechster_feiertag_datum"] = None

        self._last_update_date = heute
