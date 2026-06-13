"""Modul für die Verwaltung und den Abruf von Schulferien.

Zwei Sensor-Klassen:
1. SchulferienSensor — Hauptsensor mit API-Abfrage und Brückentag-Logik
2. SchulferienMorgenSensor — Spiegel-Sensor für morgen (liest vom Hauptsensor)

Warum zwei Klassen statt einer? Der Hauptsensor muss die API aufrufen,
Daten parsen und Brückentage berechnen. Der Morgen-Sensor braucht dieselben
Daten nur für +1 Tag. Statt die API zweimal aufzurufen, referenziert
MorgenSensor den Hauptsensor und liest dessen Daten aus.
"""

import logging
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
import aiohttp
from .api_utils import fetch_data, parse_daten, DEFAULT_TIMEOUT, compute_region_slug
from .const import (
    API_URL_FERIEN,
    API_FALLBACK_FERIEN,
    DAILY_UPDATE_HOUR,
    DAILY_UPDATE_MINUTE,
)

_LOGGER = logging.getLogger(__name__)

# EntityDescription mit Übersetzungsschlüssel für Home Assistant UI
SCHULFERIEN_SENSOR = SensorEntityDescription(
    key="schulferien",
    name="Schulferien",
    translation_key="schulferien",
)

# pylint: disable=invalid-name
SCHULFERIEN_MORGEN_SENSOR = SensorEntityDescription(
    key="schulferien_morgen",
    name="Schulferien Morgen",
    translation_key="schulferien_morgen",
)

class SchulferienSensor(SensorEntity):
    """Sensor für Schulferien und Brückentage.

    Hauptverantwortlichkeiten:
    - API-Abfrage der Schulferiendaten (OpenHolidaysAPI)
    - Berechnung ob heute ein Ferientag ist
    - Angabe der nächsten Ferien (Name, Beginn, Ende)
    - Brückentag-Erkennung (konfigurierbar in bridge_days.yaml)
    - Tägliche Aktualisierung um 03:00 Uhr

    Warum 30 Tage zurück + 365 Tage vor? Die API liefert nur
    einen begrenzten Zeitraum. 30 Tage Puffer zurück decken
    nachgelieferte/berichtigte Daten ab. 365 Tage vor reichen
    für die Vorhersage der nächsten Ferien.
    """

    # pylint: disable=unused-argument,missing-function-docstring
    def __init__(self, hass, config):
        """Initialisiert den Schulferien-Sensor mit Konfigurationsdaten."""
        self.entity_description = SCHULFERIEN_SENSOR
        self._name = config["name"]
        land_upper = config["land"].upper()
        region_slug = compute_region_slug(config["land"], config["region"])
        land_lower = config["land"].lower()
        region_slug_lower = region_slug.lower()
        self._unique_id = config.get("unique_id", f"schulferien_{land_upper}_{region_slug}")
        self._entity_id = config.get(
            "entity_id", f"sensor.schulferien_{land_lower}_{region_slug_lower}"
        )
        self._location = {
            "land": config["land"],
            "region": config["region"],
            "land_name": config["land_name"],
            "region_name": config["region_name"],
            # iso_code wird in async_added_to_hass aus HA konfiguriert
            "iso_code": "DE",
        }
        # Brückentage aus bridge_days.yaml — manuell konfigurierte Daten
        self._brueckentage = config.get("brueckentage", [])
        # Cancel-Funktion fuer den taeglichen Timer (gesetzt in async_added_to_hass)
        self._cancel_timer = None
        # Alle Feriendaten und Berechnungen
        self._ferien_info = {
            "heute_ferientag": None,
            "naechste_ferien_name": None,
            "naechste_ferien_beginn": None,
            "naechste_ferien_ende": None,
            "ferien_liste": [],
            "letztes_update": None,
        }
        _LOGGER.debug("Sensor für %s mit Land: %s, Region: %s, Brückentagen: %s",
            self._name, self._location["land"], self._location["region"],
            self._brueckentage
        )

    async def async_added_to_hass(self):
        """Initialisierung des Sensors nach dem Hinzufügen zu HA.

        Warum iso_code hier setzen? Der HA-Kontext ist erst nach
        async_added_to_hass vollständig verfügbar.
        """
        _LOGGER.debug("Schulferien-Sensor hinzugefügt, erstes Update wird ausgeführt.")

        # Sprachcode aus HA laden — für API-Lokalisierung needed
        if self.hass and self.hass.config:
            self._location["iso_code"] = self.hass.config.language[:2].upper()
        else:
            self._location["iso_code"] = "DE"
            _LOGGER.warning("Schulferien-Sensor: Fallback auf Standard 'DE'.")

        _LOGGER.debug("Schulferien-Sensor: Verwendeter Sprachcode: %s", self._location["iso_code"])

        letztes_update = self._ferien_info.get("letztes_update")
        jetzt = datetime.now()

        # Update nur bei fehlendem oder abgelaufenem (Tag gewechselt)
        # Warum? Vermeidet unnötige API-Aufrufe innerhalb eines Tages
        if not letztes_update or letztes_update.date() != jetzt.date():
            await self.async_update()
            self.async_write_ha_state()

        # Täglicher Timer um 03:00 — nach Mitternacht, bevor die meisten Nutzer aktiv sind
        async def async_daily_update(_):
            """Tägliche Aktualisierung um 03:00 Uhr."""
            _LOGGER.debug("Tägliches Update ausgelöst.")
            await self.async_update()
            self.async_write_ha_state()

        self._cancel_timer = async_track_time_change(
            self.hass,
            async_daily_update,
            hour=DAILY_UPDATE_HOUR,
            minute=DAILY_UPDATE_MINUTE,
        )
        _LOGGER.debug(
            "Tägliche Abfrage um %02d:%02d eingerichtet.", DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE
        )

    async def async_will_remove_from_hass(self):
        """Cleanup: Entfernt den taeglichen Timer-Listener.
        Warum wichtig? Ohne Cleanup feuert der Listener weiter,
        nachdem die Entity aus HA entfernt wurde (z.B. bei Multi-Instance-Unload).
        """
        if self._cancel_timer:
            self._cancel_timer()
            self._cancel_timer = None
            _LOGGER.debug("Timer-Cleanup fuer SchulferienSensor durchgefuehrt.")

    @property
    def name(self):
        """Gibt den Namen des Sensors zurück."""
        return self._name

    @property
    def unique_id(self):
        """Gibt die eindeutige ID des Sensors zurück."""
        return self._unique_id

    @property
    def entity_id(self):
        """Gibt die Entity ID des Sensors zurück."""
        return self._entity_id

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

        # Leere Liste als Fallback falls 'ferien_liste' fehlt
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
        """Aktualisiert die Schulferiendaten durch Abfrage der API.

        Warum session-Parameter? sensor.py erstellt alle Sensoren innerhalb
        eines gemeinsamen aiohttp.ClientSession. Beide Sensoren teilen sich
        die Session für initiale Updates — spart Ressourcen.
        Wenn keine Session übergeben wird, wird eine neue erstellt und
        nach dem Aufruf wieder geschlossen.
        """
        heute = datetime.now().date()
        jetzt = datetime.now()

        # Update nur einmal pro Tag — API-Antworten ändern sich tagsüber nicht
        letztes_update = self._ferien_info.get("letztes_update")
        if letztes_update and letztes_update.date() == heute:
            _LOGGER.debug(
                "Update übersprungen. Letztes Update war heute um %s.",
                letztes_update.strftime("%H:%M:%S"),
            )
            return

        _LOGGER.debug("Starte Update der Schulferiendaten.")
        close_session = False

        # Eigene Session erstellen falls keine übergeben wurde
        if session is None:
            session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
            close_session = True

        try:
            api_parameter = self.get_api_parameter(heute)
            ferien_daten = await self.hole_ferien_daten(api_parameter, session)

            if not ferien_daten:
                _LOGGER.warning("Keine Daten von der API erhalten.")
                return

            self.verarbeite_ferien_daten(ferien_daten, heute)

            self._ferien_info["letztes_update"] = jetzt
            _LOGGER.debug(
                "Update abgeschlossen. Letztes Update um: %s",
                self._ferien_info["letztes_update"],
            )

        except (aiohttp.ClientError, ValueError, KeyError, TypeError) as e:
            _LOGGER.error("Unerwarteter Fehler beim Aktualisieren der Daten: %s", e)

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("API-Session geschlossen.")

    def get_api_parameter(self, heute):
        """Erstellt die API-Parameter für die Anfrage."""
        return {
            "countryIsoCode": self._location["land"],
            "subdivisionCode": self._location["region"],
            "validFrom": (heute - timedelta(days=30)).strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
            "languageIsoCode": self._location["iso_code"],
        }

    async def hole_ferien_daten(self, api_parameter, session):
        """Versucht, die Ferientermine von der API abzurufen."""
        for url in [API_URL_FERIEN, API_FALLBACK_FERIEN]:
            _LOGGER.debug("Prüfe URL: %s", url)
            try:
                ferien_daten = await fetch_data(url, api_parameter, session)
                if ferien_daten:
                    return ferien_daten
            except aiohttp.ClientError as e:
                _LOGGER.error("Fehler beim Abrufen der Daten von %s: %s", url, e)
        return None

    def verarbeite_ferien_daten(self, ferien_daten, heute):
        """Verarbeitet die erhaltenen Ferien-Daten."""
        try:
            ferien_liste = parse_daten(ferien_daten, self._brueckentage)
            self._ferien_info["ferien_liste"] = ferien_liste
        except ValueError as e:
            _LOGGER.error("Fehler beim Verarbeiten der Daten: %s", e)
            return

        aktuelles_ereignis = next(
            (ferien
            for ferien in ferien_liste
            if ferien["start_datum"] <= heute <= ferien["end_datum"]),
            None,
        )

        if aktuelles_ereignis:
            self._ferien_info.update({
                "heute_ferientag": True,
                "naechste_ferien_name": aktuelles_ereignis["name"],
                "naechste_ferien_beginn": aktuelles_ereignis["start_datum"].strftime("%d.%m.%Y"),
                "naechste_ferien_ende": aktuelles_ereignis["end_datum"].strftime("%d.%m.%Y"),
            })
        else:
            self._ferien_info["heute_ferientag"] = False
            zukunftsferien = [ferien for ferien in ferien_liste if ferien["start_datum"] > heute]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                self._ferien_info.update({
                    "naechste_ferien_name": naechste_ferien["name"],
                    "naechste_ferien_beginn": naechste_ferien["start_datum"].strftime("%d.%m.%Y"),
                    "naechste_ferien_ende": naechste_ferien["end_datum"].strftime("%d.%m.%Y"),
                })

# Zweite Definition der EntityDescription (oben als Konstante, hier für Klassen-Referenz)
# pylint: disable=invalid-name
SCHULFERIEN_MORGEN_SENSOR = SensorEntityDescription(
    key="schulferien_morgen",
    name="Schulferien Morgen",
    translation_key="schulferien_morgen",
)

class SchulferienMorgenSensor(SensorEntity):
    """Sensor für Schulferien morgen.

    Warum Referenzsensor statt eigener API-Aufruf?
    Der Hauptsensor (SchulferienSensor) hat die Daten bereits von der API.
    Statt die API zweimal aufzurufen (heute + morgen), liest dieser Sensor
    die bereits geladenen Daten des Hauptsensors aus und filtert für morgen.
    Das spart API-Calls und garantiert Datenkonsistenz.

    Warum `ferien_liste or []`? Verhindert TypeError wenn ferien_liste None ist
    (Bug 1 Fix: None-Liste + Iteration = Crash).
    """

    def __init__(self, referenzsensor: SchulferienSensor):
        """Erstellt den Morgen-Sensor basierend auf dem Hauptsensor.

        Args:
            referenzsensor: Der Hauptsensor (SchulferienSensor) dessen Daten verwendet werden.
        """
        self.entity_description = SCHULFERIEN_MORGEN_SENSOR
        self._referenzsensor = referenzsensor
        # Name vom Referenzsensor ableiten: "Schulferien - Bayern" → "Schulferien Morgen - Bayern"
        base_name = referenzsensor._name
        if " - " in base_name:
            self._attr_name = f"Schulferien Morgen{base_name[base_name.index(' - '):]}"
        else:
            self._attr_name = f"{base_name} Morgen"
        # Unique ID und Entity ID vom Referenzsensor ableiten (_morgen Suffix)
        base_unique_id = referenzsensor.unique_id
        base_entity_id = referenzsensor.entity_id
        self._attr_unique_id = f"{base_unique_id}_morgen"
        self._attr_entity_id = f"{base_entity_id}_morgen"
        self._attr_native_value = None

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def entity_id(self):
        """Gibt die Entity ID des Sensors zurück."""
        return self._attr_entity_id

    @property
    def name(self):
        """Gibt den Namen des Sensors zurück."""
        return self._attr_name

    @property
    def native_value(self):
        """Gibt den aktuellen Zustand des Sensors zurück.

        Warum morgen = heute + 1 Tag? Dieser Sensor soll anzeigen ob
        MORGEN ein Ferientag ist. Die Daten kommen aus dem Referenzsensor.
        """
        morgen = datetime.now().date() + timedelta(days=1)
        # pylint: disable=protected-access
        # Oder-Operator verhindert TypeError bei None (Bug 1 Fix)
        ferien_liste = self._referenzsensor._ferien_info.get("ferien_liste") or []
        # pylint: enable=protected-access
        for ferien in ferien_liste:
            if ferien["start_datum"] <= morgen <= ferien["end_datum"]:
                return "ferientag"
        return "kein_ferientag"

    # pylint: disable=missing-function-docstring
    async def async_update(self):
        """Aktualisiert den Zustand des Sensors über den Referenzsensor.

        Warum passiv? Der Morgen-Sensor hat keine eigene API-Logik.
        Er aktualisiert sich aus den Daten des Referenzsensors.
        """
