"""Network failures and missing coverage must never become a negative holiday answer."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.schulferien import schulferien_sensor as school
from custom_components.schulferien import feiertag_sensor as public
from custom_components.schulferien import binary_sensor as binary
from custom_components.schulferien.fetch_state import FetchState

NOW = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
CONFIG = {
    "name": "Test - Bayern", "land": "DE", "region": "DE-BY",
    "land_name": "Deutschland", "region_name": "Bayern", "brueckentage": [],
    "schulferien_entity_id": "sensor.school", "feiertag_entity_id": "sensor.public",
}
DATA = [{"startDate": "2026-11-08", "endDate": "2026-11-09",
         "name": [{"language": "DE", "text": "Testferien"}]}]


@pytest.fixture(params=[school, public], ids=["school", "public"])
def source(request):
    module = request.param
    if module is school:
        sensor = school.SchulferienSensor(MagicMock(), CONFIG)
        tomorrow = school.SchulferienMorgenSensor(sensor)
        info = sensor._ferien_info
    else:
        sensor = public.FeiertagSensor(MagicMock(), CONFIG)
        tomorrow = public.FeiertagMorgenSensor(sensor)
        info = sensor._feiertags_info
    return module, sensor, tomorrow, info


async def test_startup_failure_recovers_same_day_without_bad_fallback(source):
    module, sensor, tomorrow, info = source
    session = MagicMock()
    with patch.object(module.dt_util, "now", return_value=NOW) as clock, \
            patch.object(module, "fetch_data", AsyncMock(side_effect=[{}, DATA])) as fetch:
        assert sensor.native_value is None and tomorrow.native_value is None
        await sensor.async_update(session)
        assert not sensor.available and not tomorrow.available
        assert info["letztes_update"] is None
        assert sensor.extra_state_attributes["data_status"] == "error"
        assert fetch.await_count == 1
        assert "/Holidays/" not in fetch.call_args.args[0]
        clock.return_value = NOW + timedelta(seconds=59)
        await sensor.async_update(session)
        assert fetch.await_count == 1
        clock.return_value = NOW + timedelta(minutes=1)
        await sensor.async_update(session)
        assert fetch.await_count == 2
        assert sensor.available and tomorrow.available
        assert sensor.native_value in ("ferientag", "feiertag")
        assert info["letztes_update"] == clock.return_value
        assert sensor._fetch_state.retry_at is None


async def test_empty_year_response_is_missing_coverage_not_no_holidays(source):
    module, sensor, tomorrow, info = source
    with patch.object(module.dt_util, "now", return_value=NOW) as clock, \
            patch.object(module, "fetch_data", AsyncMock(return_value=[])) as fetch:
        await sensor.async_update(MagicMock())
        assert sensor.native_value is None and tomorrow.native_value is None
        assert not sensor.available
        assert info["letztes_update"] is None
        assert sensor.extra_state_attributes["data_status"] == "no_data"
        clock.return_value += timedelta(hours=23)
        await sensor.async_update(MagicMock())
        assert fetch.await_count == 1
        clock.return_value += timedelta(hours=1)
        await sensor.async_update(MagicMock())
        assert fetch.await_count == 2


@pytest.mark.parametrize("bad", [None, {}, {"error": "failed"}, "invalid",
    [{"name": []}], [{"startDate": "bad", "endDate": "bad"}],
    [{"startDate": "2026-11-09", "endDate": "2026-11-08"}],
    DATA + [{"startDate": "2026-11-08"}]])
async def test_invalid_response_keeps_previous_calendar_but_never_marks_success(source, bad):
    module, sensor, tomorrow, info = source
    with patch.object(module.dt_util, "now", return_value=NOW) as clock, \
            patch.object(module, "fetch_data", AsyncMock(side_effect=[DATA, bad])):
        await sensor.async_update(MagicMock())
        old = dict(info)
        clock.return_value += timedelta(days=7)
        await sensor.async_update(MagicMock())
        assert info["letztes_update"] == old["letztes_update"]
        for key in info:
            if key.endswith("liste"):
                assert info[key] == old[key]
        assert not sensor.available and not tomorrow.available
        assert sensor._fetch_state.retry_at > clock.return_value
        assert not sensor._update_faellig(clock.return_value)


async def test_valid_negative_day_and_midnight_remain_dynamic(source):
    module, sensor, tomorrow, _ = source
    with patch.object(module.dt_util, "now", return_value=NOW) as clock, \
            patch.object(module, "fetch_data", AsyncMock(return_value=DATA)) as fetch:
        await sensor.async_update(MagicMock())
        assert sensor.native_value in ("ferientag", "feiertag")
        clock.return_value += timedelta(days=1)
        assert sensor.native_value in ("ferientag", "feiertag")
        assert tomorrow.native_value in ("kein_ferientag", "kein_feiertag")
        clock.return_value += timedelta(days=1)
        await sensor.async_update(MagicMock())
        assert sensor.native_value in ("kein_ferientag", "kein_feiertag")
        assert fetch.await_count == 1
        clock.return_value = NOW + timedelta(days=365)
        assert sensor.available and not tomorrow.available
        clock.return_value += timedelta(days=1)
        assert not sensor.available


@pytest.mark.parametrize("error", [asyncio.TimeoutError(), ValueError("bad JSON")])
async def test_exceptions_release_inflight_guard(source, error):
    module, sensor, _, _ = source
    with patch.object(module.dt_util, "now", return_value=NOW), \
            patch.object(module, "fetch_data", AsyncMock(side_effect=error)):
        await sensor.async_update(MagicMock())
        assert not sensor._fetch_state.in_progress
        assert sensor._fetch_state.status == "error"
        assert sensor._update_faellig(NOW + timedelta(minutes=1))


async def test_overlapping_updates_only_issue_one_request(source):
    module, sensor, _, _ = source
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(*_args):
        started.set()
        await release.wait()
        return DATA

    with patch.object(module.dt_util, "now", return_value=NOW), \
            patch.object(module, "fetch_data", AsyncMock(side_effect=delayed)) as fetch:
        task = asyncio.create_task(sensor.async_update(MagicMock()))
        await started.wait()
        await sensor.async_update(MagicMock())
        release.set()
        await task
        assert fetch.await_count == 1
        assert not sensor._fetch_state.in_progress


def test_backoff_is_bounded_and_weekly_guard_cannot_override_failure():
    state = FetchState()
    clock = NOW
    for delay in [1, 5, 15, 60, 360, 360, 360]:
        state.failed(clock)
        assert state.retry_at == clock + timedelta(minutes=delay)
        assert not state.due(clock, NOW - timedelta(days=8), clock)
        assert state.due(state.retry_at, NOW - timedelta(days=8), clock)
        clock = state.retry_at
    state.succeeded(NOW.date() + timedelta(days=365))
    assert state.failures == 0 and state.retry_at is None
    assert not state.due(NOW + timedelta(days=6), NOW, NOW)
    assert not state.due((NOW + timedelta(days=7)).replace(hour=2), NOW, NOW)
    assert state.due((NOW + timedelta(days=7)).replace(hour=3), NOW, NOW)


CLASSES = [binary.SchulferienFeiertagBinarySensor, binary.SchulferienFeiertagMorgenBinarySensor,
           binary.SchulferienOnlyBinarySensor, binary.SchulferienOnlyMorgenBinarySensor,
           binary.FeiertagOnlyBinarySensor, binary.FeiertagOnlyMorgenBinarySensor]


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("a", [True, False, None, "restored"])
@pytest.mark.parametrize("b", [True, False, None])
async def test_binary_three_valued_logic_preserves_only_variants(cls, a, b):
    def state(value, positive):
        if value is None:
            return None
        return SimpleNamespace(state=positive if value else "kein_" + positive,
                               attributes={"restored": value == "restored"})
    hass = MagicMock()
    hass.states.get.side_effect = lambda entity_id: {
        "sensor.school": state(a, "ferientag"),
        "sensor.public": state(b, "feiertag"),
    }[entity_id]
    sensor = cls(hass, CONFIG)
    assert sensor.is_on is None
    await sensor.async_update()
    values = {"schulferien": None if a == "restored" else a, "feiertag": b}
    needed = [values[k] for k in sensor._state_keys]
    expected = True if True in needed else None if None in needed else False
    assert sensor.is_on is expected
