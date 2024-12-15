"""Unit Test um die Ausgabe des Feiertagsensors zu testen."""

import unittest
from unittest.mock import AsyncMock, patch
from custom_components.schulferien.feiertag_sensor import FeiertagSensor

class TestFeiertagSensor(unittest.IsolatedAsyncioTestCase):
    async def test_async_update_no_holiday(self):
        mock_hass = {}
        config = {
            "name": "Feiertag",
            "unique_id": "sensor.feiertag",
            "land": "DE",
            "region": "BY",
        }
        sensor = FeiertagSensor(mock_hass, config)

        mock_session = AsyncMock()
        with patch("custom_components.schulferien.api_utils.fetch_data", AsyncMock(return_value=[])):
            await sensor.async_update(mock_session)
            self.assertEqual(sensor.state, "Kein Feiertag")

if __name__ == "__main__":
    unittest.main()
