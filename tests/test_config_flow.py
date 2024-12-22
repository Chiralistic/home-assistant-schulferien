"""Unit Test um den config flow zu testen."""

import pytest
from unittest.mock import patch
from homeassistant import config_entries
from custom_components.schulferien.config_flow import SchulferienFlowHandler
from custom_components.schulferien.const import DOMAIN, COUNTRIES, REGIONS


@pytest.fixture
def mock_config_flow(hass):
    """Fixture für die Erstellung eines ConfigFlow-Handlers."""
    flow = SchulferienFlowHandler()
    flow.hass = hass
    return flow


async def test_user_step_valid_input(hass, mock_config_flow):
    """Testet die Benutzereingabe mit gültigen Werten."""
    with patch("homeassistant.config_entries.ConfigEntries.async_create_entry") as mock_create_entry:
        result = await mock_config_flow.async_step_user(
            {"country": "DE", "region": "Berlin"}
        )

        assert result["type"] == "form"
        assert "errors" not in result

        result = await mock_config_flow.async_step_finish(
            {"country": "DE", "region": "BE"}
        )

        assert result["type"] == "create_entry"
        assert result["title"] == "Schulferien-Integration"
        mock_create_entry.assert_called_once()


async def test_user_step_invalid_region(hass, mock_config_flow):
    """Testet die Benutzereingabe mit ungültiger Region."""
    result = await mock_config_flow.async_step_user(
        {"country": "DE", "region": "Ungültig"}
    )

    assert result["type"] == "form"
    assert result["errors"] == {"region": "ungültige_region"}


async def test_finish_step_missing_input(hass, mock_config_flow):
    """Testet das Verhalten bei fehlenden Eingabewerten."""
    result = await mock_config_flow.async_step_finish({})
    assert result["type"] == "abort"
    assert result["reason"] == "fehlende_konfiguration"
