"""Modul zum Setup der Sensoren für Schulferien und Feiertage."""

import logging
import aiohttp

from .schulferien_sensor import SchulferienSensor, SchulferienMorgenSensor
from .feiertag_sensor import FeiertagSensor, FeiertagMorgenSensor
from .api_utils import load_bridge_days, compute_region_slug

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup der Sensoren für Schulferien und Feiertage."""

    land = config_entry.data.get("land")
    region = config_entry.data.get("region")
    land_name = config_entry.data.get("land_name")
    region_name = config_entry.data.get("region_name")

    instance_prefix = f"{land}_{region}".upper()
    region_slug = compute_region_slug(land, region)

    _LOGGER.debug(
        "Konfigurationsdaten aus Config Entry: Land=%s, Region=%s, "
        "Landname=%s, Regionsname=%s, Prefix=%s, Slug=%s",
        land, region, land_name, region_name, instance_prefix, region_slug
    )

    bridge_days_path = hass.config.path("custom_components/schulferien/bridge_days.yaml")
    brueckentage = await load_bridge_days(bridge_days_path)

    config_schulferien = {
        "name": f"Schulferien - {land_name} ({region_name})",
        "unique_id": f"schulferien_{instance_prefix}",
        "entity_id": f"sensor.schulferien_{land.lower()}_{region_slug.lower()}",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
        "brueckentage": brueckentage,
    }

    config_feiertag = {
        "name": f"Feiertag - {land_name} ({region_name})",
        "unique_id": f"feiertag_{instance_prefix}",
        "entity_id": f"sensor.feiertag_{land.lower()}_{region_slug.lower()}",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
    }

    async with aiohttp.ClientSession() as session:
        schulferien_sensor = SchulferienSensor(hass, config_schulferien)
        feiertag_sensor = FeiertagSensor(hass, config_feiertag)
        schulferien_morgen_sensor = SchulferienMorgenSensor(schulferien_sensor)
        feiertag_morgen_sensor = FeiertagMorgenSensor(feiertag_sensor)

        async_add_entities([
            schulferien_sensor,
            feiertag_sensor,
            schulferien_morgen_sensor,
            feiertag_morgen_sensor
        ])

        # Initiale Datenaktualisierung mit gemeinsamer Session
        await schulferien_sensor.async_update(session)
        await feiertag_sensor.async_update(session)
