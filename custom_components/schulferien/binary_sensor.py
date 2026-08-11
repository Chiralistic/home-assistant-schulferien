"""Binärsensoren für Schulferien und Feiertage.

Binärsensoren ergänzen die Sensors um einfache ON/OFF-Zustände,
die sich ideal für Automatisierungen in Home Assistant eignen.
Anstatt dass der Nutzer den Sensor-Wert ("ferientag" / "kein_ferientag")
prüfen muss, liefert ein BinarySensor direkt True/False.

Warum 6 Binärsensoren?
- Heute + Morgen jeweils: kombiniert (Schulferien ODER Feiertage),
  nur Schulferien, nur Feiertage = 3 x 2 = 6 Sensoren.
- Kombiniert: True wenn Ferientag ODER Feiertag → Automatisierungen
  die an beiden Tagen auslösen sollen (z.B. "Kinder in Schule").
- Nur Schulferien: True nur bei Ferientag → z.B. "Schule aus"-Benachrichtigung.
- Nur Feiertage: True nur bei Feiertag → z.B. "Bank geschlossen"-Info.
"""

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from .api_utils import compute_region_slug

_LOGGER = logging.getLogger(__name__)

# Kombiniert: Schulferien ODER Feiertage (heute)
SCHULFERIEN_FEIERTAG_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_feiertag",
    name="Schulferien/Feiertage",
    translation_key="schulferien_feiertag",
)

# Kombiniert: Schulferien ODER Feiertage (morgen)
SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_feiertag_morgen",
    name="Schulferien/Feiertage Morgen",
    translation_key="schulferien_feiertag_morgen",
)

# Nur Schulferien (heute)
SCHULFERIEN_ONLY_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_only",
    name="Nur Schulferien",
    translation_key="schulferien_only",
)

# Nur Schulferien (morgen)
SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR = BinarySensorEntityDescription(
    key="schulferien_only_morgen",
    name="Nur Schulferien Morgen",
    translation_key="schulferien_only_morgen",
)

# Nur Feiertag (heute)
FEIERTAG_ONLY_BINARY_SENSOR = BinarySensorEntityDescription(
    key="feiertag_only",
    name="Nur Feiertage",
    translation_key="feiertag_only",
)

# Nur Feiertag (morgen)
FEIERTAG_ONLY_MORGEN_BINARY_SENSOR = BinarySensorEntityDescription(
    key="feiertag_only_morgen",
    name="Nur Feiertage Morgen",
    translation_key="feiertag_only_morgen",
)


class SchulferienFeiertagBinarySensor(BinarySensorEntity):
    """Kombinierter Binärsensor: True bei Schulferien ODER Feiertag.

    Warum OR-Logik? Automatisierungen die an beiden Tagen auslösen
    sollen (z.B. "Kinder müssen in die Schule") müssen nicht zwischen
    Ferientag und Feiertag unterscheiden — in beiden Fällen ist Schule aus.
    """

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

        # Entity-ID-Vorschlag inkl. Bundesland: HA leitet daraus z.B.
        # binary_sensor.schulferien_feiertage_de_by ab. Ohne den Override
        # wuerde HA den regionlosen Beschreibungs-Namen verwenden und das
        # Bundesland fehlte in der Benennung (Multi-Instanz-Umbau).
        self._suggested_object_id = (
            f"schulferien_feiertage_{land_upper.lower()}_{region_slug.lower()}"
        )
        self._entity_ids = {
            # Referenz auf die beiden Sensor-Entities deren States wir prüfen
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID (ohne Domain-Praefix) inkl. Bundesland.

        HA weist entity_id selbst zu (EntityPlatform), wir schlagen nur die
        gewuenschte ID vor — ohne Bundesland waeren mehrere Instanzen nicht
        unterscheidbar (HA haengt sonst nur "_2" an).
        """
        return self._suggested_object_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors.

        Liest die States der Schulferien- und Feiertag-Sensoren aus
        und setzt den BinarySensor auf True wenn einer beide "ferientag"
        bzw. "feiertag" meldet (OR-Logik).
        """
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = bool(
            # OR-Logik: True wenn Ferientag ODER Feiertag
            (schulferien_state and schulferien_state.state == "ferientag")
            or (feiertag_state and feiertag_state.state == "feiertag")
        )


class SchulferienFeiertagMorgenBinarySensor(BinarySensorEntity):
    """Kombinierter Binärsensor für morgen: True bei Schulferien ODER Feiertag morgen.

    Gleiche OR-Logik wie der heutige Sensor, aber mit den "_morgen" Sensor-Entities.
    Ermöglicht Abendautomatisierungen wie "Morgen ist Schulferien/Feiertag — Packe das Lunch".
    """

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

        self._suggested_object_id = (
            f"schulferien_feiertage_{land_upper.lower()}_{region_slug.lower()}_morgen"
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
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID (ohne Domain-Praefix) inkl. Bundesland."""
        return self._suggested_object_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors.

        OR-Logik für morgen: True wenn Schulferien-morgen ODER Feiertag-morgen.
        """
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
    """Binärsensor: True nur bei Schulferien (kein Feiertag nötig).

    Warum separater Sensor? Nicht jeder Ferientag ist ein Schulferien-Tag.
    Ein Feiertag kann auch ein normaler Schul-Tag sein. Dieser Sensor
    unterscheidet: True nur wenn der Schulferien-Sensor "ferientag" meldet.
    """

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
            "unique_id", f"binary_sensor.nur_schulferien_{land_upper}_{region_slug}"
        )

        self._suggested_object_id = (
            f"nur_schulferien_{land_upper.lower()}_{region_slug.lower()}"
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
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID (ohne Domain-Praefix) inkl. Bundesland."""
        return self._suggested_object_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors.

        Prüft nur den Schulferien-Sensor — ignoriert Feiertage.
        """
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )

        self._state = bool(
            schulferien_state and schulferien_state.state == "ferientag"
        )


class SchulferienOnlyMorgenBinarySensor(BinarySensorEntity):
    """Binärsensor: True nur bei Schulferien morgen.

    Gleiche Logik wie SchulferienOnlyBinarySensor, aber für morgen.
    Ermöglicht abendliche Automatisierungen wie "Morgen ist Schulferien — Kein Wecker".
    """

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
            "unique_id", f"binary_sensor.nur_schulferien_{land_upper}_{region_slug}_morgen"
        )

        self._suggested_object_id = (
            f"nur_schulferien_{land_upper.lower()}_{region_slug.lower()}_morgen"
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
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID (ohne Domain-Praefix) inkl. Bundesland."""
        return self._suggested_object_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors.

        Prüft nur den Schulferien-Sensor für morgen.
        """
        schulferien_state = self._hass.states.get(
            self._entity_ids["schulferien"]
        )

        self._state = bool(
            schulferien_state and schulferien_state.state == "ferientag"
        )


class FeiertagOnlyBinarySensor(BinarySensorEntity):
    """Binärsensor: True nur bei Feiertag (kein Schulferien nötig).

    Warum separater Sensor? Feiertage sind nicht immer Schulfrei.
    Dieser Sensor meldet True nur wenn der Feiertag-Sensor "feiertag"
    meldet — unabhängig von Schulferien.
    """

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
            "unique_id", f"binary_sensor.nur_feiertage_{land_upper}_{region_slug}"
        )

        self._suggested_object_id = (
            f"nur_feiertage_{land_upper.lower()}_{region_slug.lower()}"
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
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID (ohne Domain-Praefix) inkl. Bundesland."""
        return self._suggested_object_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors.

        Prüft nur den Feiertag-Sensor — ignoriert Schulferien.
        """
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = bool(
            feiertag_state and feiertag_state.state == "feiertag"
        )


class FeiertagOnlyMorgenBinarySensor(BinarySensorEntity):
    """Binärsensor: True nur bei Feiertag morgen.

    Gleiche Logik wie FeiertagOnlyBinarySensor, aber für morgen.
    Ermöglicht abendliche Automatisierungen wie "Morgen ist Feiertag — Poststelle zu".
    """

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
            "unique_id", f"binary_sensor.nur_feiertage_{land_upper}_{region_slug}_morgen"
        )

        self._suggested_object_id = (
            f"nur_feiertage_{land_upper.lower()}_{region_slug.lower()}_morgen"
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
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID (ohne Domain-Praefix) inkl. Bundesland."""
        return self._suggested_object_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand des Sensors.

        Prüft nur den Feiertag-Sensor für morgen.
        """
        feiertag_state = self._hass.states.get(
            self._entity_ids["feiertag"]
        )

        self._state = bool(
            feiertag_state and feiertag_state.state == "feiertag"
        )


def _create_binary_sensor_configs(land, region):
    """Erstellt Konfigurationsdicts für alle 6 Binärsensoren.

    Args:
        land: Ländercode (z.B. "DE").
        region: Regionscode (z.B. "DE-BY").

    Returns:
        Dict mit Configs für alle 6 Binärsensoren.
    """
    region_slug = compute_region_slug(land, region)
    # unique_id-Praefix mit bereinigtem region_slug: Land nur einmal im Namen.
    # f"{land}_{region}" wuerde "DE_DE-RP" ergeben (Land doppelt + Bindestrich).
    instance_prefix = f"{land}_{region_slug}".upper()

    # Entity IDs mit slugified region für Konsistenz zu Sensor-Klassen
    # Warum lowercase? Home Assistant entity_ids sind case-insensitive,
    # lowercase ist die HA-Konvention und vermeidet Verwirrung im UI.
    schulferien_entity_id = f"sensor.schulferien_{land.lower()}_{region_slug.lower()}"
    feiertag_entity_id = f"sensor.feiertag_{land.lower()}_{region_slug.lower()}"
    schulferien_morgen_entity_id = f"sensor.schulferien_{land.lower()}_{region_slug.lower()}_morgen"
    feiertag_morgen_entity_id = f"sensor.feiertag_{land.lower()}_{region_slug.lower()}_morgen"

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

    return {
        "heute": config_heute,
        "morgen": config_morgen,
        "nur_schulferien_heute": {
            **config_base,
            **config_heute,
            "unique_id": f"binary_sensor.nur_schulferien_{instance_prefix}",
        },
        "nur_schulferien_morgen": {
            **config_base,
            **config_morgen,
            "unique_id": f"binary_sensor.nur_schulferien_{instance_prefix}_morgen",
        },
        "nur_feiertage_heute": {
            **config_base,
            **config_heute,
            "unique_id": f"binary_sensor.nur_feiertage_{instance_prefix}",
        },
        "nur_feiertage_morgen": {
            **config_base,
            **config_morgen,
            "unique_id": f"binary_sensor.nur_feiertage_{instance_prefix}_morgen",
        },
    }


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup der Binärsensoren für eine Konfiguration.

    Erstellt 6 Binärsensoren:
    1. Kombiniert heute (Schulferien ODER Feiertage)
    2. Kombiniert morgen
    3. Nur Schulferien heute
    4. Nur Schulferien morgen
    5. Nur Feiertag heute
    6. Nur Feiertag morgen

    Warum ueberall compute_region_slug()?
    - Das Land darf nur einmal im Namen auftauchen: region ist "DE-RP" (mit
      Laender-Praefix), der Slug ist "RP" -> "binary_sensor.…_DE_RP".
    - Keine Bindestriche in entity_ids UND unique_ids -> konsistent zu den
      Sensor-Klassen (schulferien_DE_RP).
    - Eindeutig pro Land+Region -> multiple Instanzen supporten.

    Args:
        hass: Home Assistant Instanz.
        entry: Config entry für die Konfiguration.
        async_add_entities: Funktion zum Hinzufügen von Entitäten.
    """
    _LOGGER.debug("Initialisiere alle Binärsensoren für Entry: %s", entry.title)

    land = entry.data.get("land", "DE")
    region = entry.data.get("region", "BY")

    configs = _create_binary_sensor_configs(land, region)

    sensors = [
        # Kombinierte Sensoren (Schulferien ODER Feiertage)
        SchulferienFeiertagBinarySensor(hass, configs["heute"]),
        SchulferienFeiertagMorgenBinarySensor(hass, configs["morgen"]),

        # Separate Sensoren pro Typ
        SchulferienOnlyBinarySensor(hass, configs["nur_schulferien_heute"]),
        SchulferienOnlyMorgenBinarySensor(
            hass, configs["nur_schulferien_morgen"]
        ),
        FeiertagOnlyBinarySensor(hass, configs["nur_feiertage_heute"]),
        FeiertagOnlyMorgenBinarySensor(
            hass, configs["nur_feiertage_morgen"]
        ),
    ]

    async_add_entities(sensors)
