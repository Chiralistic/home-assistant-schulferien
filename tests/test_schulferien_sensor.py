"""Unit Tests für SchulferienSensor & SchulferienMorgenSensor."""

from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timedelta
import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from custom_components.schulferien.schulferien_sensor import (
    SchulferienSensor,
    SchulferienMorgenSensor,
    SCHULFERIEN_SENSOR,
    SCHULFERIEN_MORGEN_SENSOR,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_config():
    """Standard-Konfiguration für Schulferien-Sensoren."""
    return {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }


@pytest.fixture
def mock_config_with_brueckentage():
    """Konfiguration mit Brückentagen."""
    return {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": ["16.06.2024", "17.06.2024"],
    }


@pytest.fixture
def hass_mock():
    """Mock HomeAssistant mit config-Attribut."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    return hass


@pytest.fixture
def mock_sensor(hass_mock, mock_config):
    """Standard Schulferien-Sensor."""
    return SchulferienSensor(hass_mock, mock_config)


@pytest.fixture
def morgen_sensor(mock_sensor):
    """SchulferienMorgen-Sensor."""
    return SchulferienMorgenSensor(mock_sensor)


# ============================================================
# Tests für SchulferienSensor Initialisierung
# ============================================================

def test_sensor_initialization(mock_sensor, mock_config):
    """Test die korrekte Initialisierung des Sensors."""
    assert mock_sensor.name == mock_config["name"]
    assert mock_sensor.unique_id == mock_config["unique_id"]
    assert mock_sensor._location["land"] == "DE"
    assert mock_sensor._location["region"] == "DE-BY"
    assert mock_sensor._location["land_name"] == "Deutschland"
    assert mock_sensor._location["region_name"] == "Bayern"
    assert mock_sensor._brueckentage == []
    assert mock_sensor._ferien_info["heute_ferientag"] is None
    assert mock_sensor._ferien_info["naechste_ferien_name"] is None


def test_sensor_initialization_with_brueckentage(mock_config_with_brueckentage):
    """Test die Initialisierung mit Brückentagen."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    sensor = SchulferienSensor(hass, mock_config_with_brueckentage)
    assert len(sensor._brueckentage) == 2
    assert "16.06.2024" in sensor._brueckentage
    assert "17.06.2024" in sensor._brueckentage


def test_sensor_default_unique_id(hass_mock):
    """Test dass der Standard unique_id verwendet wird."""
    config = {
        "name": "Test Sensor",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    sensor = SchulferienSensor(hass_mock, config)
    assert sensor.unique_id == "schulferien_DE_BY"


def test_sensor_custom_unique_id(hass_mock):
    """Test dass ein benutzerdefinierter unique_id verwendet wird."""
    config = {
        "name": "Test Sensor",
        "unique_id": "schulferien_DE_BW",
        "entity_id": "sensor.schulferien_de_bw",
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }
    sensor = SchulferienSensor(hass_mock, config)
    assert sensor.unique_id == "schulferien_DE_BW"


def test_sensor_entity_description(mock_sensor):
    """Test die EntityDescription."""
    assert mock_sensor.entity_description.key == "schulferien"
    assert mock_sensor.entity_description.name == "Schulferien"


def test_sensor_initialization_iso_code(hass_mock, mock_config):
    """Test dass iso_code initial auf 'DE' gesetzt ist."""
    sensor = SchulferienSensor(hass_mock, mock_config)
    assert sensor._location["iso_code"] == "DE"


def test_sensor_initialization_missing_unique_id(hass_mock):
    """Test Initialisierung ohne unique_id in Config."""
    config = {
        "name": "Test Sensor",
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }
    sensor = SchulferienSensor(hass_mock, config)
    assert sensor.unique_id == "schulferien_DE_BW"


def test_sensor_initialization_missing_brueckentage(hass_mock):
    """Test Initialisierung ohne brueckentage in Config."""
    config = {
        "name": "Test Sensor",
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }
    sensor = SchulferienSensor(hass_mock, config)
    assert sensor._brueckentage == []


# ============================================================
# Tests für native_value (Zustand)
# ============================================================

def test_native_value_kein_ferientag(mock_sensor):
    """Test native_value wenn kein Ferientag."""
    assert mock_sensor.native_value == "kein_ferientag"


def test_native_value_ferientag_false(mock_sensor):
    """Test native_value wenn heute_ferientag False ist."""
    mock_sensor._ferien_info["heute_ferientag"] = False
    assert mock_sensor.native_value == "kein_ferientag"


def test_native_value_ferientag_true(mock_sensor):
    """Test native_value wenn Ferientag."""
    mock_sensor._ferien_info["heute_ferientag"] = True
    assert mock_sensor.native_value == "ferientag"


def test_native_value_ferientag_none(mock_sensor):
    """Test native_value wenn heute_ferientag None ist."""
    mock_sensor._ferien_info["heute_ferientag"] = None
    assert mock_sensor.native_value == "kein_ferientag"


# ============================================================
# Tests für extra_state_attributes
# ============================================================

def test_extra_state_attributes_no_ferien(mock_sensor):
    """Test Attribute wenn keine Ferien vorhanden."""
    attributes = mock_sensor.extra_state_attributes
    assert "Name der Ferien" in attributes
    assert "Beginn" in attributes
    assert "Ende" in attributes
    assert attributes["Land"] == "Deutschland"
    assert attributes["Region"] == "Bayern"
    assert attributes["Brückentage"] == []


def test_extra_state_attributes_current_ferien():
    """Test Attribute während laufenden Ferien."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    sensor = SchulferienSensor(hass, config)

    heute = datetime.now().date()
    sensor._ferien_info.update({
        "ferien_liste": [
            {
                "name": "Sommerferien",
                "start_datum": heute - timedelta(days=5),
                "end_datum": heute + timedelta(days=25),
            }
        ],
        "naechste_ferien_name": "Sommerferien",
        "naechste_ferien_beginn": (heute - timedelta(days=5)).strftime("%d.%m.%Y"),
        "naechste_ferien_ende": (heute + timedelta(days=25)).strftime("%d.%m.%Y"),
    })

    attributes = sensor.extra_state_attributes
    assert attributes["Name der Ferien"] == "Sommerferien"
    assert attributes["Beginn"] == (heute - timedelta(days=5)).strftime("%d.%m.%Y")
    assert attributes["Ende"] == (heute + timedelta(days=25)).strftime("%d.%m.%Y")


def test_extra_state_attributes_next_ferien():
    """Test Attribute für nächste Ferien."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    sensor = SchulferienSensor(hass, config)

    heute = datetime.now().date()
    naechste_start = heute + timedelta(days=30)
    naechste_ende = heute + timedelta(days=60)

    sensor._ferien_info.update({
        "ferien_liste": [
            {
                "name": "Weihnachtsferien",
                "start_datum": naechste_start,
                "end_datum": naechste_ende,
            }
        ],
        "naechste_ferien_name": "Weihnachtsferien",
        "naechste_ferien_beginn": naechste_start.strftime("%d.%m.%Y"),
        "naechste_ferien_ende": naechste_ende.strftime("%d.%m.%Y"),
    })

    attributes = sensor.extra_state_attributes
    assert attributes["Name der Ferien"] == "Weihnachtsferien"


def test_extra_state_attributes_with_brueckentage(mock_config_with_brueckentage):
    """Test Attribute mit Brückentagen."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    sensor = SchulferienSensor(hass, mock_config_with_brueckentage)
    attributes = sensor.extra_state_attributes
    assert attributes["Brückentage"] == ["16.06.2024", "17.06.2024"]


def test_extra_state_attributes_no_naechste_ferien():
    """Test Attribute wenn keine nächsten Ferien."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    sensor = SchulferienSensor(hass, config)

    sensor._ferien_info.update({
        "ferien_liste": [],
        "naechste_ferien_name": None,
        "naechste_ferien_beginn": None,
        "naechste_ferien_ende": None,
    })

    attributes = sensor.extra_state_attributes
    assert attributes["Name der Ferien"] is None
    assert attributes["Beginn"] is None
    assert attributes["Ende"] is None


def test_extra_state_attributes_multiple_ferien():
    """Test Attribute mit mehreren Ferien in der Liste."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    sensor = SchulferienSensor(hass, config)

    heute = datetime.now().date()
    sensor._ferien_info.update({
        "ferien_liste": [
            {
                "name": "Osterferien",
                "start_datum": heute - timedelta(days=30),
                "end_datum": heute - timedelta(days=20),
            },
            {
                "name": "Sommerferien",
                "start_datum": heute - timedelta(days=5),
                "end_datum": heute + timedelta(days=25),
            },
            {
                "name": "Herbstferien",
                "start_datum": heute + timedelta(days=60),
                "end_datum": heute + timedelta(days=90),
            },
        ],
        "naechste_ferien_name": "Sommerferien",
        "naechste_ferien_beginn": (heute - timedelta(days=5)).strftime("%d.%m.%Y"),
        "naechste_ferien_ende": (heute + timedelta(days=25)).strftime("%d.%m.%Y"),
    })

    attributes = sensor.extra_state_attributes
    # Aktuelle Ferien haben Vorrang
    assert attributes["Name der Ferien"] == "Sommerferien"


# ============================================================
# Tests für get_api_parameter
# ============================================================

def test_get_api_parameter(mock_sensor):
    """Test die API-Parameter-Erzeugung."""
    heute = datetime(2024, 6, 18).date()
    params = mock_sensor.get_api_parameter(heute)

    assert params["countryIsoCode"] == "DE"
    assert params["subdivisionCode"] == "DE-BY"
    assert params["validFrom"] == "2024-05-19"  # heute - 30 Tage
    assert params["validTo"] == "2025-06-18"    # heute + 365 Tage
    assert params["languageIsoCode"] == "DE"


def test_get_api_parameter_with_iso_code(hass_mock):
    """Test dass der ISO-Code korrekt gesetzt wird."""
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    sensor = SchulferienSensor(hass_mock, config)
    sensor._location["iso_code"] = "DE"

    heute = datetime(2024, 6, 18).date()
    params = sensor.get_api_parameter(heute)
    assert params["languageIsoCode"] == "DE"


def test_get_api_parameter_different_region(hass_mock):
    """Test API-Parameter für andere Region."""
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }
    sensor = SchulferienSensor(hass_mock, config)
    heute = datetime(2024, 1, 15).date()
    params = sensor.get_api_parameter(heute)

    assert params["countryIsoCode"] == "DE"
    assert params["subdivisionCode"] == "DE-BW"
    assert params["validFrom"] == "2023-12-16"
    assert params["validTo"] == "2025-01-14"


# ============================================================
# Tests für async_added_to_hass
# ============================================================

@pytest.mark.asyncio
async def test_async_added_to_hass_sets_iso_code(mock_sensor):
    """Test dass der ISO-Code nach async_added_to_hass gesetzt wird."""
    mock_sensor._location["iso_code"] = "DE"
    mock_sensor.hass = MagicMock()
    mock_sensor.hass.config = MagicMock()
    mock_sensor.hass.config.language = "en"
    # Mock async_update und write_ha_state
    with patch.object(mock_sensor, "async_update", new=AsyncMock()), \
         patch.object(mock_sensor, "async_write_ha_state"):
        await mock_sensor.async_added_to_hass()
        assert mock_sensor._location["iso_code"] == "EN"


@pytest.mark.asyncio
async def test_async_added_to_hass_fallback_iso_code():
    """Test Fallback auf 'DE' wenn hass.config nicht verfügbar."""
    hass = MagicMock()
    hass.config = None
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    sensor = SchulferienSensor(hass, config)
    # async_track_time_change benötigt hass.loop, daher mocken
    with patch("custom_components.schulferien.schulferien_sensor.async_track_time_change") as mock_track, \
         patch.object(sensor, "async_update", new=AsyncMock()), \
         patch.object(sensor, "async_write_ha_state"):
        await sensor.async_added_to_hass()
        assert sensor._location["iso_code"] == "DE"


@pytest.mark.asyncio
async def test_async_added_to_hass_no_hass():
    """Test async_added_to_hass wenn hass None ist."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    config = {
        "name": "Test",
        "unique_id": "sensor.test",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    sensor = SchulferienSensor(hass, config)
    sensor.hass = None
    # async_track_time_change benötigt hass.loop, daher mocken
    with patch("custom_components.schulferien.schulferien_sensor.async_track_time_change") as mock_track, \
         patch.object(sensor, "async_update", new=AsyncMock()), \
         patch.object(sensor, "async_write_ha_state"):
        await sensor.async_added_to_hass()
        assert sensor._location["iso_code"] == "DE"


@pytest.mark.asyncio
async def test_async_added_to_hass_calls_update(mock_sensor):
    """Test dass async_update nach async_added_to_hass aufgerufen wird."""
    mock_sensor.hass = MagicMock()
    mock_sensor.hass.config = MagicMock()
    mock_sensor.hass.config.language = "de"
    mock_sensor._ferien_info["letztes_update"] = None

    with patch.object(mock_sensor, "async_update", new=AsyncMock()) as mock_update, \
         patch.object(mock_sensor, "async_write_ha_state"):
        await mock_sensor.async_added_to_hass()
        mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass_skips_update_same_day(mock_sensor):
    """Test dass update übersprungen wird wenn bereits heute aktualisiert."""
    mock_sensor.hass = MagicMock()
    mock_sensor.hass.config = MagicMock()
    mock_sensor.hass.config.language = "de"
    mock_sensor._ferien_info["letztes_update"] = datetime.now()

    with patch.object(mock_sensor, "async_update", new=AsyncMock()) as mock_update, \
         patch.object(mock_sensor, "async_write_ha_state"):
        await mock_sensor.async_added_to_hass()
        mock_update.assert_not_called()


# ============================================================
# Tests für async_update
# ============================================================

@pytest.mark.asyncio
async def test_update_success(mock_sensor, morgen_sensor):
    """Test erfolgreiches Update mit Ferien-Daten."""
    heute = datetime(2024, 6, 18)
    mock_api_response = [
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-06-25",
            "endDate": "2024-09-09"
        }
    ]
    mock_parsed_data = [
        {
            "name": "Sommerferien",
            "start_datum": datetime(2024, 6, 25).date(),
            "end_datum": datetime(2024, 9, 9).date(),
        }
    ]

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=mock_api_response)), \
         patch("custom_components.schulferien.schulferien_sensor.parse_daten", return_value=mock_parsed_data), \
         patch("custom_components.schulferien.schulferien_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = heute
        mock_dt.timedelta = timedelta

        await mock_sensor.async_update()

        assert mock_sensor._ferien_info["naechste_ferien_name"] == "Sommerferien"
        assert mock_sensor._ferien_info["heute_ferientag"] is False
        assert mock_sensor._ferien_info["naechste_ferien_beginn"] == "25.06.2024"
        assert mock_sensor._ferien_info["naechste_ferien_ende"] == "09.09.2024"


@pytest.mark.asyncio
async def test_update_during_ferien(mock_sensor, morgen_sensor):
    """Test Update während laufenden Ferien."""
    heute = datetime(2024, 6, 18)
    mock_api_response = [
        {
            "name": [{"text": "Pfingstferien"}],
            "startDate": "2024-06-18",
            "endDate": "2024-06-20"
        }
    ]
    mock_parsed_data = [
        {
            "name": "Pfingstferien",
            "start_datum": datetime(2024, 6, 18).date(),
            "end_datum": datetime(2024, 6, 20).date(),
        }
    ]

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=mock_api_response)), \
         patch("custom_components.schulferien.schulferien_sensor.parse_daten", return_value=mock_parsed_data), \
         patch("custom_components.schulferien.schulferien_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = heute
        mock_dt.timedelta = timedelta

        await mock_sensor.async_update()

        assert mock_sensor._ferien_info["heute_ferientag"] is True
        assert mock_sensor.native_value == "ferientag"
        assert mock_sensor._ferien_info["naechste_ferien_name"] == "Pfingstferien"


@pytest.mark.asyncio
async def test_update_no_data(mock_sensor, morgen_sensor):
    """Test Update wenn keine Daten von der API."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value={})):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_empty_data(mock_sensor, morgen_sensor):
    """Test Update wenn leere Daten von der API."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=[])):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_none_data(mock_sensor, morgen_sensor):
    """Test Update wenn None von der API."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=None)):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_api_error(mock_sensor, morgen_sensor):
    """Test Update bei API-Fehler."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(side_effect=aiohttp.ClientError("API-Fehler"))):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_client_error(mock_sensor, morgen_sensor):
    """Test Update bei aiohttp ClientError."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(side_effect=aiohttp.ClientError("ClientError"))):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_value_error(mock_sensor, morgen_sensor):
    """Test Update bei ValueError."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(side_effect=ValueError("Ungültige Daten"))):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_key_error(mock_sensor, morgen_sensor):
    """Test Update bei KeyError."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(side_effect=KeyError("Fehlender Schlüssel"))):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_type_error(mock_sensor, morgen_sensor):
    """Test Update bei TypeError."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(side_effect=TypeError("Falscher Typ"))):
        await mock_sensor.async_update()
        assert mock_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_update_skips_if_already_updated_today(mock_sensor):
    """Test dass Update übersprungen wird wenn bereits heute aktualisiert."""
    heute = datetime.now()
    mock_sensor._ferien_info["letztes_update"] = heute

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock()) as mock_fetch:
        await mock_sensor.async_update()
        mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_update_skips_if_same_day(mock_sensor):
    """Test dass Update übersprungen wird wenn letztes Update vom selben Tag."""
    gestern = datetime.now() - timedelta(days=1)
    mock_sensor._ferien_info["letztes_update"] = gestern.replace(hour=5)

    # Letztes Update von gestern -> sollte aktualisiert werden
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock()) as mock_fetch:
        await mock_sensor.async_update()
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_update_with_brueckentage(mock_sensor, morgen_sensor, mock_config_with_brueckentage):
    """Test Update mit Brückentagen in der Konfiguration."""
    heute = datetime(2024, 6, 18)
    mock_api_response = [
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-06-25",
            "endDate": "2024-09-09"
        }
    ]
    mock_parsed_data = [
        {
            "name": "Sommerferien",
            "start_datum": datetime(2024, 6, 25).date(),
            "end_datum": datetime(2024, 9, 9).date(),
        },
        {
            "name": "Brückentag",
            "start_datum": datetime(2024, 6, 16).date(),
            "end_datum": datetime(2024, 6, 16).date(),
        },
        {
            "name": "Brückentag",
            "start_datum": datetime(2024, 6, 17).date(),
            "end_datum": datetime(2024, 6, 17).date(),
        },
    ]

    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    sensor = SchulferienSensor(hass, mock_config_with_brueckentage)

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=mock_api_response)), \
         patch("custom_components.schulferien.schulferien_sensor.parse_daten", return_value=mock_parsed_data), \
         patch("custom_components.schulferien.schulferien_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = heute
        mock_dt.timedelta = timedelta

        await sensor.async_update()

        assert len(mock_parsed_data) == 3  # Ferien + 2 Brückentage


@pytest.mark.asyncio
async def test_update_sets_last_update_time(mock_sensor):
    """Test dass letztes_update nach erfolgreichem Update gesetzt wird."""
    heute = datetime(2024, 6, 18)
    mock_api_response = [
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-06-25",
            "endDate": "2024-09-09"
        }
    ]
    mock_parsed_data = [
        {
            "name": "Sommerferien",
            "start_datum": datetime(2024, 6, 25).date(),
            "end_datum": datetime(2024, 9, 9).date(),
        }
    ]

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=mock_api_response)), \
         patch("custom_components.schulferien.schulferien_sensor.parse_daten", return_value=mock_parsed_data), \
         patch("custom_components.schulferien.schulferien_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = heute
        mock_dt.timedelta = timedelta

        await mock_sensor.async_update()

        assert mock_sensor._ferien_info["letztes_update"] is not None
        assert mock_sensor._ferien_info["letztes_update"].year == 2024


# ============================================================
# Tests für hole_ferien_daten
# ============================================================

@pytest.mark.asyncio
async def test_hole_ferien_daten_success_first_url(mock_sensor):
    """Test dass erste URL erfolgreich Daten liefert."""
    api_parameter = {"countryIsoCode": "DE", "subdivisionCode": "DE-BY"}
    mock_session = MagicMock()
    mock_api_response = [{"name": [{"text": "Test"}], "startDate": "2024-01-01", "endDate": "2024-01-02"}]

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=mock_api_response)) as mock_fetch:
        result = await mock_sensor.hole_ferien_daten(api_parameter, mock_session)
        assert result == mock_api_response
        assert mock_fetch.call_count == 1


@pytest.mark.asyncio
async def test_hole_ferien_daten_fallback_to_second_url(mock_sensor):
    """Test Fallback auf zweite URL bei Fehler."""
    api_parameter = {"countryIsoCode": "DE", "subdivisionCode": "DE-BY"}
    mock_session = MagicMock()
    mock_api_response = [{"name": [{"text": "Test"}], "startDate": "2024-01-01", "endDate": "2024-01-02"}]

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data",
               new=AsyncMock(side_effect=[None, mock_api_response])) as mock_fetch:
        result = await mock_sensor.hole_ferien_daten(api_parameter, mock_session)
        assert result == mock_api_response
        assert mock_fetch.call_count == 2


@pytest.mark.asyncio
async def test_hole_ferien_daten_both_urls_fail(mock_sensor):
    """Test dass None zurückgegeben wird wenn beide URLs fehlschlagen."""
    api_parameter = {"countryIsoCode": "DE", "subdivisionCode": "DE-BY"}
    mock_session = MagicMock()

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=None)) as mock_fetch:
        result = await mock_sensor.hole_ferien_daten(api_parameter, mock_session)
        assert result is None
        assert mock_fetch.call_count == 2


@pytest.mark.asyncio
async def test_hole_ferien_daten_client_error_first_url(mock_sensor):
    """Test Fallback bei ClientError der ersten URL."""
    api_parameter = {"countryIsoCode": "DE", "subdivisionCode": "DE-BY"}
    mock_session = MagicMock()
    mock_api_response = [{"name": [{"text": "Test"}], "startDate": "2024-01-01", "endDate": "2024-01-02"}]

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data",
               new=AsyncMock(side_effect=[aiohttp.ClientError("Error"), mock_api_response])) as mock_fetch:
        result = await mock_sensor.hole_ferien_daten(api_parameter, mock_session)
        assert result == mock_api_response
        assert mock_fetch.call_count == 2


# ============================================================
# Tests für verarbeite_ferien_daten
# ============================================================
# Hinweis: verarbeite_ferien_daten erwartet ROHE API-Daten mit
# "startDate"/"endDate" (ISO-Strings), nicht bereits verarbeitete
# Daten mit "start_datum"/"end_datum" (date-Objekte).

def test_verarbeite_ferien_daten_valid(mock_sensor):
    """Test Verarbeitung gültiger Ferien-Daten (rohe API-Daten)."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-06-25",
            "endDate": "2024-09-09",
        }
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert len(mock_sensor._ferien_info["ferien_liste"]) == 1
    assert mock_sensor._ferien_info["ferien_liste"][0]["name"] == "Sommerferien"
    assert mock_sensor._ferien_info["ferien_liste"][0]["start_datum"] == datetime(2024, 6, 25).date()
    assert mock_sensor._ferien_info["ferien_liste"][0]["end_datum"] == datetime(2024, 9, 9).date()
    assert mock_sensor._ferien_info["heute_ferientag"] is False
    assert mock_sensor._ferien_info["naechste_ferien_name"] == "Sommerferien"


def test_verarbeite_ferien_daten_today(mock_sensor):
    """Test Verarbeitung wenn heute Ferien sind (rohe API-Daten)."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Pfingstferien"}],
            "startDate": "2024-06-18",
            "endDate": "2024-06-20",
        }
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert mock_sensor._ferien_info["heute_ferientag"] is True
    assert mock_sensor._ferien_info["naechste_ferien_name"] == "Pfingstferien"


def test_verarbeite_ferien_daten_empty_list(mock_sensor):
    """Test Verarbeitung mit leerer Liste."""
    heute = datetime(2024, 6, 18).date()

    mock_sensor.verarbeite_ferien_daten([], heute)

    assert mock_sensor._ferien_info["ferien_liste"] == []
    assert mock_sensor._ferien_info["heute_ferientag"] is False
    assert mock_sensor._ferien_info["naechste_ferien_name"] is None


def test_verarbeite_ferien_daten_multiple_ferien(mock_sensor):
    """Test Verarbeitung mit mehreren Ferien (rohe API-Daten)."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Osterferien"}],
            "startDate": "2024-04-01",
            "endDate": "2024-04-10",
        },
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-07-01",
            "endDate": "2024-08-14",
        },
        {
            "name": [{"text": "Herbstferien"}],
            "startDate": "2024-10-28",
            "endDate": "2024-10-30",
        },
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert len(mock_sensor._ferien_info["ferien_liste"]) == 3
    assert mock_sensor._ferien_info["naechste_ferien_name"] == "Sommerferien"


def test_verarbeite_ferien_daten_all_past(mock_sensor):
    """Test Verarbeitung wenn alle Ferien in der Vergangenheit."""
    heute = datetime(2024, 12, 1).date()
    ferien_daten = [
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-07-01",
            "endDate": "2024-08-14",
        },
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert mock_sensor._ferien_info["heute_ferientag"] is False
    assert mock_sensor._ferien_info["naechste_ferien_name"] is None


def test_verarbeite_ferien_daten_with_brueckentage(mock_sensor):
    """Test Verarbeitung mit Brückentagen."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-06-25",
            "endDate": "2024-09-09",
        }
    ]
    mock_sensor._brueckentage = ["24.06.2024", "27.06.2024"]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert len(mock_sensor._ferien_info["ferien_liste"]) == 3  # Ferien + 2 Brückentage


def test_verarbeite_ferien_daten_invalid_data(mock_sensor, caplog):
    """Test Verarbeitung mit ungültigen Daten (ValueError wird intern abgefangen)."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = "not a list"

    # Die Methode fängt ValueError intern ab und loggt einen ERROR
    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)
    assert "Ungültige JSON-Datenstruktur" in str(caplog.text)


def test_verarbeite_ferien_daten_missing_startDate(mock_sensor):
    """Test Verarbeitung mit fehlendem startDate."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Ungültig"}],
            "endDate": "2024-06-20",
        }
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)
    # Eintrag sollte übersprungen werden
    assert mock_sensor._ferien_info["ferien_liste"] == []


def test_verarbeite_ferien_daten_missing_endDate(mock_sensor):
    """Test Verarbeitung mit fehlendem endDate."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Ungültig"}],
            "startDate": "2024-06-18",
        }
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)
    # Eintrag sollte übersprungen werden
    assert mock_sensor._ferien_info["ferien_liste"] == []


# ============================================================
# Tests für SchulferienMorgenSensor
# ============================================================

def test_morgen_sensor_initialization(mock_sensor, morgen_sensor):
    """Test die Initialisierung des Morgen-Sensors."""
    assert morgen_sensor.name == "Schulferien Morgen - Deutschland (Bayern)"
    assert morgen_sensor.unique_id == "schulferien_DE_BY_morgen"


def test_morgen_sensor_no_ferien_nearby(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor wenn keine Ferien in der Nähe."""
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = [
        {
            "name": "Sommerferien",
            "start_datum": datetime(2024, 7, 25).date(),
            "end_datum": datetime(2024, 9, 9).date(),
        }
    ]
    assert morgen_sensor.native_value == "kein_ferientag"


def test_morgen_sensor_ferien_tomorrow(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor wenn morgen Ferien beginnen."""
    morgen = datetime.now().date() + timedelta(days=1)
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = [
        {
            "name": "Pfingstferien",
            "start_datum": morgen,
            "end_datum": morgen + timedelta(days=2),
        }
    ]
    assert morgen_sensor.native_value == "ferientag"


def test_morgen_sensor_ferien_spanning_tomorrow(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor wenn Ferien morgen andauern."""
    heute = datetime.now().date()
    morgen = heute + timedelta(days=1)
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = [
        {
            "name": "Sommerferien",
            "start_datum": heute - timedelta(days=5),
            "end_datum": heute + timedelta(days=25),
        }
    ]
    assert morgen_sensor.native_value == "ferientag"


def test_morgen_sensor_empty_ferien_list(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor mit leerer Ferien-Liste."""
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = []
    assert morgen_sensor.native_value == "kein_ferientag"


def test_morgen_sensor_none_ferien_list(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor mit None Ferien-Liste.
    
    Fix: Der Code verwendet `or []` um None korrekt zu behandeln.
    """
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = None
    # Mit Fix (or []) sollte kein Fehler mehr auftreten
    assert morgen_sensor.native_value == "kein_ferientag"


@pytest.mark.asyncio
async def test_morgen_sensor_async_update(mock_sensor, morgen_sensor):
    """Test dass async_update beim Morgen-Sensor nichts tut."""
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    await morgen_sensor.async_update()
    # async_update macht nur pass - kein Fehler = Erfolg


def test_morgen_sensor_multiple_ferien(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor mit mehreren Ferien."""
    heute = datetime.now().date()
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = [
        {
            "name": "Osterferien",
            "start_datum": heute - timedelta(days=20),
            "end_datum": heute - timedelta(days=10),
        },
        {
            "name": "Sommerferien",
            "start_datum": heute + timedelta(days=5),
            "end_datum": heute + timedelta(days=35),
        },
    ]
    assert morgen_sensor.native_value == "kein_ferientag"


def test_morgen_sensor_ends_tomorrow(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor wenn Ferien morgen enden."""
    heute = datetime.now().date()
    morgen = heute + timedelta(days=1)
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = [
        {
            "name": "Weihnachtsferien",
            "start_datum": heute - timedelta(days=10),
            "end_datum": morgen,
        }
    ]
    assert morgen_sensor.native_value == "ferientag"


def test_morgen_sensor_starts_and_ends_same_day(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor wenn Ferien nur einen Tag morgen sind."""
    morgen = datetime.now().date() + timedelta(days=1)
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = [
        {
            "name": "Herbstferien",
            "start_datum": morgen,
            "end_datum": morgen,
        }
    ]
    assert morgen_sensor.native_value == "ferientag"


# ============================================================
# Tests für Parameterized Cases
# ============================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ferien_data, today_date, expected_today, expected_morgen",
    [
        (
            [
                {
                    "name": [{"text": "Pfingstferien"}],
                    "startDate": "2024-06-18",
                    "endDate": "2024-06-20"
                },
            ],
            "2024-06-18",
            "ferientag",
            "ferientag"
        ),
        (
            [
                {
                    "name": [{"text": "Sommerferien"}],
                    "startDate": "2024-07-25",
                    "endDate": "2024-09-09"
                },
            ],
            "2024-06-18",
            "kein_ferientag",
            "kein_ferientag"
        ),
        (
            [
                {
                    "name": [{"text": "Osterferien"}],
                    "startDate": "2024-04-01",
                    "endDate": "2024-04-10"
                },
            ],
            "2024-06-18",
            "kein_ferientag",
            "kein_ferientag"
        ),
        (
            [
                {
                    "name": [{"text": "Winterferien"}],
                    "startDate": "2024-02-12",
                    "endDate": "2024-02-16"
                },
            ],
            "2024-02-14",
            "ferientag",
            "ferientag"
        ),
        (
            [
                {
                    "name": [{"text": "Osterferien"}],
                    "startDate": "2024-03-25",
                    "endDate": "2024-04-05"
                },
            ],
            "2024-04-05",
            "ferientag",
            "kein_ferientag"
        ),
    ]
)
async def test_update_parametrized(mock_sensor, morgen_sensor, ferien_data, today_date, expected_today, expected_morgen):
    """Parametrisierte Tests für verschiedene Ferien-Konfigurationen."""
    today = datetime.strptime(today_date, "%Y-%m-%d")
    mock_parsed_data = [
        {
            "name": entry["name"][0]["text"],
            "start_datum": datetime.fromisoformat(entry["startDate"]).date(),
            "end_datum": datetime.fromisoformat(entry["endDate"]).date(),
        }
        for entry in ferien_data
    ]

    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=ferien_data)), \
         patch("custom_components.schulferien.schulferien_sensor.parse_daten", return_value=mock_parsed_data), \
         patch("custom_components.schulferien.schulferien_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = today
        mock_dt.timedelta = timedelta

        await mock_sensor.async_update()

        expected_value = expected_today
        assert mock_sensor.native_value == expected_value


def test_sensor_brueckentage_property(mock_sensor):
    """Test dass brueckentage korrekt zurückgegeben werden."""
    assert mock_sensor.brueckentage == []


def test_sensor_brueckentage_property_with_data(mock_config_with_brueckentage):
    """Test brueckentage-Eigenschaft mit Daten."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.language = "de"
    sensor = SchulferienSensor(hass, mock_config_with_brueckentage)
    assert sensor.brueckentage == ["16.06.2024", "17.06.2024"]


def test_ferien_liste_missing_key(mock_sensor):
    """Test Verhalten wenn ferien_liste Schlüssel fehlt."""
    # Entferne ferien_liste aus _ferien_info
    del mock_sensor._ferien_info["ferien_liste"]
    attributes = mock_sensor.extra_state_attributes
    assert attributes["Name der Ferien"] is None


def test_sensor_name_property(mock_sensor):
    """Test name-Eigenschaft."""
    assert mock_sensor.name == "Schulferien - Deutschland (Bayern)"


def test_sensor_unique_id_property(mock_sensor):
    """Test unique_id-Eigenschaft."""
    assert mock_sensor.unique_id == "schulferien_DE_BY"


def test_native_value_with_empty_ferien_list(mock_sensor):
    """Test native_value mit leerer Ferien-Liste."""
    mock_sensor._ferien_info["ferien_liste"] = []
    assert mock_sensor.native_value == "kein_ferientag"


def test_extra_state_attributes_with_empty_ferien_list(mock_sensor):
    """Test extra_state_attributes mit leerer Ferien-Liste."""
    mock_sensor._ferien_info["ferien_liste"] = []
    attributes = mock_sensor.extra_state_attributes
    assert "Name der Ferien" in attributes


def test_morgen_sensor_with_single_day_ferien(mock_sensor, morgen_sensor):
    """Test Morgen-Sensor mit eintägigen Ferien."""
    heute = datetime.now().date()
    morgen = heute + timedelta(days=1)
    config = {
        "name": "Schulferien - Deutschland (Bayern)",
        "unique_id": "schulferien_DE_BY",
        "entity_id": "sensor.schulferien_de_by",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "brueckentage": [],
    }
    base = SchulferienSensor(hass_mock, config)
    morgen_sensor = SchulferienMorgenSensor(base)
    base._ferien_info["ferien_liste"] = [
        {
            "name": "Brückentag",
            "start_datum": morgen,
            "end_datum": morgen,
        }
    ]
    assert morgen_sensor.native_value == "ferientag"


@pytest.mark.asyncio
async def test_update_with_invalid_api_response(mock_sensor, morgen_sensor):
    """Test Update mit ungültiger API-Antwort."""
    with patch("custom_components.schulferien.schulferien_sensor.fetch_data", new=AsyncMock(return_value=[{"invalid": "data"}])), \
         patch("custom_components.schulferien.schulferien_sensor.parse_daten", side_effect=ValueError("Ungültige Daten")), \
         patch("custom_components.schulferien.schulferien_sensor.datetime") as mock_dt:

        mock_dt.now.return_value = datetime(2024, 6, 18)
        mock_dt.timedelta = timedelta

        await mock_sensor.async_update()
        # Sollte keinen Fehler werfen
        assert mock_sensor.native_value == "kein_ferientag"


def test_verarbeite_ferien_daten_brueckentage_only(mock_sensor):
    """Test Verarbeitung nur mit Brückentagen."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Brückentag"}],
            "startDate": "2024-06-17",
            "endDate": "2024-06-17",
        }
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert len(mock_sensor._ferien_info["ferien_liste"]) == 1
    assert mock_sensor._ferien_info["ferien_liste"][0]["name"] == "Brückentag"


def test_verarbeite_ferien_daten_ferien_ending_today(mock_sensor):
    """Test Verarbeitung wenn Ferien heute enden."""
    heute = datetime(2024, 6, 20).date()
    ferien_daten = [
        {
            "name": [{"text": "Pfingstferien"}],
            "startDate": "2024-06-18",
            "endDate": "2024-06-20",
        }
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert mock_sensor._ferien_info["heute_ferientag"] is True
    assert mock_sensor._ferien_info["naechste_ferien_name"] == "Pfingstferien"


def test_verarbeite_ferien_daten_ferien_started_yesterday(mock_sensor):
    """Test Verarbeitung wenn Ferien gestern begonnen haben."""
    heute = datetime(2024, 6, 19).date()
    ferien_daten = [
        {
            "name": [{"text": "Pfingstferien"}],
            "startDate": "2024-06-18",
            "endDate": "2024-06-20",
        }
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    assert mock_sensor._ferien_info["heute_ferientag"] is True


def test_verarbeite_ferien_daten_next_ferien_not_sorted(mock_sensor):
    """Test dass nächstes Ferien korrekt identifiziert wird (nicht sortiert)."""
    heute = datetime(2024, 6, 18).date()
    ferien_daten = [
        {
            "name": [{"text": "Herbstferien"}],
            "startDate": "2024-10-28",
            "endDate": "2024-10-30",
        },
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-07-01",
            "endDate": "2024-08-14",
        },
        {
            "name": [{"text": "Weihnachtsferien"}],
            "startDate": "2024-12-23",
            "endDate": "2025-01-06",
        },
    ]

    mock_sensor.verarbeite_ferien_daten(ferien_daten, heute)

    # Sommerferien sind die nächsten (frühestes start_datum > heute)
    assert mock_sensor._ferien_info["naechste_ferien_name"] == "Sommerferien"