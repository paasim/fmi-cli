import time

import pytest

from fmi_cli import ObservableProperties, Stations, StoredQueries
from fmi_cli.api import get_capabilities


@pytest.fixture(autouse=True)
def slow_down_tests():
    """yield for test, then wait for 1 seconds before next test for api rate limit"""
    # test theze from fmi_cli import ObservableProperties, Stations, StoredQueries
    yield
    time.sleep(1)


def test_get_capabilities():
    """The capabilities that are used are available."""
    caps = get_capabilities()
    assert "ListStoredQueries" in caps
    assert "DescribeStoredQueries" in caps
    assert "GetFeature" in caps


def test_stations():
    """Stations can be queried and listed."""
    stations = Stations.get()
    weather_helsinki_ids = [s.fmisid for s in stations.weather("helsinki")]
    assert 100971 in weather_helsinki_ids  # noqa: PLR2004, kaisaniemi
    assert 100968 in weather_helsinki_ids  # noqa: PLR2004, helsinki-vantaa

    airquality_ids = [s.fmisid for s in stations.airquality()]
    assert 100662 in airquality_ids  # noqa: PLR2004, helsinki kallio 2
    assert 101942 in airquality_ids  # noqa: PLR2004, sodankylä heikinheimo

    radiation_ids = [s.fmisid for s in stations.radiation()]
    assert 101004 in radiation_ids  # noqa: PLR2004, helsinki kumpula
    assert 100968 in radiation_ids  # noqa: PLR2004, helsinki-vantaa


def test_observable_properties():
    """Observable properties can be queried and listed."""
    properties = ObservableProperties.get()
    rad_obs = [p.id for p in properties.find_matches("radiation", forecasts=False)]
    rad_fc = [p.id for p in properties.find_matches("radiation", observations=False)]
    rad_all = [p.id for p in properties.find_matches("radiation")]

    assert set(rad_all) == set(rad_obs) | set(rad_fc)

    for p in properties.find_matches(r"p1m$", forecasts=False):
        assert "p1m" in p.id


def test_queries():
    """Queries can be queried and listed."""
    queries = StoredQueries.get()
    q_meps_simple_ids = [q.id for q in queries.find_matches("meps.*simple")]
    assert "fmi::forecast::meps::surface::point::simple" in q_meps_simple_ids
