"""Unit Tests für den __init__.py der Schulferien-Integration."""

from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Testet das erfolgreiche Setup eines Config Entries."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Test Entry"
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    from custom_components.schulferien import async_setup_entry

    result = await async_setup_entry(mock_hass, mock_entry)

    assert result is True
    mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
        mock_entry, ["sensor", "binary_sensor"]
    )


@pytest.mark.asyncio
async def test_async_unload_entry_success():
    """Testet das erfolgreiche Unload eines Config Entries."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Test Entry"
    mock_hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)

    from custom_components.schulferien import async_unload_entry

    result = await async_unload_entry(mock_hass, mock_entry)

    assert result is True
    assert mock_hass.config_entries.async_forward_entry_unload.call_count == 2


@pytest.mark.asyncio
async def test_async_unload_entry_partial_failure():
    """Testet Unload wenn einer der Sensoren nicht entladen werden kann."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Test Entry"
    mock_hass.config_entries.async_forward_entry_unload = AsyncMock(
        side_effect=[True, False]
    )

    from custom_components.schulferien import async_unload_entry

    result = await async_unload_entry(mock_hass, mock_entry)

    assert result is False
