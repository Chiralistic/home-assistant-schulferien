"""Binary sensors for school holidays and public holidays integration."""

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from .api_utils import compute_region_slug

_LOGGER = logging.getLogger(__name__)

SCHULFERIEN_FEIERTAG_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_feiertag",
    name="Schulferien/Feiertage",
    translation_key="schulferien_feiertag",
)

SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_feiertag_morgen",
    name="Schulferien/Feiertage Morgen",
    translation_key="schulferien_feiertag_morgen",
)

# NEU: Nur Schulferien
SCHULFERIEN_ONLY_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_only",
    name="Nur Schulferien",
    translation_key="schulferien_only",
)

SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_only_morgen",
    name="Nur Schulferien Morgen",
    translation_key="schulferien_only_morgen",
)

# NEU: Nur Feiertag
FEIERTAG_ONLY_BINARY_SENSOR = BinarySensorEntityDescription(
    key="feiertag_only",
    name="Nur Feiertage",
    translation_key="feiertag_only",
)

FEIERTAG_ONLY_MORGEN_BINARY_SENSOR = BinarySensorEntityDescription(
    key="feiertag_only_morgen",
    name="Nur Feiertage Morgen",
    translation_key="feiertag_only_morgen",
)


class SchulferienFeiertagBinarySensor(BinarySensorEntity):
    """Kombinierter Binärsensor für Schulferien und Feiertage."""

    def __init__(self, hass, config):
        """Initialisiere den Sensor.

        Args:
            hass: Home Assistant Instanz.
            config: Konfigurationsdaten für den Sensor.
        """
        self.entity_description = SCHULFERIEN_FEIERTAG_BINARY_SENSOR
        self._hass = hass
        land_upper = config.get("land", "DE").upper()
        region_slug = compute_region_slug(config.get("land", "DE"), config.get("region", "BY"))
        self._unique_id = config.get(
            "unique_id", f"binary_sensor.schulferien_feiertage_{land_upper}_{region_slug}"
        )
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors."""
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = bool(
            (schulferien_state and schulferien_state.state == "ferientag")
            or (feiertag_state and feiertag_state.state == "feiertag")
        )


class SchulferienFeiertagMorgenBinarySensor(BinarySensorEntity):
    """Kombinierter Binärsensor für morgen."""

    def __init__(self, hass, config):
        """Initialisiere den Sensor.

        Args:
            hass: Home Assistant Instanz.
            config: Konfigurationsdaten für den Sensor.
        """
        self.entity_description = SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR
        self._hass = hass
        land_upper = config.get("land", "DE").upper()
        region_slug = compute_region_slug(config.get("land", "DE"), config.get("region", "BY"))
        self._unique_id = config.get(
            "unique_id", f"binary_sensor.schulferien_feiertage_{land_upper}_{region_slug}_morgen"
        )
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors."""
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = bool(
            (schulferien_state and schulferien_state.state == "ferientag")
            or (feiertag_state and feiertag_state.state == "feiertag")
        )


class SchulferienOnlyBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Schulferien."""

    def __init__(self, hass, config):
        """Initialisiere den Sensor.

        Args:
            hass: Home Assistant Instanz.
            config: Konfigurationsdaten für den Sensor.
        """
        self.entity_description = SCHULFERIEN_ONLY_BINARY_SENSOR
        self._hass = hass
        land_upper = config.get("land", "DE").upper()
        region_slug = compute_region_slug(config.get("land", "DE"), config.get("region", "BY"))
        self._unique_id = config.get(
            "unique_id", f"binary_sensor.schulferien_only_{land_upper}_{region_slug}"
        )
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors."""
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )

        self._state = bool(
            schulferien_state and schulferien_state.state == "ferientag"
        )


class SchulferienOnlyMorgenBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Schulferien morgen."""

    def __init__(self, hass, config):
        """Initialisiere den Sensor.

        Args:
            hass: Home Assistant Instanz.
            config: Konfigurationsdaten für den Sensor.
        """
        self.entity_description = SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR
        self._hass = hass
        land_upper = config.get("land", "DE").upper()
        region_slug = compute_region_slug(config.get("land", "DE"), config.get("region", "BY"))
        self._unique_id = config.get(
            "unique_id", f"binary_sensor.schulferien_only_{land_upper}_{region_slug}_morgen"
        )
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors."""
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )

        self._state = bool(
            schulferien_state and schulferien_state.state == "ferientag"
        )


class FeiertagOnlyBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Feiertag."""

    def __init__(self, hass, config):
        """Initialisiere den Sensor.

        Args:
            hass: Home Assistant Instanz.
            config: Konfigurationsdaten für den Sensor.
        """
        self.entity_description = FEIERTAG_ONLY_BINARY_SENSOR
        self._hass = hass
        land_upper = config.get("land", "DE").upper()
        region_slug = compute_region_slug(config.get("land", "DE"), config.get("region", "BY"))
        self._unique_id = config.get(
            "unique_id", f"binary_sensor.feiertag_only_{land_upper}_{region_slug}"
        )
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors."""
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = bool(
            feiertag_state and feiertag_state.state == "feiertag"
        )


class FeiertagOnlyMorgenBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Feiertag morgen."""

    def __init__(self, hass, config):
        """Initialisiere den Sensor.

        Args:
            hass: Home Assistant Instanz.
            config: Konfigurationsdaten für den Sensor.
        """
        self.entity_description = FEIERTAG_ONLY_MORGEN_BINARY_SENSOR
        self._hass = hass
        land_upper = config.get("land", "DE").upper()
        region_slug = compute_region_slug(config.get("land", "DE"), config.get("region", "BY"))
        self._unique_id = config.get(
            "unique_id", f"binary_sensor.feiertag_only_{land_upper}_{region_slug}_morgen"
        )
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors."""
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = bool(
            feiertag_state and feiertag_state.state == "feiertag"
        )


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup der Binärsensoren für eine Konfiguration.

    Args:
        hass: Home Assistant Instanz.
        entry: Config entry für die Konfiguration.
        async_add_entities: Funktion zum Hinzufügen von Entitäten.
    """
    _LOGGER.debug("Initialisiere alle Binärsensoren für Entry: %s", entry.title)

    # Eindeutiges Präfix aus Land und Region generieren (z.B. "_DE_BY")
    land = entry.data.get("land", "DE")
    region = entry.data.get("region", "BY")
    instance_prefix = f"{land}_{region}".upper()

    # Entity IDs mit Präfix
    schulferien_entity_id = f"sensor.schulferien_{instance_prefix.lower()}"
    feiertag_entity_id = f"sensor.feiertag_{instance_prefix.lower()}"
    schulferien_morgen_entity_id = f"sensor.schulferien_{instance_prefix.lower()}_morgen"
    feiertag_morgen_entity_id = f"sensor.feiertag_{instance_prefix.lower()}_morgen"

    # Base unique_id prefix für binary sensors
    binary_unique_prefix = f"binary_sensor.schulferien_feiertage_{instance_prefix}"

    config_base = {
        "land": land,
        "region": region,
    }

    config_heute = {
        **config_base,
        "schulferien_entity_id": schulferien_entity_id,
        "feiertag_entity_id": feiertag_entity_id,
        "unique_id": binary_unique_prefix,
    }

    config_morgen = {
        **config_base,
        "schulferien_entity_id": schulferien_morgen_entity_id,
        "feiertag_entity_id": feiertag_morgen_entity_id,
        "unique_id": f"{binary_unique_prefix}_morgen",
    }

    # NEU: eigene Configs mit eigenen unique_ids
    config_schulferien_only_heute = {
        **config_base,
        **config_heute,
        "unique_id": f"binary_sensor.schulferien_only_{instance_prefix}",
    }

    config_schulferien_only_morgen = {
        **config_base,
        **config_morgen,
        "unique_id": f"binary_sensor.schulferien_only_{instance_prefix}_morgen",
    }

    config_feiertag_only_heute = {
        **config_base,
        **config_heute,
        "unique_id": f"binary_sensor.feiertag_only_{instance_prefix}",
    }

    config_feiertag_only_morgen = {
        **config_base,
        **config_morgen,
        "unique_id": f"binary_sensor.feiertag_only_{instance_prefix}_morgen",
    }

    sensors = [
        # bestehende (unverändert!)
        SchulferienFeiertagBinarySensor(hass, config_heute),
        SchulferienFeiertagMorgenBinarySensor(hass, config_morgen),

        # neue
        SchulferienOnlyBinarySensor(hass, config_schulferien_only_heute),
        SchulferienOnlyMorgenBinarySensor(
            hass, config_schulferien_only_morgen
        ),
        FeiertagOnlyBinarySensor(hass, config_feiertag_only_heute),
        FeiertagOnlyMorgenBinarySensor(
            hass, config_feiertag_only_morgen
        ),
    ]

    async_add_entities(sensors)
