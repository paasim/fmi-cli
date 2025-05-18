"""Solar radiation observations and forecasts."""

from datetime import datetime, timedelta

from fmi_cli.api import get_meps_forecast, get_stored_query_chunked
from fmi_cli.xml_helpers import parse_simple_features


def get_radiation(
    fmisid: int = 101004,
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
    parameters: None | list[str] = None,
) -> list[tuple[datetime, str, float]]:
    """Get (hourly) solar radiation observations.

    notes on params:
    * fmisid defaults to `101004` which is Helsinki Kumpula station
    * resolution can be changed to e.g. 1 minutes, but it must divide 1 hour
    * setting parameters as `None` returns the default set from the API
    """
    obs = get_stored_query_chunked(
        "fmi::observations::radiation::simple",
        fmisid,
        start_time,
        end_time,
        resolution,
        parameters,
    )
    return [(dt, k, v) for _, dt, k, v in parse_simple_features(obs)]


def get_radiation_forecast(
    fmisid: int = 101004,
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
    parameters: None | list[str] = None,
) -> list[tuple[datetime, str, float]]:
    """Get solar radiation forecast from Harmonie (MEPS) -model.

    Note that this simply calls `get_meps_forecast` (as does `get_weather_forecast`),
    which means that by default they return the same forecasted values.

    A more sensible value for `parameters` for simply solar radiation might be e.g.
    ```
    ["RadiationGlobal", "RadiationLW", "RadiationSW"]
    ```

    notes on params:
    * fmisid defaults to `101004` which is Helsinki Kumpula station
    * resolution can be changed to e.g. 1 minutes, but it must divide 1 hour
    """
    return get_meps_forecast(fmisid, start_time, end_time, resolution, parameters)
