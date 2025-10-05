import time

import pytest

from fmi_cli import get_airquality, get_airquality_all, get_airquality_forecast


@pytest.fixture(autouse=True)
def slow_down_tests():
    """yield for test, then wait for 1 seconds before next test for api rate limit"""
    yield
    time.sleep(1)


def test_get_airquality_params():
    """API returns the requested parameters."""
    # this is not the default
    params_req = ["PM10_PT1H_avg", "PM25_PT1H_avg", "AQINDEX_PT1H_avg"]
    params = {key for _, key, _ in get_airquality(parameters=params_req)}
    assert set(params_req) == params


def test_get_airquality_forecast_fmisid():
    """Results depend on fmisid"""
    obs_default_fmisid = {(ts, k): v for ts, k, v in get_airquality_forecast()}
    time.sleep(1)
    matching_keys = 0
    differing_vals = 0
    for ts, k, v in get_airquality_forecast(fmisid=103097):
        if (ts, k) not in obs_default_fmisid:
            continue
        matching_keys += 1
        if obs_default_fmisid[(ts, k)] != v:
            differing_vals += 1
    # there must be overlap in keys and values that differ
    assert matching_keys > 1
    assert differing_vals > 1


def test_airquality_all():
    """API returns obs for many stations."""
    aq_all = list(get_airquality_all())

    # multiple fmisids
    fmisids = {x[0] for x in aq_all}
    fmisids_at_least = 80
    assert len(fmisids) > fmisids_at_least
