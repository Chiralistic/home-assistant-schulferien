"""Sensor-Modul für Schulferien und Feiertage sowie Brückentage in Home Assistant."""

import logging
import os
import json
from datetime import datetime, timedelta

import aiohttp
import aiofiles
from homeassistant.helpers.entity import Entity
from .const import (
    API_URL_FERIEN,
    API_URL_FEIERTAGE,
    STANDARD_SPRACHE,
    STANDARD_LAND,
    TRANSLATION_PATH
)

_LOGGER = logging.getLogger(__name__)

async def lade_uebersetzung(sprache):
    """Lädt die Übersetzung basierend auf der gewählten Sprache asynchron."""
    dateipfad = os.path.join(os.path.dirname(__file__), TRANSLATION_PATH, f"{sprache.lower()}.json")
    try:
        async with aiofiles.open(dateipfad, "r", encoding="utf-8") as file:
            inhalt = await file.read()  # Asynchron lesen
            return json.loads(inhalt)  # JSON parsen
    except (FileNotFoundError, json.JSONDecodeError) as fehler:
        _LOGGER.error("Fehler beim Laden der Übersetzung: %s", fehler)
        return {}

async def load_translation(self):
    """Asynchrone Methode zum Laden der Übersetzungen."""
    self._translations = await lade_uebersetzung(self.sprache)


async def hole_daten(api_url, api_parameter, session=None):
    """Allgemeine Funktion, um Daten von der API abzurufen."""
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", api_url, api_parameter)
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True
    try:
        # Die API-Abfrage wird durchgeführt
        async with session.get(
            api_url,
            params=api_parameter,
            headers={"Accept": "application/json"}
        ) as antwort:
            # Löst eine Ausnahme aus, wenn die HTTP-Antwort einen Fehlerstatus hat
            antwort.raise_for_status()
            daten = await antwort.json()  # Konvertiere die Antwort in ein JSON-Objekt
            _LOGGER.debug("API-Antwort erhalten: %s", antwort.status)
            return daten
    except aiohttp.ClientError as fehler:
        # Fehlerbehandlung, falls die API-Anfrage fehlschlägt
        _LOGGER.error("API-Anfrage fehlgeschlagen: %s", fehler)
        raise RuntimeError(f"API-Anfrage fehlgeschlagen: {fehler}") from fehler
    finally:
        if close_session:
            await session.close()

def parse_daten(json_daten, brueckentage=None, typ="ferien"):
    """Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu."""
    try:
        liste = []
        # Iteriere über alle Einträge in den JSON-Daten
        for eintrag in json_daten:
            # Extrahiere den Namen des Feiertags oder der Ferien in deutscher Sprache
            name = next(
                (name_item["text"]
                for name_item in eintrag.get("name", [])
                if name_item.get("language") == "DE"),
                eintrag.get("name", [{"text": "Unbekannt"}])[0]["text"]
            )
            liste.append({
                "name": name,
                "start_datum": datetime.fromisoformat(eintrag["startDate"]).date(),
                "end_datum": datetime.fromisoformat(eintrag["endDate"]).date(),
            })

        # Falls Brückentage angegeben sind, werden diese zur Liste hinzugefügt
        if typ == "ferien" and brueckentage:
            for tag in brueckentage:
                datum = datetime.strptime(tag, "%d.%m.%Y").date()
                liste.append({
                    "name": "Brückentag",
                    "start_datum": datum,
                    "end_datum": datum,
                })

        _LOGGER.debug("JSON-Daten erfolgreich verarbeitet: %d Einträge", len(liste))
        return liste
    except (KeyError, ValueError, IndexError) as fehler:
        # Fehlerbehandlung, falls beim Verarbeiten der JSON-Daten ein Fehler auftritt
        _LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", fehler)
        raise RuntimeError("Ungültige JSON-Daten erhalten.") from fehler

class SchulferienSensor(Entity):
    """Sensor für Schulferien und Brückentage."""

    def __init__(self, hass, name, land, region, brueckentage, sprache=STANDARD_SPRACHE):
        # Initialisierung des Sensors mit den übergebenen Parametern
        self._hass = hass
        self._name = name
        self._land = land
        self._region = region
        self._brueckentage = brueckentage
        self.sprache = sprache  # Hier wird das Attribut 'sprache' gesetzt
        self._translations = {}
        self._last_update_date = None  # Speichert den Tag der letzten Abfrage

        # Interne Variablen für die Berechnung der Ferien
        self._heute_ferientag = None
        self._naechste_ferien_name = None
        self._naechste_ferien_beginn = None
        self._naechste_ferien_ende = None

    @property
    def name(self):
        return self._translations.get("name_schulferien", "Schulferien")  # Der Name des Sensors

    @property
    def unique_id(self):
        return "sensor.schulferien"  # Eindeutige ID für den Sensor

    @property
    def state(self):
        return "Ferientag" if self._heute_ferientag else "Kein Ferientag"  # Der Zustand des Sensors

    @property
    def extra_state_attributes(self):
        # Zusätzliche Attribute, die im UI angezeigt werden
        return {
            "Land": self._land,
            "Region": self._region,
            "Nächste Ferien": self._naechste_ferien_name,
            "Beginn": self._naechste_ferien_beginn,
            "Ende": self._naechste_ferien_ende,
            "Brückentage": self._brueckentage,
        }

    async def async_update(self, session=None):
        """Aktualisiere den Sensor mit den neuesten Daten von der API."""
        heute = datetime.now().date()

        # Prüfen, ob die API heute schon abgefragt wurde
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Schulferien wurde heute bereits abgefragt.")
            return

        _LOGGER.debug("Starte API-Abfrage für Schulferien.")
        api_parameter = {
            "countryIsoCode": self._land,
            "subdivisionCode": self._region,
            "languageIsoCode": self.sprache,
            "validFrom": heute.strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        try:
            ferien_daten = await hole_daten(API_URL_FERIEN, api_parameter, session)
            ferien_liste = parse_daten(ferien_daten, self._brueckentage)

            # Überprüfe, ob heute ein Ferientag ist
            self._heute_ferientag = any(
                ferien["start_datum"] <= heute <= ferien["end_datum"]
                for ferien in ferien_liste
            )

            # Bestimme die nächsten Ferien
            zukunftsferien = [
                ferien for ferien in ferien_liste if ferien["start_datum"] > heute
            ]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                self._naechste_ferien_name = naechste_ferien["name"]
                self._naechste_ferien_beginn = naechste_ferien["start_datum"].strftime("%d.%m.%Y")
                self._naechste_ferien_ende = naechste_ferien["end_datum"].strftime("%d.%m.%Y")
            else:
                self._naechste_ferien_name = None
                self._naechste_ferien_beginn = None
                self._naechste_ferien_ende = None

            # Aktualisiere den Tag der letzten Abfrage
            self._last_update_date = heute

        except RuntimeError:
            _LOGGER.warning("API konnte nicht erreicht werden.")


    async def load_translation(self):
        """Asynchrone Methode zum Laden der Übersetzungen für den Schulferien-Sensor."""
        self._translations = await lade_uebersetzung(self.sprache)


class FeiertagSensor(Entity):
    """Sensor für Feiertage."""

    def __init__(self, hass, name, land, region, sprache=STANDARD_SPRACHE):
        self._hass = hass
        self._name = name
        self._land = land
        self._region = region
        self.sprache = sprache
        self._translations = {}
        self._last_update_date = None  # Speichert den Tag der letzten Abfrage

        self._heute_feiertag = None
        self._naechster_feiertag_name = None
        self._naechster_feiertag_datum = None

    @property
    def name(self):
        return self._translations.get("name_feiertag", "Feiertag")

    @property
    def unique_id(self):
        return "sensor.feiertag"

    @property
    def state(self):
        return "Feiertag" if self._heute_feiertag else "Kein Feiertag"

    @property
    def extra_state_attributes(self):
        return {
            "Land": self._land,
            "Region": self._region,
            "Nächster Feiertag": self._naechster_feiertag_name,
            "Datum des nächsten Feiertags": self._naechster_feiertag_datum,
        }

    async def async_update(self, session=None):
        """Aktualisiere den Sensor mit den neuesten Daten von der API."""
        heute = datetime.now().date()

        # Prüfen, ob die API heute schon abgefragt wurde
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Feiertage wurde heute bereits abgefragt.")
            return

        _LOGGER.debug("Starte API-Abfrage für Feiertage.")
        api_parameter = {
            "countryIsoCode": self._land,
            "subdivisionCode": self._region,
            "languageIsoCode": self.sprache,
            "validFrom": heute.strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        try:
            feiertage_daten = await hole_daten(API_URL_FEIERTAGE, api_parameter, session)
            feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")

            # Überprüfe, ob heute ein Feiertag ist
            self._heute_feiertag = any(
                feiertag["start_datum"] == heute for feiertag in feiertage_liste
            )

            # Bestimme den nächsten Feiertag
            zukunft_feiertage = [
                feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute
            ]
            if zukunft_feiertage:
                naechster_feiertag = min(zukunft_feiertage, key=lambda f: f["start_datum"])
                self._naechster_feiertag_name = naechster_feiertag["name"]
                self._naechster_feiertag_datum = naechster_feiertag["start_datum"].strftime("%d.%m.%Y")
            else:
                self._naechster_feiertag_name = None
                self._naechster_feiertag_datum = None

            # Aktualisiere den Tag der letzten Abfrage
            self._last_update_date = heute

        except RuntimeError:
            _LOGGER.warning("API konnte nicht erreicht werden.")


    async def load_translation(self):
        """Asynchrone Methode zum Laden der Feiertags-Übersetzungen."""
        self._translations = await lade_uebersetzung(self.sprache)

class SchulferienFeiertagSensor(Entity):
    """Kombinierter Sensor für Schulferien und Feiertage."""

    def __init__(
        self, hass, name, schulferien_entity_id, feiertag_entity_id, sprache=STANDARD_SPRACHE
    ):
        self._hass = hass
        self._name = name
        self._schulferien_entity_id = schulferien_entity_id
        self._feiertag_entity_id = feiertag_entity_id
        self.sprache = sprache
        self._translations = {}
        self._state = None

    @property
    def name(self):
        return self._translations.get("name_combined", "Schulferien/Feiertag")

    @property
    def unique_id(self):
        return "sensor.schulferien_feiertag"

    @property
    def state(self):
        return "Ferientag/Feiertag" if self._state else "Kein Ferientag/Feiertag"

    @property
    def extra_state_attributes(self):
        """Zusätzliche Attribute für den kombinierten Sensor."""
        return {
            "Schulferien Sensor": self._schulferien_entity_id,
            "Feiertag Sensor": self._feiertag_entity_id,
        }

    async def async_update(self):
        """Kombiniere die Zustände der beiden Sensoren (Schulferien und Feiertag)."""
        schulferien_state = self._hass.states.get(self._schulferien_entity_id)
        feiertag_state = self._hass.states.get(self._feiertag_entity_id)

        # Überprüfen, ob entweder der Schulferien- oder der Feiertag-Sensor aktiv ist
        self._state = (
            (schulferien_state and schulferien_state.state == "Ferientag") or
            (feiertag_state and feiertag_state.state == "Feiertag")
        )

    async def load_translation(self):
        """Asynchrone Methode zum Laden der Übersetzungen für den kombinierten Sensor."""
        self._translations = await lade_uebersetzung(self.sprache)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup der Sensoren für Schulferien, Feiertage und die Kombination."""
    name = config.get("name", "Schulferien/Feiertag")
    land = config.get("country_code", STANDARD_LAND)
    region = config.get("region", "DE-NI")
    brueckentage = config.get("bridge_days", [])

    async with aiohttp.ClientSession() as session:
        # Erstellen des Schulferien-Sensors
        schulferien_sensor = SchulferienSensor(
            hass, f"{name}_schulferien", land, region, brueckentage, sprache=STANDARD_SPRACHE
        )

        # Erstellen des Feiertag-Sensors
        feiertag_sensor = FeiertagSensor(
            hass, f"{name}_feiertag", land, region, sprache=STANDARD_SPRACHE
        )

        # Erstellen des Kombi-Sensors, der die Zustände der beiden Sensoren kombiniert
        kombi_sensor = SchulferienFeiertagSensor(
            hass,
            f"{name}_kombiniert",
            schulferien_entity_id="sensor.schulferien",
            feiertag_entity_id="sensor.feiertag",
        )

        # Asynchrones Laden der Übersetzungen für beide Sensoren
        await schulferien_sensor.load_translation()
        await feiertag_sensor.load_translation()

        # Sensoren zu Home Assistant hinzufügen
        async_add_entities([schulferien_sensor, feiertag_sensor, kombi_sensor])

        # Initialisiere die Daten für beide Sensoren mit der gemeinsamen Session
        await schulferien_sensor.async_update(session)
        await feiertag_sensor.async_update(session)
