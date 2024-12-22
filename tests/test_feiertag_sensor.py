"""Unit Test um die Ausgabe des Feiertagsensors zu testen."""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
from custom_components.schulferien.feiertag_sensor import FeiertagSensor
from custom_components.schulferien.const import API_URL_FEIERTAGE


@pytest.fixture
def mock_config():
    """Erstellt eine Mock-Konfiguration."""
    return {
        "name": "Feiertag Sensor",
        "unique_id": "sensor.feiertag",
        "land": "DE",
        "region": "DE-BY",
    }


@pytest.fixture
def mock_sensor(hass, mock_config):
    """Erstellt eine Instanz des Feiertag-Sensors."""
    return FeiertagSensor(hass, mock_config)


async def test_initial_attributes(mock_sensor):
    """Testet die anfänglichen Attribute des Sensors."""
    assert mock_sensor.name == "Feiertag Sensor"
    assert mock_sensor.unique_id == "sensor.feiertag"
    assert mock_sensor.state == "Kein Feiertag"


async def test_update_today_holiday(mock_sensor):
    """Testet die Aktualisierung mit einem Feiertag heute."""
    # Simulierte API-Daten
    today = datetime.now().date()
    mock_data = [
        {"name": "Test-Feiertag", "start_datum": today},
        {"name": "Zukunft-Feiertag", "start_datum": today + timedelta(days=10)},
    ]

    with patch(
        "custom_components.schulferien.api_utils.fetch_data",
        new=AsyncMock(return_value=mock_data),
    ), patch(
        "custom_components.schulferien.api_utils.parse_daten",
        return_value=mock_data,
    ):
        await mock_sensor.async_update()

        assert mock_sensor.state == "Feiertag"
        assert mock_sensor.extra_state_attributes["Nächster Feiertag"] == "Zukunft-Feiertag"


async def test_update_no_holiday(mock_sensor):
    """Testet die Aktualisierung ohne Feiertage heute."""
    today = datetime.now().date()
    mock_data = [
        {"name": "Zukunft-Feiertag", "start_datum": today + timedelta(days=10)},
    ]

    with patch(
        "custom_components.schulferien.api_utils.fetch_data",
        new=AsyncMock(return_value=mock_data),
    ), patch(
        "custom_components.schulferien.api_utils.parse_daten",
        return_value=mock_data,
    ):
        await mock_sensor.async_update()

        assert mock_sensor.state == "Kein Feiertag"
        assert mock_sensor.extra_state_attributes["Nächster Feiertag"] == "Zukunft-Feiertag"


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
