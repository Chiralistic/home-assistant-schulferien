"""Modul für die Verwaltung und den Abruf von Feiertagen in Deutschland."""

import logging  # Standardimport zuerst
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from .api_utils import fetch_data, parse_daten
from .const import API_URL_FEIERTAGE

_LOGGER = logging.getLogger(__name__)

class FeiertagSensor(Entity):
    """Sensor für Feiertage."""

    def __init__(self, hass, config):
        self._hass = hass
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.feiertag")  # Hier wird _unique_id gesetzt
        self._land = config["land"]
        self._region = config["region"]
        self._last_update_date = None
        self._heute_feiertag = None
        self._naechster_feiertag = {"name": None, "datum": None}

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
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        return {
            "Nächster Feiertag": self._naechster_feiertag["name"],
            "Datum des nächsten Feiertags": self._naechster_feiertag["datum"],
            "Land": self._land,
            "Region": self._region,
        }

    async def async_update(self, session=None):
        """Aktualisiert die Feiertagsdaten."""
        heute = datetime.now().date()
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Feiertage wurde heute bereits abgefragt.")
            return

        api_parameter = {
            "countryIsoCode": self._land,
            "subdivisionCode": self._region,
            "validFrom": heute.strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        feiertage_daten = await fetch_data(API_URL_FEIERTAGE, api_parameter, session)
        feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")

        self._heute_feiertag = any(
            feiertag["start_datum"] == heute for feiertag in feiertage_liste
        )

        zukunft_feiertage = [
            feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute
        ]
        if zukunft_feiertage:
            naechster_feiertag = min(zukunft_feiertage, key=lambda f: f["start_datum"])
            self._naechster_feiertag["name"] = naechster_feiertag["name"]
            self._naechster_feiertag["datum"] = naechster_feiertag["start_datum"].strftime(
                "%d.%m.%Y"
            )
        else:
            self._naechster_feiertag["name"] = None
            self._naechster_feiertag["datum"] = None

        self._last_update_date = heute
