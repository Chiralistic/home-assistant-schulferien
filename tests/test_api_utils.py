"""Unit tests for API utility functions."""

import unittest
from unittest import mock
from datetime import datetime
import aiohttp
from custom_components.schulferien.api_utils import fetch_data, parse_daten

class TestApiUtils(unittest.IsolatedAsyncioTestCase):
    """Test case for API utility functions."""

    async def test_fetch_data_success(self):
        """Test successful API data fetch."""
        # Mock API response
        mock_response = mock.Mock()
        mock_response.status = 200
        mock_response.json = mock.AsyncMock(return_value={"key": "value"})

        # Mock aiohttp session
        with mock.patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await fetch_data("https://example.com/api", {"param": "value"})
            self.assertEqual(result, {"key": "value"})

    async def test_fetch_data_timeout(self):
        """Test API fetch with timeout error."""
        with mock.patch(
            "aiohttp.ClientSession.get", side_effect=aiohttp.ClientTimeout
        ):
            result = await fetch_data("https://example.com/api", {"param": "value"})
            self.assertEqual(result, {})  # Expect empty dict on error

    async def test_fetch_data_http_error(self):
        """Test API fetch with HTTP error."""
        mock_response = mock.Mock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientError

        with mock.patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await fetch_data("https://example.com/api", {"param": "value"})
            self.assertEqual(result, {})  # Expect empty dict on error

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
