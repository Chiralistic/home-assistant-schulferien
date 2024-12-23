"""Unit Test für Feiertag-Sensor."""

from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
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
    }


@pytest.fixture
def mock_sensor(mock_config):
    """Erstellt eine Instanz des Feiertag-Sensors."""
    hass = object()  # Mock für Home Assistant
    return FeiertagSensor(hass, mock_config)


@pytest.mark.asyncio
async def test_initial_attributes(mock_sensor):
    """Testet die anfänglichen Attribute des Sensors."""
    assert mock_sensor.name == "Feiertag Sensor"
    assert mock_sensor.unique_id == "sensor.feiertag"
    assert mock_sensor.state == "Kein Feiertag"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_data, expected_state, expected_next_holiday",
    [
        # Feiertag heute
        (
            [
                {"name": "Test-Feiertag", "start_datum": datetime.now().date()},
                {"name": "Zukunft-Feiertag", "start_datum": datetime.now().date() + timedelta(days=10)},
            ],
            "Feiertag",
            "Zukunft-Feiertag",
        ),
        # Kein Feiertag heute
        (
            [
                {"name": "Zukunft-Feiertag", "start_datum": datetime.now().date() + timedelta(days=10)},
            ],
            "Kein Feiertag",
            "Zukunft-Feiertag",
        ),
    ],
)
async def test_update(mock_sensor, mock_data, expected_state, expected_next_holiday):
    """Testet die Aktualisierung mit und ohne Feiertag."""
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
            mock_sensor.extra_state_attributes["Nächster Feiertag"]
            == expected_next_holiday
        )


@pytest.mark.asyncio
async def test_update_error_handling(mock_sensor):
    """Testet das Verhalten bei einem API-Fehler."""
    with patch(
        "custom_components.schulferien.api_utils.fetch_data",
        new=AsyncMock(side_effect=Exception("API-Fehler")),
    ):
        await mock_sensor.async_update()

        # Der Zustand sollte unverändert bleiben
        assert mock_sensor.state == "Kein Feiertag"
        assert mock_sensor.extra_state_attributes["Nächster Feiertag"] is None
