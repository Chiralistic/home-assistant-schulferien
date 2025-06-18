"""Unit Tests für SchulferienSensor & SchulferienMorgenSensor."""

from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
import pytest
from homeassistant.core import HomeAssistant
from custom_components.schulferien.schulferien_sensor import SchulferienSensor, SchulferienMorgenSensor

@pytest.fixture
def mock_config():
    return {
        "name": "Schulferien Sensor",
        "unique_id": "sensor.schulferien",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }

@pytest.fixture
def hass():
    return HomeAssistant()

@pytest.fixture
def mock_sensor(hass, mock_config):
    return SchulferienSensor(hass, mock_config)

@pytest.fixture
def morgen_sensor(mock_sensor):
    return SchulferienMorgenSensor(mock_sensor)

@pytest.mark.asyncio
async def test_initial_attributes(mock_sensor, morgen_sensor):
    await mock_sensor.async_added_to_hass()
    assert mock_sensor.name == "Schulferien Sensor"
    assert mock_sensor.unique_id == "sensor.schulferien"
    assert mock_sensor.native_value == "kein_ferientag"
    assert morgen_sensor.native_value == "kein_ferientag"

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_data, today, expected_today, expected_morgen",
    [
        (
            [
                {
                    "name": "Pfingstferien",
                    "start_datum": datetime(2024, 6, 18).date(),
                    "end_datum": datetime(2024, 6, 20).date()
                },
            ],
            datetime(2024, 6, 18),
            "ferientag",
            "ferientag"
        ),
        (
            [
                {
                    "name": "Sommerferien",
                    "start_datum": datetime(2024, 6, 25).date(),
                    "end_datum": datetime(2024, 9, 1).date()
                },
            ],
            datetime(2024, 6, 18),
            "kein_ferientag",
            "kein_ferientag"
        ),
        (
            [
                {
                    "name": "Kurzferien",
                    "start_datum": datetime(2024, 6, 19).date(),
                    "end_datum": datetime(2024, 6, 21).date()
                },
            ],
            datetime(2024, 6, 18),
            "kein_ferientag",
            "ferientag"
        ),
    ]
)
async def test_update(mock_sensor, morgen_sensor, mock_data, today, expected_today, expected_morgen):
    with patch("custom_components.schulferien.api_utils.fetch_data", new=AsyncMock(return_value=mock_data)), \
         patch("custom_components.schulferien.api_utils.parse_daten", return_value=mock_data), \
         patch("custom_components.schulferien.schulferien_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = today
        mock_dt.now().date.return_value = today.date()

        await mock_sensor.async_update()

        assert mock_sensor.native_value == expected_today
        assert morgen_sensor.native_value == expected_morgen

@pytest.mark.asyncio
async def test_update_error_handling(mock_sensor, morgen_sensor):
    with patch("custom_components.schulferien.api_utils.fetch_data", new=AsyncMock(side_effect=Exception("API-Fail"))):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"
        assert morgen_sensor.native_value == "kein_ferientag"

    with patch("custom_components.schulferien.api_utils.fetch_data", new=AsyncMock(return_value=None)):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"
        assert morgen_sensor.native_value == "kein_ferientag"
