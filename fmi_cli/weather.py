"""Weather observations and forecasts."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta

from fmi_cli.api import (
    get_meps_forecast,
    get_stored_query,
    get_stored_query_multipoint,
    get_stored_query_multipoint_all,
)
from fmi_cli.xml_helpers import parse_multipoint_fmisids


def get_weather(
    fmisid: int = 100971,
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
    parameters: None | list[str] = None,
) -> list[tuple[datetime, str, float]]:
    """Get (hourly) weather observations.

    notes on params:
    * fmisid defaults to `100971` which is Helsinki Kaisaniemi station
    * resolution can be changed to e.g. 10 minutes, but it must divide 1 hour
    * setting parameters as `None` returns the default set from the API
    """
    return get_stored_query_multipoint(
        "fmi::observations::weather",
        fmisid,
        start_time,
        end_time,
        resolution,
        parameters,
    )


def get_weather_all(
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
) -> Iterator[tuple[int, datetime, str, float]]:
    """Get all (hourly) weather observations."""
    return get_stored_query_multipoint_all(
        "fmi::observations::weather",
        start_time,
        end_time,
        resolution,
    )


def get_weather_30year(
    fmisid: int = 100971,
    start_date: None | date = None,
    end_date: None | date = None,
) -> list[tuple[date, str, float]]:
    """Get 30 year normal period weather observations.

    The year is set to the beginning of the period, e.g. 1991 with
    default parameter values.

    notes on params:
    * fmisid defaults to `100971` which is Helsinki Kaisaniemi station
    * sensible (non-default) values for `start_date` and `end_date` are the first
      year of the desired period
    """
    # this should never get chunked so its fine
    obs = get_stored_query(
        "fmi::observations::weather::monthly::30year::multipointcoverage",
        fmisid,
        None if start_date is None else datetime.combine(start_date, time(0), UTC),
        None if end_date is None else datetime.combine(end_date, time(0), UTC),
        None,
        None,
    )
    return [(dt.date(), k, v) for _, dt, k, v in parse_multipoint_fmisids([obs])]


def get_weather_forecast(
    fmisid: int = 100971,
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
    parameters: None | list[str] = None,
) -> list[tuple[datetime, str, float]]:
    """Get weather forecast from Harmonie (MEPS) -model.

    Note that this simply calls `get_meps_forecast` (as does `get_radiation_forecast`),
    which means that by default they return the same forecasted values.

    A more sensible value for `parameters` for simply weather might be e.g.
    ```
    ["Temperature","Humidity","WindSpeedMS","PrecipitationAmount","TotalCloudCover"]
    ```

    notes on params:
    * fmisid defaults to `100971` which is Helsinki Kaisaniemi station
    * resolution can be changed to e.g. 10 minutes, but it must divide 1 hour
    """
    return get_meps_forecast(fmisid, start_time, end_time, resolution, parameters)
