import time
from datetime import UTC, datetime, timedelta

import pytest

from fmi_cli import get_radiation, get_radiation_forecast


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
    """API returns values in the future values."""
    now = datetime.now(UTC)
    in_future = (dt > now for dt, _, _ in get_radiation_forecast())
    assert all(in_future)
