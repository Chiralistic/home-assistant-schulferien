"""Unit Tests für SchulferienFeiertagBinarySensor & Morgen-Binärsensor."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from custom_components.schulferien.binary_sensor import (
    SchulferienFeiertagBinarySensor,
    SchulferienFeiertagMorgenBinarySensor,
    SchulferienOnlyBinarySensor,
    SchulferienOnlyMorgenBinarySensor,
    FeiertagOnlyBinarySensor,
    FeiertagOnlyMorgenBinarySensor,
)

@pytest.fixture
def hass():
    hass = MagicMock()
    hass.states.get = MagicMock()
    return hass

@pytest.fixture
def config():
    return {
        "unique_id": "binary_sensor.schulferien_feiertage",
        "schulferien_entity_id": "sensor.schulferien",
        "feiertag_entity_id": "sensor.feiertag",
    }

@pytest.fixture
def config_morgen():
    return {
        "unique_id": "binary_sensor.schulferien_feiertage_morgen",
        "schulferien_entity_id": "sensor.schulferien_morgen",
        "feiertag_entity_id": "sensor.feiertag_morgen",
    }

@pytest.fixture
def today_sensor(hass, config):
    return SchulferienFeiertagBinarySensor(hass, config)

@pytest.fixture
def morgen_sensor(hass, config_morgen):
    return SchulferienFeiertagMorgenBinarySensor(hass, config_morgen)

@pytest.fixture
def schulferien_only_sensor(hass, config):
    return SchulferienOnlyBinarySensor(hass, config)

@pytest.fixture
def schulferien_only_morgen_sensor(hass, config_morgen):
    return SchulferienOnlyMorgenBinarySensor(hass, config_morgen)

@pytest.fixture
def feiertag_only_sensor(hass, config):
    return FeiertagOnlyBinarySensor(hass, config)

@pytest.fixture
def feiertag_only_morgen_sensor(hass, config_morgen):
    return FeiertagOnlyMorgenBinarySensor(hass, config_morgen)

def fake_state(hass, state_str):
    """Hilfsfunktion zum Erstellen eines fake State-Objekts."""
    def fake_state_inner(eid):
        mock = MagicMock()
        mock.state = state_str
        return mock if state_str is not None else None
    return fake_state_inner

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
    """Testet heutigen Binärsensor-Zustand."""
    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien": MagicMock(state=ferien_state) if ferien_state else None,
        "sensor.feiertag": MagicMock(state=feiertag_state) if feiertag_state else None,
    }.get(eid)

    await today_sensor.async_update()
    assert today_sensor.is_on == expected

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
async def test_morgen_binary_sensor_state(morgen_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet morgigen Binärsensor-Zustand."""
    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien_morgen": MagicMock(state=ferien_state) if ferien_state else None,
        "sensor.feiertag_morgen": MagicMock(state=feiertag_state) if feiertag_state else None,
    }.get(eid)

    await morgen_sensor.async_update()
    assert morgen_sensor.is_on == expected

# Tests für SchulferienOnlyBinarySensor
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", False),  # Beides -> False (nicht nur Schulferien)
        ("ferientag", "kein_feiertag", True),  # Nur Schulferien -> True
        ("kein_ferientag", "feiertag", False),  # Nur Feiertag -> False
        ("kein_ferientag", "kein_feiertag", False),  # Weder -> False
        (None, "feiertag", False),  # Nur Feiertag -> False
        ("ferientag", None, True),  # Nur Schulferien -> True
        (None, None, False),  # Weder -> False
    ]
)
async def test_schulferien_only_binary_sensor_state(schulferien_only_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet SchulferienOnly Binärsensor-Zustand."""
    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien": MagicMock(state=ferien_state) if ferien_state else None,
        "sensor.feiertag": MagicMock(state=feiertag_state) if feiertag_state else None,
    }.get(eid)

    await schulferien_only_sensor.async_update()
    assert schulferien_only_sensor.is_on == expected

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", False),
        ("ferientag", "kein_feiertag", True),
        ("kein_ferientag", "feiertag", False),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", False),
        ("ferientag", None, True),
        (None, None, False),
    ]
)
async def test_schulferien_only_morgen_binary_sensor_state(schulferien_only_morgen_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet SchulferienOnlyMorgen Binärsensor-Zustand."""
    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien_morgen": MagicMock(state=ferien_state) if ferien_state else None,
        "sensor.feiertag_morgen": MagicMock(state=feiertag_state) if feiertag_state else None,
    }.get(eid)

    await schulferien_only_morgen_sensor.async_update()
    assert schulferien_only_morgen_sensor.is_on == expected

# Tests für FeiertagOnlyBinarySensor
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", False),  # Beides -> False (nicht nur Feiertag)
        ("ferientag", "kein_feiertag", False),  # Nur Schulferien -> False
        ("kein_ferientag", "feiertag", True),  # Nur Feiertag -> True
        ("kein_ferientag", "kein_feiertag", False),  # Weder -> False
        (None, "feiertag", True),  # Nur Feiertag -> True
        ("ferientag", None, False),  # Nur Schulferien -> False
        (None, None, False),  # Weder -> False
    ]
)
async def test_feiertag_only_binary_sensor_state(feiertag_only_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet FeiertagOnly Binärsensor-Zustand."""
    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien": MagicMock(state=ferien_state) if ferien_state else None,
        "sensor.feiertag": MagicMock(state=feiertag_state) if feiertag_state else None,
    }.get(eid)

    await feiertag_only_sensor.async_update()
    assert feiertag_only_sensor.is_on == expected

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_state, feiertag_state, expected",
    [
        ("ferientag", "feiertag", False),
        ("ferientag", "kein_feiertag", False),
        ("kein_ferientag", "feiertag", True),
        ("kein_ferientag", "kein_feiertag", False),
        (None, "feiertag", True),
        ("ferientag", None, False),
        (None, None, False),
    ]
)
async def test_feiertag_only_morgen_binary_sensor_state(feiertag_only_morgen_sensor, hass, ferien_state, feiertag_state, expected):
    """Testet FeiertagOnlyMorgen Binärsensor-Zustand."""
    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien_morgen": MagicMock(state=ferien_state) if ferien_state else None,
        "sensor.feiertag_morgen": MagicMock(state=feiertag_state) if feiertag_state else None,
    }.get(eid)

    await feiertag_only_morgen_sensor.async_update()
    assert feiertag_only_morgen_sensor.is_on == expected