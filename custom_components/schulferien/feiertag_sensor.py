import logging
from homeassistant.core import HomeAssistant
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
import aiohttp
from .api_utils import fetch_data, parse_daten, DEFAULT_TIMEOUT
from .const import (
    API_URL_FEIERTAGE,
    API_FALLBACK_FEIERTAGE,
    DAILY_UPDATE_HOUR,
    DAILY_UPDATE_MINUTE
)

_LOGGER = logging.getLogger(__name__)

# Definition der EntityDescription mit Übersetzungsschlüssel
FEIERTAG_SENSOR = SensorEntityDescription(
    key="feiertag",
    name="Feiertag",
    translation_key="feiertag",  # Bezug zur Übersetzung
)

class FeiertagSensor(SensorEntity):
    """Sensor für Feiertage."""

    def __init__(self, hass, config):
        """Initialisiert den Feiertag-Sensor mit Konfigurationsdaten."""
        self.entity_description = FEIERTAG_SENSOR
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.feiertag")
        # Hier verwenden wir die über die Konfiguration erhaltenen Länder und Regionen
        self._location = {
            "land": config["land"],  # Wird aus dem ConfigFlow übernommen
            "region": config["region"],  # Wird aus dem ConfigFlow übernommen
            "land_name": config["land_name"],  # Ausgeschriebener Name des Landes
            "region_name": config["region_name"],  # Ausgeschriebener Name der Region
            "iso_code": "DE",  # Wird dynamisch aus der Spracheinstellung übernommen
        }
        self._feiertags_info = {
            "heute_feiertag": None,
            "naechster_feiertag_name": None,
            "naechster_feiertag_datum": None,
            "feiertage_liste": [],
            "letztes_update": None,  # Neuer Schlüssel
        }

        # Debugging der Konfigurationswerte
        _LOGGER.debug("FeiertagSensor initialisiert mit folgenden Konfigurationsdaten:")
        _LOGGER.debug("Land: %s", self._location["land"])
        _LOGGER.debug("Region: %s", self._location["region"])

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird."""
        _LOGGER.debug("Feiertag-Sensor hinzugefügt, erstes Update wird ausgeführt.")
        if self.hass and self.hass.config:
            self._location["iso_code"] = self.hass.config.language[:2].upper()
        else:
            self._location["iso_code"] = "DE"  # Standardwert
            _LOGGER.warning("Feiertag-Sensor: Fallback auf Standard 'DE'.")

        # Debug-Ausgabe des Sprachcodes im Log
        _LOGGER.debug("Feiertag-Sensor: Verwendeter Sprachcode: %s", self._location["iso_code"])

        # Holen des letzten Updates
        letztes_update = self._feiertags_info.get("letztes_update")
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
        return "feiertag" if self._feiertags_info.get("heute_feiertag", False) else "kein_feiertag"

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        heute = datetime.now().date()
        aktueller_feiertag = None
        datum = None

        # Nutze eine leere Liste, falls 'feiertage_liste' fehlt
        feiertage_liste = self._feiertags_info.get("feiertage_liste", [])
        for feiertag in feiertage_liste:
            if feiertag["start_datum"] == heute:
                aktueller_feiertag = feiertag["name"]
                datum = feiertag["start_datum"].strftime("%d.%m.%Y")
                break

        if not aktueller_feiertag:
            aktueller_feiertag = self._feiertags_info["naechster_feiertag_name"]
            datum = self._feiertags_info["naechster_feiertag_datum"]

        return {
            "Name Feiertag": aktueller_feiertag,
            "Datum": datum,
            "Land": self._location["land_name"],  # Dynamisch aus der Konfiguration übernommen
            "Region": self._location["region_name"],  # Dynamisch aus der Konfiguration übernommen
        }

    async def async_update(self, session=None):
        """
        Aktualisiert die Feiertagsdaten.
        
        Lädt die Feiertagsdaten von der API und überprüft, ob ein Feiertag ansteht.
        Wenn bereits ein Update innerhalb der letzten 24 Stunden durchgeführt wurde,
        wird kein neues Update durchgeführt.

        :param session: Optional, eine bestehende aiohttp-Session. Wenn nicht gesetzt,
                        wird eine neue Session erstellt.
        """
        jetzt = datetime.now()
        heute = jetzt.date()
        letztes_update = self._feiertags_info.get("letztes_update")

        # Falls das letzte Update am selben Tag war, wird es übersprungen
        if letztes_update and letztes_update.date() == heute:
            _LOGGER.debug(
                "Update übersprungen. Letztes Update war am: %s",
                letztes_update.date(),
            )
            return  # Kein API-Call notwendig

        _LOGGER.debug("Starte API-Abfrage für Feiertagsdaten.")
        close_session = False

        if session is None:
            session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
            close_session = True

        try:
            # Zeitraum für die Abfrage
            startdatum = (heute - timedelta(days=30)).strftime("%Y-%m-%d")
            enddatum = (heute + timedelta(days=365)).strftime("%Y-%m-%d")

            api_parameter = {
                "countryIsoCode": self._location["land"],  # Aus dem config-_flow übernommen
                "subdivisionCode": self._location["region"],  # Aus dem config-_flow übernommen
                "validFrom": startdatum,
                "validTo": enddatum,
                "languageIsoCode": self._location["iso_code"],
            }

            # Debug-Ausgabe der API-Parameter im Log
            _LOGGER.debug("Verwendete API-Parameter: %s", api_parameter)


            # API-Daten abrufen
            feiertage_daten = None
            urls = [API_URL_FEIERTAGE, API_FALLBACK_FEIERTAGE]
            for url in urls:
                _LOGGER.debug("Prüfe URL: %s", url)
                if not isinstance(url, str):
                    _LOGGER.error("Ungültige URL: %s", url)
                    continue

                try:
                    feiertage_daten = await fetch_data(url, api_parameter, session)
                    if feiertage_daten:
                        break
                except Exception as e:
                    _LOGGER.error("Fehler beim Abrufen der Daten von %s: %s", url, e)

            if not feiertage_daten:
                _LOGGER.warning("Keine Daten von der API erhalten.")
                return

            # Verarbeite die Daten
            try:
                feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")
                self._feiertags_info["feiertage_liste"] = feiertage_liste
            except Exception as e:
                _LOGGER.error("Fehler beim Verarbeiten der Daten: %s", e)
                return

            # Prüfen, ob heute ein Feiertag ist
            aktueller_feiertag = next(
                (
                    feiertag for feiertag in feiertage_liste
                    if feiertag["start_datum"] <= heute <= feiertag["end_datum"]
                ),
                None,
            )

            # Zustand und Attribute aktualisieren
            if aktueller_feiertag:
                self._feiertags_info.update({
                    "heute_feiertag": True,
                    "naechster_feiertag_name": aktueller_feiertag["name"],
                    "naechster_feiertag_datum": aktueller_feiertag["start_datum"].strftime(
                        "%d.%m.%Y"
                    ),
                })
            else:
                self._feiertags_info["heute_feiertag"] = False
                zukunft_feiertage = [
                    feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute
                ]
                if zukunft_feiertage:
                    naechster_feiertag = min(zukunft_feiertage, key=lambda f: f["start_datum"])
                    self._feiertags_info.update({
                        "naechster_feiertag_name": naechster_feiertag["name"],
                        "naechster_feiertag_datum": naechster_feiertag["start_datum"].strftime(
                            "%d.%m.%Y"
                        ),
                    })

            # Aktualisiere den Zeitstempel für das letzte Update
            self._feiertags_info["letztes_update"] = jetzt
            _LOGGER.debug(
                "Update abgeschlossen. Neues letztes Update: %s",
                self._feiertags_info["letztes_update"],
            )

        except Exception as e:
            _LOGGER.error("Unerwarteter Fehler beim Aktualisieren der Feiertagsdaten: %s", e)

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("API-Session geschlossen.")
