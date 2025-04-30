"""Unit Test für Schulferien-Sensor."""

from unittest.mock import patch, AsyncMock
from datetime import datetime
import pytest
from custom_components.schulferien.schulferien_sensor import SchulferienSensor

@pytest.fixture
def mock_config():
    """Mock-Konfiguration für den Schulferien-Sensor."""
    return {
        "name": "Schulferien Sensor",
        "unique_id": "sensor.schulferien",
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
    """Erstellt eine Instanz des Schulferien-Sensors."""
    sensor = SchulferienSensor(mock_hass, mock_config)
    mock_hass.add_job(sensor.async_added_to_hass)
    return sensor

@pytest.mark.asyncio
async def test_sensor_initialization(mock_sensor, mock_hass):
    """Testet die anfänglichen Attribute des Sensors."""
    await mock_sensor.async_added_to_hass()
    assert mock_sensor.name == "Schulferien Sensor"
    assert mock_sensor.unique_id == "sensor.schulferien"
    assert mock_sensor.state == "kein_ferientag"
    assert "Name Ferien" in mock_sensor.extra_state_attributes

@pytest.mark.asyncio
async def test_last_update_date(mock_sensor):
    """Testet das Datum des letzten Updates."""
    today = datetime.now().date()
    mock_sensor.last_update_date = today
    assert mock_sensor.last_update_date == today
