"""Unit Test für Feiertag-Sensor."""

from unittest.mock import patch, AsyncMock
from datetime import datetime
import pytest
from custom_components.schulferien.feiertag_sensor import FeiertagSensor

@pytest.fixture
def mock_config():
    """Mock-Konfiguration für den Feiertag-Sensor."""
    return {
        "name": "Feiertag Sensor",
        "unique_id": "sensor.feiertag",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }

@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    return mock.AsyncMock()

@pytest.fixture
def mock_sensor(mock_hass, mock_config):
    """Erstellt eine Instanz des Feiertag-Sensors."""
    sensor = FeiertagSensor(mock_hass, mock_config)
    mock_hass.add_job(sensor.async_added_to_hass)
    return sensor

@pytest.mark.asyncio
async def test_initial_attributes(mock_sensor, mock_hass):
    """Testet die anfänglichen Attribute des Sensors."""
    await mock_sensor.async_added_to_hass()
    assert mock_sensor.name == "Feiertag Sensor"
    assert mock_sensor.unique_id == "sensor.feiertag"
    assert mock_sensor.state == "kein_feiertag"
    assert "Name Feiertag" in mock_sensor.extra_state_attributes

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_data, expected_state, expected_next_holiday",
    [
        # Feiertag heute
        (
            [
                {"name": "Test-Feiertag", "start_datum": datetime(2024, 6, 1).date()},
                {"name": "Zukunft-Feiertag", "start_datum": datetime(2024, 6, 10).date()},
            ],
            "feiertag",
            "Zukunft-Feiertag",
        ),
        # Kein Feiertag heute
        (
            [
                {"name": "Zukunft-Feiertag", "start_datum": datetime(2024, 6, 10).date()},
            ],
            "kein_feiertag",
            "Zukunft-Feiertag",
        ),
    ],
)
async def test_update(mock_sensor, mock_data, expected_state, expected_next_holiday):
    """Testet die Aktualisierung mit und ohne Feiertag."""
    await mock_sensor.async_added_to_hass()
    with patch(
        "custom_components.schulferien.api_utils.fetch_data",
        new=AsyncMock(return_value=mock_data),
    ), patch(
        "custom_components.schulferien.api_utils.parse_daten",
        return_value=mock_data,
    ):
        await mock_sensor.async_update()

        assert mock_sensor.state == expected_state
        assert (
            mock_sensor.extra_state_attributes["Name Feiertag"]
            == expected_next_holiday
        )

@pytest.mark.asyncio
async def test_update_error_handling(mock_sensor):
    """Testet das Verhalten bei einem API-Fehler."""
    await mock_sensor.async_added_to_hass()
    # Netzwerkfehler
    with patch(
        "custom_components.schulferien.api_utils.fetch_data",
        new=AsyncMock(side_effect=Exception("API-Fehler")),
    ):
        await mock_sensor.async_update()

        assert mock_sensor.state == "kein_feiertag"
        assert mock_sensor.extra_state_attributes["Name Feiertag"] is None

    # Leere Antwort
    with patch(
        "custom_components.schulferien.api_utils.fetch_data",
        new=AsyncMock(return_value=None),
    ):
        await mock_sensor.async_update()

        assert mock_sensor.state == "kein_feiertag"
        assert mock_sensor.extra_state_attributes["Name Feiertag"] is None
