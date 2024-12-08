import aiohttp
import logging
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util.dt import now as dt_now
from .const import API_URL, STANDARD_SPRACHE, STANDARD_LAND

_LOGGER = logging.getLogger(__name__)

async def hole_ferien(api_parameter):
    """
    Fragt Ferieninformationen von der API ab.

    :param api_parameter: Dictionary mit API-Parametern.
    :return: JSON-Daten als Python-Dictionary.
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

def parse_ferien(json_daten, brueckentage):
    """
    Verarbeitet die JSON-Daten und fügt Brückentage hinzu.

    :param json_daten: JSON-Daten als Python-Dictionary.
    :param brueckentage: Liste von Brückentagen im deutschen Datumsformat.
    :return: Liste von Ferien mit Name, Start- und Enddatum.
    """
    try:
        ferien_liste = []
        for eintrag in json_daten:
            # Extrahiere den Namen der Ferien basierend auf der Sprache
            name = next(
                (name_item["text"] for name_item in eintrag["name"] if name_item["language"] == "DE"),
                eintrag["name"][0]["text"]  # Fallback: Erster Name, falls keine passende Sprache gefunden wird
            )
            ferien_liste.append({
                "name": name,
                "start_datum": datetime.fromisoformat(eintrag["startDate"]).date(),
                "end_datum": datetime.fromisoformat(eintrag["endDate"]).date(),
            })

        # Füge Brückentage hinzu
        for tag in brueckentage:
            datum = datetime.strptime(tag, "%d.%m.%Y").date()
            ferien_liste.append({
                "name": "Brückentag",
                "start_datum": datum,
                "end_datum": datum,
            })

        _LOGGER.debug("JSON-Daten erfolgreich verarbeitet: %d Ferieneinträge", len(ferien_liste))
        return ferien_liste
    except (KeyError, ValueError, IndexError) as fehler:
        _LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", fehler)
        raise RuntimeError("Ungültige JSON-Daten erhalten.")

class SchulferienSensor(Entity):
    """Sensor für Schulferien."""

    def __init__(self, hass, name, land, region, brueckentage):
        self._hass = hass
        self._name = name
        self._land = land
        self._region = region
        self._brueckentage = brueckentage  # Liste der Brückentage
        self._heute_ferientag = None
        self._naechste_ferien_name = None
        self._naechste_ferien_beginn = None
        self._naechste_ferien_ende = None

    @property
    def name(self):
        return "Schulferien"

    @property
    def unique_id(self):
        return "sensor.schulferien"

    @property
    def state(self):
        return "Ferientag" if self._heute_ferientag else "Kein Ferientag"

    @property
    def extra_state_attributes(self):
        """
        Zusätzliche Attribute des Sensors.
        """
        return {
            "Land": self._land,
            "Region": self._region,
            "Nächste Ferien": self._naechste_ferien_name,
            "Beginn": self._naechste_ferien_beginn,
            "Ende": self._naechste_ferien_ende,
            "Brückentage": self._brueckentage,  # Brückentage als Attribut hinzufügen
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
            json_daten = await hole_ferien(api_parameter)
            ferien_liste = parse_ferien(json_daten, self._brueckentage)

            # Heute ein Ferientag?
            self._heute_ferientag = any(
                ferien["start_datum"] <= heute <= ferien["end_datum"]
                for ferien in ferien_liste
            )

            # Nächste Ferien
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

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """
    Einrichtung des Sensors basierend auf `configuration.yaml`.

    :param hass: Home Assistant Instanz.
    :param config: Konfigurationsdaten.
    :param async_add_entities: Funktion zum Hinzufügen von Sensoren.
    """
    name = config.get("name", "Schulferien")
    land = config.get("country_code", STANDARD_LAND)
    region = config.get("region", "DE-NI")
    brueckentage = config.get("bridge_days", [])
    async_add_entities([SchulferienSensor(hass, name, land, region, brueckentage)])
