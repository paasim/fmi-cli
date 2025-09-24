import time
from datetime import UTC, datetime, timedelta
from math import isnan

import pytest

from fmi_cli import (
    get_weather,
    get_weather_30year,
    get_weather_daily,
    get_weather_forecast,
)


@pytest.fixture(autouse=True)
def slow_down_tests():
    """yield for test, then wait for 1 seconds before next test for api rate limit"""
    yield
    time.sleep(1)


def test_get_weather_chunked_correctly():
    """Results contain all timestamps for all observations"""
    start_time = datetime(2025, 1, 1, tzinfo=UTC)
    end_time = datetime(2025, 1, 3, tzinfo=UTC)
    resolution = timedelta(minutes=3)

    parameters = ["t2m", "rh"]
    ws = get_weather(
        start_time=start_time,
        end_time=end_time,
        resolution=resolution,
        parameters=parameters,
    )
    is_nan = (isnan(v) for _, _, v in ws)
    assert not all(is_nan)

    times_exp = {start_time}
    while start_time < end_time:
        start_time += resolution
        times_exp.add(start_time)

    for param in parameters:
        times = set()
        for ts, par, _ in ws:
            if par != param:
                continue
            assert ts not in times
            times.add(ts)
        assert times == times_exp


def test_get_weather_daily_fmisid():
    """Results depend on fmisid"""
    w0 = get_weather_daily()
    time.sleep(1)
    w1 = get_weather_daily(fmisid=101004)
    # same observations but different values
    for (t0, k0, _), (t1, k1, _) in zip(w0, w1, strict=True):
        assert t0 == t1
        assert k0 == k1
    assert [x[0] for x in w0] != [x[1] for x in w1]


def test_get_weather_30year_is_1991():
    """Results depend on fmisid"""
    years = {dt.year for dt, _, _ in get_weather_30year()}
    assert years == {1991}


def test_get_weather_forecast_resolution_and_retuns_values():
    """API returns the requested resolution."""
    # default is hourly
    res = timedelta(minutes=30)
    fc = get_weather_forecast(resolution=res)
    mins = {d.minute for d, _, _ in fc}
    is_nan = (isnan(v) for _, _, v in fc)
    assert mins == {0, 30}
    assert not all(is_nan)


def test_get_weather_hourly_long():
    """Daily weather works for long query period"""
    start_time = datetime(2022, 1, 1, tzinfo=UTC)
    end_time = datetime(2022, 2, 3, tzinfo=UTC)
    w0 = get_weather(start_time=start_time, end_time=end_time)
    n_temp_obs = sum(1 for w in w0 if w[1] == "t2m")
    assert n_temp_obs == (end_time - start_time).total_seconds() // 60 // 60 + 1


def test_get_weather_daily_long():
    """Daily weather works for long query period"""
    start_date = datetime(2022, 1, 1, tzinfo=UTC).date()
    end_date = datetime(2023, 2, 1, tzinfo=UTC).date()
    w0 = get_weather_daily(start_date=start_date, end_date=end_date)
    n_temp_obs = sum(1 for w in w0 if w[1] == "tday")
    assert n_temp_obs == (end_date - start_date).days + 1
