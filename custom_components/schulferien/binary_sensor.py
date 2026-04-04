import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

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
        self.entity_description = SCHULFERIEN_FEIERTAG_BINARY_SENSOR
        self._hass = hass
        self._unique_id = config.get(
            "unique_id", "binary_sensor.schulferien_feiertage"
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
        return self._state

    async def async_update(self):
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = (
            (schulferien_state and schulferien_state.state == "ferientag")
            or (feiertag_state and feiertag_state.state == "feiertag")
        )


class SchulferienFeiertagMorgenBinarySensor(BinarySensorEntity):
    """Kombinierter Binärsensor für morgen."""

    def __init__(self, hass, config):
        self.entity_description = SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR
        self._hass = hass
        self._unique_id = config.get(
            "unique_id", "binary_sensor.schulferien_feiertage_morgen"
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
        return self._state

    async def async_update(self):
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = (
            (schulferien_state and schulferien_state.state == "ferientag")
            or (feiertag_state and feiertag_state.state == "feiertag")
        )


class SchulferienOnlyBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Schulferien."""

    def __init__(self, hass, config):
        self.entity_description = SCHULFERIEN_ONLY_BINARY_SENSOR
        self._hass = hass
        self._unique_id = config.get(
            "unique_id", "binary_sensor.schulferien_only"
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
        return self._state

    async def async_update(self):
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )

        self._state = (
            schulferien_state and schulferien_state.state == "ferientag"
        )


class SchulferienOnlyMorgenBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Schulferien morgen."""

    def __init__(self, hass, config):
        self.entity_description = SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR
        self._hass = hass
        self._unique_id = config.get(
            "unique_id", "binary_sensor.schulferien_only_morgen"
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
        return self._state

    async def async_update(self):
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )

        self._state = (
            schulferien_state and schulferien_state.state == "ferientag"
        )


class FeiertagOnlyBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Feiertag."""

    def __init__(self, hass, config):
        self.entity_description = FEIERTAG_ONLY_BINARY_SENSOR
        self._hass = hass
        self._unique_id = config.get(
            "unique_id", "binary_sensor.feiertag_only"
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
        return self._state

    async def async_update(self):
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = (
            feiertag_state and feiertag_state.state == "feiertag"
        )


class FeiertagOnlyMorgenBinarySensor(BinarySensorEntity):
    """Binärsensor: Nur Feiertag morgen."""

    def __init__(self, hass, config):
        self.entity_description = FEIERTAG_ONLY_MORGEN_BINARY_SENSOR
        self._hass = hass
        self._unique_id = config.get(
            "unique_id", "binary_sensor.feiertag_only_morgen"
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
        return self._state

    async def async_update(self):
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = (
            feiertag_state and feiertag_state.state == "feiertag"
        )


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("Initialisiere alle Binärsensoren.")

    config_heute = {
        "schulferien_entity_id": "sensor.schulferien",
        "feiertag_entity_id": "sensor.feiertag",
        "unique_id": "binary_sensor.schulferien_feiertage",
    }

    config_morgen = {
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
        "unique_id": "binary_sensor.schulferien_feiertage_morgen",
    }

    # NEU: eigene Configs mit eigenen unique_ids
    config_schulferien_only_heute = {
        **config_heute,
        "unique_id": "binary_sensor.schulferien_only",
    }

    config_schulferien_only_morgen = {
        **config_morgen,
        "unique_id": "binary_sensor.schulferien_only_morgen",
    }

    config_feiertag_only_heute = {
        **config_heute,
        "unique_id": "binary_sensor.feiertag_only",
    }

    config_feiertag_only_morgen = {
        **config_morgen,
        "unique_id": "binary_sensor.feiertag_only_morgen",
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
