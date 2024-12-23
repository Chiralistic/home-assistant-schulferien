"""Unit Test um die Implementierung der Brückentage zu testen."""

import unittest
from unittest.mock import mock_open, patch
from custom_components.schulferien.sensor import load_bridge_days

class TestLoadBridgeDays(unittest.TestCase):
    """Test für den Sensor für Schulferien und Brückentage."""

    async def test_load_bridge_days_success(self):
        """Testet das erfolgreiche Laden der Brückentage aus einer YAML-Datei."""
        mock_yaml = """
        bridge_days:
          - "01.01.2024"
          - "02.01.2024"
        """
        with patch("builtins.open", mock_open(read_data=mock_yaml)):
            bridge_days = await load_bridge_days("fake_path.yaml")
            self.assertEqual(bridge_days, ["01.01.2024", "02.01.2024"])

    def test_load_bridge_days_file_not_found(self):
        """Testet das Verhalten, wenn die YAML-Datei nicht gefunden wird."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            bridge_days = await load_bridge_days("fake_path.yaml")
            self.assertEqual(bridge_days, [])

    def test_load_bridge_days_yaml_error(self):
        """Testet das Verhalten bei einem YAML-Parsing-Fehler."""
        with patch("builtins.open", mock_open(read_data="invalid_yaml: [")):
            bridge_days = await load_bridge_days("fake_path.yaml")
            self.assertEqual(bridge_days, [])

if __name__ == "__main__":
    unittest.main()
