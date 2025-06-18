"""Unit Test um die Implementierung der Brückentage zu testen."""

from unittest.mock import mock_open, patch
import pytest
from custom_components.schulferien.sensor import load_bridge_days

@pytest.mark.asyncio
async def test_load_bridge_days_success():
    """Testet das erfolgreiche Laden der Brückentage aus einer YAML-Datei."""
    mock_yaml = """
    bridge_days:
      - "01.01.2024"
      - "02.01.2024"
    """
    with patch(
        "builtins.open", mock_open(read_data=mock_yaml)
    ), patch("yaml.safe_load", return_value={"bridge_days": ["01.01.2024", "02.01.2024"]}):
        bridge_days = await load_bridge_days("fake_path.yaml")
        assert bridge_days == ["01.01.2024", "02.01.2024"]

@pytest.mark.asyncio
async def test_load_bridge_days_file_not_found():
    """Testet das Verhalten, wenn die YAML-Datei nicht gefunden wird."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        bridge_days = await load_bridge_days("fake_path.yaml")
        assert bridge_days == []

@pytest.mark.asyncio
async def test_load_bridge_days_yaml_error():
    """Testet das Verhalten bei einem YAML-Parsing-Fehler."""
    with patch("builtins.open", mock_open(read_data="invalid_yaml: [")):
        bridge_days = await load_bridge_days("fake_path.yaml")
        assert bridge_days == []
