"""Unit tests for API utility functions."""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
import aiohttp
from custom_components.schulferien.api_utils import fetch_data, parse_daten


# ============================================================
# Tests für fetch_data
# ============================================================

@pytest.mark.asyncio
async def test_fetch_data_success():
    """Test API fetch with HTTP success."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={"key": "value"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_fetch_data_success_with_headers():
    """Test API fetch verifies correct headers are sent."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={"data": "test"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {"data": "test"}

    # Verify headers were passed correctly
    mock_session.get.assert_called_once()
    call_kwargs = mock_session.get.call_args
    assert call_kwargs[1]["headers"] == {"Accept": "application/json"}


@pytest.mark.asyncio
async def test_fetch_data_creates_session_when_none():
    """Test fetch_data creates its own session when none provided."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={"created": "session"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession") as MockSession:
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_response)
        mock_session_instance.close = AsyncMock()
        MockSession.return_value = mock_session_instance

        result = await fetch_data("https://example.com/api", {"param": "value"})
        assert result == {"created": "session"}
        MockSession.assert_called_once()
        mock_session_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_data_timeout():
    """Test API fetch with timeout error."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={})
    mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError("Request timed out"))
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_http_404():
    """Test API fetch with HTTP 404 error."""
    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.request_info = MagicMock()
    mock_response.request_info.url = "https://example.com/api"
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=mock_response.request_info,
        history=(),
        status=404,
        message="Not Found"
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_http_500():
    """Test API fetch with HTTP 500 error."""
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.request_info = MagicMock()
    mock_response.request_info.url = "https://example.com/api"
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=mock_response.request_info,
        history=(),
        status=500,
        message="Internal Server Error"
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_http_503():
    """Test API fetch with HTTP 503 error."""
    mock_response = MagicMock()
    mock_response.status = 503
    mock_response.request_info = MagicMock()
    mock_response.request_info.url = "https://example.com/api"
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=mock_response.request_info,
        history=(),
        status=503,
        message="Service Unavailable"
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_connection_error():
    """Test API fetch with connection error."""
    mock_session = MagicMock()
    mock_session.get.side_effect = aiohttp.ClientConnectionError("Connection failed")

    result = await fetch_data(
        "https://example.com/api", {"param": "value"}, mock_session
    )
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_general_client_error():
    """Test API fetch with general client error."""
    mock_session = MagicMock()
    mock_session.get.side_effect = aiohttp.ClientError("General client error")

    result = await fetch_data(
        "https://example.com/api", {"param": "value"}, mock_session
    )
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_invalid_json_response():
    """Test API fetch with invalid JSON response."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data(
        "https://example.com/api", {"param": "value"}, mock_session
    )
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_invalid_url():
    """Test fetch_data raises ValueError for invalid URL."""
    with pytest.raises(ValueError):
        await fetch_data("", {"param": "value"})

    with pytest.raises(ValueError):
        await fetch_data(123, {"param": "value"})


@pytest.mark.asyncio
async def test_fetch_data_passes_params_correctly():
    """Test that API parameters are passed correctly to the request."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={"received": "params"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    params = {"land": "DE", "region": "DE-BY", "validFrom": "2024-01-01"}
    await fetch_data("https://example.com/api", params, mock_session)

    # Verify the params were passed to get()
    call_args = mock_session.get.call_args
    assert call_args[1]["params"] == params


@pytest.mark.asyncio
async def test_fetch_data_session_not_closed_when_provided():
    """Test that provided session is not closed by fetch_data."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={"data": "test"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    await fetch_data("https://example.com/api", {"param": "value"}, mock_session)

    # Session close should NOT be called when session is provided externally
    mock_session.close.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_data_http_401():
    """Test API fetch with HTTP 401 Unauthorized error."""
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.request_info = MagicMock()
    mock_response.request_info.url = "https://example.com/api"
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=mock_response.request_info,
        history=(),
        status=401,
        message="Unauthorized"
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_data_http_403():
    """Test API fetch with HTTP 403 Forbidden error."""
    mock_response = MagicMock()
    mock_response.status = 403
    mock_response.request_info = MagicMock()
    mock_response.request_info.url = "https://example.com/api"
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=mock_response.request_info,
        history=(),
        status=403,
        message="Forbidden"
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    result = await fetch_data("https://example.com/api", {"param": "value"}, mock_session)
    assert result == {}


# ============================================================
# Tests für parse_daten
# ============================================================

def test_parse_daten_valid():
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
    assert result == expected


def test_parse_daten_with_brueckentage():
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
    assert result == expected


def test_parse_daten_with_feiertage_typ():
    """Test parsing JSON data with typ='feiertage'."""
    json_data = [
        {
            "name": [{"text": "Weihnachten"}],
            "startDate": "2024-12-25",
            "endDate": "2024-12-25"
        }
    ]
    result = parse_daten(json_data, typ="feiertage")
    expected = [
        {
            "name": "Weihnachten",
            "start_datum": datetime(2024, 12, 25).date(),
            "end_datum": datetime(2024, 12, 25).date()
        }
    ]
    assert result == expected


def test_parse_daten_empty_list():
    """Test parsing an empty list."""
    result = parse_daten([])
    assert result == []


def test_parse_daten_multiple_entries():
    """Test parsing multiple entries."""
    json_data = [
        {
            "name": [{"text": "Winterferien"}],
            "startDate": "2024-02-01",
            "endDate": "2024-02-09"
        },
        {
            "name": [{"text": "Osterferien"}],
            "startDate": "2024-03-25",
            "endDate": "2024-04-05"
        }
    ]
    result = parse_daten(json_data)
    assert len(result) == 2
    assert result[0]["name"] == "Winterferien"
    assert result[1]["name"] == "Osterferien"


def test_parse_daten_missing_startDate_skips_entry():
    """Test that entries without startDate are skipped, not raising error."""
    json_data = [
        {"endDate": "2024-06-15"},
        {
            "name": [{"text": "Gültige Ferien"}],
            "startDate": "2024-06-01",
            "endDate": "2024-06-10"
        }
    ]
    result = parse_daten(json_data)
    assert len(result) == 1
    assert result[0]["name"] == "Gültige Ferien"


def test_parse_daten_missing_endDate_skips_entry():
    """Test that entries without endDate are skipped, not raising error."""
    json_data = [
        {"startDate": "2024-06-01"},
        {
            "name": [{"text": "Gültige Ferien"}],
            "startDate": "2024-06-10",
            "endDate": "2024-06-20"
        }
    ]
    result = parse_daten(json_data)
    assert len(result) == 1
    assert result[0]["name"] == "Gültige Ferien"


def test_parse_daten_missing_both_dates_skips_entry():
    """Test that entries without both dates are skipped."""
    json_data = [
        {"name": [{"text": "Kein Datum"}]},
        {
            "name": [{"text": "Gültige Ferien"}],
            "startDate": "2024-06-01",
            "endDate": "2024-06-15"
        }
    ]
    result = parse_daten(json_data)
    assert len(result) == 1
    assert result[0]["name"] == "Gültige Ferien"


def test_parse_daten_invalid_json_structure():
    """Test parsing with non-list input raises ValueError."""
    with pytest.raises(ValueError, match="Ungültige JSON-Datenstruktur"):
        parse_daten("not a list")

    with pytest.raises(ValueError, match="Ungültige JSON-Datenstruktur"):
        parse_daten({"key": "value"})

    with pytest.raises(ValueError, match="Ungültige JSON-Datenstruktur"):
        parse_daten(42)


def test_parse_daten_invalid_date_format():
    """Test parsing with invalid date format raises RuntimeError."""
    json_data = [
        {
            "name": [{"text": "Ungültiges Datum"}],
            "startDate": "invalid-date",
            "endDate": "2024-06-15"
        }
    ]
    with pytest.raises(RuntimeError):
        parse_daten(json_data)


def test_parse_daten_invalid_brueckentag_format():
    """Test parsing with invalid brückentag format logs warning but continues."""
    json_data = [
        {
            "name": [{"text": "Ferien"}],
            "startDate": "2024-06-01",
            "endDate": "2024-06-15"
        }
    ]
    brueckentage = ["16.06.2024", "ungültiges-datum", "17.06.2024"]
    result = parse_daten(json_data, brueckentage)
    # Nur die gültigen Brückentage werden hinzugefügt
    assert len(result) == 3  # Ferien + 2 gültige Brückentage


def test_parse_daten_name_with_missing_text():
    """Test parsing when name text array entry is missing - raises RuntimeError."""
    json_data = [
        {
            "name": [],
            "startDate": "2024-06-01",
            "endDate": "2024-06-15"
        }
    ]
    # Die Integration wirft RuntimeError bei leerem name-Array
    with pytest.raises(RuntimeError, match="Ungültige JSON-Daten erhalten"):
        parse_daten(json_data)


def test_parse_daten_name_with_missing_first_element():
    """Test parsing when name array has the expected structure."""
    json_data = [
        {
            "name": [{"text": "Test"}],
            "startDate": "2024-06-01",
            "endDate": "2024-06-15"
        }
    ]
    result = parse_daten(json_data)
    assert result[0]["name"] == "Test"


def test_parse_daten_brueckentage_only():
    """Test parsing with only brückentage (no main data)."""
    json_data = []
    brueckentage = ["01.07.2024", "02.07.2024"]
    result = parse_daten(json_data, brueckentage)
    assert len(result) == 2
    assert result[0]["name"] == "Brückentag"
    assert result[0]["start_datum"] == datetime(2024, 7, 1).date()


def test_parse_daten_with_iso_code_in_name():
    """Test parsing when name contains ISO code information."""
    json_data = [
        {
            "name": [{"text": "Sommerferien", "isoCode": "DE"}],
            "startDate": "2024-07-25",
            "endDate": "2024-09-09"
        }
    ]
    result = parse_daten(json_data)
    assert result[0]["name"] == "Sommerferien"


def test_parse_daten_date_range_correct():
    """Test that date ranges are correctly parsed."""
    json_data = [
        {
            "name": [{"text": "Ganze Ferien"}],
            "startDate": "2024-01-01",
            "endDate": "2024-12-31"
        }
    ]
    result = parse_daten(json_data)
    assert result[0]["start_datum"] == datetime(2024, 1, 1).date()
    assert result[0]["end_datum"] == datetime(2024, 12, 31).date()


def test_parse_daten_single_day_event():
    """Test parsing a single-day event."""
    json_data = [
        {
            "name": [{"text": "Ein-Tages-Event"}],
            "startDate": "2024-06-15",
            "endDate": "2024-06-15"
        }
    ]
    result = parse_daten(json_data)
    assert len(result) == 1
    assert result[0]["start_datum"] == result[0]["end_datum"]
    assert result[0]["start_datum"] == datetime(2024, 6, 15).date()


def test_parse_daten_special_characters_in_name():
    """Test parsing names with special characters."""
    json_data = [
        {
            "name": [{"text": "Herbstferien (2024)"}],
            "startDate": "2024-10-28",
            "endDate": "2024-11-08"
        }
    ]
    result = parse_daten(json_data)
    assert result[0]["name"] == "Herbstferien (2024)"


def test_parse_daten_unicode_in_name():
    """Test parsing names with unicode characters."""
    json_data = [
        {
            "name": [{"text": "Sömmérferiëñ"}],
            "startDate": "2024-07-01",
            "endDate": "2024-07-31"
        }
    ]
    result = parse_daten(json_data)
    assert result[0]["name"] == "Sömmérferiëñ"


def test_parse_daten_long_duration():
    """Test parsing a long duration event."""
    json_data = [
        {
            "name": [{"text": "Sommerferien"}],
            "startDate": "2024-07-25",
            "endDate": "2024-09-09"
        }
    ]
    result = parse_daten(json_data)
    assert len(result) == 1
    assert result[0]["name"] == "Sommerferien"
    assert result[0]["start_datum"] == datetime(2024, 7, 25).date()
    assert result[0]["end_datum"] == datetime(2024, 9, 9).date()


def test_parse_daten_brueckentage_with_invalid_typ():
    """Test that brückentage are only added when typ=='ferien'."""
    json_data = [
        {
            "name": [{"text": "Feiertag"}],
            "startDate": "2024-12-25",
            "endDate": "2024-12-25"
        }
    ]
    brueckentage = ["26.12.2024"]
    result = parse_daten(json_data, brueckentage, typ="feiertage")
    # Brückentage werden nur bei typ="ferien" hinzugefügt
    assert len(result) == 1
    assert result[0]["name"] == "Feiertag"


def test_parse_daten_empty_name_text_value():
    """Test parsing when name text is empty string."""
    json_data = [
        {
            "name": [{"text": ""}],
            "startDate": "2024-06-01",
            "endDate": "2024-06-15"
        }
    ]
    result = parse_daten(json_data)
    # Leerer String ist ein gültiger Wert
    assert result[0]["name"] == ""


def test_parse_daten_multiple_brueckentage():
    """Test parsing with multiple consecutive brückentage."""
    json_data = [
        {
            "name": [{"text": "Ferien"}],
            "startDate": "2024-06-01",
            "endDate": "2024-06-02"
        }
    ]
    brueckentage = ["03.06.2024", "04.06.2024", "05.06.2024"]
    result = parse_daten(json_data, brueckentage)
    assert len(result) == 4  # Ferien + 3 Brückentage