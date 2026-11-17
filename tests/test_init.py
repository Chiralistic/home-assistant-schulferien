"""Unit Tests für den __init__.py der Schulferien-Integration."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from custom_components.schulferien.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Setup forwardet an alle drei Plattformen, sensor zuerst.

    Warum sensor zuerst? binary_sensor liest die Sensor-States und calendar
    die Listen der Sensor-Instanzen — beide setzen die Sensoren voraus.
    """
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Test Entry"
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    from custom_components.schulferien import async_setup_entry

    result = await async_setup_entry(mock_hass, mock_entry)

    assert result is True
    mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
        mock_entry, ["sensor", "binary_sensor", "calendar"]
    )


@pytest.mark.asyncio
async def test_async_unload_entry_success():
    """Unload entlaedt alle Plattformen und raeumt hass.data des Entries auf.

    Warum aufraeumen? Sonst hielte hass.data nach dem Entfernen des Eintrags
    weiter Referenzen auf die alten Sensor-Instanzen (Speicherleck, und ein
    Reload wuerde kurzzeitig veraltete Listen im Kalender zeigen).
    """
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Test Entry"
    mock_entry.entry_id = "abc"
    mock_hass.data = {DOMAIN: {"abc": {"schulferien": object()}, "andere": {}}}
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    from custom_components.schulferien import async_unload_entry

    result = await async_unload_entry(mock_hass, mock_entry)

    assert result is True
    mock_hass.config_entries.async_unload_platforms.assert_called_once_with(
        mock_entry, ["sensor", "binary_sensor", "calendar"]
    )
    assert "abc" not in mock_hass.data[DOMAIN]
    # Andere Instanzen (Multi-Region) bleiben unberuehrt
    assert "andere" in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_partial_failure():
    """Schlaegt das Entladen fehl, bleiben die Sensor-Referenzen erhalten.

    Warum? Die noch geladenen Plattformen (z.B. der Kalender) brauchen sie
    weiterhin — ein halb entladener Eintrag darf nicht ins Leere greifen.
    """
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Test Entry"
    mock_entry.entry_id = "abc"
    mock_hass.data = {DOMAIN: {"abc": {"schulferien": object()}}}
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    from custom_components.schulferien import async_unload_entry

    result = await async_unload_entry(mock_hass, mock_entry)

    assert result is False
    assert "abc" in mock_hass.data[DOMAIN]
