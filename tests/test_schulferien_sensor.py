"""Unit Test für Schulferien-Sensor."""

from datetime import datetime
import pytest
from custom_components.schulferien.schulferien_sensor import SchulferienSensor


@pytest.fixture
def mock_hass():
    """Mock Home Assistant Instanz."""
    return object()


@pytest.fixture
def mock_config():
    """Mock-Konfiguration."""
    return {
        "name": "Schulferien Sensor",
        "land": "DE",
        "region": "DE-BY",
        "brueckentage": ["2024-05-01"],
    }


@pytest.fixture
def sensor(mock_hass, mock_config):
    """Instanz des SchulferienSensors."""
    return SchulferienSensor(mock_hass, mock_config)


@pytest.mark.parametrize(
    "sensor_name, expected_state",
    [
        ("Schulferien Sensor", "Kein Ferientag"),
    ],
)
def test_sensor_initialization(sensor, sensor_name, expected_state):
    """Testet die Initialisierung des Sensors."""
    assert sensor.name == sensor_name
    assert sensor.unique_id == "sensor.schulferien"
    assert sensor.state == expected_state


def test_extra_state_attributes(sensor):
    """Testet zusätzliche Zustandsattribute."""
    attributes = sensor.extra_state_attributes
    assert attributes["Land"] == "Deutschland"
    assert attributes["Region"] == "Bayern"
    assert attributes["Brückentage"] == ["2024-05-01"]


@pytest.mark.parametrize(
    "ferien_info, expected_state, expected_attributes",
    [
        (
            {
                "heute_ferientag": True,
                "naechste_ferien_name": "Sommerferien",
                "naechste_ferien_beginn": "01.08.2024",
                "naechste_ferien_ende": "31.08.2024",
            },
            "Ferientag",
            {
                "Nächste Ferien": "Sommerferien",
                "Beginn": "01.08.2024",
                "Ende": "31.08.2024",
            },
        )
    ],
)

def test_last_update_date(sensor):
    """Testet das Datum des letzten Updates."""
    today = datetime.now().date()
    sensor.last_update_date = today
    assert sensor.last_update_date == today
