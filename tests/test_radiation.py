import time
from datetime import UTC, datetime, timedelta

import pytest

from fmi_cli import get_radiation, get_radiation_all, get_radiation_forecast


@pytest.fixture(autouse=True)
def slow_down_tests():
    """yield for test, then wait for 1 seconds before next test for api rate limit"""
    yield
    time.sleep(1)


def test_get_radiation_range():
    """API returns the requested range."""
    # this is not the default
    start_time = datetime(2025, 5, 10, tzinfo=UTC)
    resolution = timedelta(minutes=10)
    end_time = start_time + timedelta(days=1)
    rad = get_radiation(start_time=start_time, end_time=end_time, resolution=resolution)

    # all different times between start and end
    times_exp = {start_time}
    while start_time < end_time:
        start_time += resolution
        times_exp.add(start_time)

    times = {dt for dt, _, _ in rad}
    assert times_exp == times


def test_get_radiation_forecast_values_in_future():
    """API returns values in the future."""
    now = datetime.now(UTC)
    forecast_timestamps = {dt for dt, _, _ in get_radiation_forecast()}
    min_ts = min(forecast_timestamps)
    for ts in forecast_timestamps:
        assert ts == min_ts or ts > now  # at most one timestamp can be in the past


def test_radiation_all_works():
    """API returns all values in dt range."""
    start_time = datetime(2025, 9, 1, tzinfo=UTC)
    end_time = datetime(2025, 9, 10, tzinfo=UTC)
    resolution = timedelta(hours=1)
    rad_all = list(get_radiation_all(start_time, end_time, resolution))

    # all different times between start and end
    times_exp = {start_time}
    while start_time < end_time:
        start_time += resolution
        times_exp.add(start_time)

    times = {x[1] for x in rad_all}
    assert times_exp == times

    # multiple fmisids
    fmisids = {x[0] for x in rad_all}
    fmisids_at_least = 5
    assert len(fmisids) > fmisids_at_least
