"""Helper methods for interacting with the API."""

import logging
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from time import sleep
from urllib.parse import urlencode

from requests import get

from fmi_cli.xml_helpers import parse_simple_features

logger = logging.getLogger(__package__)
logger.addHandler(logging.StreamHandler())

TS_FMT = "%FT%TZ"
WFS_PARAMS = {"service": "WFS", "version": "2.0.0"}
WFS_PATH = "https://opendata.fmi.fi/wfs"
META_PATH = "https://opendata.fmi.fi/meta"
TIMEOUT = 20


def _query(path: str, params: dict[str, str]) -> ET.Element:
    resp = get(path, params=urlencode(params, safe=":"), timeout=TIMEOUT)
    resp.raise_for_status()
    return ET.fromstring(resp.content)  # noqa: S314


def query_wfs(params: dict[str, str]) -> ET.Element:
    """Query from the download (WFS) service."""
    return _query(WFS_PATH, WFS_PARAMS | params)


def query_meta(params: dict[str, str]) -> ET.Element:
    """Query from the metadata service."""
    return _query(META_PATH, params)


def get_capabilities() -> list[str]:
    """List capabilities of the API."""
    cap = query_wfs({"request": "getCapabilities"})
    return [o.attrib["name"] for o in cap.findall("{*}OperationsMetadata/{*}Operation")]


def get_stored_query(  # noqa: PLR0913
    query_id: str,
    fmisid: int,
    start_time: None | datetime,
    end_time: None | datetime,
    resolution: None | timedelta,
    parameters: None | list[str],
) -> ET.Element:
    """Get any stored query from FMI API.

    Resulting XML is returned as is. Queries can be listed by using the
    `StoredQueries`-object.

    Note that this might return an error if `start_time` and `end_time` specify
    a range that is too long for the API. See `stored_query_chunked` for a safe version
    that splits the query into chunks.
    """
    params = {
        "request": "getFeature",
        "fmisid": str(fmisid),
        "storedquery_id": query_id,
    }
    if start_time is not None:
        params["starttime"] = start_time.astimezone(UTC).strftime(TS_FMT)
    if end_time is not None:
        params["endtime"] = end_time.astimezone(UTC).strftime(TS_FMT)
    if resolution is not None:
        params["timestep"] = str(int(resolution.total_seconds() // 60))
    if parameters is not None and len(parameters) > 0:
        params["parameters"] = ",".join(parameters)
    return query_wfs(params)


def get_stored_query_chunked(  # noqa: PLR0913
    query_id: str,
    fmisid: int,
    start_time: None | datetime,
    end_time: None | datetime,
    resolution: timedelta,
    parameters: None | list[str],
) -> Iterator[ET.Element]:
    """Get any stored query from FMI API.

    Splits the query into multiple chunks needed.

    Resulting XML is returned as is.
    """
    if start_time is None or end_time is None:
        yield get_stored_query(
            query_id, fmisid, start_time, end_time, resolution, parameters
        )
        return
    lims = _mk_limits(start_time, end_time, resolution)
    start, end = next(lims)
    logger.info("querying for %s - %s", start, end)
    yield get_stored_query(query_id, fmisid, start, end, resolution, parameters)
    for start, end in lims:
        # to ensure api limits (600 requests in 5 mins) are respected
        # (this should allow for sleeping only for 0.5 seconds)
        sleep(1)
        logger.info("querying for %s - %s", start, end)
        yield get_stored_query(query_id, fmisid, start, end, resolution, parameters)


def get_meps_forecast(
    fmisid: int,
    start_time: None | datetime = None,
    end_time: None | datetime = None,
    resolution: timedelta = timedelta(hours=1),
    parameters: None | list[str] = None,
) -> list[tuple[datetime, str, float]]:
    """Get Harmonie (MEPS) -forecast.

    Resulting XML is returned as is.

    Used by `get_weather_forecast` and `get_radiation_forecast`.
    """
    fc = get_stored_query_chunked(
        "fmi::forecast::meps::surface::point::simple",
        fmisid,
        start_time,
        end_time,
        resolution,
        parameters,
    )
    return [(dt, k, v) for _, dt, k, v in parse_simple_features(fc)]


def _mk_limits(
    start_time: datetime,
    end_time: datetime,
    resolution: timedelta,
) -> Iterator[tuple[datetime, datetime]]:
    secs = resolution.total_seconds()
    if secs > 60 * 60 and (24 * 60 * 60) % secs != 0:
        msg = "lower resolution than an hour must divide 24 hours evenly"
        raise ValueError(msg)
    if secs < 60 * 60 and (60 * 60) % secs != 0:
        msg = "higher resolution than an hour must divide the hour evenly"
        raise ValueError(msg)
    # at most a week of hourly data at a time
    # - daily data could be downloaded year a time but 168 days is fine
    diff = timedelta(seconds=min(7 * 24 * 60 * 60 // secs, 168) * secs)
    start = start_time
    while start <= end_time:
        end = min(start + diff, end_time)
        yield (start, end)
        start = end + resolution
