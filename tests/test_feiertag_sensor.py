"""Unit Tests für FeiertagSensor & FeiertagMorgenSensor."""

from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
import pytest
from homeassistant.core import HomeAssistant
from custom_components.schulferien.feiertag_sensor import FeiertagSensor, FeiertagMorgenSensor

@pytest.fixture
def mock_config():
    return {
        "name": "Feiertag Sensor",
        "unique_id": "sensor.feiertag",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }

@pytest.fixture
def hass():
    return HomeAssistant()

@pytest.fixture
def mock_sensor(hass, mock_config):
    return FeiertagSensor(hass, mock_config)

@pytest.fixture
def morgen_sensor(mock_sensor):
    return FeiertagMorgenSensor(mock_sensor)

@pytest.mark.asyncio
async def test_initial_attributes(mock_sensor, morgen_sensor):
    await mock_sensor.async_added_to_hass()

    assert mock_sensor.name == "Feiertag Sensor"
    assert mock_sensor.unique_id == "sensor.feiertag"
    assert mock_sensor.native_value == "kein_feiertag"
    assert morgen_sensor.native_value == "kein_feiertag"

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_data, today, tomorrow_state",
    [
        (
            [
                {
                    "name": "Morgen-Feiertag",
                    "start_datum": datetime(2024, 6, 19).date(),
                    "end_datum": datetime(2024, 6, 19).date()
                }
            ],
            datetime(2024, 6, 18),
            "feiertag",
        ),
        (
            [
                {
                    "name": "Nächster Feiertag",
                    "start_datum": datetime(2024, 6, 25).date(),
                    "end_datum": datetime(2024, 6, 25).date()
                }
            ],
            datetime(2024, 6, 18),
            "kein_feiertag",
        )
    ],
)
async def test_feiertag_morgen_sensor(mock_sensor, morgen_sensor, mock_data, today, tomorrow_state):
    with patch("custom_components.schulferien.api_utils.fetch_data", new=AsyncMock(return_value=mock_data)), \
         patch("custom_components.schulferien.api_utils.parse_daten", return_value=mock_data), \
         patch("custom_components.schulferien.feiertag_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = today
        mock_dt.now().date.return_value = today.date()

        await mock_sensor.async_update()

        assert morgen_sensor.native_value == tomorrow_state

@pytest.mark.asyncio
async def test_update_error_handling(mock_sensor, morgen_sensor):
    with patch("custom_components.schulferien.api_utils.fetch_data", new=AsyncMock(side_effect=Exception("API-Fehler"))):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_feiertag"
        assert morgen_sensor.native_value == "kein_feiertag"

    with patch("custom_components.schulferien.api_utils.fetch_data", new=AsyncMock(return_value=None)):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_feiertag"
        assert morgen_sensor.native_value == "kein_feiertag"
