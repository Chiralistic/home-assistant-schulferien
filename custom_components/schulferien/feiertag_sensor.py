"""Modul für die Verwaltung und den Abruf von Feiertagen in Deutschland."""

import logging
import aiohttp
from datetime import datetime
from homeassistant.helpers.entity import Entity
from .api_utils import hole_daten, parse_daten
from .const import API_URL_FEIERTAGE

_LOGGER = logging.getLogger(__name__)

class FeiertagSensor(Entity):
    """Sensor für Feiertage."""

    def __init__(self, hass, config):
        self._hass = hass
        self._name = config["name"]
        self._location = {"land": config["land"], "region": config["region"]}
        self._last_update_date = None
        self._heute_feiertag = None
        self._naechster_feiertag = {"name": None, "datum": None}

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"sensor.feiertag_{self._location['land']}_{self._location['region']}_{self._name}"

    @property
    def state(self):
        return "Feiertag" if self._heute_feiertag else "Kein Feiertag"

    @property
    def extra_state_attributes(self):
        return {
            "Land": self._location["land"],
            "Region": self._location["region"],
            "Nächster Feiertag": self._naechster_feiertag["name"],
            "Datum des nächsten Feiertags": self._naechster_feiertag["datum"],
        }

    async def async_update(self, session=None):
        """Aktualisiert die Feiertagsdaten."""
        heute = datetime.now().date()
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Feiertage wurde heute bereits abgefragt.")
            return

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            api_parameter = {
                "countryIsoCode": self._location["land"],
                "subdivisionCode": self._location["region"],
                "validFrom": heute.strftime("%Y-%m-%d"),
                "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
            }

            feiertage_daten = await hole_daten(API_URL_FEIERTAGE, api_parameter, session)
            feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")

            self._heute_feiertag = any(
                feiertag["start_datum"] == heute for feiertag in feiertage_liste
            )

            zukunft_feiertage = [
                feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute
            ]
            if zukunft_feiertage:
                naechster_feiertag = min(
                    zukunft_feiertage, key=lambda f: f["start_datum"]
                )
                self._naechster_feiertag["name"] = naechster_feiertag["name"]
                self._naechster_feiertag["datum"] = naechster_feiertag["start_datum"].strftime(
                    "%d.%m.%Y"
                )
            else:
                self._naechster_feiertag["name"] = None
                self._naechster_feiertag["datum"] = None

            self._last_update_date = heute

        except RuntimeError as error:
            _LOGGER.warning("API konnte nicht erreicht werden: %s", error)

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("Session wurde geschlossen.")
