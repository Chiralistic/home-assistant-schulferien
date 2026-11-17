"""Unit Tests für die Kalender-Entitäten (calendar.py)."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.schulferien.calendar import FerienKalender, async_setup_entry
from custom_components.schulferien.const import DOMAIN
from homeassistant.util import dt as dt_util

TZ = dt_util.get_time_zone("Europe/Berlin")


def _sensor(info_attr, listen_key, eintraege):
    """Fake-Sensor mit der Info-Dict-Struktur der echten Sensoren."""
    sensor = MagicMock()
    setattr(sensor, info_attr, {listen_key: eintraege})
    return sensor


def _hass(sensoren, entry_id="entry_by"):
    hass = MagicMock()
    hass.data = {DOMAIN: {entry_id: sensoren}}
    return hass


def _kalender(hass, sensor_key="schulferien", entry_id="entry_by"):
    if sensor_key == "schulferien":
        listen_key, info_attr = "ferien_liste", "_ferien_info"
    else:
        listen_key, info_attr = "feiertage_liste", "_feiertags_info"
    return FerienKalender(
        hass,
        entry_id,
        sensor_key=sensor_key,
        listen_key=listen_key,
        info_attr=info_attr,
        name="Test",
        unique_id="kalender_test",
        object_id="test",
        location="Deutschland, Bayern",
    )


FERIEN = [
    {"name": "Weihnachtsferien", "start_datum": date(2026, 12, 24),
     "end_datum": date(2027, 1, 8)},
    {"name": "Buß- und Bettag", "start_datum": date(2026, 11, 18),
     "end_datum": date(2026, 11, 18)},
    {"name": "Herbstferien", "start_datum": date(2026, 11, 2),
     "end_datum": date(2026, 11, 6)},
]


@pytest.fixture(autouse=True)
def _berlin():
    """dt_util auf Europe/Berlin, damit Datumsgrenzen lokal geprueft werden."""
    alt = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(TZ)
    yield
    dt_util.set_default_time_zone(alt)


@pytest.mark.asyncio
async def test_setup_creates_two_calendars_with_expected_ids():
    """Pro Entry ein Schulferien- und ein Feiertags-Kalender.

    Warum stabile unique_ids mit 'kalender_'-Präfix? Die Sensoren nutzen
    bereits 'schulferien_DE_BY' — ohne Präfix gäbe es keine Kollision (andere
    Domain), aber der Präfix hält die IDs auch im Registry-Export eindeutig.
    """
    hass = _hass({})
    entry = MagicMock()
    entry.entry_id = "entry_by"
    entry.data = {"land": "DE", "region": "DE-BY",
                  "land_name": "Deutschland", "region_name": "Bayern"}
    added = []

    await async_setup_entry(hass, entry, added.extend)

    assert [k.unique_id for k in added] == [
        "kalender_schulferien_DE_BY", "kalender_feiertage_DE_BY"]
    assert [k.suggested_object_id for k in added] == [
        "schulferien_de_by", "feiertage_de_by"]
    assert added[0].name == "Schulferien - Deutschland (Bayern)"


def test_inclusive_api_end_becomes_exclusive_calendar_end():
    """API-endDate ist inklusiv, HA erwartet bei Ganztagsterminen exklusives Ende.

    Ohne +1 Tag würde ein eintägiger Termin (Buß- und Bettag) start == end
    haben und in der Kalender-Karte gar nicht erscheinen, und der letzte
    Ferientag würde fehlen.
    """
    hass = _hass({"schulferien": _sensor("_ferien_info", "ferien_liste", FERIEN)})
    events = _kalender(hass)._events()

    bettag = next(e for e in events if e.summary == "Buß- und Bettag")
    assert bettag.start == date(2026, 11, 18)
    assert bettag.end == date(2026, 11, 19)
    assert bettag.location == "Deutschland, Bayern"


def test_events_sorted_by_start():
    """Die API liefert unsortiert und Brückentage werden hinten angehängt."""
    hass = _hass({"schulferien": _sensor("_ferien_info", "ferien_liste", FERIEN)})
    starts = [e.start for e in _kalender(hass)._events()]
    assert starts == sorted(starts)


def test_event_is_current_or_next():
    """`event` bestimmt den on/off-State: laufender Termin, sonst der nächste."""
    hass = _hass({"schulferien": _sensor("_ferien_info", "ferien_liste", FERIEN)})
    kalender = _kalender(hass)

    with patch.object(dt_util, "now", return_value=datetime(2026, 11, 18, 10, tzinfo=TZ)):
        assert kalender.event.summary == "Buß- und Bettag"
    with patch.object(dt_util, "now", return_value=datetime(2026, 11, 19, 0, 1, tzinfo=TZ)):
        assert kalender.event.summary == "Weihnachtsferien"
    with patch.object(dt_util, "now", return_value=datetime(2027, 2, 1, tzinfo=TZ)):
        assert kalender.event is None


@pytest.mark.asyncio
async def test_get_events_filters_overlapping_range():
    """Nur Termine, die das angefragte Fenster überschneiden (Ende exklusiv)."""
    hass = _hass({"schulferien": _sensor("_ferien_info", "ferien_liste", FERIEN)})
    kalender = _kalender(hass)

    # Woche 16.11. - 23.11. (00:00, exklusiv): nur der Bettag
    events = await kalender.async_get_events(
        hass, datetime(2026, 11, 16, tzinfo=TZ), datetime(2026, 11, 23, tzinfo=TZ))
    assert [e.summary for e in events] == ["Buß- und Bettag"]

    # Fenster endet genau am Ferienbeginn 00:00 -> Weihnachtsferien nicht dabei
    events = await kalender.async_get_events(
        hass, datetime(2026, 12, 1, tzinfo=TZ), datetime(2026, 12, 24, tzinfo=TZ))
    assert not events

    # Fenster endet am Ferienbeginn mittags -> Weihnachtsferien dabei
    events = await kalender.async_get_events(
        hass, datetime(2026, 12, 1, tzinfo=TZ), datetime(2026, 12, 24, 12, tzinfo=TZ))
    assert [e.summary for e in events] == ["Weihnachtsferien"]


@pytest.mark.asyncio
async def test_get_events_uses_local_dates_for_utc_queries():
    """Das Frontend fragt in UTC an; Mitternacht Berlin ist 23:00 UTC am Vortag.

    Ohne Umrechnung in lokale Zeit würde ein Tagesfenster für den 18.11. als
    17.11. interpretiert und den Bettag verfehlen.
    """
    hass = _hass({"schulferien": _sensor("_ferien_info", "ferien_liste", FERIEN)})
    events = await _kalender(hass).async_get_events(
        hass,
        datetime(2026, 11, 17, 23, tzinfo=dt_util.UTC),
        datetime(2026, 11, 18, 23, tzinfo=dt_util.UTC),
    )
    assert [e.summary for e in events] == ["Buß- und Bettag"]


def test_feiertag_calendar_reads_feiertage_liste():
    """Der Feiertags-Kalender liest _feiertags_info['feiertage_liste']."""
    feiertage = [{"name": "1. Weihnachtstag", "start_datum": date(2026, 12, 25),
                  "end_datum": date(2026, 12, 25)}]
    hass = _hass({"feiertag": _sensor("_feiertags_info", "feiertage_liste", feiertage)})
    events = _kalender(hass, sensor_key="feiertag")._events()
    assert [e.summary for e in events] == ["1. Weihnachtstag"]


@pytest.mark.parametrize("sensoren", [
    {},                                                     # Sensor (noch) nicht registriert
    {"schulferien": _sensor("_ferien_info", "ferien_liste", None)},  # Liste None
    {"schulferien": _sensor("_ferien_info", "ferien_liste", [])},    # noch kein Fetch
])
def test_missing_data_yields_empty_calendar(sensoren):
    """Plattformen laden parallel und der erste Fetch kann scheitern.

    Der Kalender muss dann leer (State off) sein statt mit einer Exception
    'nicht verfügbar' zu werden.
    """
    kalender = _kalender(_hass(sensoren))
    assert kalender._events() == []  # pylint: disable=protected-access
    assert kalender.event is None


def test_invalid_entries_are_skipped():
    """Ein kaputter Eintrag darf nicht den ganzen Kalender leeren."""
    eintraege = FERIEN + [{"name": "Kaputt", "start_datum": None,
                           "end_datum": date(2026, 1, 1)}]
    hass = _hass({"schulferien": _sensor("_ferien_info", "ferien_liste", eintraege)})
    assert len(_kalender(hass)._events()) == len(FERIEN)  # pylint: disable=protected-access


def test_entries_isolated_per_config_entry():
    """Multi-Region: jeder Kalender liest nur die Sensoren seines Entries."""
    hass = MagicMock()
    hass.data = {DOMAIN: {
        "entry_by": {"schulferien": _sensor("_ferien_info", "ferien_liste", FERIEN)},
        "entry_nw": {"schulferien": _sensor("_ferien_info", "ferien_liste", [])},
    }}
    assert _kalender(hass, entry_id="entry_by")._events()
    assert _kalender(hass, entry_id="entry_nw")._events() == []
