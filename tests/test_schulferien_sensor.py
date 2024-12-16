"""Unit Test um die Ausgabe des Schulferiensensors zu testen."""

import unittest
from unittest.mock import AsyncMock, patch
from custom_components.schulferien.schulferien_sensor import SchulferienSensor

class TestSchulferienSensor(unittest.IsolatedAsyncioTestCase):
    async def test_async_update_success(self):
        mock_hass = {}
        config = {
            "name": "Schulferien",
            "unique_id": "sensor.schulferien",
            "land": "DE",
            "region": "BY",
            "brueckentage": ["01.01.2024"],
        }
        sensor = SchulferienSensor(mock_hass, config)

        mock_session = AsyncMock()
        with patch("custom_components.schulferien.api_utils.fetch_data", AsyncMock(return_value=[])):
            await sensor.async_update(mock_session)
            self.assertEqual(sensor.state, "Kein Ferientag")

if __name__ == "__main__":
    unittest.main()
