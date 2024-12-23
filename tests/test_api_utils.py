import asyncio
import json
import os
import unittest
from unittest import mock
from datetime import datetime, timedelta
from api_utils import load_cache, save_cache, fetch_data, parse_daten

# Constants for testing
TEST_CACHE_FILE = "test_cache.json"
CACHE_VALIDITY_DURATION = 24  # in hours

class TestApiUtils(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Set up test environment before each test."""
        self.test_data = {"key": "value"}
        self.test_cache_data = {
            "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            "data": self.test_data
        }
        # Create a temporary cache file for testing
        async with aiofiles.open(TEST_CACHE_FILE, "w", encoding="utf-8") as file:
            await file.write(json.dumps(self.test_cache_data))

    async def asyncTearDown(self):
        """Clean up after each test."""
        if os.path.exists(TEST_CACHE_FILE):
            os.remove(TEST_CACHE_FILE)

    async def test_load_cache_valid(self):
        """Test loading valid cache data."""
        result = await load_cache(TEST_CACHE_FILE)
        self.assertEqual(result, self.test_data)

    async def test_load_cache_expired(self):
        """Test loading expired cache data."""
        expired_cache_data = {
            "timestamp": (datetime.now() - timedelta(hours=CACHE_VALIDITY_DURATION + 1)).isoformat(),
            "data": self.test_data
        }
        async with aiofiles.open(TEST_CACHE_FILE, "w", encoding="utf-8") as file:
            await file.write(json.dumps(expired_cache_data))

        result = await load_cache(TEST_CACHE_FILE)
        self.assertIsNone(result)

    async def test_load_cache_invalid_json(self):
        """Test loading cache with invalid JSON."""
        async with aiofiles.open(TEST_CACHE_FILE, "w", encoding="utf-8") as file:
            await file.write("invalid json")

        result = await load_cache(TEST_CACHE_FILE)
        self.assertIsNone(result)

    async def test_save_cache(self):
        """Test saving cache data."""
        new_data = {"new_key": "new_value"}
        await save_cache(new_data, TEST_CACHE_FILE)

        async with aiofiles.open(TEST_CACHE_FILE, "r", encoding="utf-8") as file:
            content = await file.read()
            saved_cache = json.loads(content)
            self.assertEqual(saved_cache["data"], new_data)

    @mock.patch("aiohttp.ClientSession.get")
    async def test_fetch_data_from_api(self, mock_get):
        """Test fetching data from the API when no valid cache exists."""
        mock_response = mock.Mock()
        mock_response.status = 200
        mock_response.json = mock.AsyncMock(return_value=self.test_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        api_url = "https://example.com/api"
        api_params = {"param": "value"}
        
        result = await fetch_data(api_url, api_params, TEST_CACHE_FILE)
        self.assertEqual(result, self.test_data)

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

    def test_parse_daten_invalid(self):
        """Test parsing invalid JSON data."""
        with self.assertRaises(RuntimeError):
            parse_daten([{"startDate": "invalid-date"}])

if __name__ == "__main__":
    unittest.main()
