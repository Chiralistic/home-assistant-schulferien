"""Hauptmodul für die Schulferien- und Feiertags-Integration."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .schulferien_sensor import SchulferienSensor
from .feiertag_sensor import FeiertagSensor
from .kombinierter_sensor import SchulferienFeiertagSensor
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Richte die Sensoren aus einem Konfigurationseintrag ein."""

    name = f"Schulferien {entry.data['country']} {entry.data['region']}"
    country = entry.data["country"]
    region = entry.data["region"]
    brueckentage = entry.data.get("bridge_days", [])

    # Erstellen des Schulferien-Sensors
    schulferien_sensor = SchulferienSensor(
        hass, {"name": f"{name}_schulferien", "land": country, "region": region, "brueckentage": brueckentage}
    )

    # Erstellen des Feiertag-Sensors
    feiertag_sensor = FeiertagSensor(
        hass, {"name": f"{name}_feiertag", "land": country, "region": region}
    )

    # Erstellen des kombinierten Schulferien- und Feiertag-Sensors
    kombi_sensor = SchulferienFeiertagSensor(
        hass,
        {
            "name": f"{name}_kombiniert",
            "schulferien_entity_id": schulferien_sensor.unique_id,
            "feiertag_entity_id": feiertag_sensor.unique_id,
        },
    )

    # Füge die Sensoren zu Home Assistant hinzu
    async_add_entities([schulferien_sensor, feiertag_sensor, kombi_sensor])

    _LOGGER.debug("Sensoren erfolgreich eingerichtet.")