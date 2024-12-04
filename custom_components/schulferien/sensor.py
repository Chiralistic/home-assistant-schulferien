# /custom_components/schulferien/sensor.py

import aiohttp
import logging
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util.dt import now as dt_now
from .const import API_URL, STANDARD_SPRACHE

_LOGGER = logging.getLogger(__name__)

async def hole_ferien(api_parameter):
    """
    Fragt Ferieninformationen von der API im JSON-Format ab.

    :param api_parameter: Dictionary mit API-Parametern.
    :return: Liste von Ferieninformationen.
    """
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", API_URL, api_parameter)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                API_URL, params=api_parameter, headers={"Accept": "application/json"}
            ) as antwort:
                antwort.raise_for_status()
                daten = await antwort.json()
                _LOGGER.debug("API-Antwort erhalten: %s", antwort.status)
                return daten
        except aiohttp.ClientError as fehler:
            _LOGGER.error("API-Anfrage fehlgeschlagen: %s", fehler)
            raise RuntimeError(f"API-Anfrage fehlgeschlagen: {fehler}")

class SchulferienSensor(Entity):
    """Sensor für Schulferien."""

    def __init__(self, land, region):
        self._name = "Schulferien"
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
            ferien_daten = await hole_ferien(api_parameter)

            # JSON direkt auswerten
            self._heute_ferientag = any(
                ferien["startDate"] <= heute.strftime("%Y-%m-%d") <= ferien["endDate"]
                for ferien in ferien_daten
            )

            zukunftsferien = [
                ferien for ferien in ferien_daten if ferien["startDate"] > heute.strftime("%Y-%m-%d")
            ]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["startDate"])
                self._naechste_ferien_name = naechste_ferien["name"]
                self._naechste_ferien_beginn = naechste_ferien["startDate"]
                self._naechste_ferien_ende = naechste_ferien["endDate"]
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

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setzt die Sensor-Integration basierend auf Konfigurationseintrag auf."""
    land = config_entry.data["land"]
    region = config_entry.data["region"]
    async_add_entities([SchulferienSensor(land, region)])
