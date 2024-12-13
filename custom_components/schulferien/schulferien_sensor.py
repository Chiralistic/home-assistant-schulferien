"""Modul für die Verwaltung und den Abruf von Schulferien in Deutschland."""

from datetime import datetime, timedelta  # Standardimporte zuerst
import logging
from homeassistant.helpers.entity import Entity
from .api_utils import hole_daten, parse_daten, manage_session, close_session_if_needed
from .const import API_URL_FERIEN

_LOGGER = logging.getLogger(__name__)

class SchulferienSensor(Entity):
    """Sensor für Schulferien und Brückentage."""

    def __init__(self, hass, config):
        self._hass = hass
        self._name = config["name"]
        self._land = config["land"]
        self._region = config["region"]
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
        return self._name

    @property
    def unique_id(self):
        return f"sensor.schulferien_{self._land}_{self._region}_{self._name}"

    @property
    def state(self):
        return "Ferientag" if self.ferien_info["heute_ferientag"] else "Kein Ferientag"

    @property
    def last_update_date(self):
        return self._last_update_date

    @last_update_date.setter
    def last_update_date(self, value):
        self._last_update_date = value

    @property
    def ferien_info(self):
        return self._ferien_info

    @property
    def brueckentage(self):
        return self._brueckentage

    @property
    def extra_state_attributes(self):
        return {
            "Land": self._land,
            "Region": self._region,
            "Nächste Ferien": self.ferien_info["naechste_ferien_name"],
            "Beginn": self.ferien_info["naechste_ferien_beginn"],
            "Ende": self.ferien_info["naechste_ferien_ende"],
            "Brückentage": self.brueckentage,
        }

    async def async_update(self, session=None):
        """Aktualisiere den Sensor mit den neuesten Daten von der API."""
        heute = datetime.now().date()
        if self.last_update_date == heute:
            _LOGGER.debug("Die API für Schulferien wurde heute bereits abgefragt.")
            return

        session, close_session = await manage_session(session)

        try:
            api_parameter = {
                "countryIsoCode": self._land,
                "subdivisionCode": self._region,
                "validFrom": heute.strftime("%Y-%m-%d"),
                "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
            }

            ferien_daten = await hole_daten(API_URL_FERIEN, api_parameter, session)
            ferien_liste = parse_daten(ferien_daten, self.brueckentage)

            self.ferien_info["heute_ferientag"] = any(
                ferien["start_datum"] <= heute <= ferien["end_datum"]
                for ferien in ferien_liste
            )

            zukunftsferien = [ferien for ferien in ferien_liste if ferien["start_datum"] > heute]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                self.ferien_info["naechste_ferien_name"] = naechste_ferien["name"]
                self.ferien_info["naechste_ferien_beginn"] = naechste_ferien["start_datum"].strftime(
                    "%d.%m.%Y"
                )
                self.ferien_info["naechste_ferien_ende"] = naechste_ferien["end_datum"].strftime(
                    "%d.%m.%Y"
                )
            else:
                self.ferien_info["naechste_ferien_name"] = None
                self.ferien_info["naechste_ferien_beginn"] = None
                self.ferien_info["naechste_ferien_ende"] = None

            self.last_update_date = heute

        except RuntimeError as error:
            _LOGGER.warning("API konnte nicht erreicht werden: %s", error)

        finally:
            await close_session_if_needed(session, close_session)
