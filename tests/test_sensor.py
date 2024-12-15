"""Unit Test um die Implementierung der Brückentage zu testen."""

import unittest
from unittest.mock import mock_open, patch
from custom_components.schulferien.sensor import load_bridge_days

class TestLoadBridgeDays(unittest.TestCase):
    def test_load_bridge_days_success(self):
        mock_yaml = """
        bridge_days:
          - "01.01.2024"
          - "02.01.2024"
        """
        with patch("builtins.open", mock_open(read_data=mock_yaml)):
            bridge_days = load_bridge_days("fake_path.yaml")
            self.assertEqual(bridge_days, ["01.01.2024", "02.01.2024"])

    def test_load_bridge_days_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            bridge_days = load_bridge_days("fake_path.yaml")
            self.assertEqual(bridge_days, [])

    def test_load_bridge_days_yaml_error(self):
        with patch("builtins.open", mock_open(read_data="invalid_yaml: [")):
            bridge_days = load_bridge_days("fake_path.yaml")
            self.assertEqual(bridge_days, [])

if __name__ == "__main__":
    unittest.main()
