"""Unit Test für den ConfigFlow der Schulferien-Integration."""

from unittest.mock import patch
import pytest
from custom_components.schulferien.config_flow import SchulferienFlowHandler

@pytest.fixture
def mock_config_flow():
    """Fixture für die Erstellung eines ConfigFlow-Handlers."""
    return SchulferienFlowHandler()

@pytest.mark.asyncio
async def test_user_step_valid_input(mock_config_flow):
    """Testet die Benutzereingabe mit gültigen Werten."""
    # Patch die Methode async_create_entry
    with patch(
        "homeassistant.config_entries.ConfigFlow.async_create_entry"
    ) as mock_create_entry:
        # Schritt 1: Benutzerformular
        with patch.object(
            mock_config_flow, '_fetch_supported_countries', return_value={"DE": "Deutschland"}
        ):
            result = await mock_config_flow.async_step_user()
            assert result["type"] == "form"
            assert "errors" not in result

            result = await mock_config_flow.async_step_user(
                {"country": "DE"}
            )
            assert result["type"] == "form"
            assert "errors" not in result

        # Schritt 2: Regionsformular
        with patch.object(
            mock_config_flow, '_fetch_supported_regions', return_value={"BE": "Berlin"}
        ):
            result = await mock_config_flow.async_step_region()
            assert result["type"] == "form"
            assert "errors" not in result

            result = await mock_config_flow.async_step_region(
                {"region": "BE"}
            )
            assert result["type"] == "form"
            assert "errors" not in result

        # Schritt 3: Abschlussformular
        result = await mock_config_flow.async_step_finish()
        assert result["type"] == "create_entry"
        assert result["title"] == "Schulferien - Deutschland (Berlin)"
        mock_create_entry.assert_called_once()

@pytest.mark.asyncio
async def test_user_step_invalid_region(mock_config_flow):
    """Testet die Benutzereingabe mit ungültiger Region."""
    with patch.object(
        mock_config_flow, '_fetch_supported_countries', return_value={"DE": "Deutschland"}
    ):
        await mock_config_flow.async_step_user({"country": "DE"})

    with patch.object(
        mock_config_flow, '_fetch_supported_regions', return_value={"BE": "Berlin"}
    ):
        result = await mock_config_flow.async_step_region({"region": "Ungültig"})
        assert result["type"] == "form"
        assert result["errors"] == {"region": "ungültige_region"}

@pytest.mark.asyncio
async def test_finish_step_missing_input(mock_config_flow):
    """Testet das Verhalten bei fehlenden Eingabewerten."""
    result = await mock_config_flow.async_step_finish()
    assert result["type"] == "abort"
    assert result["reason"] == "incomplete_configuration"
