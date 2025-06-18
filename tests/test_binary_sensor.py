"""Unit Tests für SchulferienFeiertagBinarySensor & Morgen-Binärsensor."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from custom_components.schulferien.binary_sensor import (
    SchulferienFeiertagBinarySensor,
    SchulferienFeiertagMorgenBinarySensor,
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
def today_sensor(hass, config):
    return SchulferienFeiertagBinarySensor(hass, config)

@pytest.fixture
def morgen_sensor(hass, config):
    return SchulferienFeiertagMorgenBinarySensor(hass, config)

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
    def fake_state(state_str):
        mock = MagicMock()
        mock.state = state_str
        return mock if state_str is not None else None

    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien": fake_state(ferien_state),
        "sensor.feiertag": fake_state(feiertag_state),
    }.get(eid)

    await today_sensor.async_update()
    assert today_sensor.is_on is expected

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
    def fake_state(state_str):
        mock = MagicMock()
        mock.state = state_str
        return mock if state_str is not None else None

    hass.states.get.side_effect = lambda eid: {
        "sensor.schulferien": fake_state(ferien_state),
        "sensor.feiertag": fake_state(feiertag_state),
    }.get(eid)

    with patch("custom_components.schulferien.binary_sensor.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 6, 18)
        mock_dt.now().date.return_value = datetime(2024, 6, 18).date()

        await morgen_sensor.async_update()
        assert morgen_sensor.is_on is expected
