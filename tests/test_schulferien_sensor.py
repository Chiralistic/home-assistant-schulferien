"""Unit Test um die Ausgabe des Schulferiensensors zu testen."""

import pytest
from datetime import datetime, timedelta
from custom_components.schulferien.schulferien_sensor import SchulferienSensor

@pytest.fixture
def mock_hass():
    return object()

@pytest.fixture
def mock_config():
    return {
        "name": "Schulferien Sensor",
        "land": "DE",
        "region": "BY",
        "brueckentage": ["2024-05-01"]
    }

@pytest.fixture
def sensor(mock_hass, mock_config):
    return SchulferienSensor(mock_hass, mock_config)

def test_sensor_initialization(sensor):
    assert sensor.name == "Schulferien Sensor"
    assert sensor.unique_id == "sensor.schulferien"
    assert sensor.state == "Kein Ferientag"

def test_extra_state_attributes(sensor):
    attributes = sensor.extra_state_attributes
    assert attributes["Land"] == "Deutschland"
    assert attributes["Region"] == "Bayern"
    assert attributes["Brückentage"] == ["2024-05-01"]

def test_update_ferien_info(sensor):
    sensor._ferien_info = {
        "heute_ferientag": True,
        "naechste_ferien_name": "Sommerferien",
        "naechste_ferien_beginn": "01.08.2024",
        "naechste_ferien_ende": "31.08.2024"
    }
    assert sensor.state == "Ferientag"
    attributes = sensor.extra_state_attributes
    assert attributes["Nächste Ferien"] == "Sommerferien"
    assert attributes["Beginn"] == "01.08.2024"
    assert attributes["Ende"] == "31.08.2024"

def test_last_update_date(sensor):
    today = datetime.now().date()
    sensor.last_update_date = today
    assert sensor.last_update_date == today
