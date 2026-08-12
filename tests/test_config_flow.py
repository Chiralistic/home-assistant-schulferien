"""Unit Tests für den ConfigFlow der Schulferien-Integration."""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import voluptuous as vol
from custom_components.schulferien.config_flow import SchulferienFlowHandler


# ============================================================
# Hilfsfunktion: aiohttp-Response-Kontextmanager mocken
# ============================================================

def _make_response_mock(status, json_data=None, text_str="", side_effect=None):
    """Erstellt einen gemockten HTTP-Response für async with session.get()."""
    mock_resp = MagicMock()
    mock_resp.status = status
    if side_effect is not None:
        mock_resp.json = AsyncMock(side_effect=side_effect)
    elif json_data is not None:
        mock_resp.json = AsyncMock(return_value=json_data)
    else:
        mock_resp.json = AsyncMock(return_value={})
    mock_resp.text = AsyncMock(return_value=text_str)
    return mock_resp


def _make_get_ctxmock(status, json_data=None, text_str="", side_effect=None):
    """Erstellt einen gemockten AsyncContextManager für session.get()."""
    mock_resp = _make_response_mock(status, json_data, text_str, side_effect)

    async def mock_aenter():
        return mock_resp

    async def mock_aexit(_exc_type, _exc_val, _exc_tb):
        pass

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(side_effect=mock_aenter)
    mock_ctx.__aexit__ = AsyncMock(side_effect=mock_aexit)
    return mock_ctx


def _make_session_ctxmock(get_ctx):
    """Erstellt einen gemockten ClientSession-Kontextmanager."""
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=get_ctx)

    async def mock_aenter():
        return mock_session

    async def mock_aexit(_exc_type, _exc_val, _exc_tb):
        pass

    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(side_effect=mock_aenter)
    mock_session_ctx.__aexit__ = AsyncMock(side_effect=mock_aexit)
    return mock_session_ctx


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    ha = MagicMock()
    ha.config.language = "de"
    return ha


@pytest.fixture
def config_flow(hass):
    """Fixture für die Erstellung eines ConfigFlow-Handlers."""
    flow = SchulferienFlowHandler()
    flow.hass = hass
    return flow


# ============================================================
# Tests für __init__
# ============================================================

def test_init_defaults():
    """Test dass Initialisierung Standardwerte setzt."""
    flow = SchulferienFlowHandler()
    assert flow.language_iso_code == "DE"
    assert flow.supported_countries == {}
    assert not flow.supported_regions


# ============================================================
# Tests für _get_hass_language
# ============================================================

def test_get_hass_language_de(config_flow, hass):
    """Test Sprachcode für Deutsch."""
    hass.config.language = "de"
    result = config_flow._get_hass_language(hass)
    assert result == "DE"


def test_get_hass_language_en(config_flow, hass):
    """Test Sprachcode für Englisch."""
    hass.config.language = "en"
    result = config_flow._get_hass_language(hass)
    assert result == "EN"


def test_get_hass_language_french(config_flow, hass):
    """Test Sprachcode für Französisch."""
    hass.config.language = "fr"
    result = config_flow._get_hass_language(hass)
    assert result == "FR"


def test_get_hass_language_long_code(config_flow, hass):
    """Test dass nur die ersten 2 Zeichen verwendet werden."""
    hass.config.language = "de-DE"
    result = config_flow._get_hass_language(hass)
    assert result == "DE"


def test_get_hass_language_single_char(config_flow, hass):
    """Test bei einzeichen Sprachcode."""
    hass.config.language = "d"
    result = config_flow._get_hass_language(hass)
    assert result == "D"


def test_get_hass_language_empty(config_flow, hass):
    """Test bei leerem Sprachcode."""
    hass.config.language = ""
    result = config_flow._get_hass_language(hass)
    assert result == ""


# ============================================================
# Tests für _fetch_supported_countries
# ============================================================

@pytest.mark.asyncio
async def test_fetch_supported_countries_success(config_flow):
    """Test erfolgreiches Laden der Länderliste."""
    mock_response = [{
        "isoCode": "DE",
        "name": [
            {"text": "Deutschland", "language": "DE"},
            {"text": "Germany", "language": "EN"},
        ]
    }, {
        "isoCode": "AT",
        "name": [
            {"text": "Österreich", "language": "DE"},
        ]
    }]

    get_ctx = _make_get_ctxmock(200, mock_response)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_countries()

    assert result == {"DE": "Deutschland", "AT": "Österreich"}
    assert config_flow.supported_countries == {"DE": "Deutschland", "AT": "Österreich"}


@pytest.mark.asyncio
async def test_fetch_supported_countries_fallback_iso(config_flow):
    """Test Fallback wenn Sprache nicht gefunden."""
    mock_response = [{
        "isoCode": "DE",
        "name": [
            {"text": "Deutschland", "language": "FR"},
        ]
    }]

    get_ctx = _make_get_ctxmock(200, mock_response)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_countries()

    assert result == {"DE": "DE"}


@pytest.mark.asyncio
async def test_fetch_supported_countries_http_error(config_flow):
    """Test bei HTTP-Fehler."""
    get_ctx = _make_get_ctxmock(500)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_countries()

    assert result == {}


@pytest.mark.asyncio
async def test_fetch_supported_countries_json_error(config_flow):
    """Test bei ungültigem JSON."""
    get_ctx = _make_get_ctxmock(200, side_effect=ValueError("Invalid JSON"))
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_countries()

    assert result == {}


@pytest.mark.asyncio
async def test_fetch_supported_countries_missing_name(config_flow):
    """Test dass Einträge ohne 'name' ignoriert werden."""
    mock_response = [{
        "isoCode": "DE",
        "name": [
            {"text": "Deutschland", "language": "DE"},
        ]
    }, {
        "isoCode": "XX",
    }]

    get_ctx = _make_get_ctxmock(200, mock_response)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_countries()

    assert result == {"DE": "Deutschland"}
    assert "XX" not in result


@pytest.mark.asyncio
async def test_fetch_supported_countries_empty_list(config_flow):
    """Test bei leerer API-Antwort."""
    get_ctx = _make_get_ctxmock(200, [])
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_countries()

    assert result == {}


@pytest.mark.asyncio
async def test_fetch_supported_countries_type_error(config_flow):
    """Test bei TypeError (z.B. countries_data ist None)."""
    get_ctx = _make_get_ctxmock(200, None)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_countries()

    assert result == {}


# ============================================================
# Tests für _fetch_supported_regions
# ============================================================

@pytest.mark.asyncio
async def test_fetch_supported_regions_success(config_flow):
    """Test erfolgreiches Laden der Regionenliste."""
    mock_response = [{
        "code": "DE-BY",
        "name": [
            {"text": "Bayern", "language": "DE"},
        ]
    }, {
        "code": "DE-BE",
        "name": [
            {"text": "Berlin", "language": "DE"},
        ]
    }]

    get_ctx = _make_get_ctxmock(200, mock_response)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_regions("DE")

    assert result == {"DE-BY": "Bayern", "DE-BE": "Berlin"}


@pytest.mark.asyncio
async def test_fetch_supported_regions_fallback_code(config_flow):
    """Test Fallback wenn Regionsname nicht gefunden."""
    mock_response = [{
        "code": "DE-BY",
        "name": [
            {"text": "Bayern", "language": "FR"},
        ]
    }]

    get_ctx = _make_get_ctxmock(200, mock_response)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_regions("DE")

    assert result == {"DE-BY": "DE-BY"}


@pytest.mark.asyncio
async def test_fetch_supported_regions_http_error(config_flow):
    """Test bei HTTP-Fehler für Regionen."""
    get_ctx = _make_get_ctxmock(404)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_regions("DE")

    assert result == {}


@pytest.mark.asyncio
async def test_fetch_supported_regions_json_error(config_flow):
    """Test bei ungültigem JSON für Regionen."""
    get_ctx = _make_get_ctxmock(200, side_effect=ValueError("Invalid JSON"))
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_regions("DE")

    assert result == {}


@pytest.mark.asyncio
async def test_fetch_supported_regions_empty_list(config_flow):
    """Test bei leerer Regionenliste."""
    get_ctx = _make_get_ctxmock(200, [])
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_regions("DE")

    assert result == {}


@pytest.mark.asyncio
async def test_fetch_supported_regions_missing_name_key(config_flow):
    """Test dass Regionen ohne 'name' ignoriert werden."""
    mock_response = [{
        "code": "DE-BY",
        "name": [
            {"text": "Bayern", "language": "DE"},
        ]
    }, {
        "code": "DE-BE",
    }]

    get_ctx = _make_get_ctxmock(200, mock_response)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_regions("DE")

    assert result == {"DE-BY": "Bayern"}
    assert "DE-BE" not in result


@pytest.mark.asyncio
async def test_fetch_supported_regions_different_country(config_flow):
    """Test Regionen für anderes Land."""
    mock_response = [{
        "code": "AT-4",
        "name": [
            {"text": "Oberösterreich", "language": "DE"},
        ]
    }]

    get_ctx = _make_get_ctxmock(200, mock_response)
    session_ctx = _make_session_ctxmock(get_ctx)

    with patch("aiohttp.ClientSession", return_value=session_ctx):
        result = await config_flow._fetch_supported_regions("AT")

    assert result == {"AT-4": "Oberösterreich"}


# ============================================================
# Tests für async_step_user
# ============================================================

@pytest.mark.asyncio
async def test_user_step_no_input_shows_form(config_flow):
    """Test dass Formular angezeigt wird wenn keine Eingabe."""
    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={"DE": "Deutschland", "AT": "Österreich"})
    ):
        result = await config_flow.async_step_user()

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "errors" not in result or result.get("errors") == {}


@pytest.mark.asyncio
async def test_user_step_no_countries_aborts(config_flow):
    """Test dass Abbruch bei keinen verfügbaren Ländern."""
    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={})
    ):
        result = await config_flow.async_step_user()

    assert result["type"] == "abort"
    assert result["reason"] == "no_countries_available"


@pytest.mark.asyncio
async def test_user_step_valid_input_proceeds_to_region(config_flow):
    """Test dass nach gültiger Eingabe Regions-Formular angezeigt wird."""
    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={"DE": "Deutschland"})
    ), patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={"DE-BY": "Bayern"})
    ):
        result = await config_flow.async_step_user({"country": "DE"})

    # async_step_user ruft async_step_region auf, das kein user_input bekommt → zeigt Formular
    assert result["type"] == "form"
    assert result["step_id"] == "region"
    assert config_flow.selected_country == "DE"


@pytest.mark.asyncio
async def test_user_step_sets_language(config_flow):
    """Test dass Sprachcode beim Aufruf gesetzt wird."""
    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={"DE": "Deutschland"})
    ):
        await config_flow.async_step_user()

    assert config_flow.language_iso_code == "DE"


# ============================================================
# Tests für async_step_region
# ============================================================

@pytest.mark.asyncio
async def test_region_step_missing_country_aborts(config_flow):
    """Test dass Abbruch wenn kein Land ausgewählt."""
    result = await config_flow.async_step_region()

    assert result["type"] == "abort"
    assert result["reason"] == "missing_country"


@pytest.mark.asyncio
async def test_region_step_no_input_shows_form(config_flow):
    """Test dass Regions-Formular angezeigt wird."""
    config_flow.selected_country = "DE"

    with patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={"DE-BY": "Bayern", "DE-BE": "Berlin"})
    ):
        result = await config_flow.async_step_region()

    assert result["type"] == "form"
    assert result["step_id"] == "region"


@pytest.mark.asyncio
async def test_region_step_no_regions_uses_default(config_flow):
    """Test dass Standardregion verwendet wird wenn keine verfügbar."""
    config_flow.selected_country = "XX"
    config_flow.supported_countries = {"XX": "Unbekannt"}

    with patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={})
    ):
        result = await config_flow.async_step_region()

    assert result["type"] == "form"
    assert result["step_id"] == "region"
    # Das Formular verwendet vol.In(regions), wenn regions={"DE-NS": "Keine Regionen"}
    # vol.In() erstellt ein _EnumChoices-Objekt, container ist das Dict
    # data_schema ist ein Schema-Objekt, schema() gibt das interne Dict zurück
    schema_dict = (
        result["data_schema"].schema
        if hasattr(result["data_schema"], "schema")
        else result["data_schema"]
    )
    # Den Key mit vol.Required("region") finden
    region_key = None
    for key in schema_dict.keys():
        if isinstance(key, vol.Required):
            region_key = key
            break
    assert region_key is not None
    # schema.container ist das Dict das an vol.In übergeben wurde
    assert hasattr(schema_dict[region_key], "container")


@pytest.mark.asyncio
async def test_region_step_valid_input_proceeds_to_finish(config_flow):
    """Test dass nach gültiger Eingabe Eintrag erstellt wird."""
    config_flow.selected_country = "DE"
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"DE": {"DE-BY": "Bayern"}}

    # Patch _fetch_supported_regions damit kein echter Socket verwendet wird
    with patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={"DE-BY": "Bayern"})
    ), patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        result = await config_flow.async_step_region({"region": "DE-BY"})

    assert result["type"] == "create_entry"
    assert config_flow.selected_region == "DE-BY"


@pytest.mark.asyncio
async def test_region_step_valid_input_with_multiple_regions(config_flow):
    """Test dass nach gültiger Eingabe mit mehreren Regionen Eintrag erstellt wird."""
    config_flow.selected_country = "DE"
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"DE": {"DE-BE": "Berlin"}}

    with patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={
            "DE-BY": "Bayern",
            "DE-BE": "Berlin",
            "DE-BW": "Baden-Württemberg",
        })
    ), patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        result = await config_flow.async_step_region({"region": "DE-BE"})

    assert result["type"] == "create_entry"
    assert config_flow.selected_region == "DE-BE"


@pytest.mark.asyncio
async def test_region_step_valid_input_uses_real_api_mock(config_flow):
    """Test mit echtem aiohttp-Mock für den Regions-Aufruf."""
    config_flow.selected_country = "DE"
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"DE": {"DE-BW": "Baden-Württemberg"}}

    with patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={"DE-BW": "Baden-Württemberg"})
    ), patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        result = await config_flow.async_step_region({"region": "DE-BW"})

    assert result["type"] == "create_entry"
    assert config_flow.selected_region == "DE-BW"


@pytest.mark.asyncio
async def test_region_step_preserves_language(config_flow):
    """Test dass Sprachcode über Regions-Schritt erhalten bleibt."""
    config_flow.language_iso_code = "DE"
    config_flow.selected_country = "DE"

    with patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={"DE-BY": "Bayern"})
    ):
        await config_flow.async_step_region({"region": "DE-BY"})

    assert config_flow.language_iso_code == "DE"


# ============================================================
# Tests für async_step_finish
# ============================================================

@pytest.mark.asyncio
async def test_finish_step_missing_attributes_aborts(config_flow):
    """Test dass Abbruch wenn Attribute fehlen."""
    result = await config_flow.async_step_finish()

    assert result["type"] == "abort"
    assert result["reason"] == "incomplete_configuration"


@pytest.mark.asyncio
async def test_finish_step_missing_region_aborts(config_flow):
    """Test dass Abbruch wenn selected_region Attribut fehlt."""
    config_flow.selected_country = "DE"
    if hasattr(config_flow, "selected_region"):
        delattr(config_flow, "selected_region")
    result = await config_flow.async_step_finish()

    assert result["type"] == "abort"
    assert result["reason"] == "incomplete_configuration"


@pytest.mark.asyncio
async def test_finish_step_success_creates_entry(config_flow):
    """Test dass Eintrag bei erfolgreicher Konfiguration erstellt wird."""
    config_flow.selected_country = "DE"
    config_flow.selected_region = "DE-BY"
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"DE": {"DE-BY": "Bayern"}}

    with patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        result = await config_flow.async_step_finish()

    assert result["type"] == "create_entry"
    call_kwargs = mock_create.call_args[1]
    assert "Deutschland" in call_kwargs["title"]
    assert "Bayern" in call_kwargs["title"]


@pytest.mark.asyncio
async def test_finish_step_config_data_correct(config_flow):
    """Test dass Config-Daten korrekt sind."""
    config_flow.selected_country = "DE"
    config_flow.selected_region = "DE-BE"
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"DE": {"DE-BE": "Berlin"}}

    with patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        await config_flow.async_step_finish()

    call_args = mock_create.call_args
    assert call_args[1]["data"]["land"] == "DE"
    assert call_args[1]["data"]["region"] == "DE-BE"
    assert call_args[1]["data"]["land_name"] == "Deutschland"
    assert call_args[1]["data"]["region_name"] == "Berlin"


@pytest.mark.asyncio
async def test_finish_step_fallback_region_name(config_flow):
    """Test Fallback wenn Regionsname nicht gefunden."""
    config_flow.selected_country = "DE"
    config_flow.selected_region = "DE-XX"
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"DE": {}}

    with patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        await config_flow.async_step_finish()

    call_args = mock_create.call_args
    assert call_args[1]["data"]["region_name"] == "DE-XX"


@pytest.mark.asyncio
async def test_finish_step_fallback_country_name(config_flow):
    """Test Fallback wenn Ländername nicht gefunden."""
    config_flow.selected_country = "XX"
    config_flow.selected_region = "XX-REG"
    config_flow.supported_countries = {}
    config_flow.supported_regions = {"XX": {"XX-REG": "Region"}}

    with patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        await config_flow.async_step_finish()

    call_args = mock_create.call_args
    assert call_args[1]["data"]["land_name"] == "XX"


@pytest.mark.asyncio
async def test_finish_step_missing_region_in_dict(config_flow):
    """Test Fallback wenn Region nicht im Regions-Wörterbuch."""
    config_flow.selected_country = "DE"
    config_flow.selected_region = "DE-XX"
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"AT": {"AT-1": "Burgenland"}}

    with patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        await config_flow.async_step_finish()

    call_args = mock_create.call_args
    assert call_args[1]["data"]["region_name"] == "DE-XX"


@pytest.mark.asyncio
async def test_finish_step_title_format(config_flow):
    """Test dass Titel korrekt formatiert ist."""
    config_flow.selected_country = "AT"
    config_flow.selected_region = "AT-3"
    config_flow.supported_countries = {"AT": "Österreich"}
    config_flow.supported_regions = {"AT": {"AT-3": "Steiermark"}}

    with patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}
        await config_flow.async_step_finish()

    title = mock_create.call_args[1]["title"]
    assert "Österreich" in title
    assert "Steiermark" in title


# ============================================================
# Tests für Integrationsszenarien
# ============================================================

@pytest.mark.asyncio
async def test_full_flow_user_to_finish(config_flow):
    """Test den vollständigen Konfigurationsfluss."""
    config_flow.supported_countries = {"AT": "Österreich"}
    config_flow.supported_regions = {"AT": {"AT-1": "Burgenland"}}

    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={
            "DE": "Deutschland",
            "AT": "Österreich",
            "CH": "Schweiz",
        })
    ), patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={
            "AT-1": "Burgenland",
            "AT-2": "Kärnten",
        })
    ), patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}

        # Schritt 1: Länder-Formular anzeigen
        result = await config_flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Schritt 2: Land auswählen → zeigt Regions-Formular
        result = await config_flow.async_step_user({"country": "AT"})
        assert result["type"] == "form"
        assert result["step_id"] == "region"
        assert config_flow.selected_country == "AT"

        # Schritt 3: Region auswählen → erstellt Eintrag
        result = await config_flow.async_step_region({"region": "AT-1"})
        assert result["type"] == "create_entry"
        assert config_flow.selected_region == "AT-1"

    assert "Österreich" in mock_create.call_args[1]["title"]
    assert "Burgenland" in mock_create.call_args[1]["title"]


@pytest.mark.asyncio
async def test_language_iso_code_persists(config_flow):
    """Test dass language_iso_code über Schritte hinweg erhalten bleibt."""
    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={"DE": "Deutschland"})
    ):
        await config_flow.async_step_user()

    assert config_flow.language_iso_code == "DE"


@pytest.mark.asyncio
async def test_full_flow_germany(config_flow):
    """Test vollständigen Flow für Deutschland."""
    config_flow.supported_countries = {"DE": "Deutschland"}
    config_flow.supported_regions = {"DE": {"DE-BY": "Bayern"}}

    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={"DE": "Deutschland"})
    ), patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={
            "DE-BW": "Baden-Württemberg",
            "DE-BY": "Bayern",
        })
    ), patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}

        # Schritt 1: Länder-Formular
        result = await config_flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Schritt 2: Land auswählen → zeigt Regions-Formular
        result = await config_flow.async_step_user({"country": "DE"})
        assert result["type"] == "form"
        assert result["step_id"] == "region"

        # Schritt 3: Region auswählen → erstellt Eintrag
        result = await config_flow.async_step_region({"region": "DE-BY"})
        assert result["type"] == "create_entry"

    assert "Deutschland" in mock_create.call_args[1]["title"]
    assert "Bayern" in mock_create.call_args[1]["title"]


@pytest.mark.asyncio
async def test_full_flow_switzerland(config_flow):
    """Test vollständigen Flow für die Schweiz."""
    config_flow.supported_countries = {"CH": "Schweiz"}
    config_flow.supported_regions = {"CH": {"CH-ZH": "Zürich"}}

    with patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={"CH": "Schweiz"})
    ), patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={
            "CH-ZH": "Zürich",
            "CH-BE": "Bern",
        })
    ), patch.object(config_flow, 'async_create_entry') as mock_create:
        mock_create.return_value = {"type": "create_entry"}

        # Schritt 1: Länder-Formular
        result = await config_flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Schritt 2: Land auswählen → zeigt Regions-Formular
        result = await config_flow.async_step_user({"country": "CH"})
        assert result["type"] == "form"
        assert result["step_id"] == "region"

        # Schritt 3: Region auswählen → erstellt Eintrag
        result = await config_flow.async_step_region({"region": "CH-ZH"})
        assert result["type"] == "create_entry"

    assert "Schweiz" in mock_create.call_args[1]["title"]
    assert "Zürich" in mock_create.call_args[1]["title"]


@pytest.mark.asyncio
async def test_region_step_with_empty_regions_dict(config_flow):
    """Test Regions-Schritt wenn API leeres Dictionary zurückgibt."""
    config_flow.selected_country = "DE"

    with patch.object(
        config_flow, '_fetch_supported_regions',
        new=AsyncMock(return_value={})
    ):
        result = await config_flow.async_step_region()

    assert result["type"] == "form"
    assert result["step_id"] == "region"


@pytest.mark.asyncio
async def test_user_step_preserves_language_iso_code(config_flow):
    """Test dass language_iso_code beim user_step aus HA gelesen wird."""
    config_flow.language_iso_code = "FR"

    with patch.object(
        config_flow, '_get_hass_language',
        return_value="DE"
    ), patch.object(
        config_flow, '_fetch_supported_countries',
        new=AsyncMock(return_value={"DE": "Deutschland"})
    ):
        await config_flow.async_step_user()

    assert config_flow.language_iso_code == "DE"
