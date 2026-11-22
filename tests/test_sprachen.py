"""Tests für die Sprachauswahl der Ferien-/Feiertagsnamen (Options-Flow).

Hintergrund: Die Namen ("Herbstferien") sind Daten aus der API, keine
Frontend-Übersetzungen. Bisher kamen sie immer in der HA-Systemsprache.
Mehrsprachige Haushalte (z.B. HA auf Englisch, Kinder lesen Deutsch) wählen
im Options-Flow mehrere Sprachen und bekommen "Herbstferien / Autumn Holidays".
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.schulferien.api_utils import (
    BRUECKENTAG_NAMEN,
    normalisiere_sprachen,
    parse_daten,
    sprachen_aus_liste,
    waehle_namen,
)
from custom_components.schulferien.config_flow import (
    SchulferienFlowHandler,
    SchulferienOptionsFlow,
)
from custom_components.schulferien.const import CONF_LANGUAGES, DOMAIN
from custom_components.schulferien.feiertag_sensor import FeiertagSensor


# So antwortet die API ohne languageIsoCode (geprüft für DE-BY)
HERBSTFERIEN = {
    "name": [
        {"language": "DE", "text": "Herbstferien"},
        {"language": "EN", "text": "Autumn Holidays"},
    ],
    "startDate": "2026-11-02",
    "endDate": "2026-11-06",
}


# ============================================================
# api_utils
# ============================================================

def test_zwei_sprachen_werden_in_auswahl_reihenfolge_verbunden():
    """Die Reihenfolge der Auswahl bestimmt die Reihenfolge im Namen.

    Warum? Wer Deutsch zuerst wählt, will "Herbstferien" vorne sehen —
    auf schmalen Kalenderkarten wird der Rest abgeschnitten.
    """
    assert parse_daten([HERBSTFERIEN], sprachen=["DE", "EN"])[0]["name"] == (
        "Herbstferien / Autumn Holidays"
    )
    assert parse_daten([HERBSTFERIEN], sprachen=["EN", "DE"])[0]["name"] == (
        "Autumn Holidays / Herbstferien"
    )


def test_eine_sprache_ergibt_nur_diesen_namen():
    """Eine Sprache gewählt = genau ein Name, ohne Trenner."""
    assert parse_daten([HERBSTFERIEN], sprachen=["DE"])[0]["name"] == "Herbstferien"


def test_ohne_sprachen_bleibt_der_erste_api_name():
    """Ohne Sprachen: erster Name der API, wie vor dem Options-Flow.

    Warum? Aufrufer ohne Sprachangabe (und alte Tests/Mocks) sollen exakt
    das bisherige Verhalten behalten.
    """
    assert parse_daten([HERBSTFERIEN])[0]["name"] == "Herbstferien"


def test_fehlende_sprache_faellt_auf_ersten_namen_zurueck():
    """Liefert die API eine gewählte Sprache nicht, kommt der erste Name.

    Warum? Ein Name in fremder Sprache ist nützlicher als "Unbekannt" oder
    ein leerer Kalendereintrag.
    """
    assert parse_daten([HERBSTFERIEN], sprachen=["FR"])[0]["name"] == "Herbstferien"


def test_fehlende_sprache_wird_bei_mehreren_einfach_ausgelassen():
    """Von ["FR", "EN"] bleibt nur EN — kein Platzhalter für FR."""
    assert parse_daten([HERBSTFERIEN], sprachen=["FR", "EN"])[0]["name"] == "Autumn Holidays"


def test_gleicher_text_in_mehreren_sprachen_nur_einmal():
    """"Pfingstferien / Pfingstferien" wäre Rauschen, also nur einmal."""
    namen = {"DE": "Pfingstferien", "EN": "Pfingstferien"}
    assert waehle_namen(namen, ["DE", "EN"]) == "Pfingstferien"


def test_alle_sprachvarianten_bleiben_erhalten():
    """parse_daten behält alle Varianten in "namen".

    Warum? Das Options-Formular bietet daraus die Sprachen an, die die API
    für diese Region wirklich liefert.
    """
    eintrag = parse_daten([HERBSTFERIEN], sprachen=["DE"])[0]
    assert eintrag["namen"] == {"DE": "Herbstferien", "EN": "Autumn Holidays"}


def test_brueckentag_wird_lokalisiert():
    """Brückentage folgen der Sprachauswahl wie die API-Namen.

    Warum? Sonst stünde im englisch/deutschen Kalender "Autumn Holidays /
    Herbstferien" neben einem rein deutschen "Brückentag".
    """
    liste = parse_daten([HERBSTFERIEN], ["30.10.2026"], sprachen=["EN", "DE"])
    brueckentag = next(e for e in liste if e["start_datum"] == date(2026, 10, 30))
    assert brueckentag["name"] == "Bridge Day / Brückentag"
    assert brueckentag["name_quelle"] == "fest"


def test_brueckentag_ohne_sprachen_bleibt_deutsch():
    """Ohne Sprachangabe bleibt "Brückentag" — das bisherige feste Wort."""
    liste = parse_daten([HERBSTFERIEN], ["30.10.2026"])
    assert liste[-1]["name"] == "Brückentag"
    assert next(iter(BRUECKENTAG_NAMEN)) == "DE"


def test_normalisiere_sprachen():
    """HA-Codes ("de", "pt-BR") werden zu API-Codes, Duplikate fallen weg."""
    assert normalisiere_sprachen(["de", "pt-BR", "DE", "", None, "en"]) == ["DE", "PT", "EN"]
    assert normalisiere_sprachen(None) == []


def test_sprachen_aus_liste_in_erscheinungsreihenfolge():
    """Sammelt die Sprachen der geladenen Einträge ohne Duplikate."""
    liste = [
        {"namen": {"DE": "a", "EN": "b"}},
        {"namen": {"EN": "c", "FR": "d"}},
        {"namen": {"": "ohne Sprache"}},
        {},
    ]
    assert sprachen_aus_liste(liste) == ["DE", "EN", "FR"]


# ============================================================
# FeiertagSensor: Ostersonntag folgt der Sprachauswahl
# ============================================================

def _feiertag_sensor(sprachen=None):
    config = {
        "unique_id": "feiertag_DE_BY",
        "name": "Feiertag",
        "land": "DE",
        "region": "DE-BY",
        "land_name": "Deutschland",
        "region_name": "Bayern",
        "sprachen": sprachen,
    }
    sensor = FeiertagSensor(MagicMock(), config)
    sensor._location["iso_code"] = "EN"
    return sensor


OSTERMONTAG_2024 = [{
    "name": [
        {"language": "DE", "text": "Ostermontag"},
        {"language": "EN", "text": "Easter Monday"},
    ],
    "startDate": "2024-04-01",
    "endDate": "2024-04-01",
}]


def test_ostersonntag_folgt_der_sprachauswahl():
    """Der ergänzte Ostersonntag heißt wie die API-Feiertage daneben.

    Warum? Er wird per Gauss ergänzt und hatte bisher immer den deutschen
    Namen — im Kalender neben "Ostermontag / Easter Monday" fiel das auf.
    """
    sensor = _feiertag_sensor(["DE", "EN"])
    assert sensor.verarbeite_feiertags_daten(OSTERMONTAG_2024, date(2024, 4, 1))
    liste = sensor._feiertags_info["feiertage_liste"]
    namen = {e["start_datum"]: e["name"] for e in liste}
    assert namen[date(2024, 4, 1)] == "Ostermontag / Easter Monday"
    assert namen[date(2024, 3, 31)] == "Ostersonntag / Easter Sunday"


def test_ostersonntag_dedupe_ist_sprachunabhaengig():
    """Liefert die API Ostersonntag selbst, wird er nicht doppelt ergänzt.

    Warum hier nochmal? Die Deduplizierung läuft über das Datum; mit
    zusammengesetzten Namen darf kein zweiter Eintrag entstehen.
    """
    mit_sonntag = OSTERMONTAG_2024 + [{
        "name": [
            {"language": "DE", "text": "Ostersonntag"},
            {"language": "EN", "text": "Easter Sunday"},
        ],
        "startDate": "2024-03-31",
        "endDate": "2024-03-31",
    }]
    for sprachen in (["DE"], ["EN"], ["DE", "EN"]):
        sensor = _feiertag_sensor(sprachen)
        assert sensor.verarbeite_feiertags_daten(mit_sonntag, date(2024, 4, 1))
        liste = sensor._feiertags_info["feiertage_liste"]
        assert sum(e["start_datum"] == date(2024, 3, 31) for e in liste) == 1


def test_ohne_option_nimmt_feiertag_die_ha_sprache():
    """Ohne Option: HA-Sprache (hier EN), wie vor dem Options-Flow."""
    sensor = _feiertag_sensor(None)
    assert sensor.verarbeite_feiertags_daten(OSTERMONTAG_2024, date(2024, 4, 1))
    namen = {e["start_datum"]: e["name"] for e in sensor._feiertags_info["feiertage_liste"]}
    assert namen[date(2024, 4, 1)] == "Easter Monday"


# ============================================================
# Options-Flow
# ============================================================

def _options_flow(options=None, ferien_liste=None, feiertage_liste=None, language="en"):
    flow = SchulferienOptionsFlow()
    flow.hass = MagicMock()
    flow.hass.config.language = language
    entry = MagicMock()
    entry.entry_id = "abc"
    entry.options = options or {}
    flow.hass.config_entries.async_get_known_entry = MagicMock(return_value=entry)
    flow.handler = "abc"
    sensoren = {}
    if ferien_liste is not None:
        sensoren["schulferien"] = MagicMock(_ferien_info={"ferien_liste": ferien_liste})
    if feiertage_liste is not None:
        sensoren["feiertag"] = MagicMock(_feiertags_info={"feiertage_liste": feiertage_liste})
    flow.hass.data = {DOMAIN: {"abc": sensoren}} if sensoren else {}
    return flow


def _schema_info(result):
    """Liefert (Default, angebotene Codes, Labels) des languages-Feldes."""
    schema = result["data_schema"].schema
    key = next(k for k in schema if str(k) == CONF_LANGUAGES)
    optionen = schema[key].config["options"]
    return key.default(), [o["value"] for o in optionen], [o["label"] for o in optionen]


def test_config_flow_bietet_options_flow_an():
    """Ohne async_get_options_flow zeigt HA keinen "Konfigurieren"-Knopf."""
    assert isinstance(
        SchulferienFlowHandler.async_get_options_flow(MagicMock()),
        SchulferienOptionsFlow,
    )


@pytest.mark.asyncio
async def test_formular_bietet_sprachen_der_region_an():
    """Angeboten wird, was die API für die Region liefert, plus HA-Sprache.

    Warum nicht alle API-Sprachen? Für DE-BY kommen nur DE und EN an; eine
    Liste von ~30 Sprachen, die fast alle nur auf den Fallback führen,
    wäre irreführend. Brückentag/Ostersonntag (feste Namen in 9 Sprachen)
    dürfen die Auswahl deshalb nicht aufblähen.
    """
    ferien = parse_daten([HERBSTFERIEN], ["30.10.2026"], sprachen=["EN"])
    flow = _options_flow(ferien_liste=ferien, feiertage_liste=[], language="en")
    with patch.object(flow, "_hole_sprachnamen", AsyncMock(
        return_value={"DE": "German", "EN": "English"}
    )):
        result = await flow.async_step_init()

    default, codes, labels = _schema_info(result)
    assert codes == ["EN", "DE"]
    assert labels == ["English (EN)", "German (DE)"]
    # Default = HA-Sprache: Speichern ohne Änderung ändert nichts
    assert default == ["EN"]


@pytest.mark.asyncio
async def test_auswahl_als_chips():
    """Dropdown (Chips) statt Checkboxen.

    Warum? Checkboxen stehen immer in Listenreihenfolge und verbergen die
    gewählte Reihenfolge, die den Namen bestimmt. Chips stehen in der
    Reihenfolge des Hinzufügens.
    """
    flow = _options_flow()
    with patch.object(flow, "_hole_sprachnamen", AsyncMock(return_value={})):
        result = await flow.async_step_init()
    schema = result["data_schema"].schema
    key = next(k for k in schema if str(k) == CONF_LANGUAGES)
    assert schema[key].config["mode"] == "dropdown"
    assert schema[key].config["multiple"] is True


@pytest.mark.asyncio
async def test_formular_zeigt_aktuelle_auswahl_als_default():
    """Bereits gewählte Sprachen sind vorausgewählt, in ihrer Reihenfolge."""
    flow = _options_flow(options={CONF_LANGUAGES: ["DE", "EN"]})
    with patch.object(flow, "_hole_sprachnamen", AsyncMock(return_value={})):
        result = await flow.async_step_init()

    default, codes, labels = _schema_info(result)
    assert default == ["DE", "EN"]
    assert codes == ["DE", "EN"]
    # Ohne Sprachnamen (API nicht erreichbar) bleibt das Formular bedienbar
    assert labels == ["DE", "EN"]


@pytest.mark.asyncio
async def test_speichern_normalisiert_die_codes():
    """Gespeichert werden API-Codes in Auswahl-Reihenfolge, ohne Duplikate."""
    flow = _options_flow()
    result = await flow.async_step_init({CONF_LANGUAGES: ["de", "EN", "de"]})
    assert result["type"] == "create_entry"
    assert result["data"] == {CONF_LANGUAGES: ["DE", "EN"]}


@pytest.mark.asyncio
async def test_leere_auswahl_bedeutet_ha_sprache():
    """Nichts gewählt = leere Liste = Sensoren nehmen wieder die HA-Sprache."""
    flow = _options_flow(options={CONF_LANGUAGES: ["DE"]})
    result = await flow.async_step_init({CONF_LANGUAGES: []})
    assert result["data"] == {CONF_LANGUAGES: []}
    assert _feiertag_sensor([]).anzeige_sprachen() == ["EN"]


# ============================================================
# __init__: Reload nach Options-Änderung
# ============================================================

@pytest.mark.asyncio
async def test_options_aenderung_laedt_entry_neu():
    """Nach dem Speichern der Optionen wird der Entry neu geladen.

    Warum? Die Sensoren lesen die Sprachen beim Erstellen. Ohne Reload
    erschienen die neuen Namen erst nach einem HA-Neustart.
    """
    from custom_components.schulferien import async_setup_entry

    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_reload = AsyncMock()
    entry = MagicMock()
    entry.entry_id = "abc"

    await async_setup_entry(hass, entry)

    listener = entry.add_update_listener.call_args.args[0]
    entry.async_on_unload.assert_called_once_with(entry.add_update_listener.return_value)
    await listener(hass, entry)
    hass.config_entries.async_reload.assert_awaited_once_with("abc")
