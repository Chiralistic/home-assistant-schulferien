"""Unit Tests für sensor.py (async_setup_entry, load_bridge_days)."""

import yaml

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.schulferien.sensor import async_setup_entry
from custom_components.schulferien.api_utils import load_bridge_days


# ============================================================
# Tests für load_bridge_days
# ============================================================

@pytest.mark.asyncio
async def test_load_bridge_days_success():
    """Test erfolgreiches Laden der Brückentage aus YAML."""
    yaml_content = """
bridge_days:
  - "01.01.2024"
  - "02.01.2024"
"""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value=yaml_content)

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        return_value={"bridge_days": ["01.01.2024", "02.01.2024"]},
    ):
        result = await load_bridge_days("fake_path.yaml")
        assert result == ["01.01.2024", "02.01.2024"]


@pytest.mark.asyncio
async def test_load_bridge_days_success_with_objects():
    """Test Laden wenn Brückentage als Objekte vorliegen."""
    yaml_content = """
bridge_days:
  - date: "2024-04-22"
    name: "Brücktag"
"""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value=yaml_content)

    bridge_days_data = [{"date": "2024-04-22", "name": "Brücktag"}]

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        return_value={"bridge_days": bridge_days_data},
    ):
        result = await load_bridge_days("fake_path.yaml")
        assert result == bridge_days_data


@pytest.mark.asyncio
async def test_load_bridge_days_empty_file():
    """Test Laden bei leerer Datei."""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value="")

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch("custom_components.schulferien.api_utils.yaml.safe_load", return_value={}):
        result = await load_bridge_days("empty_path.yaml")
        assert result == []


@pytest.mark.asyncio
async def test_load_bridge_days_file_not_found():
    """Test Verhalten wenn YAML-Datei nicht gefunden wird."""
    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open"
    ) as mock_open_fn:
        mock_open_fn.side_effect = FileNotFoundError("Datei nicht gefunden")
        result = await load_bridge_days("nonexistent.yaml")
        assert result == []


@pytest.mark.asyncio
async def test_load_bridge_days_yaml_error():
    """Test Verhalten bei YAML-Parsing-Fehler."""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value="invalid_yaml: [")

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        side_effect=yaml.YAMLError("Invalid YAML"),
    ):
        result = await load_bridge_days("invalid.yaml")
        assert result == []


@pytest.mark.asyncio
async def test_load_bridge_days_no_bridge_days_key():
    """Test wenn bridge_days Key fehlt."""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value="other_key: value")

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        return_value={"other_key": "value"},
    ):
        result = await load_bridge_days("no_key.yaml")
        assert result == []


@pytest.mark.asyncio
async def test_load_bridge_days_empty_bridge_days_list():
    """Test wenn bridge_days Liste leer ist."""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value="bridge_days: []")

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        return_value={"bridge_days": []},
    ):
        result = await load_bridge_days("empty_list.yaml")
        assert result == []


@pytest.mark.asyncio
async def test_load_bridge_days_with_null_bridge_days():
    """Test wenn bridge_days Null ist."""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value="bridge_days: null")

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        return_value={"bridge_days": None},
    ):
        result = await load_bridge_days("null.yaml")
        # bridge_days ist None, .get() gibt None zurück (nicht [])
        assert result is None


@pytest.mark.asyncio
async def test_load_bridge_days_non_list_bridge_days():
    """Test wenn bridge_days kein List ist."""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value="bridge_days: 'string'")

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        return_value={"bridge_days": "string"},
    ):
        result = await load_bridge_days("string.yaml")
        assert result == "string"


# ============================================================
# Tests für async_setup_entry
# ============================================================

@pytest.mark.asyncio
async def test_async_setup_entry_creates_all_sensors():
    """Test dass alle Sensoren erstellt werden."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }

    added_entities = []

    # sync def, da sensor.py Zeile 84: async_add_entities([...]) ohne await
    def mock_add_entities(entities):
        added_entities.extend(entities)

    mock_bridge_days = ["01.01.2024"]

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=mock_bridge_days),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    assert len(added_entities) == 4
    assert added_entities[0] == mock_schulferien_instance
    assert added_entities[1] == mock_feiertag_instance
    assert added_entities[2].__class__.__name__ == "SchulferienMorgenSensor"
    assert added_entities[3].__class__.__name__ == "FeiertagMorgenSensor"


@pytest.mark.asyncio
async def test_async_setup_entry_config_data_passed():
    """Test dass Config-Daten korrekt an Sensoren weitergegeben werden."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-HE",
        "land_name": "Deutschland",
        "region_name": "Hessen",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    mock_bridge_days = []

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=mock_bridge_days),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    # Prüfen dass SchulferienSensor mit korrekten Config erstellt wurde
    mock_schulferien.assert_called_once()
    schulferien_config = mock_schulferien.call_args[0][1]
    assert schulferien_config["land"] == "DE"
    assert schulferien_config["region"] == "DE-HE"
    assert schulferien_config["land_name"] == "Deutschland"
    assert schulferien_config["region_name"] == "Hessen"
    assert schulferien_config["brueckentage"] == []
    assert schulferien_config["name"] == "Schulferien - Deutschland (Hessen)"
    assert schulferien_config["unique_id"] == "schulferien_DE_HE"
    assert schulferien_config["entity_id"] == "sensor.schulferien_de_he"

    # Prüfen dass FeiertagSensor mit korrekten Config erstellt wurde
    mock_feiertag.assert_called_once()
    feiertag_config = mock_feiertag.call_args[0][1]
    assert feiertag_config["land"] == "DE"
    assert feiertag_config["region"] == "DE-HE"
    assert feiertag_config["land_name"] == "Deutschland"
    assert feiertag_config["region_name"] == "Hessen"
    assert feiertag_config["name"] == "Feiertag - Deutschland (Hessen)"
    assert feiertag_config["unique_id"] == "feiertag_DE_HE"
    assert feiertag_config["entity_id"] == "sensor.feiertag_de_he"


@pytest.mark.asyncio
async def test_async_setup_entry_initial_updates():
    """Test dass initiale Updates aufgerufen werden."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    mock_bridge_days = []

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=mock_bridge_days),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    # Initiale Updates sollten mit Session aufgerufen werden
    mock_schulferien_instance.async_update.assert_called_once_with(mock_session)
    mock_feiertag_instance.async_update.assert_called_once_with(mock_session)


@pytest.mark.asyncio
async def test_async_setup_entry_bridge_days_passed_to_schulferien():
    """Test dass Brückentage an den Schulferien-Sensor übergeben werden."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-NW",
        "land_name": "Deutschland",
        "region_name": "Nordrhein-Westfalen",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    mock_bridge_days = ["17.10.2024", "29.10.2024"]

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=mock_bridge_days),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    schulferien_config = mock_schulferien.call_args[0][1]
    assert schulferien_config["brueckentage"] == ["17.10.2024", "29.10.2024"]


@pytest.mark.asyncio
async def test_async_setup_entry_morning_sensors_reference_parent():
    """Test dass Morgen-Sensoren ihre Eltern-Sensoren referenzieren."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-BE",
        "land_name": "Deutschland",
        "region_name": "Berlin",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    mock_bridge_days = []

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=mock_bridge_days),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    # Der FeiertagMorgenSensor sollte den FeiertagSensor als Referenz haben
    feiertag_morgen = added_entities[3]
    assert feiertag_morgen._referenzsensor == mock_feiertag_instance


@pytest.mark.asyncio
async def test_async_setup_entry_sensor_order():
    """Test dass Sensoren in der richtigen Reihenfolge erstellt werden."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-HH",
        "land_name": "Deutschland",
        "region_name": "Hamburg",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    mock_bridge_days = []

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=mock_bridge_days),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    # Reihenfolge: Schulferien, Feiertag, SchulferienMorgen, FeiertagMorgen
    # mock_schulferien/mock_feiertag geben MagicMock zurück, also prüfen wir
    assert mock_schulferien.call_count == 1
    assert mock_feiertag.call_count == 1
    # SchulferienMorgenSensor und FeiertagMorgenSensor sind echte Klassen
    assert added_entities[2].__class__.__name__ == "SchulferienMorgenSensor"
    assert added_entities[3].__class__.__name__ == "FeiertagMorgenSensor"


@pytest.mark.asyncio
async def test_async_setup_entry_default_paths():
    """Test dass Standard-Pfade korrekt verwendet werden."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-SN",
        "land_name": "Deutschland",
        "region_name": "Sachsen",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days"
    ) as mock_load:
        mock_load.return_value = []

        with patch(
            "custom_components.schulferien.sensor.aiohttp.ClientSession"
        ) as mock_session_class, patch(
            "custom_components.schulferien.sensor.SchulferienSensor"
        ) as mock_schulferien, patch(
            "custom_components.schulferien.sensor.FeiertagSensor"
        ) as mock_feiertag:

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            mock_schulferien_instance = MagicMock()
            mock_schulferien_instance.async_update = AsyncMock()
            mock_schulferien.return_value = mock_schulferien_instance

            mock_feiertag_instance = MagicMock()
            mock_feiertag_instance.async_update = AsyncMock()
            mock_feiertag.return_value = mock_feiertag_instance

            await async_setup_entry(hass, config_entry, mock_add_entities)

    # load_bridge_days sollte mit dem korrekten Pfad aufgerufen werden
    mock_load.assert_called_once_with(
        "custom_components/schulferien/bridge_days.yaml"
    )


@pytest.mark.asyncio
async def test_async_setup_entry_schulferien_morgen_references_parent():
    """Test dass SchulferienMorgenSensor den SchulferienSensor referenziert."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-BB",
        "land_name": "Deutschland",
        "region_name": "Brandenburg",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=[]),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    # Der SchulferienMorgenSensor sollte den SchulferienSensor als Referenz haben
    schulferien_morgen = added_entities[2]
    assert schulferien_morgen._referenzsensor == mock_schulferien_instance


@pytest.mark.asyncio
async def test_async_setup_entry_with_bridge_days_objects():
    """Test dass Brückentage als Objekte korrekt übergeben werden."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-HB",
        "land_name": "Deutschland",
        "region_name": "Bremen",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    bridge_days_objects = [{"date": "2024-04-22", "name": "Brücktag"}]

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=bridge_days_objects),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    schulferien_config = mock_schulferien.call_args[0][1]
    assert schulferien_config["brueckentage"] == bridge_days_objects


@pytest.mark.asyncio
async def test_async_setup_entry_all_entity_ids():
    """Test dass alle Sensoren die korrekten unique_ids haben."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-RP",
        "land_name": "Deutschland",
        "region_name": "Rheinland-Pfalz",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=[]),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.unique_id = "schulferien_DE_RP"
        mock_schulferien_instance.entity_id = "sensor.schulferien_de_rp"
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.unique_id = "feiertag_DE_RP"
        mock_feiertag_instance.entity_id = "sensor.feiertag_de_rp"
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    assert added_entities[0].unique_id == "schulferien_DE_RP"
    assert added_entities[1].unique_id == "feiertag_DE_RP"
    assert added_entities[2].unique_id == "schulferien_DE_RP_morgen"
    assert added_entities[3].unique_id == "feiertag_DE_RP_morgen"


@pytest.mark.asyncio
async def test_async_setup_entry_session_passed_to_updates():
    """Test dass die Session an die Update-Methoden übergeben wird."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        "region": "DE-TH",
        "land_name": "Deutschland",
        "region_name": "Thüringen",
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=[]),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    # async_update sollte mit der Session aufgerufen werden
    mock_schulferien_instance.async_update.assert_called_once_with(mock_session)
    mock_feiertag_instance.async_update.assert_called_once_with(mock_session)


@pytest.mark.asyncio
async def test_async_setup_entry_missing_config_values():
    """Test Verhalten wenn Config-Werte fehlen."""
    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    config_entry = MagicMock()
    config_entry.data = {
        "land": "DE",
        # region fehlt
        "land_name": "Deutschland",
        # region_name fehlt
    }

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=[]),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien_instance = MagicMock()
        mock_schulferien_instance.async_update = AsyncMock()
        mock_schulferien.return_value = mock_schulferien_instance

        mock_feiertag_instance = MagicMock()
        mock_feiertag_instance.async_update = AsyncMock()
        mock_feiertag.return_value = mock_feiertag_instance

        await async_setup_entry(hass, config_entry, mock_add_entities)

    schulferien_config = mock_schulferien.call_args[0][1]
    assert schulferien_config["land"] == "DE"
    assert schulferien_config["region"] is None
    assert schulferien_config["region_name"] is None


# ============================================================
# Edge Case Tests
# ============================================================

@pytest.mark.asyncio
async def test_load_bridge_days_whitespace_only_file():
    """Test Laden bei whitespace-nur Datei."""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value="   \n  \n  ")

    # whitespace-only wird von yaml.safe_load als None geparst
    # content ist nicht leer (whitespace), also geht es zu yaml.safe_load
    # yaml.safe_load("   \n  \n  ") gibt None -> or {} macht daraus {}
    # {}.get("bridge_days", []) gibt []
    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch("custom_components.schulferien.api_utils.yaml.safe_load", return_value=None):
        result = await load_bridge_days("whitespace.yaml")
        assert result == []


@pytest.mark.asyncio
async def test_load_bridge_days_special_characters_in_yaml():
    """Test Laden mit Sonderzeichen im YAML."""
    yaml_content = """
bridge_days:
  - "25.12.2024 - Heiligabend"
  - "31.12.2024 - Silvester"
"""
    mock_aiofile = MagicMock()
    mock_aiofile.__aenter__ = AsyncMock(return_value=mock_aiofile)
    mock_aiofile.__aexit__ = AsyncMock(return_value=None)
    mock_aiofile.read = AsyncMock(return_value=yaml_content)

    with patch(
        "custom_components.schulferien.api_utils.aiofiles.open",
        return_value=mock_aiofile,
    ), patch(
        "custom_components.schulferien.api_utils.yaml.safe_load",
        return_value={
            "bridge_days": ["25.12.2024 - Heiligabend", "31.12.2024 - Silvester"]
        },
    ):
        result = await load_bridge_days("special.yaml")
        assert result == ["25.12.2024 - Heiligabend", "31.12.2024 - Silvester"]


@pytest.mark.asyncio
async def test_async_setup_entry_multiple_regions():
    """Test async_setup_entry mit verschiedenen Regionen."""
    regions = [
        {
            "land": "DE",
            "region": "DE-BW",
            "land_name": "Deutschland",
            "region_name": "Baden-Württemberg",
        },
        {
            "land": "DE",
            "region": "DE-BY",
            "land_name": "Deutschland",
            "region_name": "Bayern",
        },
        {
            "land": "DE",
            "region": "DE-BE",
            "land_name": "Deutschland",
            "region_name": "Berlin",
        },
    ]

    for region_data in regions:
        hass = MagicMock()
        hass.config.path = MagicMock(
            return_value="custom_components/schulferien/bridge_days.yaml"
        )

        config_entry = MagicMock()
        config_entry.data = region_data

        added_entities = []

        def make_add_entities(entities):
            def add(entities_list):
                entities.extend(entities_list)
            return add

        mock_add_entities = make_add_entities(added_entities)

        with patch(
            "custom_components.schulferien.sensor.load_bridge_days",
            new=AsyncMock(return_value=[]),
        ), patch(
            "custom_components.schulferien.sensor.aiohttp.ClientSession"
        ) as mock_session_class, patch(
            "custom_components.schulferien.sensor.SchulferienSensor"
        ) as mock_schulferien, patch(
            "custom_components.schulferien.sensor.FeiertagSensor"
        ) as mock_feiertag:

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            mock_schulferien_instance = MagicMock()
            mock_schulferien_instance.async_update = AsyncMock()
            mock_schulferien.return_value = mock_schulferien_instance

            mock_feiertag_instance = MagicMock()
            mock_feiertag_instance.async_update = AsyncMock()
            mock_feiertag.return_value = mock_feiertag_instance

            await async_setup_entry(hass, config_entry, mock_add_entities)

        assert len(added_entities) == 4
        schulferien_config = mock_schulferien.call_args[0][1]
        assert schulferien_config["region"] == region_data["region"]


@pytest.mark.asyncio
async def test_multiple_instances_different_regions():
    """Testet dass zwei Instanzen mit verschiedenen Regionen parallel laufen."""
    added_entities_instance1 = []
    added_entities_instance2 = []

    config_entry_by = MagicMock()
    config_entry_by.data = {
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }

    config_entry_bw = MagicMock()
    config_entry_bw.data = {
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }

    hass = MagicMock()
    hass.config.path = MagicMock(
        return_value="custom_components/schulferien/bridge_days.yaml"
    )

    def make_add_entities(entities):
        def add(entities_list):
            entities.extend(entities_list)
        return add

    def create_sensor_instance(hass, config):
        region = config["region"]
        region_slug = region.split("-")[-1].lower()
        mock_instance = MagicMock()
        mock_instance.async_update = AsyncMock()
        mock_instance.unique_id = f"schulferien_DE_{region_slug.upper()}"
        mock_instance.entity_id = f"sensor.schulferien_de_{region_slug}"
        return mock_instance

    def create_feiertag_instance(hass, config):
        region = config["region"]
        region_slug = region.split("-")[-1].lower()
        mock_instance = MagicMock()
        mock_instance.async_update = AsyncMock()
        mock_instance.unique_id = f"feiertag_DE_{region_slug.upper()}"
        mock_instance.entity_id = f"sensor.feiertag_de_{region_slug}"
        return mock_instance

    with patch(
        "custom_components.schulferien.sensor.load_bridge_days",
        new=AsyncMock(return_value=[]),
    ), patch(
        "custom_components.schulferien.sensor.aiohttp.ClientSession"
    ) as mock_session_class, patch(
        "custom_components.schulferien.sensor.SchulferienSensor"
    ) as mock_schulferien, patch(
        "custom_components.schulferien.sensor.FeiertagSensor"
    ) as mock_feiertag:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        mock_schulferien.side_effect = create_sensor_instance
        mock_feiertag.side_effect = create_feiertag_instance

        mock_add_entities_by = make_add_entities(added_entities_instance1)
        mock_add_entities_bw = make_add_entities(added_entities_instance2)

        await async_setup_entry(hass, config_entry_by, mock_add_entities_by)
        await async_setup_entry(hass, config_entry_bw, mock_add_entities_bw)

    assert len(added_entities_instance1) == 4
    assert len(added_entities_instance2) == 4

    schulferien_calls = mock_schulferien.call_args_list
    assert len(schulferien_calls) == 2

    region_values = [call[0][1]["region"] for call in schulferien_calls]
    assert "DE-BY" in region_values
    assert "DE-BW" in region_values

    entity_ids = []
    for entities in [added_entities_instance1, added_entities_instance2]:
        for entity in entities:
            entity_ids.append(entity.entity_id)

    assert "sensor.schulferien_de_by" in entity_ids
    assert "sensor.schulferien_de_bw" in entity_ids
    assert len(set(entity_ids)) == len(entity_ids)
