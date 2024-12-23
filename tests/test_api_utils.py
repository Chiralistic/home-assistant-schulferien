"""Unit tests for API utility functions."""

import unittest
from unittest import mock
from datetime import datetime
import aiohttp
from custom_components.schulferien.api_utils import fetch_data, parse_daten

class TestApiUtils(unittest.IsolatedAsyncioTestCase):
    """Test case for API utility functions."""

    @mock.patch("aiohttp.ClientSession.get", new_callable=mock.AsyncMock)
    async def test_fetch_data_success(self, mock_get):
        """Test API fetch with HTTP error."""
        mock_get.return_value.__aenter__.return_value = mock.AsyncMock(
            status=200, json=mock.AsyncMock(return_value={"key": "value"})        )

        result = await fetch_data("https://example.com/api", {"param": "value"})
        self.assertEqual(result, {"key": "value"})

    async def test_fetch_data_timeout(self):
        """Test API fetch with timeout error."""
        mock_response = mock.AsyncMock()
        mock_response.status = 504  # Simuliere Timeout-Fehler
        mock_response.json = mock.AsyncMock(return_value={})

        with mock.patch(
            "aiohttp.ClientSession.get",
            side_effect=aiohttp.ClientTimeout,
        ):
            result = await fetch_data("https://example.com/api", {"param": "value"})
            assert result == {}  # Erwarte leere Daten bei Timeout

    @mock.patch("aiohttp.ClientSession.get", new_callable=mock.AsyncMock)
    async def test_fetch_data_http_error(self, mock_get):
        """Test API fetch with HTTP error."""
        mock_get.return_value.__aenter__.return_value.raise_for_status.side_effect = aiohttp.ClientError
        result = await fetch_data("https://example.com/api", {"param": "value"})
        self.assertEqual(result, {})

    def test_parse_daten_valid(self):
        """Test parsing valid JSON data."""
        json_data = [
            {
                "name": [{"text": "Ferien"}],
                "startDate": "2024-06-01",
                "endDate": "2024-06-15"
            }
        ]
        result = parse_daten(json_data)
        expected = [
            {
                "name": "Ferien",
                "start_datum": datetime(2024, 6, 1).date(),
                "end_datum": datetime(2024, 6, 15).date()
            }
        ]
        self.assertEqual(result, expected)

    def test_parse_daten_with_brueckentage(self):
        """Test parsing JSON data with additional brückentage."""
        json_data = [
            {
                "name": [{"text": "Ferien"}],
                "startDate": "2024-06-01",
                "endDate": "2024-06-15"
            }
        ]
        brueckentage = ["16.06.2024", "17.06.2024"]
        result = parse_daten(json_data, brueckentage)
        expected = [
            {
                "name": "Ferien",
                "start_datum": datetime(2024, 6, 1).date(),
                "end_datum": datetime(2024, 6, 15).date()
            },
            {
                "name": "Brückentag",
                "start_datum": datetime(2024, 6, 16).date(),
                "end_datum": datetime(2024, 6, 16).date()
            },
            {
                "name": "Brückentag",
                "start_datum": datetime(2024, 6, 17).date(),
                "end_datum": datetime(2024, 6, 17).date()
            },
        ]
        self.assertEqual(result, expected)

    def test_parse_daten_invalid(self):
        """Test parsing invalid JSON data."""
        with self.assertRaises(RuntimeError):
            parse_daten([{"startDate": "invalid-date"}])

    def test_parse_daten_missing_fields(self):
        """Test parsing JSON data with missing fields."""
        with self.assertRaises(RuntimeError):
            parse_daten([{"endDate": "2024-06-15"}])  # Missing startDate

if __name__ == "__main__":
    unittest.main()
