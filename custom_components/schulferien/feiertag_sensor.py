"""Modul für die Verwaltung und den Abruf von Feiertagen in Deutschland."""

import logging
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.entity import Entity
import aiohttp
from .api_utils import fetch_data, parse_daten, DEFAULT_TIMEOUT
from .const import API_URL_FEIERTAGE, API_FALLBACK_FEIERTAGE, COUNTRIES, REGIONS

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
            "feiertage_liste": [],  # <-- Initialisiert als leere Liste
        }

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird."""
        # Initiale Abfrage beim Hinzufügen der Entität
        await self.async_update()
        self.async_write_ha_state()  # Zustand direkt nach Update speichern
        _LOGGER.debug("Initiale Abfrage beim Hinzufügen der Entität durchgeführt.")

        """Frage die API täglich um drei Uhr morgens ab."""
        # Zeitplan für die tägliche Abfrage um 3 Uhr morgens
        async def async_daily_update(_):
            await self.async_update()
            self.async_write_ha_state()  # Zustand nach Update speichern

        # Korrekte async-Zeitplanung verwenden
        async_track_time_change(
            self._hass,
            async_daily_update,  # Direkt awaitable Funktion verwenden
            hour=3,
            minute=0,
            second=0,
        )
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
        return "Feiertag" if self._feiertags_info.get("heute_feiertag", False) else "Kein Feiertag"

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
        """Aktualisiert die Feiertagsdaten."""
        heute = datetime.now().date()

        # Session sicherstellen
        close_session = False
        if session is None:  # Lokale Session erstellen, wenn keine übergeben wurde
            session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
            close_session = True  # Merken, dass diese geschlossen werden muss

        try:
            # Zeitraum erweitern, um laufende Feiertage zu erfassen
            startdatum = (heute - timedelta(days=30)).strftime("%Y-%m-%d")
            enddatum = (heute + timedelta(days=365)).strftime("%Y-%m-%d")

            api_parameter = {
                "countryIsoCode": self._location["land"],
                "subdivisionCode": self._location["region"],
                "validFrom": startdatum,
                "validTo": enddatum,
                "languageIsoCode": "DE",
            }

            # URLs für die Abfrage
            urls = [API_URL_FEIERTAGE, API_FALLBACK_FEIERTAGE]
            feiertage_daten = None

            # API-Daten abrufen
            for url in urls:
                _LOGGER.debug("Prüfe URL: %s", url)  # Log-Ausgabe zur Fehlerdiagnose
                if not isinstance(url, str):  # Typ prüfen
                    _LOGGER.error("Ungültige URL im Feiertags-Sensor: %s", url)
                    continue  # Überspringe ungültige URLs

                try:
                    # API-Call
                    feiertage_daten = await fetch_data(url, api_parameter, session)
                    if feiertage_daten:  # Bei Erfolg abbrechen
                        break
                except Exception as e:
                    _LOGGER.error("Fehler beim Abrufen der Daten von %s: %s", url, e)

            if not feiertage_daten:
                _LOGGER.warning("Keine Feiertagsdaten von der API erhalten.")
                # Leere Attribute setzen
                self._feiertags_info.update({
                    "heute_feiertag": False,
                    "naechster_feiertag_name": None,
                    "naechster_feiertag_datum": None,
                })
                self.async_write_ha_state()  # Zustand speichern
                return

            # Verarbeite die Daten
            try:
                feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")
                self._feiertags_info["feiertage_liste"] = feiertage_liste
            except Exception as e:
                _LOGGER.error("Fehler beim Verarbeiten der Feiertagsdaten: %s", e)
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
                # Aktueller Feiertag vorhanden
                self._feiertags_info.update({
                    "heute_feiertag": True,
                    "naechster_feiertag_name": aktueller_feiertag["name"],
                    "naechster_feiertag_datum": aktueller_feiertag["start_datum"].strftime("%d.%m.%Y"),
                })
            else:
                # Kein aktueller Feiertag, also prüfe den nächsten
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

            # Zustand speichern
            self._last_update_date = heute
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Unerwarteter Fehler beim Aktualisieren der Feiertagsdaten: %s", e)

        finally:
            # Lokale Session schließen, wenn sie erstellt wurde
            if close_session:
                await session.close()
                _LOGGER.debug("API-Session geschlossen.")
