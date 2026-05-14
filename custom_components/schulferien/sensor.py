"""Modul zum Setup der Sensoren für Schulferien und Feiertage."""

import logging
import aiohttp

from .schulferien_sensor import SchulferienSensor, SchulferienMorgenSensor
from .feiertag_sensor import FeiertagSensor, FeiertagMorgenSensor
from .api_utils import load_bridge_days, compute_region_slug

_LOGGER = logging.getLogger(__name__)

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

    # Konfigurationsdaten direkt aus dem Config Entry übernehmen
    land = config_entry.data.get("land")
    region = config_entry.data.get("region")
    land_name = config_entry.data.get("land_name")
    region_name = config_entry.data.get("region_name")

    # Eindeutiges Präfix aus Land und Region für unique_ids (z.B. "_DE_DE-BY")
    instance_prefix = f"{land}_{region}".upper()
    # Slugified region für entity_ids (z.B. "BY" statt "DE-BY")
    region_slug = compute_region_slug(land, region)

    # Debug-Ausgabe der Konfigurationsdaten
    _LOGGER.debug(
        "Konfigurationsdaten aus Config Entry: Land=%s, Region=%s, "
        "Landname=%s, Regionsname=%s, Prefix=%s, Slug=%s",
        land, region, land_name, region_name, instance_prefix, region_slug
    )

    # Pfad zur bridge_days.yaml ermitteln und Brückentage asynchron laden
    bridge_days_path = hass.config.path("custom_components/schulferien/bridge_days.yaml")
    brueckentage = await load_bridge_days(bridge_days_path)

    # Konfiguration für Schulferien-Sensor
    # unique_id und entity_id verwenden beide slugified region für Konsistenz
    config_schulferien = {
        "name": f"Schulferien - {land_name} ({region_name})",
        "unique_id": f"schulferien_{land.upper()}_{region_slug}",
        "entity_id": f"sensor.schulferien_{land.lower()}_{region_slug.lower()}",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
        "brueckentage": brueckentage,
    }

    # Konfiguration für Feiertag-Sensor
    # unique_id und entity_id verwenden beide slugified region für Konsistenz
    config_feiertag = {
        "name": f"Feiertag - {land_name} ({region_name})",
        "unique_id": f"feiertag_{land.upper()}_{region_slug}",
        "entity_id": f"sensor.feiertag_{land.lower()}_{region_slug.lower()}",
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
    }

    # Gemeinsame HTTP-Session für initiale Datenaktualisierung beider Sensoren
    async with aiohttp.ClientSession() as session:
        # Schulferien-Sensor erstellen (liest API-Daten für Schulferien)
        schulferien_sensor = SchulferienSensor(hass, config_schulferien)
        # Feiertag-Sensor erstellen (liest API-Daten für Feiertage)
        feiertag_sensor = FeiertagSensor(hass, config_feiertag)
        # Morgen-Sensoren basieren auf den Haupt-Sensoren (lesen deren Daten)
        schulferien_morgen_sensor = SchulferienMorgenSensor(schulferien_sensor)
        feiertag_morgen_sensor = FeiertagMorgenSensor(feiertag_sensor)

        # Alle vier Sensoren bei Home Assistant registrieren
        async_add_entities([
            schulferien_sensor,
            feiertag_sensor,
            schulferien_morgen_sensor,
            feiertag_morgen_sensor
        ])

        # Initiale Datenaktualisierung mit gemeinsamer Session
        await schulferien_sensor.async_update(session)
        await feiertag_sensor.async_update(session)
