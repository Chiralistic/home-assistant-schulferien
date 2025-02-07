"""Modul zum Setup der Sensoren für Schulferien, Feiertage und den kombinierten Sensor."""

import logging
import aiofiles
import aiohttp
import yaml

from .schulferien_sensor import SchulferienSensor
from .feiertag_sensor import FeiertagSensor
from .kombinierter_sensor import SchulferienFeiertagSensor

_LOGGER = logging.getLogger(__name__)

async def load_bridge_days(bridge_days_path):
    """Lädt die Brückentage aus der bridge_days.yaml-Datei asynchron."""
    try:
        async with aiofiles.open(bridge_days_path, "r", encoding="utf-8") as file:
            content = await file.read()
            if not content:
                return []
            bridge_days_config = yaml.safe_load(content)
            return bridge_days_config.get("bridge_days", [])
    except FileNotFoundError:
        _LOGGER.warning("Die Datei bridge_days.yaml wurde nicht gefunden.")
        return []
    except yaml.YAMLError as error:
        _LOGGER.error("Fehler beim Laden der Brückentage: %s", error)
        return []

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup der Sensoren für Schulferien, Feiertage und die Kombination über Config Flow."""
    
    # Konfigurationsdaten direkt aus dem Config Entry übernehmen
    land = config_entry.data.get("land")
    region = config_entry.data.get("region")
    land_name = config_entry.data.get("land_name")
    region_name = config_entry.data.get("region_name")

    # Debugging: Loggen der vollständigen Konfiguration
    _LOGGER.debug(
        "Konfigurationsdaten aus Config Entry: Land=%s, Region=%s, Landname=%s, Regionsname=%s",
        land, region, land_name, region_name
    )

    # Brückentage asynchron laden
    bridge_days_path = hass.config.path("custom_components/schulferien/bridge_days.yaml")
    brueckentage = await load_bridge_days(bridge_days_path)

    # Konfiguration für Schulferien-Sensor
    config_schulferien = {
        "name": "Schulferien",
        "unique_id": "sensor.schulferien",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
        "brueckentage": brueckentage,
    }

    # Konfiguration für Feiertag-Sensor
    config_feiertag = {
        "name": "Feiertag",
        "unique_id": "sensor.feiertag",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
    }

    # Konfiguration für kombinierten Sensor
    config_kombi = {
        "name": "Schulferien/Feiertage kombiniert",
        "unique_id": "sensor.schulferien_feiertage",
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
        _LOGGER.debug("Füge Schulferien-Sensor hinzu.")
        _LOGGER.debug("Füge Feiertag-Sensor hinzu.")
        _LOGGER.debug("Füge kombinierten Schulferien-Feiertag-Sensor hinzu.")

        # Initialisiere die Daten für beide Sensoren mit der gemeinsamen Session
        await schulferien_sensor.async_update(session)
        await feiertag_sensor.async_update(session)
