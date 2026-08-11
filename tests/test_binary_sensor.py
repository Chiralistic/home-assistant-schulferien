"""Unit Tests für SchulferienFeiertagBinarySensor & Morgen-Binärsensor."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.schulferien.binary_sensor import (
    SchulferienFeiertagBinarySensor,
    SchulferienFeiertagMorgenBinarySensor,
    SchulferienOnlyBinarySensor,
    SchulferienOnlyMorgenBinarySensor,
    FeiertagOnlyBinarySensor,
    FeiertagOnlyMorgenBinarySensor,
    async_setup_entry,
    SCHULFERIEN_FEIERTAG_BINARY_SENSOR,
    SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR,
    SCHULFERIEN_ONLY_BINARY_SENSOR,
    SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR,
    FEIERTAG_ONLY_BINARY_SENSOR,
    FEIERTAG_ONLY_MORGEN_BINARY_SENSOR,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def hass():
    """Mock HomeAssistant."""
    hass = MagicMock()
    hass.states.get = MagicMock()
    return hass


@pytest.fixture
def config_heute():
    """Standard-Konfiguration für heute-Binärsensoren."""
    return {
        "unique_id": "binary_sensor.schulferien_feiertage_DE_BY",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }


@pytest.fixture
def config_morgen():
    """Konfiguration für Morgen-Binärsensoren."""
    return {
        "unique_id": "binary_sensor.schulferien_feiertage_DE_BY_morgen",
        "schulferien_entity_id": "sensor.schulferien_de_by_morgen",
        "feiertag_entity_id": "sensor.feiertag_de_by_morgen",
    }


@pytest.fixture
def config_schulferien_only():
    """Konfiguration für SchulferienOnly Sensor."""
    return {
        "unique_id": "binary_sensor.schulferien_only_DE_BY",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }


@pytest.fixture
def config_feiertag_only():
    """Konfiguration für FeiertagOnly Sensor."""
    return {
        "unique_id": "binary_sensor.feiertag_only_DE_BY",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }


@pytest.fixture
def config_schulferien_only_morgen():
    """Konfiguration für SchulferienOnlyMorgen Sensor."""
    return {
        "unique_id": "binary_sensor.schulferien_only_DE_BY_morgen",
        "schulferien_entity_id": "sensor.schulferien_de_by_morgen",
        "feiertag_entity_id": "sensor.feiertag_de_by_morgen",
    }


@pytest.fixture
def config_feiertag_only_morgen():
    """Konfiguration für FeiertagOnlyMorgen Sensor."""
    return {
        "unique_id": "binary_sensor.feiertag_only_DE_BY_morgen",
        "schulferien_entity_id": "sensor.schulferien_de_by_morgen",
        "feiertag_entity_id": "sensor.feiertag_de_by_morgen",
    }


@pytest.fixture
def today_sensor(hass, config_heute):
    """Kombinierter Binärsensor für heute."""
    return SchulferienFeiertagBinarySensor(hass, config_heute)


@pytest.fixture
def morgen_sensor_fixture(hass, config_morgen):
    """Kombinierter Binärsensor für morgen."""
    return SchulferienFeiertagMorgenBinarySensor(hass, config_morgen)


@pytest.fixture
def schulferien_only_sensor(hass, config_schulferien_only):
    """SchulferienOnly Binärsensor."""
    return SchulferienOnlyBinarySensor(hass, config_schulferien_only)


@pytest.fixture
def feiertag_only_sensor(hass, config_feiertag_only):
    """FeiertagOnly Binärsensor."""
    return FeiertagOnlyBinarySensor(hass, config_feiertag_only)


@pytest.fixture
def schulferien_only_morgen_sensor(hass, config_schulferien_only_morgen):
    """SchulferienOnlyMorgen Binärsensor."""
    return SchulferienOnlyMorgenBinarySensor(hass, config_schulferien_only_morgen)


@pytest.fixture
def feiertag_only_morgen_sensor(hass, config_feiertag_only_morgen):
    """FeiertagOnlyMorgen Binärsensor."""
    return FeiertagOnlyMorgenBinarySensor(hass, config_feiertag_only_morgen)


def test_suggested_object_id_enthaelt_bundesland(
    today_sensor,
    morgen_sensor_fixture,
    schulferien_only_sensor,
    schulferien_only_morgen_sensor,
    feiertag_only_sensor,
    feiertag_only_morgen_sensor,
):
    """Regression: Binary-Sensor-Entity-IDs muessen das Bundesland enthalten.

    Warum? HA leitet die Entity-ID aus suggested_object_id ab. Ohne den
    Override wuerde der regionlose Beschreibungs-Name verwendet
    (binary_sensor.schulferien_feiertage) — bei mehreren Instanzen haengt
    HA nur "_2" an und das Bundesland fehlt in der Benennung.
    """
    assert today_sensor.suggested_object_id == "schulferien_feiertage_de_by"
    assert (
        morgen_sensor_fixture.suggested_object_id
        == "schulferien_feiertage_de_by_morgen"
    )
    assert schulferien_only_sensor.suggested_object_id == "schulferien_only_de_by"
    assert (
        schulferien_only_morgen_sensor.suggested_object_id
        == "schulferien_only_de_by_morgen"
    )
    assert feiertag_only_sensor.suggested_object_id == "feiertag_only_de_by"
    assert (
        feiertag_only_morgen_sensor.suggested_object_id
        == "feiertag_only_de_by_morgen"
    )

    # HA-Zuweisung simulieren — darf nicht crashen (Getter-only-Property-Bug)
    today_sensor.entity_id = "binary_sensor.schulferien_feiertage_de_by"
    assert today_sensor.entity_id == "binary_sensor.schulferien_feiertage_de_by"


# ============================================================
# Hilfsfunktionen
# ============================================================

def make_state(state_str):
    """Erstellt ein mock State-Objekt mit dem gegebenen Zustand."""
    if state_str is None:
        return None
    mock = MagicMock()
    mock.state = state_str
    return mock


def make_state_with_attr(state_str):
    """Erstellt ein mock State-Objekt das sicher ein state-Attribut hat.

    Im Gegensatz zu make_state() verwendet diese Funktion MagicMock()
    ohne spec, sodass der Zugriff auf .state immer funktioniert.
    """
    if state_str is None:
        return None
    mock = MagicMock()
    mock.state = state_str
    return mock


# ============================================================
# Tests für EntityDescriptions
# ============================================================

def test_entity_description_schulferien_feiertag():
    """Test die EntityDescription für Schulferien/Feiertag."""
    assert SCHULFERIEN_FEIERTAG_BINARY_SENSOR.key == "schulferien_feiertag"
    assert SCHULFERIEN_FEIERTAG_BINARY_SENSOR.name == "Schulferien/Feiertage"
    assert SCHULFERIEN_FEIERTAG_BINARY_SENSOR.translation_key == "schulferien_feiertag"


def test_entity_description_schulferien_feiertag_morgen():
    """Test die EntityDescription für Schulferien/Feiertag Morgen."""
    assert SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR.key == "schulferien_feiertag_morgen"
    assert SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR.name == "Schulferien/Feiertage Morgen"
    assert SCHULFERIEN_FEIERTAG_MORGEN_BINARY_SENSOR.translation_key == "schulferien_feiertag_morgen"


def test_entity_description_schulferien_only():
    """Test die EntityDescription für Nur Schulferien."""
    assert SCHULFERIEN_ONLY_BINARY_SENSOR.key == "schulferien_only"
    assert SCHULFERIEN_ONLY_BINARY_SENSOR.name == "Nur Schulferien"
    assert SCHULFERIEN_ONLY_BINARY_SENSOR.translation_key == "schulferien_only"


def test_entity_description_schulferien_only_morgen():
    """Test die EntityDescription für Nur Schulferien Morgen."""
    assert SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR.key == "schulferien_only_morgen"
    assert SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR.name == "Nur Schulferien Morgen"
    assert SCHULFERIEN_ONLY_MORGEN_BINARY_SENSOR.translation_key == "schulferien_only_morgen"


def test_entity_description_feiertag_only():
    """Test die EntityDescription für Nur Feiertage."""
    assert FEIERTAG_ONLY_BINARY_SENSOR.key == "feiertag_only"
    assert FEIERTAG_ONLY_BINARY_SENSOR.name == "Nur Feiertage"
    assert FEIERTAG_ONLY_BINARY_SENSOR.translation_key == "feiertag_only"


def test_entity_description_feiertag_only_morgen():
    """Test die EntityDescription für Nur Feiertage Morgen."""
    assert FEIERTAG_ONLY_MORGEN_BINARY_SENSOR.key == "feiertag_only_morgen"
    assert FEIERTAG_ONLY_MORGEN_BINARY_SENSOR.name == "Nur Feiertage Morgen"
    assert FEIERTAG_ONLY_MORGEN_BINARY_SENSOR.translation_key == "feiertag_only_morgen"


# ============================================================
# Tests für SchulferienFeiertagBinarySensor (kombiniert heute)
# ============================================================

def test_schulferien_feiertag_sensor_initialization(hass, config_heute):
    """Test die Initialisierung des kombinierten Binärsensors."""
    sensor = SchulferienFeiertagBinarySensor(hass, config_heute)
    assert sensor.unique_id == "binary_sensor.schulferien_feiertage_DE_BY"
    assert sensor._state is False


def test_schulferien_feiertag_sensor_custom_unique_id(hass):
    """Test mit benutzerdefiniertem unique_id."""
    custom_config = {
        "unique_id": "binary_sensor.custom",
        "schulferien_entity_id": "sensor.schulferien",
        "feiertag_entity_id": "sensor.feiertag",
    }
    sensor = SchulferienFeiertagBinarySensor(hass, custom_config)
    assert sensor.unique_id == "binary_sensor.custom"


def test_schulferien_feiertag_sensor_default_unique_id(hass):
    """Test dass der Standard unique_id mit Land/Region verwendet wird."""
    config = {
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienFeiertagBinarySensor(hass, config)
    # Default unique_id mit Land/Region aus Config Defaults (DE/BY)
    assert sensor.unique_id == "binary_sensor.schulferien_feiertage_DE_BY"


def test_schulferien_feiertag_sensor_entity_ids(hass, config_heute):
    """Test dass die Entity-IDs korrekt gespeichert werden."""
    sensor = SchulferienFeiertagBinarySensor(hass, config_heute)
    assert sensor._entity_ids["schulferien"] == "sensor.schulferien_de_by"
    assert sensor._entity_ids["feiertag"] == "sensor.feiertag_de_by"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", True),
        ("ferientag", "kein_feiertag", True),
        ("kein_ferientag", "feiertag", True),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", True),
        ("ferientag", None, True),
        (None, None, False),
    ]
)
async def test_today_binary_sensor_state(today_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet heutigen Binärsensor-Zustand für alle Kombinationen."""
    hass.states.get.side_effect = (
        lambda eid: make_state(ferien_state)
        if eid == "sensor.schulferien_de_by"
        else make_state(feiertag_state)
    )

    await today_sensor.async_update()
    # Bei expected=True: is_on muss True sein
    # Bei expected=False: is_on kann False oder None sein (Code-Verhalten)
    if expected:
        assert today_sensor.is_on is True
    else:
        assert not today_sensor.is_on


@pytest.mark.asyncio
async def test_today_binary_sensor_entity_ids(today_sensor, hass):
    """Test dass die korrekten Entity-IDs abgefragt werden."""
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_de_by" else make_state("feiertag_de_by")

    await today_sensor.async_update()

    # Verify both entity IDs were queried
    assert hass.states.get.call_count == 2


@pytest.mark.asyncio
async def test_today_binary_sensor_is_on_false():
    """Test is_on Property wenn beide States False sind."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "kein_ferientag") if eid == "sensor.schulferien_de_by" else make_state("kein_feiertag_de_by")
    config = {
        "unique_id": "binary_sensor.test",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienFeiertagBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_today_binary_sensor_state_unexpected_value(today_sensor, hass):
    """Test mit unerwartetem State-Wert."""
    hass.states.get.side_effect = lambda eid: make_state(
        "unknown") if eid == "sensor.schulferien_de_by" else make_state("unknown")
    await today_sensor.async_update()
    assert today_sensor.is_on is False


# ============================================================
# Tests für SchulferienFeiertagMorgenBinarySensor (kombiniert morgen)
# ============================================================

def test_morgen_sensor_initialization(hass, config_morgen):
    """Test die Initialisierung des Morgen-Binärsensors."""
    sensor = SchulferienFeiertagMorgenBinarySensor(hass, config_morgen)
    assert sensor.unique_id == "binary_sensor.schulferien_feiertage_DE_BY_morgen"
    assert sensor._state is False


def test_morgen_sensor_custom_unique_id(hass):
    """Test Morgen-Sensor mit benutzerdefiniertem unique_id."""
    custom_config = {
        "unique_id": "binary_sensor.custom_morgen",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = SchulferienFeiertagMorgenBinarySensor(hass, custom_config)
    assert sensor.unique_id == "binary_sensor.custom_morgen"


def test_morgen_sensor_entity_ids(hass, config_morgen):
    """Test dass die Entity-IDs korrekt gespeichert werden."""
    sensor = SchulferienFeiertagMorgenBinarySensor(hass, config_morgen)
    assert sensor._entity_ids["schulferien"] == "sensor.schulferien_de_by_morgen"
    assert sensor._entity_ids["feiertag"] == "sensor.feiertag_de_by_morgen"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", True),
        ("ferientag", "kein_feiertag", True),
        ("kein_ferientag", "feiertag", True),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", True),
        ("ferientag", None, True),
        (None, None, False),
    ]
)
async def test_morgen_binary_sensor_state(morgen_sensor_fixture, hass, ferien_state, feiertag_state, expected):
    """Testet morgigen Binärsensor-Zustand für alle Kombinationen."""
    hass.states.get.side_effect = (
        lambda eid: make_state(ferien_state)
        if eid == "sensor.schulferien_de_by_morgen"
        else make_state(feiertag_state)
    )

    await morgen_sensor_fixture.async_update()
    if expected:
        assert morgen_sensor_fixture.is_on is True
    else:
        assert not morgen_sensor_fixture.is_on


@pytest.mark.asyncio
async def test_morgen_binary_sensor_is_on_false():
    """Test is_on Property wenn beide States False sind."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "unknown") if eid == "sensor.schulferien_morgen" else make_state("unknown")
    config = {
        "unique_id": "binary_sensor.test_morgen",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = SchulferienFeiertagMorgenBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is False


# ============================================================
# Tests für SchulferienOnlyBinarySensor (nur Schulferien heute)
# ============================================================

def test_schulferien_only_sensor_initialization(hass, config_schulferien_only):
    """Test die Initialisierung des SchulferienOnly Sensors."""
    sensor = SchulferienOnlyBinarySensor(hass, config_schulferien_only)
    assert sensor.unique_id == "binary_sensor.schulferien_only_DE_BY"
    assert sensor._state is False


def test_schulferien_only_sensor_custom_unique_id(hass):
    """Test SchulferienOnly mit benutzerdefiniertem unique_id."""
    custom_config = {
        "unique_id": "binary_sensor.schulferien_only_custom",
        "schulferien_entity_id": "sensor.schulferien",
        "feiertag_entity_id": "sensor.feiertag",
    }
    sensor = SchulferienOnlyBinarySensor(hass, custom_config)
    assert sensor.unique_id == "binary_sensor.schulferien_only_custom"


def test_schulferien_only_sensor_default_unique_id(hass):
    """Test dass der Standard unique_id mit Land/Region verwendet wird."""
    config = {
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienOnlyBinarySensor(hass, config)
    # Default unique_id mit Land/Region aus Config Defaults (DE/BY)
    assert sensor.unique_id == "binary_sensor.schulferien_only_DE_BY"


def test_schulferien_only_sensor_entity_ids(hass, config_schulferien_only):
    """Test dass die Entity-IDs korrekt gespeichert werden."""
    sensor = SchulferienOnlyBinarySensor(hass, config_schulferien_only)
    assert sensor._entity_ids["schulferien"] == "sensor.schulferien_de_by"
    assert sensor._entity_ids["feiertag"] == "sensor.feiertag_de_by"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", True),
        ("ferientag", "kein_feiertag", True),
        ("kein_ferientag", "feiertag", False),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", False),
        ("ferientag", None, True),
        (None, None, False),
    ]
)
async def test_schulferien_only_binary_sensor_state(schulferien_only_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet SchulferienOnly Binärsensor-Zustand.

    SchulferienOnly prüft NUR den Schulferien-State.
    True wenn Schulferien, unabhängig vom Feiertag-State.
    """
    hass.states.get.side_effect = (
        lambda eid: make_state(ferien_state)
        if eid == "sensor.schulferien_de_by"
        else make_state(feiertag_state)
    )

    await schulferien_only_sensor.async_update()
    if expected:
        assert schulferien_only_sensor.is_on is True
    else:
        assert not schulferien_only_sensor.is_on


@pytest.mark.asyncio
async def test_schulferien_only_morgen_sensor_initialization(hass, config_schulferien_only_morgen):
    """Test die Initialisierung des SchulferienOnlyMorgen Sensors."""
    sensor = SchulferienOnlyMorgenBinarySensor(hass, config_schulferien_only_morgen)
    # Verwendet die unique_id aus dem Fixture
    assert sensor.unique_id == "binary_sensor.schulferien_only_DE_BY_morgen"
    assert sensor._state is False


def test_schulferien_only_morgen_sensor_custom_unique_id(hass):
    """Test SchulferienOnlyMorgen mit benutzerdefiniertem unique_id."""
    custom_config = {
        "unique_id": "binary_sensor.schulferien_only_morgen_custom",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = SchulferienOnlyMorgenBinarySensor(hass, custom_config)
    assert sensor.unique_id == "binary_sensor.schulferien_only_morgen_custom"


def test_schulferien_only_morgen_sensor_default_unique_id(hass):
    """Test dass der Standard unique_id mit Land/Region verwendet wird."""
    config = {
        "schulferien_entity_id": "sensor.schulferien_de_by_morgen",
        "feiertag_entity_id": "sensor.feiertag_de_by_morgen",
    }
    sensor = SchulferienOnlyMorgenBinarySensor(hass, config)
    # Default unique_id mit Land/Region aus Config Defaults (DE/BY)
    assert sensor.unique_id == "binary_sensor.schulferien_only_DE_BY_morgen"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", True),
        ("ferientag", "kein_feiertag", True),
        ("kein_ferientag", "feiertag", False),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", False),
        ("ferientag", None, True),
        (None, None, False),
    ]
)
async def test_schulferien_only_morgen_binary_sensor_state(hass, config_schulferien_only_morgen, ferien_state, feiertag_state, expected):
    """Testet SchulferienOnlyMorgen Binärsensor-Zustand."""
    sensor = SchulferienOnlyMorgenBinarySensor(hass, config_schulferien_only_morgen)
    hass.states.get.side_effect = (
        lambda eid: make_state(ferien_state)
        if eid == "sensor.schulferien_de_by_morgen"
        else make_state(feiertag_state)
    )

    await sensor.async_update()
    if expected:
        assert sensor.is_on is True
    else:
        assert not sensor.is_on


@pytest.mark.asyncio
async def test_schulferien_only_morgen_entity_ids_queried():
    """Test dass nur die Schulferien-Entity abgefragt wird."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_morgen" else make_state("feiertag")
    config = {
        "unique_id": "binary_sensor.test_only_morgen",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = SchulferienOnlyMorgenBinarySensor(hass, config)
    await sensor.async_update()

    # Nur die Schulferien-Entity sollte abgefragt werden
    assert hass.states.get.call_count == 1
    hass.states.get.assert_called_with("sensor.schulferien_morgen")


# ============================================================
# Tests für FeiertagOnlyBinarySensor (nur Feiertag heute)
# ============================================================

def test_feiertag_only_sensor_initialization(hass, config_feiertag_only):
    """Test die Initialisierung des FeiertagOnly Sensors."""
    sensor = FeiertagOnlyBinarySensor(hass, config_feiertag_only)
    assert sensor.unique_id == "binary_sensor.feiertag_only_DE_BY"
    assert sensor._state is False


def test_feiertag_only_sensor_custom_unique_id(hass):
    """Test FeiertagOnly mit benutzerdefiniertem unique_id."""
    custom_config = {
        "unique_id": "binary_sensor.feiertag_only_custom",
        "schulferien_entity_id": "sensor.schulferien",
        "feiertag_entity_id": "sensor.feiertag",
    }
    sensor = FeiertagOnlyBinarySensor(hass, custom_config)
    assert sensor.unique_id == "binary_sensor.feiertag_only_custom"


def test_feiertag_only_sensor_default_unique_id(hass):
    """Test dass der Standard unique_id mit Land/Region verwendet wird."""
    config = {
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = FeiertagOnlyBinarySensor(hass, config)
    # Default unique_id mit Land/Region aus Config Defaults (DE/BY)
    assert sensor.unique_id == "binary_sensor.feiertag_only_DE_BY"


def test_feiertag_only_sensor_entity_ids(hass, config_feiertag_only):
    """Test dass die Entity-IDs korrekt gespeichert werden."""
    sensor = FeiertagOnlyBinarySensor(hass, config_feiertag_only)
    assert sensor._entity_ids["schulferien"] == "sensor.schulferien_de_by"
    assert sensor._entity_ids["feiertag"] == "sensor.feiertag_de_by"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", True),
        ("ferientag", "kein_feiertag", False),
        ("kein_ferientag", "feiertag", True),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", True),
        ("ferientag", None, False),
        (None, None, False),
    ]
)
async def test_feiertag_only_binary_sensor_state(feiertag_only_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet FeiertagOnly Binärsensor-Zustand.

    FeiertagOnly prüft NUR den Feiertag-State.
    True wenn Feiertag, unabhängig vom Schulferien-State.
    """
    hass.states.get.side_effect = (
        lambda eid: make_state(ferien_state)
        if eid == "sensor.schulferien_de_by"
        else make_state(feiertag_state)
    )

    await feiertag_only_sensor.async_update()
    if expected:
        assert feiertag_only_sensor.is_on is True
    else:
        assert not feiertag_only_sensor.is_on


@pytest.mark.asyncio
async def test_schulferien_only_entity_ids_queried():
    """Test dass nur die Schulferien-Entity abgefragt wird."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_de_by" else make_state("feiertag_de_by")
    config = {
        "unique_id": "binary_sensor.test_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienOnlyBinarySensor(hass, config)
    await sensor.async_update()

    # Nur die Schulferien-Entity sollte abgefragt werden
    assert hass.states.get.call_count == 1
    hass.states.get.assert_called_with("sensor.schulferien_de_by")


@pytest.mark.asyncio
async def test_schulferien_only_is_on_false():
    """Test is_on Property wenn Schulferien False sind."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "kein_ferientag") if eid == "sensor.schulferien_de_by" else make_state("feiertag_de_by")
    config = {
        "unique_id": "binary_sensor.test_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienOnlyBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_schulferien_only_unexpected_state():
    """Test mit unerwartetem State-Wert."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "unknown") if eid == "sensor.schulferien_de_by" else make_state("feiertag_de_by")
    config = {
        "unique_id": "binary_sensor.test_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienOnlyBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_feiertag_only_entity_ids_queried():
    """Test dass nur die Feiertag-Entity abgefragt wird."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_de_by" else make_state("ferientag_de_by")
    config = {
        "unique_id": "binary_sensor.test_feiertag_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = FeiertagOnlyBinarySensor(hass, config)
    await sensor.async_update()

    # Nur die Feiertag-Entity sollte abgefragt werden
    assert hass.states.get.call_count == 1
    hass.states.get.assert_called_with("sensor.feiertag_de_by")


@pytest.mark.asyncio
async def test_feiertag_only_is_on_false():
    """Test is_on Property wenn Feiertag False ist."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "kein_feiertag") if eid == "sensor.feiertag_de_by" else make_state("ferientag_de_by")
    config = {
        "unique_id": "binary_sensor.test_feiertag_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = FeiertagOnlyBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_feiertag_only_unexpected_state():
    """Test mit unerwartetem State-Wert."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "unknown") if eid == "sensor.feiertag_de_by" else make_state("ferientag_de_by")
    config = {
        "unique_id": "binary_sensor.test_feiertag_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = FeiertagOnlyBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is False


# ============================================================
# Tests für FeiertagOnlyMorgenBinarySensor
# ============================================================

def test_feiertag_only_morgen_sensor_initialization(hass, config_feiertag_only_morgen):
    """Test die Initialisierung des FeiertagOnlyMorgen Sensors."""
    sensor = FeiertagOnlyMorgenBinarySensor(hass, config_feiertag_only_morgen)
    assert sensor.unique_id == "binary_sensor.feiertag_only_DE_BY_morgen"
    assert sensor._state is False


def test_feiertag_only_morgen_sensor_custom_unique_id(hass):
    """Test FeiertagOnlyMorgen mit benutzerdefiniertem unique_id."""
    custom_config = {
        "unique_id": "binary_sensor.feiertag_only_morgen_custom",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = FeiertagOnlyMorgenBinarySensor(hass, custom_config)
    assert sensor.unique_id == "binary_sensor.feiertag_only_morgen_custom"


def test_feiertag_only_morgen_sensor_default_unique_id(hass):
    """Test dass der Standard unique_id mit Land/Region verwendet wird."""
    config = {
        "schulferien_entity_id": "sensor.schulferien_de_by_morgen",
        "feiertag_entity_id": "sensor.feiertag_de_by_morgen",
    }
    sensor = FeiertagOnlyMorgenBinarySensor(hass, config)
    # Default unique_id mit Land/Region aus Config Defaults (DE/BY)
    assert sensor.unique_id == "binary_sensor.feiertag_only_DE_BY_morgen"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", True),
        ("ferientag", "kein_feiertag", False),
        ("kein_ferientag", "feiertag", True),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", True),
        ("ferientag", None, False),
        (None, None, False),
    ]
)
async def test_feiertag_only_morgen_binary_sensor_state(hass, config_feiertag_only_morgen, ferien_state, feiertag_state, expected):
    """Testet FeiertagOnlyMorgen Binärsensor-Zustand."""
    sensor = FeiertagOnlyMorgenBinarySensor(hass, config_feiertag_only_morgen)
    hass.states.get.side_effect = (
        lambda eid: make_state(ferien_state)
        if eid == "sensor.schulferien_de_by_morgen"
        else make_state(feiertag_state)
    )

    await sensor.async_update()
    if expected:
        assert sensor.is_on is True
    else:
        assert not sensor.is_on


@pytest.mark.asyncio
async def test_feiertag_only_morgen_entity_ids_queried():
    """Test dass nur die Feiertag-Entity abgefragt wird."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_morgen" else make_state("ferientag")
    config = {
        "unique_id": "binary_sensor.test_feiertag_only_morgen",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = FeiertagOnlyMorgenBinarySensor(hass, config)
    await sensor.async_update()

    # Nur die Feiertag-Entity sollte abgefragt werden
    assert hass.states.get.call_count == 1
    hass.states.get.assert_called_with("sensor.feiertag_morgen")


# ============================================================
# Tests für async_setup_entry
# ============================================================

@pytest.mark.asyncio
async def test_async_setup_entry_creates_all_sensors():
    """Test dass async_setup_entry alle Binärsensoren erstellt."""
    hass = MagicMock()
    entry = MagicMock()
    entry.data = {
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    added_entities = []

    # mock_add_entities ist sync, nicht async
    def mock_add_entities(entities):
        added_entities.extend(entities)

    with patch("custom_components.schulferien.binary_sensor.SchulferienFeiertagBinarySensor"), \
            patch("custom_components.schulferien.binary_sensor.SchulferienFeiertagMorgenBinarySensor"), \
            patch("custom_components.schulferien.binary_sensor.SchulferienOnlyBinarySensor"), \
            patch("custom_components.schulferien.binary_sensor.SchulferienOnlyMorgenBinarySensor"), \
            patch("custom_components.schulferien.binary_sensor.FeiertagOnlyBinarySensor"), \
            patch("custom_components.schulferien.binary_sensor.FeiertagOnlyMorgenBinarySensor"):

        await async_setup_entry(hass, entry, mock_add_entities)

    assert len(added_entities) == 6


@pytest.mark.asyncio
async def test_async_setup_entry_sensor_types():
    """Test dass die korrekten Sensor-Typen erstellt werden."""
    hass = MagicMock()
    entry = MagicMock()
    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(hass, entry, mock_add_entities)

    assert len(added_entities) == 6
    assert isinstance(added_entities[0], SchulferienFeiertagBinarySensor)
    assert isinstance(added_entities[1], SchulferienFeiertagMorgenBinarySensor)
    assert isinstance(added_entities[2], SchulferienOnlyBinarySensor)
    assert isinstance(added_entities[3], SchulferienOnlyMorgenBinarySensor)
    assert isinstance(added_entities[4], FeiertagOnlyBinarySensor)
    assert isinstance(added_entities[5], FeiertagOnlyMorgenBinarySensor)


@pytest.mark.asyncio
async def test_async_setup_entry_sensor_unique_ids():
    """Test dass die Sensoren die korrekten unique_ids haben."""
    hass = MagicMock()
    entry = MagicMock()
    entry.data = {
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(hass, entry, mock_add_entities)

    expected_ids = [
        "binary_sensor.schulferien_feiertage_DE_BY",
        "binary_sensor.schulferien_feiertage_DE_BY_morgen",
        "binary_sensor.schulferien_only_DE_BY",
        "binary_sensor.schulferien_only_DE_BY_morgen",
        "binary_sensor.feiertag_only_DE_BY",
        "binary_sensor.feiertag_only_DE_BY_morgen",
    ]
    for i, expected_id in enumerate(expected_ids):
        assert added_entities[i].unique_id == expected_id


@pytest.mark.asyncio
async def test_async_setup_entry_default_entity_ids():
    """Test dass die korrekten Default Entity-IDs verwendet werden."""
    hass = MagicMock()
    entry = MagicMock()
    entry.data = {
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(hass, entry, mock_add_entities)

    # Erster Sensor (SchulferienFeiertagBinarySensor) sollte die Default-IDs haben
    assert added_entities[0]._entity_ids["schulferien"] == "sensor.schulferien_de_by"
    assert added_entities[0]._entity_ids["feiertag"] == "sensor.feiertag_de_by"

    # Zweiter Sensor (SchulferienFeiertagMorgenBinarySensor) sollte die Morgen-IDs haben
    assert added_entities[1]._entity_ids["schulferien"] == "sensor.schulferien_de_by_morgen"
    assert added_entities[1]._entity_ids["feiertag"] == "sensor.feiertag_de_by_morgen"

    # Dritter Sensor (SchulferienOnlyBinarySensor)
    assert added_entities[2]._entity_ids["schulferien"] == "sensor.schulferien_de_by"
    assert added_entities[2]._entity_ids["feiertag"] == "sensor.feiertag_de_by"

    # Vierter Sensor (SchulferienOnlyMorgenBinarySensor)
    assert added_entities[3]._entity_ids["schulferien"] == "sensor.schulferien_de_by_morgen"
    assert added_entities[3]._entity_ids["feiertag"] == "sensor.feiertag_de_by_morgen"

    # Fünfter Sensor (FeiertagOnlyBinarySensor)
    assert added_entities[4]._entity_ids["schulferien"] == "sensor.schulferien_de_by"
    assert added_entities[4]._entity_ids["feiertag"] == "sensor.feiertag_de_by"

    # Sechster Sensor (FeiertagOnlyMorgenBinarySensor)
    assert added_entities[5]._entity_ids["schulferien"] == "sensor.schulferien_de_by_morgen"
    assert added_entities[5]._entity_ids["feiertag"] == "sensor.feiertag_de_by_morgen"


# ============================================================
# Tests für is_on Property
# ============================================================

@pytest.mark.asyncio
async def test_is_on_property_schulferien_feiertag(config_heute):
    """Test is_on Property für kombinierten Sensor."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state("ferientag")
    sensor = SchulferienFeiertagBinarySensor(hass, config_heute)
    await sensor.async_update()
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_is_on_property_schulferien_only(config_schulferien_only):
    """Test is_on Property für SchulferienOnly Sensor."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_de_by" else make_state("kein_feiertag_de_by")
    sensor = SchulferienOnlyBinarySensor(hass, config_schulferien_only)
    await sensor.async_update()
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_is_on_property_feiertag_only(config_feiertag_only):
    """Test is_on Property für FeiertagOnly Sensor."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_de_by" else make_state("kein_ferientag_de_by")
    sensor = FeiertagOnlyBinarySensor(hass, config_feiertag_only)
    await sensor.async_update()
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_is_on_property_schulferien_only_morgen():
    """Test is_on Property für SchulferienOnlyMorgen Sensor."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_morgen" else make_state("feiertag")
    config = {
        "unique_id": "binary_sensor.test_morgen",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = SchulferienOnlyMorgenBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_is_on_property_feiertag_only_morgen():
    """Test is_on Property für FeiertagOnlyMorgen Sensor."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_morgen" else make_state("ferientag")
    config = {
        "unique_id": "binary_sensor.test_morgen",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }
    sensor = FeiertagOnlyMorgenBinarySensor(hass, config)
    await sensor.async_update()
    assert sensor.is_on is True


# ============================================================
# Tests für edge cases
# ============================================================

@pytest.mark.asyncio
async def test_schulferien_state_none_feiertag_state_none(today_sensor, hass):
    """Test wenn beide States None sind."""
    hass.states.get.return_value = None
    await today_sensor.async_update()
    assert not today_sensor.is_on


@pytest.mark.asyncio
async def test_schulferien_state_none_feiertag_state_exists(today_sensor, hass):
    """Test wenn nur Feiertag-State existiert."""
    hass.states.get.side_effect = lambda eid: None if eid == "sensor.schulferien_de_by" else make_state(
        "feiertag")
    await today_sensor.async_update()
    assert today_sensor.is_on is True


@pytest.mark.asyncio
async def test_schulferien_state_exists_feiertag_state_none(today_sensor, hass):
    """Test wenn nur Schulferien-State existiert."""
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_de_by" else None
    await today_sensor.async_update()
    assert today_sensor.is_on is True


@pytest.mark.asyncio
async def test_schulferien_only_with_both_true(schulferien_only_sensor, hass):
    """Test SchulferienOnly wenn beide True wären."""
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_de_by" else make_state("feiertag_de_by")
    await schulferien_only_sensor.async_update()
    # SchulferienOnly prüft nur Schulferien -> True
    assert schulferien_only_sensor.is_on is True


@pytest.mark.asyncio
async def test_feiertag_only_with_both_true(feiertag_only_sensor, hass):
    """Test FeiertagOnly wenn beide True wären."""
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_de_by" else make_state("ferientag_de_by")
    await feiertag_only_sensor.async_update()
    # FeiertagOnly prüft nur Feiertag -> True
    assert feiertag_only_sensor.is_on is True


@pytest.mark.asyncio
async def test_update_with_wrong_entity_ids(hass):
    """Test Verhalten bei falschen Entity-IDs."""
    config_wrong = {
        "unique_id": "binary_sensor.test",
        "schulferien_entity_id": "sensor.falsche_schulferien",
        "feiertag_entity_id": "sensor.falsches_feiertag",
    }
    sensor = SchulferienFeiertagBinarySensor(hass, config_wrong)
    hass.states.get.return_value = None
    await sensor.async_update()
    assert not sensor.is_on


@pytest.mark.asyncio
async def test_schulferien_state_other_value(today_sensor, hass):
    """Test wenn Schulferien-State ein anderer Wert ist."""
    hass.states.get.side_effect = lambda eid: make_state(
        "kein_ferientag") if eid == "sensor.schulferien_de_by" else make_state("kein_feiertag_de_by")
    await today_sensor.async_update()
    assert today_sensor.is_on is False


@pytest.mark.asyncio
async def test_feiertag_state_other_value(today_sensor, hass):
    """Test wenn Feiertag-State ein anderer Wert ist."""
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_de_by" else make_state("kein_ferientag_de_by")
    await today_sensor.async_update()
    assert today_sensor.is_on is True


@pytest.mark.asyncio
async def test_combined_sensor_with_empty_string_state(today_sensor, hass):
    """Test mit leerem State-String."""
    hass.states.get.side_effect = lambda eid: make_state(
        "") if eid == "sensor.schulferien_de_by" else make_state("")
    await today_sensor.async_update()
    assert today_sensor.is_on is False


@pytest.mark.asyncio
async def test_all_sensors_initialization():
    """Test dass alle Sensoren ohne Fehler initialisiert werden können."""
    hass = MagicMock()
    config = {
        "unique_id": "binary_sensor.test_DE_BY",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensors = [
        SchulferienFeiertagBinarySensor(hass, config),
        SchulferienFeiertagMorgenBinarySensor(hass, config),
        SchulferienOnlyBinarySensor(hass, config),
        SchulferienOnlyMorgenBinarySensor(hass, config),
        FeiertagOnlyBinarySensor(hass, config),
        FeiertagOnlyMorgenBinarySensor(hass, config),
    ]
    for sensor in sensors:
        assert sensor._state is False
        assert sensor.unique_id is not None


@pytest.mark.asyncio
async def test_schulferien_only_morgen_with_both_true(hass, config_schulferien_only_morgen):
    """Test SchulferienOnlyMorgen wenn beide True wären."""
    sensor = SchulferienOnlyMorgenBinarySensor(hass, config_schulferien_only_morgen)
    hass.states.get.side_effect = lambda eid: make_state("ferientag")
    await sensor.async_update()
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_feiertag_only_morgen_with_both_true(hass, config_feiertag_only_morgen):
    """Test FeiertagOnlyMorgen wenn beide True wären."""
    sensor = FeiertagOnlyMorgenBinarySensor(hass, config_feiertag_only_morgen)
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_de_by_morgen" else make_state("ferientag")
    await sensor.async_update()
    assert sensor.is_on is True


# ============================================================
# Tests für Brückentag-State
# ============================================================

@pytest.mark.asyncio
async def test_combined_sensor_brueckentag_state(today_sensor, hass):
    """Test kombinierter Sensor mit Brückentag-State."""
    hass.states.get.side_effect = lambda eid: make_state(
        "brueckentag") if eid == "sensor.feiertag" else make_state("kein_ferientag")
    await today_sensor.async_update()
    # "brueckentag" != "feiertag" und != "ferientag" → False
    assert today_sensor.is_on is False


@pytest.mark.asyncio
async def test_schulferien_only_brueckentag_state(schulferien_only_sensor, hass):
    """Test SchulferienOnly mit Brückentag als Schulferien-State."""
    hass.states.get.side_effect = lambda eid: make_state(
        "brueckentag") if eid == "sensor.schulferien" else make_state("kein_feiertag")
    await schulferien_only_sensor.async_update()
    # "brueckentag" != "ferientag" → False
    assert schulferien_only_sensor.is_on is False


@pytest.mark.asyncio
async def test_feiertag_only_brueckentag_state(feiertag_only_sensor, hass):
    """Test FeiertagOnly mit Brückentag als Feiertag-State."""
    hass.states.get.side_effect = lambda eid: make_state(
        "brueckentag") if eid == "sensor.feiertag" else make_state("kein_ferientag")
    await feiertag_only_sensor.async_update()
    # "brueckentag" != "feiertag" → False
    assert feiertag_only_sensor.is_on is False


# ============================================================
# Tests für State-Objekt ohne state-Attribut
# ============================================================

@pytest.mark.asyncio
async def test_schulferien_state_without_state_attr(today_sensor, hass):
    """Test wenn Schulferien-State kein state-Attribut hat.

    Der Code macht (schulferien_state and schulferien_state.state == "ferientag").
    Wenn schulferien_state ein MagicMock mit spec=[] ist, ist es truthy,
    aber der Zugriff auf .state wirft AttributeError.
    Wir testen dass der Sensor damit umgehen kann.
    """
    mock_state = MagicMock()
    mock_state.state = "kein_ferientag"
    hass.states.get.side_effect = lambda eid: mock_state if eid == "sensor.schulferien_de_by" else make_state(
        "kein_feiertag_de_by")
    await today_sensor.async_update()
    assert not today_sensor.is_on


# ============================================================
# Tests für Performance/Call-Count
# ============================================================

@pytest.mark.asyncio
async def test_combined_sensor_queries_both_entities():
    """Test dass beide Entities beim kombinierten Sensor abgefragt werden."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_de_by" else make_state("feiertag_de_by")
    config = {
        "unique_id": "binary_sensor.test_combined",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienFeiertagBinarySensor(hass, config)
    await sensor.async_update()
    assert hass.states.get.call_count == 2


@pytest.mark.asyncio
async def test_schulferien_only_queries_one_entity():
    """Test dass SchulferienOnly nur eine Entity abfragt."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "ferientag") if eid == "sensor.schulferien_de_by" else make_state("feiertag_de_by")
    config = {
        "unique_id": "binary_sensor.test_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = SchulferienOnlyBinarySensor(hass, config)
    await sensor.async_update()
    assert hass.states.get.call_count == 1


@pytest.mark.asyncio
async def test_feiertag_only_queries_one_entity():
    """Test dass FeiertagOnly nur eine Entity abfragt."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: make_state(
        "feiertag") if eid == "sensor.feiertag_de_by" else make_state("ferientag_de_by")
    config = {
        "unique_id": "binary_sensor.test_feiertag_only",
        "schulferien_entity_id": "sensor.schulferien_de_by",
        "feiertag_entity_id": "sensor.feiertag_de_by",
    }
    sensor = FeiertagOnlyBinarySensor(hass, config)
    await sensor.async_update()
    assert hass.states.get.call_count == 1


@pytest.mark.asyncio
async def test_binary_sensor_multiple_instances_different_regions():
    """Testet dass zwei BinarySensor-Instanzen mit verschiedenen Regionen parallel laufen."""
    from custom_components.schulferien.binary_sensor import async_setup_entry

    added_entities_instance1 = []
    added_entities_instance2 = []

    config_entry_by = MagicMock()
    config_entry_by.data = {
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }

    config_entry_at = MagicMock()
    config_entry_at.data = {
        "land": "AT",
        "region": "AT-OO",
        "land_name": "Österreich",
        "region_name": "Oberösterreich",
    }

    hass = MagicMock()

    with patch(
        "custom_components.schulferien.binary_sensor.compute_region_slug"
    ) as mock_slug:
        mock_slug.side_effect = lambda land, region: region.split("-")[-1]

        mock_add_entities_by = lambda entities: added_entities_instance1.extend(entities)
        mock_add_entities_at = lambda entities: added_entities_instance2.extend(entities)

        await async_setup_entry(hass, config_entry_by, mock_add_entities_by)
        await async_setup_entry(hass, config_entry_at, mock_add_entities_at)

    assert len(added_entities_instance1) == 6
    assert len(added_entities_instance2) == 6

    entity_ids_instance1 = []
    for e in added_entities_instance1:
        entity_ids_instance1.extend(e._entity_ids.values())

    entity_ids_instance2 = []
    for e in added_entities_instance2:
        entity_ids_instance2.extend(e._entity_ids.values())

    for eid in entity_ids_instance1:
        assert "de_by" in eid

    for eid in entity_ids_instance2:
        assert "at_oo" in eid

    all_entity_ids = set(entity_ids_instance1) | set(entity_ids_instance2)

    de_by_ids = set(entity_ids_instance1)
    at_oo_ids = set(entity_ids_instance2)

    assert de_by_ids & at_oo_ids == set()

    unique_ids_instance1 = [e.unique_id for e in added_entities_instance1]
    unique_ids_instance2 = [e.unique_id for e in added_entities_instance2]

    for uid in unique_ids_instance1:
        assert "DE_BY" in uid

    for uid in unique_ids_instance2:
        assert "AT_OO" in uid
