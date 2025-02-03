"""Modul für die Verwaltung und den Abruf von Schulferien in Deutschland."""

import logging
from homeassistant.core import HomeAssistant
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
import aiohttp
from .api_utils import fetch_data, parse_daten, DEFAULT_TIMEOUT
from .const import (
    API_URL_FERIEN,
    API_FALLBACK_FERIEN,
    DAILY_UPDATE_HOUR,
    DAILY_UPDATE_MINUTE,
)

_LOGGER = logging.getLogger(__name__)

# Definition der EntityDescription mit Übersetzungsschlüssel
SCHULFERIEN_SENSOR = SensorEntityDescription(
    key="schulferien",
    name="Schulferien",
    translation_key="schulferien",  # Bezug zur Übersetzung
)

class SchulferienSensor(SensorEntity):
    """Sensor für Schulferien und Brückentage."""

    def __init__(self, hass, config):
        """Initialisiert den Schulferien-Sensor mit Konfigurationsdaten."""
        self.entity_description = SCHULFERIEN_SENSOR
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.schulferien")
        self._location = {
            "land": config["land"],
            "region": config["region"],
            "land_name": config["land_name"],  # Ausgeschriebener Name des Landes
            "region_name": config["region_name"],  # Ausgeschriebener Name der Region
            "iso_code": "DE",  # Wird dynamisch aus der Spracheinstellung übernommen
        }
        self._brueckentage = config.get("brueckentage", [])
        self._ferien_info = {
            "heute_ferientag": None,
            "naechste_ferien_name": None,
            "naechste_ferien_beginn": None,
            "naechste_ferien_ende": None,
            "ferien_liste": [],
            "letztes_update": None,  # Neuer Schlüssel
        }
        _LOGGER.debug("Sensor für %s mit Land: %s, Region: %s, Brückentagen: %s",
            self._name, self._location["land"], self._location["region"], 
            self._brueckentage
        )

    async def async_added_to_hass(self):
        """Initialisierung des Sensors."""
        _LOGGER.debug("Schulferien-Sensor hinzugefügt, erstes Update wird ausgeführt.")
        
        if self.hass and self.hass.config:
            self._location["iso_code"] = self.hass.config.language[:2].upper()
        else:
            self._location["iso_code"] = "DE"  # Standardwert
            _LOGGER.warning("Schulferien-Sensor: Fallback auf Standard 'DE'.")

        # Debug-Ausgabe des Sprachcodes im Log
        _LOGGER.debug("Schulferien-Sensor: Verwendeter Sprachcode: %s", self._location["iso_code"])

        # Holen des letzten Updates
        letztes_update = self._ferien_info.get("letztes_update")
        jetzt = datetime.now()

        # Update nur, wenn noch kein Update vorhanden oder wenn der Tag gewechselt hat
        if not letztes_update or letztes_update.date() != jetzt.date():
            await self.async_update()
            self.async_write_ha_state()

        async def async_daily_update(_):
            """Tägliche Aktualisierung um 03:00 Uhr."""
            _LOGGER.debug("Tägliches Update ausgelöst.")
            await self.async_update()
            self.async_write_ha_state()

        async_track_time_change(
            self.hass,
            async_daily_update,
            hour=DAILY_UPDATE_HOUR,
            minute=DAILY_UPDATE_MINUTE,
        )
        _LOGGER.debug(
            "Tägliche Abfrage um %02d:%02d eingerichtet.", DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE
        )

    @property
    def name(self):
        """Gibt den Namen des Sensors zurück."""
        return self._name

    @property
    def unique_id(self):
        """Gibt die eindeutige ID des Sensors zurück."""
        return self._unique_id

    @property
    def native_value(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return "ferientag" if self._ferien_info.get("heute_ferientag", False) else "kein_ferientag"

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
            "Land": self._location["land_name"],
            "Region": self._location["region_name"],
            "Brückentage": self._brueckentage,
        }

    async def async_update(self, session=None):
        """Aktualisiert die Schulferiendaten durch Abfrage der API."""
        heute = datetime.now().date()
        jetzt = datetime.now()

        # Prüfen, ob ein Update notwendig ist (nur bei Tageswechsel)
        letztes_update = self._ferien_info.get("letztes_update")
        if letztes_update and letztes_update.date() == heute:
            _LOGGER.debug("Update übersprungen. Letztes Update war heute um %s.", letztes_update.strftime("%H:%M:%S"))
            return  # Update nicht erforderlich

        _LOGGER.debug("Starte Update der Schulferiendaten.")
        close_session = False

        if session is None:
            session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
            close_session = True

        try:
            # Zeitraum erweitern, um laufende Ferien zu erfassen
            startdatum = (heute - timedelta(days=30)).strftime("%Y-%m-%d")
            enddatum = (heute + timedelta(days=365)).strftime("%Y-%m-%d")

            api_parameter = {
                "countryIsoCode": self._location["land"],
                "subdivisionCode": self._location["region"],
                "validFrom": startdatum,
                "validTo": enddatum,
                "languageIsoCode": self._location["iso_code"],
            }

            # API-Daten abrufen
            ferien_daten = None
            urls = [API_URL_FERIEN, API_FALLBACK_FERIEN]  # Haupt- und Fallback-URL
            for url in urls:
                _LOGGER.debug("Prüfe URL: %s", url)
                try:
                    ferien_daten = await fetch_data(url, api_parameter, session)
                    if ferien_daten:
                        break
                except aiohttp.ClientError as e:
                    _LOGGER.error("Fehler beim Abrufen der Daten von %s: %s", url, e)

            if not ferien_daten:
                _LOGGER.warning("Keine Daten von der API erhalten.")
                return

            # Verarbeite die Daten
            try:
                ferien_liste = parse_daten(ferien_daten, self._brueckentage)
                self._ferien_info["ferien_liste"] = ferien_liste
            except ValueError as e:
                _LOGGER.error("Fehler beim Verarbeiten der Daten: %s", e)
                return

            # Prüfen, ob heute ein Ferientag ist
            aktuelles_ereignis = next(
                (
                    ferien for ferien in ferien_liste
                    if ferien["start_datum"] <= heute <= ferien["end_datum"]
                ),
                None,
            )

            # Zustand und Attribute setzen
            if aktuelles_ereignis:
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
                self._ferien_info["heute_ferientag"] = False

                # Nächste Ferien ermitteln
                zukunftsferien = [
                    ferien for ferien in ferien_liste if ferien["start_datum"] > heute
                ]
                if zukunftsferien:
                    naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                    self._ferien_info.update({
                        "naechste_ferien_name": naechste_ferien["name"],
                        "naechste_ferien_beginn": naechste_ferien["start_datum"].strftime(
                            "%d.%m.%Y"
                        ),
                        "naechste_ferien_ende": naechste_ferien["end_datum"].strftime(
                            "%d.%m.%Y"
                        ),
                    })

            # Letztes Update-Zeitpunkt speichern
            self._ferien_info["letztes_update"] = jetzt
            _LOGGER.debug("Update abgeschlossen. Letztes Update um: %s", self._ferien_info["letztes_update"])

        except Exception as e:
            _LOGGER.error("Unerwarteter Fehler beim Aktualisieren der Daten: %s", e)

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("API-Session geschlossen.")
