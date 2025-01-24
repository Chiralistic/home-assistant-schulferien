"""Modul für die Verwaltung und den Abruf von Feiertagen in Deutschland."""

import logging
from homeassistant.core import HomeAssistant
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
import aiohttp
from .api_utils import fetch_data, parse_daten, DEFAULT_TIMEOUT
from .const import API_URL_FEIERTAGE, API_FALLBACK_FEIERTAGE, COUNTRIES, REGIONS, DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE

_LOGGER = logging.getLogger(__name__)

def get_country_name(code):
    """Gibt den ausgeschriebenen Ländernamen für einen Ländercode zurück."""
    return COUNTRIES.get(code, code)

def get_region_name(country_code, region_code):
    """Gibt den ausgeschriebenen Regionsnamen für einen Regionscode zurück."""
    return REGIONS.get(country_code, {}).get(region_code, region_code)

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
        self._hass = hass
        self._name = config["name"]
        self._unique_id = config.get("unique_id", "sensor.feiertag")
        self._location = {"land": config["land"], "region": config["region"]}
        self._feiertags_info = {
            "heute_feiertag": None,
            "naechster_feiertag_name": None,
            "naechster_feiertag_datum": None,
            "feiertage_liste": [],
            "letztes_update": None,  # Neuer Schlüssel
        }

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird."""
        _LOGGER.debug("Feiertag-Sensor hinzugefügt. Starte Initial-Update.")
        await self.async_update()
        self.async_write_ha_state()

        async def async_daily_update(_):
            """Tägliche Aktualisierung."""
            _LOGGER.debug("Tägliches Update ausgelöst.")
            await self.async_update()
            self.async_write_ha_state()

        async_track_time_change(
            self._hass,
            async_daily_update,
            hour=DAILY_UPDATE_HOUR,
            minute=DAILY_UPDATE_MINUTE,
        )
        _LOGGER.debug("Tägliche Abfrage um %02d:%02d eingerichtet.", DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE)

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
            "Land": get_country_name(self._location["land"]),
            "Region": get_region_name(self._location["land"], self._location["region"]),
        }

    async def async_update(self, session=None):
        """Aktualisiert die Feiertagsdaten nur, wenn das Intervall überschritten wurde."""
        jetzt = datetime.now()
        heute = jetzt.date()

        # Prüfen, ob ein Update notwendig ist
        if self._feiertags_info.get("letztes_update") and (
            jetzt - self._feiertags_info["letztes_update"]
        ) < timedelta(hours=24):
            _LOGGER.debug(
                "Update übersprungen. Letztes Update war vor %s Stunden.",
                (jetzt - self._feiertags_info["letztes_update"]).total_seconds() // 3600,
            )
            return  # Update nicht erforderlich

        _LOGGER.debug("Starte Update der Feiertagsdaten.")
        close_session = False

        if session is None:
            session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
            close_session = True

        try:
            # Zeitraum für die Abfrage
            startdatum = (heute - timedelta(days=30)).strftime("%Y-%m-%d")
            enddatum = (heute + timedelta(days=365)).strftime("%Y-%m-%d")

            # Holen der aktuellen Sprache aus der Home Assistant-Konfiguration
            language_iso_code = self.hass.config.language[:2].upper()  # Z.B. "de" -> "DE"

            # Debug-Ausgabe des Sprachcodes im Log
            self._logger.debug(f"Verwendeter Sprachcode: {language_iso_code}")

            api_parameter = {
                "countryIsoCode": self._location["land"],
                "subdivisionCode": self._location["region"],
                "validFrom": startdatum,
                "validTo": enddatum,
                "languageIsoCode": language_iso_code,
            }

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
                    "naechster_feiertag_datum": aktueller_feiertag["start_datum"].strftime("%d.%m.%Y"),
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
                        "naechster_feiertag_datum": naechster_feiertag["start_datum"].strftime("%d.%m.%Y"),
                    })

            # Aktualisiere den Zeitstempel für das letzte Update
            self._feiertags_info["letztes_update"] = jetzt
            _LOGGER.debug(
                "Update abgeschlossen. Letztes Update um: %s",
                self._feiertags_info["letztes_update"],
            )

        except Exception as e:
            _LOGGER.error("Unerwarteter Fehler beim Aktualisieren der Feiertagsdaten: %s", e)

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("API-Session geschlossen.")
