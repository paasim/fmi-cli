"""Air quality observations and forecasts."""

from datetime import datetime, timedelta

from fmi_cli.api import get_stored_query_chunked
from fmi_cli.xml_helpers import parse_simple_features


def get_airquality(
    fmisid: int = 100662,
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
    parameters: None | list[str] = None,
) -> list[tuple[datetime, str, float]]:
    """Get hourly air quality observations.

    notes on params:
    * fmisid defaults to `100662` which is Helsinki Kallio 2 station
    * resolution can be changed, but it must be at least 1 hour and divide 24 hours
    * setting parameters as `None` returns the default set from the API
    """
    obs = get_stored_query_chunked(
        "urban::observations::airquality::hourly::simple",
        fmisid,
        start_time,
        end_time,
        resolution,
        parameters,
    )
    return [(dt, k, v) for _, dt, k, v in parse_simple_features(obs)]


def get_airquality_forecast(
    fmisid: int = 100662,
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
    parameters: None | list[str] = None,
) -> list[tuple[datetime, str, float]]:
    """Get SILAM air quality forecast.

    notes on params:
    * fmisid defaults to `100662` which is Helsinki Kallio 2 station
    * resolution can be changed to e.g. 10 minutes, but it must divide 1 hour
    * setting parameters as `None` returns the default set from the API
    """
    fc = get_stored_query_chunked(
        "fmi::forecast::silam::airquality::surface::point::simple",
        fmisid,
        start_time,
        end_time,
        resolution,
        parameters,
    )
    return [(dt, k, v) for _, dt, k, v in parse_simple_features(fc)]
