from homeassistant.components.sensor import SensorEntity
from .schulferien_sensor import SchulferienSensor
from .feiertag_sensor import FeiertagSensor
from .kombinierter_sensor import SchulferienFeiertagSensor
import aiohttp

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
