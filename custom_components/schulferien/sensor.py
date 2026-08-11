"""Modul zum Setup der Sensoren für Schulferien und Feiertage."""

import logging
import aiohttp

from .schulferien_sensor import SchulferienSensor, SchulferienMorgenSensor
from .feiertag_sensor import FeiertagSensor, FeiertagMorgenSensor
from .api_utils import load_bridge_days, compute_region_slug

_LOGGER = logging.getLogger(__name__)


def _create_sensor_configs(land, region, land_name, region_name, brueckentage):
    """Erstellt Konfigurationsdicts für Schulferien- und Feiertag-Sensoren.

    Args:
        land: Ländercode (z.B. "DE").
        region: Regionscode (z.B. "DE-BY").
        land_name: Angezeigter Ländername.
        region_name: Angezeigter Regionsname.
        brueckentage: Liste der Brückentage.

    Returns:
        Tuple von (schulferien_config, feiertag_config).
    """
    region_slug = compute_region_slug(land, region)

    schulferien_config = {
        "name": f"Schulferien - {land_name} ({region_name})",
        "unique_id": f"schulferien_{land.upper()}_{region_slug}",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
        "brueckentage": brueckentage,
    }

    feiertag_config = {
        "name": f"Feiertag - {land_name} ({region_name})",
        "unique_id": f"feiertag_{land.upper()}_{region_slug}",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
    }

    return schulferien_config, feiertag_config


def _create_sensors(hass, config_schulferien, config_feiertag):
    """Erstellt und registriert alle vier Sensoren.

    Args:
        hass: Home Assistant Instanz.
        config_schulferien: Konfig für Schulferien-Sensor.
        config_feiertag: Konfig für Feiertag-Sensor.

    Returns:
        Liste der vier Sensor-Instanzen.
    """
    schulferien_sensor = SchulferienSensor(hass, config_schulferien)
    feiertag_sensor = FeiertagSensor(hass, config_feiertag)
    schulferien_morgen_sensor = SchulferienMorgenSensor(schulferien_sensor)
    feiertag_morgen_sensor = FeiertagMorgenSensor(feiertag_sensor)

    return [
        schulferien_sensor,
        feiertag_sensor,
        schulferien_morgen_sensor,
        feiertag_morgen_sensor,
    ]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup der Sensoren für Schulferien und Feiertage.

    Diese Funktion wird von Home Assistant aufgerufen, wenn die Integration
    mit einem Config Entry geladen wird. Sie erstellt vier Sensoren:
    - SchulferienSensor: Zeigt aktuellen Ferientag an
    - FeiertagSensor: Zeigt aktuellen Feiertag an
    - SchulferienMorgenSensor: Zeigt Ferientag morgen an
    - FeiertagMorgenSensor: Zeigt Feiertag morgen an

    Args:
        hass: Home Assistant Instanz.
        config_entry: Config Entry mit Land/Region-Konfiguration.
        async_add_entities: Funktion zum Hinzufügen von Entitäten.
    """
    land = config_entry.data.get("land")
    region = config_entry.data.get("region")
    land_name = config_entry.data.get("land_name")
    region_name = config_entry.data.get("region_name")

    bridge_days_path = hass.config.path("custom_components/schulferien/bridge_days.yaml")
    brueckentage = await load_bridge_days(bridge_days_path)

    config_schulferien, config_feiertag = _create_sensor_configs(
        land, region, land_name, region_name, brueckentage
    )

    sensors = _create_sensors(hass, config_schulferien, config_feiertag)

    # Entities zu HA registrieren bevor Updates laufen
    async_add_entities(sensors)

    async with aiohttp.ClientSession() as session:
        await sensors[0].async_update(session)
        await sensors[1].async_update(session)
