import aiohttp
import logging
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from .const import API_URL_FERIEN, API_URL_FEIERTAGE, STANDARD_SPRACHE, STANDARD_LAND

_LOGGER = logging.getLogger(__name__)

async def hole_daten(api_url, api_parameter):
    """Allgemeine Funktion, um Daten von der API abzurufen."""
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", api_url, api_parameter)
    async with aiohttp.ClientSession() as session:
        try:
            # Die API-Abfrage wird durchgeführt
            async with session.get(api_url, params=api_parameter, headers={"Accept": "application/json"}) as antwort:
                antwort.raise_for_status()  # Löst eine Ausnahme aus, wenn die HTTP-Antwort einen Fehlerstatus hat
                daten = await antwort.json()  # Konvertiere die Antwort in ein JSON-Objekt
                _LOGGER.debug("API-Antwort erhalten: %s", antwort.status)
                return daten
        except aiohttp.ClientError as fehler:
            # Fehlerbehandlung, falls die API-Anfrage fehlschlägt
            _LOGGER.error("API-Anfrage fehlgeschlagen: %s", fehler)
            raise RuntimeError(f"API-Anfrage fehlgeschlagen: {fehler}")

def parse_daten(json_daten, brueckentage=None, typ="ferien"):
    """Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu."""
    try:
        liste = []
        # Iteriere über alle Einträge in den JSON-Daten
        for eintrag in json_daten:
            # Extrahiere den Namen des Feiertags oder der Ferien in deutscher Sprache
            name = next(
                (name_item["text"] for name_item in eintrag["name"] if name_item["language"] == "DE"),
                eintrag["name"][0]["text"]
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
        raise RuntimeError("Ungültige JSON-Daten erhalten.")

class SchulferienSensor(Entity):
    """Sensor für Schulferien und Brückentage."""

    def __init__(self, hass, name, land, region, brueckentage):
        # Initialisierung des Sensors mit den übergebenen Parametern
        self._hass = hass
        self._name = name
        self._land = land
        self._region = region
        self._brueckentage = brueckentage

        # Interne Variablen für die Berechnung der Ferien
        self._heute_ferientag = None
        self._naechste_ferien_name = None
        self._naechste_ferien_beginn = None
        self._naechste_ferien_ende = None

    @property
    def name(self):
        return "Schulferien"  # Der Name des Sensors

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

    async def async_update(self):
        """Aktualisiere den Sensor mit den neuesten Daten von der API."""
        heute = datetime.now().date()
        api_parameter = {
            "countryIsoCode": self._land,
            "subdivisionCode": self._region,
            "languageIsoCode": STANDARD_SPRACHE,
            "validFrom": heute.strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        try:
            # Hole die Ferien-Daten von der API
            ferien_daten = await hole_daten(API_URL_FERIEN, api_parameter)
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

        except RuntimeError:
            _LOGGER.warning("API konnte nicht erreicht werden, Daten sind möglicherweise nicht aktuell.")

class FeiertagSensor(Entity):
    """Sensor für Feiertage."""

    def __init__(self, hass, name, land, region):
        self._hass = hass
        self._name = name
        self._land = land
        self._region = region

        self._heute_feiertag = None
        self._naechster_feiertag_name = None
        self._naechster_feiertag_datum = None

    @property
    def name(self):
        return "Feiertag"

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

    async def async_update(self):
        heute = datetime.now().date()
        api_parameter = {
            "countryIsoCode": self._land,
            "subdivisionCode": self._region,
            "languageIsoCode": STANDARD_SPRACHE,
            "validFrom": heute.strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
        }

        try:
            # Hole die Feiertage-Daten von der API
            feiertage_daten = await hole_daten(API_URL_FEIERTAGE, api_parameter)
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

        except RuntimeError:
            _LOGGER.warning("API konnte nicht erreicht werden, Daten sind möglicherweise nicht aktuell.")

class SchulferienFeiertagSensor(Entity):
    """Kombinierter Sensor für Schulferien und Feiertage."""

    def __init__(self, hass, name, schulferien_entity_id, feiertag_entity_id):
        self._hass = hass
        self._name = name
        self._schulferien_entity_id = schulferien_entity_id
        self._feiertag_entity_id = feiertag_entity_id
        self._state = None

    @property
    def name(self):
        return "Schulferien/Feiertag"

    @property
    def unique_id(self):
        return "sensor.schulferien_feiertag"

    @property
    def state(self):
        return "Ferientag/Feiertag" if self._state else "Kein Ferientag/Feiertag"

    async def async_update(self):
        """Kombiniere die Zustände der anderen beiden Sensoren."""
        schulferien_state = self._hass.states.get(self._schulferien_entity_id)
        feiertag_state = self._hass.states.get(self._feiertag_entity_id)

        self._state = (
            (schulferien_state and schulferien_state.state == "Ferientag")
            or (feiertag_state and feiertag_state.state == "Feiertag")
        )


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup der Sensoren für Schulferien, Feiertage und die Kombination."""
    name = config.get("name", "Schulferien/Feiertag")
    land = config.get("country_code", STANDARD_LAND)
    region = config.get("region", "DE-NI")
    brueckentage = config.get("bridge_days", [])

    # Erstellen des Schulferien-Sensors
    schulferien_sensor = SchulferienSensor(hass, f"{name}_schulferien", land, region, brueckentage)
    
    # Erstellen des Feiertag-Sensors
    feiertag_sensor = FeiertagSensor(hass, f"{name}_feiertag", land, region)

    # Erstellen des Kombi-Sensors, der die Zustände der beiden Sensoren kombiniert
    kombi_sensor = SchulferienFeiertagSensor(
        hass,
        f"{name}_kombiniert",
        schulferien_entity_id="sensor.schulferien",
        feiertag_entity_id="sensor.feiertag",
    )

    # Sensoren zu Home Assistant hinzufügen
    async_add_entities([schulferien_sensor, feiertag_sensor, kombi_sensor])
