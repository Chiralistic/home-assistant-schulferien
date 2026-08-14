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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
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

# Erwarteter Sensor-State pro _entity_ids-Key: der Schulferien-Sensor meldet
# "ferientag", der Feiertag-Sensor "feiertag". any() ueber die gelesenen Keys
# ergibt OR bei kombiniert und Single-Check bei only-*.
_ERWARTETER_ZUSTAND = {
    "schulferien": "ferientag",
    "feiertag": "feiertag",
}


# pylint: disable=too-many-instance-attributes  # 8/7: _sensor_unique_ids + _unsub (Slice 5)
class SchulferienBinarySensorBase(BinarySensorEntity):
    """Basisklasse fuer alle Schulferien-Binärsensoren.

    Zentralisiert Name/unique_id/suggested_object_id, das _entity_ids-Dict,
    _state und die is_on-Berechnung. Subklassen deklarieren nur noch:
    - entity_description (Beschreibung/Übersetzung, Klassen-Attribut)
    - _id_prefix + _morgen_variante (ID-Schema)
    - _state_keys (welche Sensor-States gelesen werden)

    Warum self._hass statt self.hass? Die Tests konstruieren die Klassen
    direkt (ClassName(hass, config)) und rufen async_update ohne HA-Add auf
    — self.hass waere dort AttributeError. self._hass bleibt der
    Test-Kompatibilitaets-Vertrag (Slice 5 ergaenzt Subscription + Registry).
    """

    _id_prefix: str = ""
    _morgen_variante: bool = False
    _state_keys: tuple = ()

    def __init__(self, hass, config):
        """Initialisiere den Sensor.

        Args:
            hass: Home Assistant Instanz.
            config: Konfigurationsdaten fuer den Sensor.
        """
        self._hass = hass
        land_upper = config.get("land", "DE").upper()
        region_slug = compute_region_slug(config.get("land", "DE"), config.get("region", "BY"))

        land_name = config.get("land_name", land_upper)
        region_name = config.get("region_name", region_slug)
        # Anzeigename inkl. Bundesland: Basisname aus der EntityDescription
        self._name = f"{self.entity_description.name} - {land_name} ({region_name})"
        morgen_suffix = "_morgen" if self._morgen_variante else ""
        self._unique_id = config.get(
            "unique_id",
            f"binary_sensor.{self._id_prefix}_{land_upper}_{region_slug}{morgen_suffix}",
        )
        # Entity-ID-Vorschlag inkl. Bundesland (lowercase = HA-Konvention)
        self._suggested_object_id = (
            f"{self._id_prefix}_{land_upper.lower()}_{region_slug.lower()}{morgen_suffix}"
        )
        self._entity_ids = {
            "schulferien": config["schulferien_entity_id"],
            "feiertag": config["feiertag_entity_id"],
        }
        self._state = False
        # Volle Sensor-Unique-IDs fuer den Registry-Lookup in async_added_to_hass
        # (Slice 5): transportiert aus _create_binary_sensor_configs.
        self._sensor_unique_ids = {
            "schulferien": config.get("schulferien_unique_id"),
            "feiertag": config.get("feiertag_unique_id"),
        }
        # Unsubscribe-Callable der State-Subscription (Slice 5)
        self._unsub_state_change = None
    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Gibt den Anzeigenamen inkl. Bundesland zurueck."""
        return self._name

    @property
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID (ohne Domain-Praefix) inkl. Bundesland."""
        return self._suggested_object_id

    @property
    def is_on(self):
        """Gibt den aktuellen Zustand des Sensors zurueck."""
        return self._state

    async def async_update(self):
        """Aktualisiert den Zustand ueber die Sensor-States.

        Liest die States der in _state_keys referenzierten Sensoren und
        kombiniert sie mit any(): kombiniert = OR ueber beide Keys, only-*
        = Single-Check. None-States (Sensor noch nicht registriert) werden
        als falsy behandelt — kein Crash, konsistent zum Bestandsverhalten.
        """
        states = {
            key: self._hass.states.get(self._entity_ids[key])
            for key in self._state_keys
        }
        self._state = any(
            states[key] and states[key].state == _ERWARTETER_ZUSTAND[key]
            for key in self._state_keys
        )

    async def async_added_to_hass(self):
        """Lifecycle: Registry-Aufloesung + State-Subscription.

        Warum Registry-Lookup hier und nicht in async_setup_entry?
        async_forward_entry_setups startet beide Plattformen via
        asyncio.gather ohne Ordering-Garantie (config_entries.py:2769-2810)
        — erst hier (spaetester Lifecycle-Punkt) sind die Sensor-Entities
        registriert. Der Lookup-Key ist die volle Sensor-Unique-ID
        (("sensor", "schulferien", unique_id) in der Entity-Registry).

        Warum Fallback auf konstruierte ID? Beim First-Setup-Race und in
        Tests ohne Registry liefert async_get_entity_id None — die
        konstruierte Entity-ID aus dem Config-Dict bleibt dann aktiv.

        Warum Subscription zusaetzlich zum Polling? User-Entscheid: der
        30s-Poll ruft weiter async_update (Recompute-Pfad), die Subscription
        macht den BinarySensor auch zwischen Polls frisch. Kein Netz — reiner
        Recompute, idempotent.
        """
        registry = er.async_get(self.hass)
        for key in self._state_keys:
            unique_id = self._sensor_unique_ids.get(key)
            if unique_id:
                resolved = registry.async_get_entity_id(
                    "sensor", "schulferien", unique_id
                )
                if resolved:
                    self._entity_ids[key] = resolved

        entity_ids = [self._entity_ids[key] for key in self._state_keys]
        self._unsub_state_change = async_track_state_change_event(
            self.hass,
            entity_ids,
            self._handle_state_change,
        )

    async def _handle_state_change(self, _event):
        """Rechnet _state neu und schreibt den HA-State — ohne Netz."""
        await self.async_update()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Cleanup: entfernt die State-Subscription.

        Warum wichtig? Ohne Cleanup feuert der Listener nach dem Unload
        weiter (Leak) — dieselbe Fehlerklasse wie der fehlende Timer-Cancel
        der Sensoren (Prezedenz 475bacf).
        """
        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None

class SchulferienFeiertagBinarySensor(SchulferienBinarySensorBase):
    """Kombinierter Binärsensor: True bei Schulferien ODER Feiertag.

    Warum OR-Logik? Automatisierungen die an beiden Tagen ausloesen sollen
    (z.B. "Kinder muessen in die Schule") muessen nicht zwischen Ferientag
    und Feiertag unterscheiden — in beiden Faellen ist Schule aus.
    """

    entity_description = SCHULFERIEN_FEIERTAG_BINARY_SENSOR
    _id_prefix = "schulferien_feiertage"
    _state_keys = ("schulferien", "feiertag")


class SchulferienFeiertagMorgenBinarySensor(SchulferienBinarySensorBase):
    """Kombinierter Binärsensor fuer morgen: True bei Schulferien ODER Feiertag morgen."""

    entity_description = SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR
    _id_prefix = "schulferien_feiertage"
    _morgen_variante = True
    _state_keys = ("schulferien", "feiertag")


class SchulferienOnlyBinarySensor(SchulferienBinarySensorBase):
    """Binärsensor: True nur bei Schulferien (kein Feiertag noetig)."""

    entity_description = SCHULFERIEN_ONLY_BINARY_SENSOR
    _id_prefix = "nur_schulferien"
    _state_keys = ("schulferien",)


class SchulferienOnlyMorgenBinarySensor(SchulferienBinarySensorBase):
    """Binärsensor: True nur bei Schulferien morgen."""

    entity_description = SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR
    _id_prefix = "nur_schulferien"
    _morgen_variante = True
    _state_keys = ("schulferien",)


class FeiertagOnlyBinarySensor(SchulferienBinarySensorBase):
    """Binärsensor: True nur bei Feiertag (kein Schulferien noetig)."""

    entity_description = FEIERTAG_ONLY_BINARY_SENSOR
    _id_prefix = "nur_feiertage"
    _state_keys = ("feiertag",)


class FeiertagOnlyMorgenBinarySensor(SchulferienBinarySensorBase):
    """Binärsensor: True nur bei Feiertag morgen."""

    entity_description = FEIERTAG_ONLY_MORGEN_BINARY_SENSOR
    _id_prefix = "nur_feiertage"
    _morgen_variante = True
    _state_keys = ("feiertag",)


# pylint: disable=too-many-locals  # 4 Unique-ID-Variablen (Slice 4/5 Transport)
def _create_binary_sensor_configs(land, region, land_name, region_name):
    """Erstellt Konfigurationsdicts für alle 6 Binärsensoren.

    Args:
        land: Ländercode (z.B. "DE").
        region: Regionscode (z.B. "DE-BY").
        land_name: Anzeigename des Landes (z.B. "Deutschland").
        region_name: Anzeigename der Region (z.B. "Bayern").
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

    # Volle Sensor-Unique-IDs fuer den Registry-Lookup (Slice 5): die
    # Sensor-Registry ist ("sensor", "schulferien", unique_id) — der
    # Lookup-Key ist die volle Sensor-Unique-ID, nicht die Entity-ID.
    schulferien_unique_id = f"schulferien_{instance_prefix}"
    feiertag_unique_id = f"feiertag_{instance_prefix}"
    schulferien_morgen_unique_id = f"{schulferien_unique_id}_morgen"
    feiertag_morgen_unique_id = f"{feiertag_unique_id}_morgen"

    binary_unique_prefix = f"binary_sensor.schulferien_feiertage_{instance_prefix}"

    config_base = {
        "land": land,
        "region": region,
        "land_name": land_name,
        "region_name": region_name,
    }

    config_heute = {
        **config_base,
        "schulferien_entity_id": schulferien_entity_id,
        "feiertag_entity_id": feiertag_entity_id,
        "schulferien_unique_id": schulferien_unique_id,
        "feiertag_unique_id": feiertag_unique_id,
        "unique_id": binary_unique_prefix,
    }

    config_morgen = {
        **config_base,
        "schulferien_entity_id": schulferien_morgen_entity_id,
        "feiertag_entity_id": feiertag_morgen_entity_id,
        "schulferien_unique_id": schulferien_morgen_unique_id,
        "feiertag_unique_id": feiertag_morgen_unique_id,
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
    land_name = entry.data.get("land_name", land)
    region_name = entry.data.get("region_name", region)

    configs = _create_binary_sensor_configs(land, region, land_name, region_name)

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
