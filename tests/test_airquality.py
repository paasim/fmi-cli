import time

import pytest

from fmi_cli import get_airquality, get_airquality_forecast


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
    w0 = get_airquality_forecast()
    time.sleep(1)
    w1 = get_airquality_forecast(fmisid=101932)
    # same observations but different values
    for (t0, k0, _), (t1, k1, _) in zip(w0, w1, strict=True):
        assert t0 == t1
        assert k0 == k1
    assert [x[0] for x in w0] != [x[1] for x in w1]
