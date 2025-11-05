"""Helper methods for interacting with the API."""

import logging
import os
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from time import sleep

from requests import HTTPError, Response, Session
from requests.adapters import HTTPAdapter

from fmi_cli.xml_helpers import parse_multipoint_fmisids, parse_multipoint_points

logger = logging.getLogger(__package__)
logger.addHandler(logging.StreamHandler())

TS_FMT = "%FT%TZ"
WFS_PARAMS = {"service": "WFS", "version": "2.0.0"}
WFS_PATH = "https://opendata.fmi.fi/wfs"
META_PATH = "https://opendata.fmi.fi/meta"
TIMEOUT = int(os.environ.get("FMI_CLI_TIMEOUT", "120"))
CAP_NS = {"ns2": "http://www.opengis.net/ows/1.1"}


def _raise_for_status(resp: Response) -> None:
    """Add HTTP error content as a note to the exception."""
    try:
        resp.raise_for_status()
    except HTTPError as e:
        if "text/xml" in resp.headers.get("Content-Type", ""):
            e.add_note(resp.content.decode())
        raise


def _query(s: Session, path: str, params: dict[str, str]) -> ET.Element:
    resp = s.get(path, params=params, timeout=TIMEOUT)
    _raise_for_status(resp)
    return ET.fromstring(resp.content)  # noqa: S314


def init_session(max_retries: int = 3) -> Session:
    """Initialize a session with retries (defaulting to 3)."""
    s = Session()
    s.mount("https://opendata.fmi.fi", HTTPAdapter(max_retries=max_retries))
    return s


def query_wfs(params: dict[str, str], session: Session | None) -> ET.Element:
    """Query from the download (WFS) service."""
    with session if session is not None else init_session() as s:
        return _query(s, WFS_PATH, WFS_PARAMS | params)


def query_meta(params: dict[str, str]) -> ET.Element:
    """Query from the metadata service."""
    with init_session() as s:
        return _query(s, META_PATH, params)


def get_capabilities() -> list[str]:
    """List capabilities of the API."""
    cap = query_wfs({"request": "getCapabilities"}, None)
    cap_path = "ns2:OperationsMetadata/ns2:Operation"
    return [o.attrib["name"] for o in cap.findall(cap_path, CAP_NS)]


def get_stored_query(  # noqa: PLR0913
    query_id: str,
    place: int | tuple[float, float, float, float],
    start_time: None | datetime,
    end_time: None | datetime,
    resolution: None | timedelta,
    session: None | Session,
    parameters: None | list[str] = None,
) -> ET.Element:
    """Get any stored query from FMI API.

    Resulting XML is returned as is. Queries can be listed by using the
    `StoredQueries`-object. If `session` is `None`, it is automatically created.

    Note that this might return an error if `start_time` and `end_time` specify
    a range that is too long for the API. See `stored_query_chunked` for a safe version
    that splits the query into chunks.
    """
    params = {
        "request": "getFeature",
        "storedquery_id": query_id,
    }
    match place:
        case int():
            params["fmisid"] = str(place)
        case tuple():
            params["bbox"] = ",".join(str(x) for x in place)

    if start_time is not None:
        params["starttime"] = start_time.astimezone(UTC).strftime(TS_FMT)
    if end_time is not None:
        params["endtime"] = end_time.astimezone(UTC).strftime(TS_FMT)
    if resolution is not None:
        params["timestep"] = str(int(resolution.total_seconds() // 60))
    if parameters is not None and len(parameters) > 0:
        params["parameters"] = ",".join(parameters)
    return query_wfs(params, session)


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
    with init_session() as s:
        if start_time is None or end_time is None:
            yield get_stored_query(
                query_id, fmisid, start_time, end_time, resolution, s, parameters
            )
            return
        lims = _mk_limits(start_time, end_time, resolution)
        start, end = next(lims)
        logger.info("querying for %s - %s", start, end)
        yield get_stored_query(query_id, fmisid, start, end, resolution, s, parameters)
        for start, end in lims:
            # to ensure api limits (600 requests in 5 mins) are respected
            # (it should allow for sleeping only for 0.5 seconds)
            sleep(1)
            logger.info("querying for %s - %s", start, end)
            yield get_stored_query(
                query_id, fmisid, start, end, resolution, s, parameters
            )


def get_stored_query_chunked_bbox(
    query_id: str,
    bboxes: list[tuple[float, float, float, float]],
    start_time: None | datetime,
    end_time: None | datetime,
    resolution: timedelta,
) -> Iterator[ET.Element]:
    """Get any stored query from FMI API.

    Splits the query into multiple chunks needed.

    Resulting XML is returned as is.
    """
    with init_session() as s:
        if start_time is None or end_time is None:
            for bbox in bboxes:
                yield get_stored_query(
                    query_id, bbox, start_time, end_time, resolution, s
                )
                sleep(0.5)
            return
        lims = _mk_limits(start_time, end_time, resolution)
        start, end = next(lims)
        logger.info("querying for %s - %s", start, end)
        for bbox in bboxes:
            yield get_stored_query(query_id, bbox, start, end, resolution, session=s)
            sleep(0.5)
        for start, end in lims:
            # to ensure api limits (600 requests in 5 mins) are respected
            # (it should allow for sleeping only for 0.5 seconds)
            sleep(1)
            logger.info("querying for %s - %s", start, end)
            for bbox in bboxes:
                yield get_stored_query(
                    query_id, bbox, start, end, resolution, session=s
                )
                sleep(0.5)


def get_stored_query_multipoint(  # noqa: PLR0913
    query_id: str,
    fmisid: int,
    start_time: None | datetime,
    end_time: None | datetime,
    resolution: timedelta,
    parameters: None | list[str],
) -> list[tuple[datetime, str, float]]:
    """Get any stored query.

    Split the query (= calls `get_stored_query_chunked`) into separate chunks if
    the time range is too long.
    """
    start_time = None if start_time is None else start_time.astimezone(UTC)
    end_time = None if end_time is None else end_time.astimezone(UTC)
    obs = get_stored_query_chunked(
        query_id + "::multipointcoverage",
        fmisid,
        start_time,
        end_time,
        resolution,
        parameters,
    )
    parser = (
        parse_multipoint_points if "forecast" in query_id else parse_multipoint_fmisids
    )
    res = [(dt, k, v) for _, dt, k, v in parser(obs)]
    if start_time is not None and end_time is not None:
        len_exp = (
            end_time.timestamp() - start_time.timestamp()
        ) / resolution.total_seconds()
        if len_exp > len({dt for dt, _, _ in res}):
            logger.warning(
                "queried for values for %s timestamps but got %s",
                int(len_exp),
                len(res),
            )

    return res


def get_stored_query_multipoint_all(
    query_id: str,
    start_time: None | datetime,
    end_time: None | datetime,
    resolution: timedelta,
) -> Iterator[tuple[int, datetime, str, float]]:
    """Get any stored query.

    Split the query (= calls `get_stored_query_chunked`) into separate chunks if
    the time range is too long.
    """
    start_time = None if start_time is None else start_time.astimezone(UTC)
    end_time = None if end_time is None else end_time.astimezone(UTC)
    obs = get_stored_query_chunked_bbox(
        query_id + "::multipointcoverage",
        grid_fi_bbox_parts(),
        start_time,
        end_time,
        resolution,
    )
    yield from parse_multipoint_fmisids(obs)


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
    return get_stored_query_multipoint(
        "fmi::forecast::meps::surface::point",
        fmisid,
        start_time,
        end_time,
        resolution,
        parameters,
    )


def grid_fi_bbox_parts() -> list[tuple[float, float, float, float]]:
    """Bounding box that contains finland in parts that are not too big."""
    lons = [(18, 21)]
    lons.extend((lon, lon + 1) for lon in range(21, 28))
    lons.append((28, 32))
    return [(l0, 59, l1, 71) for l0, l1 in lons]


def _mk_limits(
    start_time: datetime,
    end_time: datetime,
    resolution: timedelta,
) -> Iterator[tuple[datetime, datetime]]:
    secs = resolution.total_seconds()
    start_time = start_time.astimezone(UTC)
    end_time = end_time.astimezone(UTC)
    if secs > 60 * 60 and (24 * 60 * 60) % secs != 0:
        msg = "lower resolution than an hour must divide 24 hours evenly"
        raise ValueError(msg)
    if secs < 60 * 60 and (60 * 60) % secs != 0:
        msg = "higher resolution than an hour must divide the hour evenly"
        raise ValueError(msg)
    # at most a week of hourly data at a time
    # - daily data could be downloaded a year at a time but but i guess this is fine
    diff = timedelta(seconds=min(7 * 24 * 60 * 60 // secs, 168) * secs)
    start = start_time
    while start <= end_time:
        end = min(start + diff, end_time)
        yield (start, end)
        start = end + resolution
