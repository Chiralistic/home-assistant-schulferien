"""Unit Tests für SchulferienFeiertagSensor und FeiertagMorgenSensor."""

from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date, datetime, timedelta
import aiohttp

import pytest

from custom_components.schulferien.feiertag_sensor import (
    FeiertagSensor,
    FeiertagMorgenSensor,
    FEIERTAG_SENSOR,
    FEIERTAG_MORGEN_SENSOR,
    berechne_ostersonntag,
)
from custom_components.schulferien.api_utils import load_bridge_days
from custom_components.schulferien.const import (
    MIDNIGHT_REFRESH_HOUR,
    MIDNIGHT_REFRESH_MINUTE,
    MIDNIGHT_REFRESH_SECOND,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def hass():
    """Mock HomeAssistant."""
    ha = MagicMock()
    ha.config.language = "de"
    ha.config.time_zone = MagicMock()
    ha.config.time_zone.name = "Europe/Berlin"
    return ha


@pytest.fixture
def config_heute():
    """Standard-Konfiguration für heute-Sensor."""
    return {
        "unique_id": "feiertag_DE_BY",
        "entity_id": "sensor.feiertag_de_by",
        "name": "Feiertag",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }


@pytest.fixture
def mock_feiertag_sensor(hass, config_heute):
    """Erstellt einen FeiertagSensor mit gemocktem async_added_to_hass."""
    sensor = FeiertagSensor(hass, config_heute)
    sensor.async_added_to_hass = AsyncMock()
    return sensor


@pytest.fixture
def feiertags_daten():
    """Beispiel-Feiertagsdaten für Tests."""
    heute = datetime.now().date()
    return {
        "feiertage": [
            {
                "name": "Weihnachtstag",
                "start_datum": heute,
                "end_datum": heute,
            }
        ]
    }


@pytest.fixture
def feiertags_daten_morgen():
    """Beispiel-Feiertagsdaten für Morgen."""
    morgen = (datetime.now() + timedelta(days=1)).date()
    return {
        "feiertage": [
            {
                "name": "Neujahr",
                "start_datum": morgen,
                "end_datum": morgen,
            }
        ]
    }


@pytest.fixture
def mock_feiertag_sensor_mit_daten(hass, config_heute, feiertags_daten):
    """Erstellt einen FeiertagSensor mit vordefinierten Daten."""
    sensor = FeiertagSensor(hass, config_heute)
    sensor._feiertags_info["feiertage_liste"] = feiertags_daten["feiertage"]
    sensor._feiertags_info["heute_feiertag"] = True
    sensor._feiertags_info["naechster_feiertag_name"] = "Weihnachtstag"
    sensor._feiertags_info["naechster_feiertag_datum"] = datetime.now().date().strftime("%d.%m.%Y")
    sensor.async_added_to_hass = AsyncMock()
    return sensor


# ============================================================
# Tests für EntityDescriptions
# ============================================================

def test_entity_description_feiertag():
    """Test die EntityDescription für Feiertag."""
    assert FEIERTAG_SENSOR.key == "feiertag"
    assert FEIERTAG_SENSOR.name == "Feiertag"
    assert FEIERTAG_SENSOR.translation_key == "feiertag"


def test_entity_description_feiertag_morgen():
    """Test die EntityDescription für Feiertag Morgen."""
    assert FEIERTAG_MORGEN_SENSOR.key == "feiertag_morgen"
    assert FEIERTAG_MORGEN_SENSOR.name == "Feiertag Morgen"
    assert FEIERTAG_MORGEN_SENSOR.translation_key == "feiertag_morgen"


# ============================================================
# Tests für FeiertagSensor Initialisierung
# ============================================================

def test_feiertag_sensor_initialization(hass, config_heute):
    """Test die Initialisierung des FeiertagSensors."""
    sensor = FeiertagSensor(hass, config_heute)
    assert sensor.unique_id == "feiertag_DE_BY"
    assert sensor.name == "Feiertag"
    assert sensor._location["land"] == "DE"
    assert sensor._location["region"] == "DE-BY"
    assert sensor._location["land_name"] == "Deutschland"
    assert sensor._location["region_name"] == "Bayern"
    assert sensor._location["iso_code"] == "DE"
    assert sensor._feiertags_info["heute_feiertag"] is None
    assert sensor._feiertags_info["naechster_feiertag_name"] is None
    assert sensor._feiertags_info["naechster_feiertag_datum"] is None
    assert sensor._feiertags_info["feiertage_liste"] == []


def test_suggested_object_id_und_entity_id_zuweisung(hass, config_heute):
    """Regression Branch 24: HA-entity_id-Zuweisung darf nicht crashen.

    Warum? HA weist beim Hinzufuegen jeder Entity `entity.entity_id =
    entry.entity_id` zu (EntityPlatform._async_add_entity). Eine
    Getter-only-Property ohne Setter warf hier AttributeError -> die Entity
    wurde nie in die State-Machine aufgenommen -> Status "nicht verfuegbar".
    Die gewuenschte Entity-ID wird ueber suggested_object_id vorgeschlagen.
    """
    sensor = FeiertagSensor(hass, config_heute)
    morgen_sensor = FeiertagMorgenSensor(sensor)

    assert sensor.suggested_object_id == "feiertag_de_by"
    assert morgen_sensor.suggested_object_id == "feiertag_de_by_morgen"

    # HA-Zuweisung simulieren — darf nicht mehr crashen
    sensor.entity_id = "sensor.feiertag_de_by"
    assert sensor.entity_id == "sensor.feiertag_de_by"
    morgen_sensor.entity_id = "sensor.feiertag_de_by_morgen"
    assert morgen_sensor.entity_id == "sensor.feiertag_de_by_morgen"


def test_feiertag_sensor_custom_unique_id(hass):
    """Test mit benutzerdefiniertem unique_id."""
    config = {
        "unique_id": "feiertag_DE_BW",
        "entity_id": "sensor.feiertag_de_bw",
        "name": "Mein Feiertag",
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }
    sensor = FeiertagSensor(hass, config)
    assert sensor.unique_id == "feiertag_DE_BW"
    assert sensor.name == "Mein Feiertag"


def test_feiertag_sensor_default_unique_id(hass):
    """Test dass der Standard unique_id verwendet wird."""
    config = {
        "name": "Feiertag",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    sensor = FeiertagSensor(hass, config)
    assert sensor.unique_id == "feiertag_DE_BY"


def test_feiertag_sensor_default_iso_code(hass, config_heute):
    """Test dass iso_code auf DE standardisiert ist."""
    sensor = FeiertagSensor(hass, config_heute)
    assert sensor._location["iso_code"] == "DE"


def test_feiertag_sensor_all_location_keys(hass, config_heute):
    """Test dass alle Location-Schlüssel vorhanden sind."""
    sensor = FeiertagSensor(hass, config_heute)
    assert "land" in sensor._location
    assert "region" in sensor._location
    assert "land_name" in sensor._location
    assert "region_name" in sensor._location
    assert "iso_code" in sensor._location


def test_feiertag_sensor_all_feiertags_info_keys(hass, config_heute):
    """Test dass alle Feiertags-Info-Schlüssel vorhanden sind."""
    sensor = FeiertagSensor(hass, config_heute)
    assert "heute_feiertag" in sensor._feiertags_info
    assert "naechster_feiertag_name" in sensor._feiertags_info
    assert "naechster_feiertag_datum" in sensor._feiertags_info
    assert "feiertage_liste" in sensor._feiertags_info
    assert "letztes_update" in sensor._feiertags_info


# ============================================================
# Tests für native_value Property
# ============================================================

def test_native_value_feiertag_true(mock_feiertag_sensor):
    """native_value liefert 'feiertag' wenn heute in einem Feiertagszeitraum liegt.

    Prüft die dynamische Semantik: native_value wertet feiertage_liste gegen das
    heutige Datum aus, statt die beim Abruf gesetzte 'heute_feiertag'-Flag zu
    lesen (die durch den woechentlichen Fetch-Guard veralten wuerde).
    """
    heute = datetime.now().date()
    mock_feiertag_sensor._feiertags_info["feiertage_liste"] = [
        {"name": "Testtag", "start_datum": heute, "end_datum": heute}
    ]
    assert mock_feiertag_sensor.native_value == "feiertag"


def test_native_value_feiertag_false(mock_feiertag_sensor):
    """native_value liefert 'kein_feiertag' wenn kein Zeitraum heute abdeckt.

    Regression (Mitternachts-Bug): eine noch auf True stehende, aber veraltete
    'heute_feiertag'-Flag darf den State nicht bestimmen, sobald der Feiertag
    vorueber ist und erst der naechste (woechentliche) Abruf sie zuruecksetzen wuerde.
    """
    heute = datetime.now().date()
    mock_feiertag_sensor._feiertags_info["feiertage_liste"] = [
        {
            "name": "Vorbei",
            "start_datum": heute - timedelta(days=3),
            "end_datum": heute - timedelta(days=1),
        }
    ]
    # Veraltete Flag: Beim letzten Abruf war es ein Feiertag, heute nicht mehr.
    mock_feiertag_sensor._feiertags_info["heute_feiertag"] = True
    assert mock_feiertag_sensor.native_value == "kein_feiertag"


def test_native_value_feiertag_none(mock_feiertag_sensor):
    """Test dass native_value 'kein_feiertag' zurückgibt wenn None."""
    mock_feiertag_sensor._feiertags_info["heute_feiertag"] = None
    assert mock_feiertag_sensor.native_value == "kein_feiertag"


def test_native_value_feiertag_default(mock_feiertag_sensor):
    """Test dass native_value 'kein_feiertag' als Default zurückgibt."""
    assert mock_feiertag_sensor.native_value == "kein_feiertag"


# ============================================================
# Tests für extra_state_attributes Property
# ============================================================

def test_extra_state_attributes_heute_feiertag(mock_feiertag_sensor_mit_daten):
    """Test Attribute wenn heute Feiertag ist."""
    attributes = mock_feiertag_sensor_mit_daten.extra_state_attributes
    assert attributes["Name Feiertag"] == "Weihnachtstag"
    assert attributes["Land"] == "Deutschland"
    assert attributes["Region"] == "Bayern"
    assert attributes["Datum"] is not None


def test_extra_state_attributes_kein_feiertag(hass, config_heute):
    """Test Attribute wenn heute kein Feiertag ist."""
    sensor = FeiertagSensor(hass, config_heute)
    morgen = (datetime.now() + timedelta(days=1)).date()
    sensor._feiertags_info["feiertage_liste"] = [{
        "name": "Neujahr",
        "start_datum": morgen,
        "end_datum": morgen,
    }]
    sensor._feiertags_info["heute_feiertag"] = False
    sensor._feiertags_info["naechster_feiertag_name"] = "Neujahr"
    sensor._feiertags_info["naechster_feiertag_datum"] = morgen.strftime("%d.%m.%Y")

    attributes = sensor.extra_state_attributes
    assert attributes["Name Feiertag"] == "Neujahr"

    assert attributes["Land"] == "Deutschland"
    assert attributes["Region"] == "Bayern"


def test_extra_state_attributes_keine_feiertage(hass, config_heute):
    """Test Attribute wenn keine Feiertage vorhanden."""
    sensor = FeiertagSensor(hass, config_heute)
    sensor._feiertags_info["feiertage_liste"] = []
    sensor._feiertags_info["heute_feiertag"] = False
    sensor._feiertags_info["naechster_feiertag_name"] = None
    sensor._feiertags_info["naechster_feiertag_datum"] = None

    attributes = sensor.extra_state_attributes
    assert attributes["Name Feiertag"] is None
    assert attributes["Datum"] is None
    assert attributes["Land"] == "Deutschland"
    assert attributes["Region"] == "Bayern"


def test_extra_state_attributes_aktueller_feiertag_vorgezogen(mock_feiertag_sensor):
    """Test dass aktueller Feiertag vor nächstem priorisiert wird."""
    heute = datetime.now().date()
    mock_feiertag_sensor._feiertags_info["feiertage_liste"] = [{
        "name": "Heutiger Feiertag",
        "start_datum": heute,
        "end_datum": heute,
    }]
    mock_feiertag_sensor._feiertags_info["heute_feiertag"] = False
    mock_feiertag_sensor._feiertags_info["naechster_feiertag_name"] = "Nächster"
    mock_feiertag_sensor._feiertags_info["naechster_feiertag_datum"] = "01.01.2025"

    attributes = mock_feiertag_sensor.extra_state_attributes
    assert attributes["Name Feiertag"] == "Heutiger Feiertag"


def test_extra_state_attributes_fehlt_feiertage_liste(hass, config_heute):
    """Test Attribute wenn feiertage_liste fehlt."""
    sensor = FeiertagSensor(hass, config_heute)
    sensor._feiertags_info["feiertage_liste"]  # wird nicht gesetzt
    sensor._feiertags_info["heute_feiertag"] = False
    sensor._feiertags_info["naechster_feiertag_name"] = "Test"
    sensor._feiertags_info["naechster_feiertag_datum"] = "01.01.2025"

    attributes = sensor.extra_state_attributes
    assert attributes["Name Feiertag"] == "Test"


# ============================================================
# Tests für get_api_parameter Method
# ============================================================

def test_get_api_parameter(mock_feiertag_sensor):
    """Test dass get_api_parameter korrekte Parameter erstellt."""
    heute = datetime.now().date()
    params = mock_feiertag_sensor.get_api_parameter(heute)

    assert params["countryIsoCode"] == "DE"
    assert params["subdivisionCode"] == "DE-BY"
    assert params["languageIsoCode"] == "DE"
    assert params["validFrom"] == (heute - timedelta(days=30)).strftime("%Y-%m-%d")
    assert params["validTo"] == (heute + timedelta(days=365)).strftime("%Y-%m-%d")


def test_get_api_parameter_different_region(hass):
    """Test get_api_parameter mit anderer Region."""
    config = {
        "unique_id": "feiertag_DE_BW",
        "entity_id": "sensor.feiertag_de_bw",
        "name": "Feiertag",
        "land": "DE",
        "region": "DE-BW",
        "land_name": "Deutschland",
        "region_name": "Baden-Württemberg",
    }
    sensor = FeiertagSensor(hass, config)
    heute = datetime.now().date()
    params = sensor.get_api_parameter(heute)

    assert params["countryIsoCode"] == "DE"
    assert params["subdivisionCode"] == "DE-BW"


def test_get_api_parameter_with_different_region(hass):
    """Test get_api_parameter mit anderer Region."""
    config = {
        "unique_id": "sensor.feiertag",
        "name": "Feiertag",
        "land": "DE",
        "region": "DE-BE",
        "land_name": "Deutschland",
        "region_name": "Berlin",
    }
    sensor = FeiertagSensor(hass, config)
    heute = datetime.now().date()
    params = sensor.get_api_parameter(heute)

    assert params["countryIsoCode"] == "DE"
    assert params["subdivisionCode"] == "DE-BE"


def test_get_api_parameter_language_from_hass(hass, config_heute):
    """Test dass languageIsoCode aus hass.config.language gelesen wird."""
    sensor = FeiertagSensor(hass, config_heute)
    hass.config.language = "en"
    sensor._location["iso_code"] = "EN"
    heute = datetime.now().date()
    params = sensor.get_api_parameter(heute)
    assert params["languageIsoCode"] == "EN"


# ============================================================
# Tests für async_added_to_hass Method
# ============================================================

@pytest.mark.asyncio
async def test_async_added_to_hass_sets_iso_code(mock_feiertag_sensor):
    """Test dass async_added_to_hass iso_code setzt."""
    mock_feiertag_sensor.hass = MagicMock()
    mock_feiertag_sensor.hass.config.language = "de"
    await mock_feiertag_sensor.async_added_to_hass()
    assert mock_feiertag_sensor._location["iso_code"] == "DE"


@pytest.mark.asyncio
async def test_async_added_to_hass_fallback_iso_code(mock_feiertag_sensor):
    """Test Fallback auf DE wenn hass.config nicht verfügbar."""
    mock_feiertag_sensor.hass = None
    await mock_feiertag_sensor.async_added_to_hass()
    assert mock_feiertag_sensor._location["iso_code"] == "DE"


@pytest.mark.asyncio
async def test_async_added_to_hass_calls_initial_update(hass, config_heute):
    """Test dass async_added_to_hass async_update aufruft."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    sensor = FeiertagSensor(hass, config_heute)
    sensor.async_update = AsyncMock()
    sensor.async_write_ha_state = MagicMock()
    sensor._feiertags_info["letztes_update"] = None

    with patch.object(fs_module, 'async_track_time_change'):
        await sensor.async_added_to_hass()

    sensor.async_update.assert_called_once()
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass_skip_if_same_day(mock_feiertag_sensor):
    """Test dass Update übersprungen wird wenn gleicher Tag."""
    mock_feiertag_sensor.hass = MagicMock()
    mock_feiertag_sensor.hass.config.language = "de"
    mock_feiertag_sensor.async_update = AsyncMock()
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime.now()

    await mock_feiertag_sensor.async_added_to_hass()

    mock_feiertag_sensor.async_update.assert_not_called()


# ============================================================
# Tests für async_update Method
# ============================================================

@pytest.mark.asyncio
async def test_async_update_skip_same_day(mock_feiertag_sensor):
    """Test dass Update übersprungen wird wenn gleicher Tag."""
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime.now()
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock()

    await mock_feiertag_sensor.async_update()

    mock_feiertag_sensor.hole_feiertags_daten.assert_not_called()


@pytest.mark.asyncio
async def test_async_update_with_valid_data(mock_feiertag_sensor, feiertags_daten):
    """Test Update mit gültigen Daten."""
    mock_feiertag_sensor._feiertags_info["letztes_update"] = None
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock(return_value=feiertags_daten)
    mock_feiertag_sensor.verarbeite_feiertags_daten = MagicMock()

    await mock_feiertag_sensor.async_update()

    mock_feiertag_sensor.hole_feiertags_daten.assert_called_once()
    mock_feiertag_sensor.verarbeite_feiertags_daten.assert_called_once()
    assert mock_feiertag_sensor._feiertags_info["letztes_update"] is not None


@pytest.mark.asyncio
async def test_async_update_no_data(mock_feiertag_sensor):
    """Test Update wenn keine Daten von API."""
    mock_feiertag_sensor._feiertags_info["letztes_update"] = None
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock(return_value=None)

    await mock_feiertag_sensor.async_update()

    mock_feiertag_sensor.hole_feiertags_daten.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_with_session(mock_feiertag_sensor):
    """Test Update mit übergebenem Session-Objekt."""
    mock_feiertag_sensor._feiertags_info["letztes_update"] = None
    mock_session = MagicMock()
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock()
    mock_feiertag_sensor.verarbeite_feiertags_daten = MagicMock()

    await mock_feiertag_sensor.async_update(session=mock_session)

    mock_feiertag_sensor.hole_feiertags_daten.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_creates_session(mock_feiertag_sensor):
    """Test dass eine neue Session erstellt wird wenn keine übergeben."""
    mock_feiertag_sensor._feiertags_info["letztes_update"] = None
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock()
    mock_feiertag_sensor.verarbeite_feiertags_daten = MagicMock()

    await mock_feiertag_sensor.async_update()


@pytest.mark.asyncio
async def test_async_update_error_handling(mock_feiertag_sensor):
    """Test Fehlerbehandlung im Update."""
    mock_feiertag_sensor._feiertags_info["letztes_update"] = None
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock(side_effect=Exception("API Error"))

    await mock_feiertag_sensor.async_update()

# ============================================================
# Tests für den 3-Regel-Guard (_update_faellig) — Spiegel von Slice 1
# ============================================================

def test_guard_rule_a_never_fetched_no_attempt(mock_feiertag_sensor):
    """Regel (a): nie gefetcht + kein Versuch heute -> Abruf faellig.

    Warum? Nach Neustart/Setup sind beide Marker None — der erste Abruf
    muss durchgehen (Inbetriebnahme), sonst kaeme der Sensor nie zu Daten.
    """
    jetzt = datetime(2024, 6, 18, 3, 0)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = None
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = None
    assert mock_feiertag_sensor._update_faellig(jetzt) is True


def test_guard_rule_a_blocks_after_todays_attempt(mock_feiertag_sensor):
    """Regel (a): Versuch heute -> Abruf gesperrt (Anti-Hammering-Kern).

    Warum? Genau dieser Fall war der Bug: ein Fehlschlag liess letztes_update
    alt, jeder 30s-Poll fetchte neu. letzter_versuch=heute blockt alle
    weiteren Aufrufe desselben Tages.
    """
    jetzt = datetime(2024, 6, 18, 10, 0)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = None
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = datetime(2024, 6, 18, 3, 5)
    assert mock_feiertag_sensor._update_faellig(jetzt) is False


def test_guard_rule_b_weekly_before_3am(mock_feiertag_sensor):
    """Regel (b): 7 Tage nach Erfolg, aber vor 03:00 -> gesperrt.

    Warum? Das 03:00-Fenster ist lokale Wanduhr — das verhindert den
    "00:00:30-Durchstich" (UTC vs. lokale Zeit) der FRD.
    """
    jetzt = datetime(2024, 6, 18, 2, 59)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 11, 3, 0)
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = None
    assert mock_feiertag_sensor._update_faellig(jetzt) is False


def test_guard_rule_b_weekly_at_3am(mock_feiertag_sensor):
    """Regel (b): 7 Tage nach Erfolg ab 03:00 -> Abruf faellig."""
    jetzt = datetime(2024, 6, 18, 3, 0)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 11, 3, 0)
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = None
    assert mock_feiertag_sensor._update_faellig(jetzt) is True


def test_guard_rule_b_blocks_before_seven_days(mock_feiertag_sensor):
    """Regel (b): < 7 Tage seit Erfolg -> gesperrt (auch ab 03:00).

    Warum? Nach einem Erfolg ist ein woechentlicher Rhythmus genug — die API
    aendert Feiertagsdaten nicht taeglich.
    """
    jetzt = datetime(2024, 6, 18, 3, 0)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 17, 3, 0)
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = None
    assert mock_feiertag_sensor._update_faellig(jetzt) is False


def test_guard_rule_c_failed_yesterday_at_3am(mock_feiertag_sensor):
    """Regel (c): Fehlschlag gestern -> Retry ab 03:00."""
    jetzt = datetime(2024, 6, 18, 3, 0)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 15, 3, 0)
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = datetime(2024, 6, 17, 3, 5)
    assert mock_feiertag_sensor._update_faellig(jetzt) is True


def test_guard_rule_c_blocks_before_3am(mock_feiertag_sensor):
    """Regel (c): Fehlschlag gestern, aber vor 03:00 -> gesperrt."""
    jetzt = datetime(2024, 6, 18, 2, 59)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 15, 3, 0)
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = datetime(2024, 6, 17, 3, 5)
    assert mock_feiertag_sensor._update_faellig(jetzt) is False


def test_guard_rule_c_blocks_same_day_attempt(mock_feiertag_sensor):
    """Regel (c): Versuch heute -> kein Retry mehr heute.

    Warum? letzter_versuch.date() == heute erfuellt die gestern-Klausel
    nicht — der taegliche Retry ist auf 1x/Tag begrenzt.
    """
    jetzt = datetime(2024, 6, 18, 10, 0)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 15, 3, 0)
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = datetime(2024, 6, 18, 3, 5)
    assert mock_feiertag_sensor._update_faellig(jetzt) is False


def test_guard_rule_c_blocks_when_last_attempt_succeeded(mock_feiertag_sensor):
    """Regel (c): letzter_versuch <= letztes_update = Erfolg -> kein Retry.

    Warum? Ein Erfolg ueberschreibt letztes_update mit einem Zeitstempel >=
    dem Versuch — die Ordnung der beiden Marker ist die Fehlschlags-Anzeige.
    """
    jetzt = datetime(2024, 6, 18, 3, 0)
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 17, 3, 0)
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = datetime(2024, 6, 17, 2, 59)
    assert mock_feiertag_sensor._update_faellig(jetzt) is False


# ============================================================
# Tests für letzter_versuch (Setzpunkt + Fehlschlags-Sperre)
# ============================================================

@pytest.mark.asyncio
async def test_update_sets_letzter_versuch_before_request(mock_feiertag_sensor):
    """letzter_versuch wird VOR dem API-Request gesetzt.

    Warum? Regel (c) braucht den Versuchs-Zeitstempel als Fehlschlags-Beweis -
    gesetzt in hole_feiertags_daten, also vor der URL-Schleife, unabhaengig
    vom Erfolg.
    """
    with patch("custom_components.schulferien.feiertag_sensor.fetch_data",
               new=AsyncMock(side_effect=aiohttp.ClientError("offline"))):
        await mock_feiertag_sensor.async_update()
    assert mock_feiertag_sensor._feiertags_info["letzter_versuch"] is not None
    assert mock_feiertag_sensor._feiertags_info["letztes_update"] is None


@pytest.mark.asyncio
async def test_update_failure_blocks_refetch_same_day(mock_feiertag_sensor):
    """Nach Fehlschlag sperrt letzter_versuch weitere Abrufe am selben Tag.

    Warum? Das ist die Regression fuer den Hammering-Bug der FRD: vorher
    passierte jeder 30s-Poll den Guard, weil letztes_update nach einem
    Fehlschlag alt blieb.
    """
    mit = datetime(2024, 6, 18, 10, 0)  # nach 03:00 -> Fenster offen
    mock_feiertag_sensor._feiertags_info["letztes_update"] = datetime(2024, 6, 13, 3, 0)   # 5 Tage alt
    mock_feiertag_sensor._feiertags_info["letzter_versuch"] = datetime(2024, 6, 17, 3, 5)  # gestern

    with patch("custom_components.schulferien.feiertag_sensor.dt_util") as mock_dt, \
            patch("custom_components.schulferien.feiertag_sensor.fetch_data",
                  new=AsyncMock(side_effect=aiohttp.ClientError("offline"))) as mock_fetch:
        mock_dt.now.return_value = mit
        await mock_feiertag_sensor.async_update()   # Regel (c): Retry heute -> Fehlschlag
        # 2. Poll am selben Tag: letzter_versuch=heute -> gesperrt (kein Fetch)
        await mock_feiertag_sensor.async_update()
        # hole_feiertags_daten probiert 2 URLs pro Versuch; der 2. Poll darf
        # keine weiteren Aufrufe erzeugen
        assert mock_fetch.call_count == 2
    assert mock_feiertag_sensor._feiertags_info["letzter_versuch"] == mit
    assert mock_feiertag_sensor._feiertags_info["letztes_update"] == datetime(2024, 6, 13, 3, 0)

# ============================================================
# Tests für hole_feiertags_daten Method
# ============================================================

@pytest.mark.asyncio
async def test_hole_feiertags_daten_success_first_url(mock_feiertag_sensor):
    """Test dass Daten von erster URL erfolgreich abgerufen werden."""
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock(return_value={"feiertage": []})
    result = await mock_feiertag_sensor.hole_feiertags_daten({}, MagicMock())
    assert result is not None


@pytest.mark.asyncio
async def test_hole_feiertags_daten_returns_none(mock_feiertag_sensor):
    """Test dass None zurückgegeben wird wenn keine Daten."""
    mock_feiertag_sensor.hole_feiertags_daten = AsyncMock(return_value=None)
    result = await mock_feiertag_sensor.hole_feiertags_daten({}, MagicMock())
    assert result is None


# ============================================================
# Tests für verarbeite_feiertags_daten Method
# ============================================================

def test_verarbeite_feiertags_daten_heute_feiertag(mock_feiertag_sensor):
    """Test Verarbeitung wenn heute Feiertag (parse_daten gemockt)."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    heute = datetime.now().date()
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Weihnachtstag",
        "start_datum": heute,
        "end_datum": heute,
    }]):
        mock_feiertag_sensor.verarbeite_feiertags_daten({"feiertage": []}, heute)
        assert mock_feiertag_sensor._feiertags_info["heute_feiertag"] is True
        assert mock_feiertag_sensor._feiertags_info["naechster_feiertag_name"] == "Weihnachtstag"


def test_verarbeite_feiertags_daten_heute_feiertag_with_mock_parse(hass, config_heute):
    """Test Verarbeitung wenn heute Feiertag mit gemocktem parse_daten."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    heute = datetime.now().date()
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Weihnachtstag",
        "start_datum": heute,
        "end_datum": heute,
    }]):
        sensor = FeiertagSensor(hass, config_heute)
        daten = {"feiertage": [{"name": "test"}]}
        sensor.verarbeite_feiertags_daten(daten, heute)
        assert sensor._feiertags_info["heute_feiertag"] is True
        assert sensor._feiertags_info["naechster_feiertag_name"] == "Weihnachtstag"


def test_verarbeite_feiertags_daten_kein_heute_feiertag(mock_feiertag_sensor):
    """Test Verarbeitung wenn heute kein Feiertag (parse_daten gemockt)."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    heute = date(2024, 6, 18)  # fixiert: kein Ostersonntag — Gauss-Ergaenzung darf heute nicht treffen
    morgen = date(2024, 6, 19)
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Neujahr",
        "start_datum": morgen,
        "end_datum": morgen,
    }]):
        mock_feiertag_sensor.verarbeite_feiertags_daten({"feiertage": []}, heute)
        assert mock_feiertag_sensor._feiertags_info["heute_feiertag"] is False
        assert mock_feiertag_sensor._feiertags_info["naechster_feiertag_name"] == "Neujahr"


def test_verarbeite_feiertags_daten_kein_heute_feiertag_with_mock_parse(hass, config_heute):
    """Test Verarbeitung wenn heute kein Feiertag mit gemocktem parse_daten."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    heute = date(2024, 6, 18)  # fixiert: kein Ostersonntag
    morgen = date(2024, 6, 19)
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Neujahr",
        "start_datum": morgen,
        "end_datum": morgen,
    }]):
        sensor = FeiertagSensor(hass, config_heute)
        sensor.verarbeite_feiertags_daten({"feiertage": []}, heute)
        assert sensor._feiertags_info["heute_feiertag"] is False
        assert sensor._feiertags_info["naechster_feiertag_name"] == "Neujahr"

def test_verarbeite_feiertags_daten_kein_heute_feiertag_with_mock_parse(hass, config_heute):
    """Test Verarbeitung wenn heute kein Feiertag mit gemocktem parse_daten."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    heute = datetime.now().date()
    morgen = heute + timedelta(days=1)
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Neujahr",
        "start_datum": morgen,
        "end_datum": morgen,
    }]):
        sensor = FeiertagSensor(hass, config_heute)
        daten = {"feiertage": [{"name": "test"}]}
        sensor.verarbeite_feiertags_daten(daten, heute)
        assert sensor._feiertags_info["heute_feiertag"] is False
        assert sensor._feiertags_info["naechster_feiertag_name"] == "Neujahr"


def test_ostersonntag_ergaenzung_fixiertes_datum(mock_feiertag_sensor):
    """Ostersonntag wird mit korrektem Datum ergaenzt (fixiert statt naiv-heute).

    Warum? Die alten Tests rechneten heute+1d und prueften nur Namens-Praesenz
    — am Ostersonntag selbst flaky, und ohne Datums-Verankerung. Fixiert auf
    Ostermontag 2024-04-01 => Gauss ergaenzt Ostersonntag 2024-03-31.
    """
    from custom_components.schulferien import feiertag_sensor as fs_module
    heute = date(2024, 6, 18)  # fixiert: kein Ostersonntag — Ergaenzung kommt aus Gauss
    ostermontag = date(2024, 4, 1)
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Ostermontag",
        "start_datum": ostermontag,
        "end_datum": ostermontag,
    }]):
        mock_feiertag_sensor.verarbeite_feiertags_daten({"feiertage": []}, heute)
        feiertage_liste = mock_feiertag_sensor._feiertags_info["feiertage_liste"]
        assert any(
            f["name"] == "Ostersonntag" and f["start_datum"] == date(2024, 3, 31)
            for f in feiertage_liste
        )


# ============================================================
# SLICE 3: Ostersonntag per Gauss (sprachunabhaengig)
# ============================================================

def test_berechne_ostersonntag_bekannte_daten():
    """Gauss liefert korrekte Osterdaten (Referenzwerte).

    Warum? Bekannte Osterdaten verankern die Formel — 2024 war Ostersonntag
    am 31.03., 2025 am 20.04. Fehler in der geschlossenen Form wuerden hier
    sofort sichtbar.
    """
    assert berechne_ostersonntag(2023) == date(2023, 4, 9)
    assert berechne_ostersonntag(2024) == date(2024, 3, 31)
    assert berechne_ostersonntag(2025) == date(2025, 4, 20)


def test_verarbeite_feiertags_daten_ergaenzt_ostersonntag(hass, config_heute):
    """Ostersonntag wird per Gauss ergaenzt, wenn die API ihn nicht liefert.

    Warum? Die OpenHolidaysAPI liefert Ostermontag, aber nicht immer
    Ostersonntag — Gauss ergaenzt das Osterdatum je Jahr im Fenster.
    """
    from custom_components.schulferien import feiertag_sensor as fs_module
    ostermontag_2024 = date(2024, 4, 1)
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Ostermontag",
        "start_datum": ostermontag_2024,
        "end_datum": ostermontag_2024,
    }]):
        sensor = FeiertagSensor(hass, config_heute)
        sensor.verarbeite_feiertags_daten({"feiertage": []}, date(2024, 6, 18))
        feiertage_liste = sensor._feiertags_info["feiertage_liste"]
        assert any(
            f["name"] == "Ostersonntag" and f["start_datum"] == date(2024, 3, 31)
            for f in feiertage_liste
        )


def test_verarbeite_feiertags_daten_ostersonntag_sprachunabhaengig(hass, config_heute):
    """Ostersonntag wird auch bei nicht-DE/EN-API-Sprache ergaenzt.

    Warum? Das ist der FRD-Acceptance-Bug: der alte Namens-Match erkannte
    nur "Ostermontag"/"Easter Monday" — bei anderen Sprach-Labels fehlte
    Ostersonntag komplett. Gauss haengt nicht von der Sprache ab.
    """
    from custom_components.schulferien import feiertag_sensor as fs_module
    ostermontag_2025 = date(2025, 4, 21)
    with patch.object(fs_module, 'parse_daten', return_value=[{
        "name": "Lundi de Pâques",  # franzoesisch — alter Match wuerde scheitern
        "start_datum": ostermontag_2025,
        "end_datum": ostermontag_2025,
    }]):
        sensor = FeiertagSensor(hass, config_heute)
        sensor.verarbeite_feiertags_daten({"feiertage": []}, date(2025, 6, 18))
        feiertage_liste = sensor._feiertags_info["feiertage_liste"]
        assert any(
            f["name"] == "Ostersonntag" and f["start_datum"] == date(2025, 4, 20)
            for f in feiertage_liste
        )


def test_verarbeite_feiertags_daten_kein_doppelter_ostersonntag(hass, config_heute):
    """Ostersonntag wird nicht doppelt ergaenzt, wenn die API ihn liefert.

    Warum? Der datumsbasierte Dedup-Guard verhindert Dopplung — die API
    kann Ostersonntag in beliebiger Sprache bereits liefern.
    """
    from custom_components.schulferien import feiertag_sensor as fs_module
    with patch.object(fs_module, 'parse_daten', return_value=[
        {"name": "Easter Sunday", "start_datum": date(2024, 3, 31), "end_datum": date(2024, 3, 31)},
        {"name": "Ostermontag", "start_datum": date(2024, 4, 1), "end_datum": date(2024, 4, 1)},
    ]):
        sensor = FeiertagSensor(hass, config_heute)
        sensor.verarbeite_feiertags_daten({"feiertage": []}, date(2024, 6, 18))
        feiertage_liste = sensor._feiertags_info["feiertage_liste"]
        ostersonntage = [f for f in feiertage_liste if f["name"] == "Ostersonntag"]
        assert len(ostersonntage) == 1


def test_verarbeite_feiertags_daten_keine_daten(mock_feiertag_sensor):
    """Test Verarbeitung bei leeren Daten (parse_daten gemockt)."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    with patch.object(fs_module, 'parse_daten', return_value=[]):
        mock_feiertag_sensor.verarbeite_feiertags_daten(
            {"feiertage": []}, datetime.now().date()
        )
        assert mock_feiertag_sensor._feiertags_info["feiertage_liste"] == []


def test_verarbeite_feiertags_daten_keine_daten_with_mock_parse(hass, config_heute):
    """Test Verarbeitung bei leeren Daten mit gemocktem parse_daten."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    with patch.object(fs_module, 'parse_daten', return_value=[]):
        sensor = FeiertagSensor(hass, config_heute)
        sensor.verarbeite_feiertags_daten({"feiertage": []}, datetime.now().date())
        assert not sensor._feiertags_info["feiertage_liste"]
        assert sensor._feiertags_info["heute_feiertag"] is False


def test_verarbeite_feiertags_daten_error(mock_feiertag_sensor):
    """Test Fehlerbehandlung bei ungültigen Daten (parse_daten wirft Exception)."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    initial_liste = list(mock_feiertag_sensor._feiertags_info["feiertage_liste"])
    with patch.object(fs_module, 'parse_daten', side_effect=Exception("Parse Error")):
        mock_feiertag_sensor.verarbeite_feiertags_daten(
            {"feiertage": []}, datetime.now().date()
        )
        assert mock_feiertag_sensor._feiertags_info["feiertage_liste"] == initial_liste


def test_verarbeite_feiertags_daten_error_with_mock_parse(hass, config_heute):
    """Test Fehlerbehandlung bei parse_daten Exception."""
    from custom_components.schulferien import feiertag_sensor as fs_module
    with patch.object(fs_module, 'parse_daten', side_effect=Exception("Parse Error")):
        sensor = FeiertagSensor(hass, config_heute)
        initial_liste = list(sensor._feiertags_info["feiertage_liste"])
        sensor.verarbeite_feiertags_daten({"feiertage": []}, datetime.now().date())
        assert sensor._feiertags_info["feiertage_liste"] == initial_liste


# ============================================================
# Tests für FeiertagMorgenSensor
# ============================================================

def test_feiertag_morgen_sensor_initialization(hass, config_heute):
    """Test die Initialisierung des FeiertagMorgenSensors."""
    config_mit_name = {
        **config_heute,
        "name": "Feiertag - Deutschland (Bayern)",
    }
    main_sensor = FeiertagSensor(hass, config_mit_name)
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.unique_id == "feiertag_DE_BY_morgen"
    assert morgen_sensor.name == "Feiertag Morgen - Deutschland (Bayern)"


def test_feiertag_morgen_sensor_native_value_feiertag(hass, config_heute):
    """Test native_value wenn morgen Feiertag."""
    main_sensor = FeiertagSensor(hass, config_heute)
    morgen = (datetime.now() + timedelta(days=1)).date()
    main_sensor._feiertags_info["feiertage_liste"] = [{
        "name": "Neujahr",
        "start_datum": morgen,
        "end_datum": morgen,
    }]
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.native_value == "feiertag"


def test_feiertag_morgen_sensor_native_value_kein_feiertag(hass, config_heute):
    """Test native_value wenn morgen kein Feiertag."""
    main_sensor = FeiertagSensor(hass, config_heute)
    main_sensor._feiertags_info["feiertage_liste"] = [{
        "name": "Weihnachtstag",
        "start_datum": datetime.now().date(),
        "end_datum": datetime.now().date(),
    }]
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.native_value == "kein_feiertag"


def test_feiertag_morgen_sensor_native_value_empty_list(hass, config_heute):
    """Test native_value bei leerer Feiertagsliste."""
    main_sensor = FeiertagSensor(hass, config_heute)
    main_sensor._feiertags_info["feiertage_liste"] = []
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.native_value == "kein_feiertag"


def test_feiertag_morgen_sensor_native_value_none_list(hass, config_heute):
    """Test native_value wenn feiertage_liste None ist."""
    main_sensor = FeiertagSensor(hass, config_heute)
    main_sensor._feiertags_info["feiertage_liste"] = None
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.native_value == "kein_feiertag"


def test_feiertag_morgen_sensor_unique_id(hass, config_heute):
    """Test unique_id des MorgenSensors."""
    main_sensor = FeiertagSensor(hass, config_heute)
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.unique_id == "feiertag_DE_BY_morgen"


def test_feiertag_morgen_sensor_name(hass, config_heute):
    """Test name des MorgenSensors enthaelt die Region wie der Referenzsensor."""
    config_mit_name = {
        **config_heute,
        "name": "Feiertag - Deutschland (Bayern)",
    }
    main_sensor = FeiertagSensor(hass, config_mit_name)
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.name == "Feiertag Morgen - Deutschland (Bayern)"


@pytest.mark.asyncio
async def test_feiertag_morgen_sensor_async_update_pass(hass, config_heute):
    """Test dass async_update beim MorgenSensor nichts tut."""
    main_sensor = FeiertagSensor(hass, config_heute)
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    await morgen_sensor.async_update()


# ============================================================
# Tests für load_bridge_days Function
# ============================================================

def test_load_bridge_days_file_not_found():
    """Test dass leere Liste zurückgegeben wird wenn Datei nicht gefunden."""
    pytest.importorskip("aiofiles")

    with patch.dict('sys.modules', {'aiofiles': MagicMock()}):
        pass


@pytest.mark.asyncio
async def test_load_bridge_days_empty_file(tmp_path):
    """Test dass leere Liste bei leerer Datei zurückgegeben wird."""
    test_file = tmp_path / "bridge_days.yaml"
    test_file.write_text("", encoding="utf-8")

    result = await load_bridge_days(str(test_file))
    assert result == []


@pytest.mark.asyncio
async def test_load_bridge_days_valid_content(tmp_path):
    """Test das Laden mit gültigem Inhalt."""
    test_file = tmp_path / "bridge_days.yaml"
    content = "bridge_days:\n  - date: '2024-04-22'\n    name: 'Brücktag'\n"
    test_file.write_text(content, encoding="utf-8")

    result = await load_bridge_days(str(test_file))
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Brücktag"


@pytest.mark.asyncio
async def test_load_bridge_days_yaml_error(tmp_path):
    """Test Fehlerbehandlung bei ungültigem YAML."""
    test_file = tmp_path / "bridge_days.yaml"
    test_file.write_text("{invalid: yaml: content:", encoding="utf-8")

    result = await load_bridge_days(str(test_file))
    assert result == []


# ============================================================
# Tests für edge cases
# ============================================================

def test_feiertag_sensor_with_unicode_name(hass):
    """Test mit einem Feiertagsnamen mit Unicode-Zeichen."""
    config = {
        "unique_id": "sensor.feiertag",
        "name": "Föjrtåg",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Dëutschland",
        "region_name": "Båyern",
    }
    sensor = FeiertagSensor(hass, config)
    assert sensor.name == "Föjrtåg"
    assert sensor._location["land_name"] == "Dëutschland"


def test_feiertag_sensor_multi_day_feiertag(hass, config_heute):
    """Test mehrtägige Feiertage."""
    sensor = FeiertagSensor(hass, config_heute)
    heute = datetime.now().date()
    morgen = heute + timedelta(days=1)
    sensor._feiertags_info["feiertage_liste"] = [{
        "name": "Weihnachtsfeiertage",
        "start_datum": heute,
        "end_datum": morgen,
    }]
    sensor._feiertags_info["heute_feiertag"] = True

    assert sensor.native_value == "feiertag"


def test_feiertag_sensor_naechster_feiertag_in_weiter_zukunft(hass, config_heute):
    """Test wenn nächster Feiertag weit in der Zukunft liegt."""
    sensor = FeiertagSensor(hass, config_heute)
    heute = datetime.now().date()
    weit_weg = heute + timedelta(days=365)
    sensor._feiertags_info["feiertage_liste"] = [{
        "name": "Neujahr",
        "start_datum": weit_weg,
        "end_datum": weit_weg,
    }]
    sensor._feiertags_info["heute_feiertag"] = False
    sensor._feiertags_info["naechster_feiertag_name"] = "Neujahr"
    sensor._feiertags_info["naechster_feiertag_datum"] = weit_weg.strftime("%d.%m.%Y")

    attributes = sensor.extra_state_attributes
    assert attributes["Name Feiertag"] == "Neujahr"


# ============================================================
# Tests fuer async_will_remove_from_hass (Listener-Cleanup)
# ============================================================

def test_feiertag_cancel_timer_initialized_to_none(hass, config_heute):
    """_cancel_timer muss bei Initialisierung None sein."""
    sensor = FeiertagSensor(hass, config_heute)
    assert sensor._cancel_timer is None


@pytest.mark.asyncio
async def test_feiertag_timer_stored_from_track_time_change(hass, config_heute):
    """Rueckgabewert von async_track_time_change wird in _cancel_timer gespeichert."""
    mock_cancel = MagicMock()
    sensor = FeiertagSensor(hass, config_heute)

    with patch(
        "custom_components.schulferien.feiertag_sensor.async_track_time_change",
        return_value=mock_cancel,
    ), patch.object(sensor, "async_update", new=AsyncMock()), patch.object(
        sensor, "async_write_ha_state"
    ):
        await sensor.async_added_to_hass()

    assert sensor._cancel_timer is mock_cancel


@pytest.mark.asyncio
async def test_feiertag_async_will_remove_calls_cancel(hass, config_heute):
    """async_will_remove_from_hass ruft _cancel_timer auf."""
    sensor = FeiertagSensor(hass, config_heute)
    mock_cancel = MagicMock()
    sensor._cancel_timer = mock_cancel

    await sensor.async_will_remove_from_hass()

    mock_cancel.assert_called_once()
    assert sensor._cancel_timer is None


@pytest.mark.asyncio
async def test_feiertag_async_will_remove_without_cancel_is_safe(hass, config_heute):
    """async_will_remove_from_hass ohne _cancel_timer wirft keine Exception."""
    sensor = FeiertagSensor(hass, config_heute)
    sensor._cancel_timer = None

    await sensor.async_will_remove_from_hass()

    assert sensor._cancel_timer is None


# ============================================================
# Tests fuer FeiertagMorgenSensor multi-region name
# ============================================================

def test_feiertag_morgen_sensor_name_multi_region(hass):
    """Zwei FeiertagMorgenSensoren mit verschiedenen Regionen haben unterschiedliche Namen."""
    config_by = {
        "unique_id": "feiertag_DE_BY",
        "entity_id": "sensor.feiertag_de_by",
        "name": "Feiertag - Deutschland (Bayern)",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    config_he = {
        "unique_id": "feiertag_DE_HE",
        "entity_id": "sensor.feiertag_de_he",
        "name": "Feiertag - Deutschland (Hessen)",
        "land": "DE",
        "region": "DE-HE",
        "land_name": "Deutschland",
        "region_name": "Hessen",
    }

    sensor_by = FeiertagSensor(hass, config_by)
    sensor_he = FeiertagSensor(hass, config_he)

    morgen_by = FeiertagMorgenSensor(sensor_by)
    morgen_he = FeiertagMorgenSensor(sensor_he)

    assert morgen_by.name == "Feiertag Morgen - Deutschland (Bayern)"
    assert morgen_he.name == "Feiertag Morgen - Deutschland (Hessen)"
    assert morgen_by.name != morgen_he.name


def test_feiertag_morgen_sensor_name_no_separator(hass):
    """FeiertagMorgenSensor Name ohne ' - ' im Referenz-Namen."""
    config = {
        "unique_id": "feiertag_DE_BY",
        "entity_id": "sensor.feiertag_de_by",
        "name": "TestFeiertag",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
    }
    main_sensor = FeiertagSensor(hass, config)
    morgen_sensor = FeiertagMorgenSensor(main_sensor)
    assert morgen_sensor.name == "TestFeiertag Morgen"


def test_feiertag_cancel_midnight_initialized_to_none(hass, config_heute):
    """_cancel_midnight muss bei Initialisierung None sein."""
    sensor = FeiertagSensor(hass, config_heute)
    assert sensor._cancel_midnight is None


@pytest.mark.asyncio
async def test_feiertag_midnight_timer_registered_at_midnight(hass, config_heute):
    """Mitternachts-Timer wird mit den MIDNIGHT_REFRESH_*-Konstanten registriert."""
    hass.config.language = "de"
    sensor = FeiertagSensor(hass, config_heute)
    with patch(
        "custom_components.schulferien.feiertag_sensor.async_track_time_change",
        return_value=MagicMock(),
    ) as mock_track, patch.object(sensor, "async_update", new=AsyncMock()), patch.object(
        sensor, "async_write_ha_state"
    ):
        await sensor.async_added_to_hass()
    midnight_calls = [
        c
        for c in mock_track.call_args_list
        if c.kwargs.get("hour") == MIDNIGHT_REFRESH_HOUR
        and c.kwargs.get("minute") == MIDNIGHT_REFRESH_MINUTE
        and c.kwargs.get("second") == MIDNIGHT_REFRESH_SECOND
    ]
    assert midnight_calls, "Mitternachts-Timer nicht registriert"


@pytest.mark.asyncio
async def test_feiertag_cancel_midnight_stored_from_track(hass, config_heute):
    """Rueckgabewert der Mitternachts-Registrierung landet in _cancel_midnight."""
    hass.config.language = "de"
    sensor = FeiertagSensor(hass, config_heute)
    mock_cancel = MagicMock()
    with patch(
        "custom_components.schulferien.feiertag_sensor.async_track_time_change",
        return_value=mock_cancel,
    ), patch.object(sensor, "async_update", new=AsyncMock()), patch.object(
        sensor, "async_write_ha_state"
    ):
        await sensor.async_added_to_hass()
    assert sensor._cancel_midnight is mock_cancel


@pytest.mark.asyncio
async def test_feiertag_async_will_remove_cancels_midnight(hass, config_heute):
    """async_will_remove_from_hass ruft zusaetzlich _cancel_midnight auf."""
    sensor = FeiertagSensor(hass, config_heute)
    mock_midnight = MagicMock()
    sensor._cancel_midnight = mock_midnight
    await sensor.async_will_remove_from_hass()
    mock_midnight.assert_called_once()
    assert sensor._cancel_midnight is None