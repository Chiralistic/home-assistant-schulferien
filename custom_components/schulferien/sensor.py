"""Sensor-Modul für Schulferien und Feiertage sowie Brückentage in Home Assistant."""

import logging
from datetime import datetime, timedelta

import aiohttp
from homeassistant.helpers.entity import Entity
from .const import API_URL_FERIEN, API_URL_FEIERTAGE, STANDARD_LAND

_LOGGER = logging.getLogger(__name__)

async def hole_daten(api_url: str, api_parameter: dict, session: aiohttp.ClientSession = None) -> dict:
    """Allgemeine Funktion, um Daten von der API abzurufen."""
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", api_url, api_parameter)
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    timeout = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)

    try:
        async with session.get(api_url, params=api_parameter, headers={"Accept": "application/json"}, timeout=timeout) as antwort:
            antwort.raise_for_status()
            daten = await antwort.json()
            _LOGGER.debug("API-Antwort erhalten: %s", antwort.status)
            return daten
    except aiohttp.ClientTimeout as fehler:
        _LOGGER.error("Die Anfrage zur API hat das Timeout überschritten: %s", fehler)
        raise RuntimeError("API-Anfrage überschritt das Timeout-Limit.") from fehler
    except aiohttp.ClientError as fehler:
        _LOGGER.error("API-Anfrage fehlgeschlagen: %s", fehler)
        raise RuntimeError(f"API-Anfrage fehlgeschlagen: {fehler}") from fehler
    finally:
        if close_session:
            _LOGGER.debug("Die API-Session wird geschlossen.")
            await session.close()

def parse_daten(json_daten, brueckentage=None, typ="ferien"):
    """Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu."""
    try:
        liste = []
        for eintrag in json_daten:
            name = eintrag.get("name", [{"text": "Unbekannt"}])[0]["text"]
            liste.append({
                "name": name,
                "start_datum": datetime.fromisoformat(eintrag["startDate"]).date(),
                "end_datum": datetime.fromisoformat(eintrag["endDate"]).date(),
            })

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
    except (KeyError, ValueError, IndexError, TypeError) as fehler:
        _LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", fehler)
        raise RuntimeError("Ungültige JSON-Daten erhalten.") from fehler

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
        return "Ferientag" if self._ferien_info["heute_ferientag"] else "Kein Ferientag"

    @property
    def extra_state_attributes(self):
        return {
            "Land": self._land,
            "Region": self._region,
            "Nächste Ferien": self._ferien_info["naechste_ferien_name"],
            "Beginn": self._ferien_info["naechste_ferien_beginn"],
            "Ende": self._ferien_info["naechste_ferien_ende"],
            "Brückentage": self._brueckentage,
        }

    async def async_update(self, session=None):
        """Aktualisiere den Sensor mit den neuesten Daten von der API."""
        heute = datetime.now().date()
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Schulferien wurde heute bereits abgefragt.")
            return

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            api_parameter = {
                "countryIsoCode": self._land,
                "subdivisionCode": self._region,
                "validFrom": heute.strftime("%Y-%m-%d"),
                "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
            }

            ferien_daten = await hole_daten(API_URL_FERIEN, api_parameter, session)
            ferien_liste = parse_daten(ferien_daten, self._brueckentage)

            self._ferien_info["heute_ferientag"] = any(
                ferien["start_datum"] <= heute <= ferien["end_datum"]
                for ferien in ferien_liste
            )

            zukunftsferien = [ferien for ferien in ferien_liste if ferien["start_datum"] > heute]
            if zukunftsferien:
                naechste_ferien = min(zukunftsferien, key=lambda f: f["start_datum"])
                self._ferien_info["naechste_ferien_name"] = naechste_ferien["name"]
                self._ferien_info["naechste_ferien_beginn"] = naechste_ferien["start_datum"].strftime("%d.%m.%Y")
                self._ferien_info["naechste_ferien_ende"] = naechste_ferien["end_datum"].strftime("%d.%m.%Y")
            else:
                self._ferien_info["naechste_ferien_name"] = None
                self._ferien_info["naechste_ferien_beginn"] = None
                self._ferien_info["naechste_ferien_ende"] = None

            self._last_update_date = heute

        except RuntimeError as error:
            _LOGGER.warning("API konnte nicht erreicht werden: %s", error)

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("Session wurde geschlossen.")


class FeiertagSensor(Entity):
    """Sensor für Feiertage."""

    def __init__(self, hass, config):
        self._hass = hass
        self._name = config["name"]
        self._land = config["land"]
        self._region = config["region"]
        self._last_update_date = None
        self._heute_feiertag = None
        self._naechster_feiertag_name = None
        self._naechster_feiertag_datum = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"sensor.feiertag_{self._land}_{self._region}_{self._name}"

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
        heute = datetime.now().date()
        if self._last_update_date == heute:
            _LOGGER.debug("Die API für Feiertage wurde heute bereits abgefragt.")
            return

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            api_parameter = {
                "countryIsoCode": self._land,
                "subdivisionCode": self._region,
                "validFrom": heute.strftime("%Y-%m-%d"),
                "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
            }

            feiertage_daten = await hole_daten(API_URL_FEIERTAGE, api_parameter, session)
            feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")

            self._heute_feiertag = any(feiertag["start_datum"] == heute for feiertag in feiertage_liste)

            zukunft_feiertage = [feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute]
            if zukunft_feiertage:
                naechster_feiertag = min(zukunft_feiertage, key=lambda f: f["start_datum"])
                self._naechster_feiertag_name = naechster_feiertag["name"]
                self._naechster_feiertag_datum = naechster_feiertag["start_datum"].strftime("%d.%m.%Y")
            else:
                self._naechster_feiertag_name = None
                self._naechster_feiertag_datum = None

            self._last_update_date = heute

        except RuntimeError as error:
            _LOGGER.warning("API konnte nicht erreicht werden: %s", error)

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("Session wurde geschlossen.")

class SchulferienFeiertagSensor(Entity):
    """Kombinierter Sensor für Schulferien und Feiertage."""

    def __init__(self, hass, config):
        self._hass = hass
        self._name = config["name"]
        self._schulferien_entity_id = config["schulferien_entity_id"]
        self._feiertag_entity_id = config["feiertag_entity_id"]
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return "sensor.schulferien_feiertag"

    @property
    def state(self):
        return "Ferientag/Feiertag" if self._state else "Kein Ferientag/Feiertag"

    @property
    def extra_state_attributes(self):
        return {
            "Schulferien Sensor": self._schulferien_entity_id,
            "Feiertag Sensor": self._feiertag_entity_id,
        }

    async def async_update(self):
        schulferien_state = self._hass.states.get(self._schulferien_entity_id)
        feiertag_state = self._hass.states.get(self._feiertag_entity_id)

        _LOGGER.debug("Schulferien-Sensorzustand: %s", schulferien_state.state if schulferien_state else "None")
        _LOGGER.debug("Feiertag-Sensorzustand: %s", feiertag_state.state if feiertag_state else "None")

        self._state = (
            (schulferien_state and schulferien_state.state == "Ferientag") or
            (feiertag_state and feiertag_state.state == "Feiertag")
        )

        _LOGGER.debug("Kombinierter Sensorzustand: %s", self.state)



async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup der Sensoren für Schulferien, Feiertage und die Kombination."""

    name = config.get("name", "Schulferien/Feiertag")
    land = config.get("country_code", "DE")
    region = config.get("region", "DE-NI")
    brueckentage = config.get("bridge_days", [])

    # Konfiguration für Schulferien-Sensor
    config_schulferien = {
        "name": f"{name}_schulferien",
        "land": land,
        "region": region,
        "brueckentage": brueckentage,
    }

    # Konfiguration für Feiertag-Sensor
    config_feiertag = {
        "name": f"{name}_feiertag",
        "land": land,
        "region": region,
    }

    # Konfiguration für kombinierten Sensor
    config_kombi = {
        "name": f"{name}_kombiniert",
        "schulferien_entity_id": "sensor.schulferien",
        "feiertag_entity_id": "sensor.feiertag",
    }

    async with aiohttp.ClientSession() as session:
        # Erstellen des Schulferien-Sensors
        schulferien_sensor = SchulferienSensor(hass, config_schulferien)

        # Erstellen des Feiertag-Sensors
        feiertag_sensor = FeiertagSensor(hass, config_feiertag)

        # Erstellen des kombinierten Schulferien- und Feiertag-Sensors
        kombi_sensor = SchulferienFeiertagSensor(hass, config_kombi)

        # Sensoren zu Home Assistant hinzufügen
        async_add_entities([schulferien_sensor, feiertag_sensor, kombi_sensor])

        # Initialisiere die Daten für beide Sensoren mit der gemeinsamen Session
        await schulferien_sensor.async_update(session)
        await feiertag_sensor.async_update(session)
