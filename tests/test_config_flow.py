"""Unit Test um den config_flow zu testen."""

import unittest
from unittest.mock import patch
from homeassistant import config_entries
from custom_components.schulferien.config_flow import SchulferienConfigFlow

class TestConfigFlow(unittest.TestCase):
    def setUp(self):
        self.flow = SchulferienConfigFlow()

    @patch("custom_components.schulferien.config_flow.REGIONS", {"DE": {"BY": "Bayern"}})
    @patch("custom_components.schulferien.config_flow.COUNTRIES", {"DE": "Deutschland"})
    def test_config_flow_user_step(self):
        user_input = {"country": "DE", "region": "Bayern"}
        result = self.flow.async_show_form(
            step_id="user",
            data_schema={
                "country": "DE",
                "region": "Bayern"
            },
        )
        self.assertEqual(result.errors, {})

if __name__ == "__main__":
    unittest.main()
