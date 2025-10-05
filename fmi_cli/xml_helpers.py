"""Helpers for working with xml."""

import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime

from fmi_cli.point import Point

MP_NS = {
    "gml": "http://www.opengis.net/gml/3.2",
    "gmlcov": "http://www.opengis.net/gmlcov/1.0",
    "om": "http://www.opengis.net/om/2.0",
    "omso": "http://inspire.ec.europa.eu/schemas/omso/3.0",
    "sam": "http://www.opengis.net/sampling/2.0",
    "sams": "http://www.opengis.net/samplingSpatial/2.0",
    "swe": "http://www.opengis.net/swe/2.0",
    "target": "http://xml.fmi.fi/namespace/om/atmosphericfeatures/1.1",
    "wfs": "http://www.opengis.net/wfs/2.0",
    "xlink": "http://www.w3.org/1999/xlink",
}


def extract_elem(
    xml: ET.Element, elem_name: str, field_path: str, namespace: dict[str, str]
) -> ET.Element:
    """Extract xml element, raising ValueError if it does not exist."""
    field = xml.find(field_path, namespace)
    if field is None:
        err = f"{elem_name} ({field_path}) missing"
        raise ValueError(err)
    return field


def extract_elem_text(
    xml: ET.Element, elem_name: str, field_path: str, namespace: dict[str, str]
) -> str:
    """Extract text from xml element, raising ValueError if it does not exist."""
    if (text := extract_elem(xml, elem_name, field_path, namespace).text) is None:
        err = f"{elem_name} ({field_path}) text missing"
        raise ValueError(err)
    return text.strip()


def extract_attrib_ns(
    xml: ET.Element, elem_name: str, ns_name: str, ns: dict[str, str]
) -> str:
    """Extract attibute from xml element, raising ValueError if it does not exist."""
    if (x := xml.attrib.get(f"{{{ns[ns_name]}}}{elem_name}")) is None:
        msg = f"attribute {ns_name}:{elem_name} missing"
        raise ValueError(msg)
    return x


def get_space_separated(
    multipoint_data: ET.Element, path: str, elem_name: str
) -> Iterator[list[str]]:
    """Extract a list of space-separated elements from element text.

    Skips empty lines.
    """
    txt = extract_elem_text(multipoint_data, elem_name, path, MP_NS)
    for line in txt.splitlines():
        obs_tup = line.strip().split()
        if len(obs_tup) == 0:
            continue
        yield obs_tup


def get_fmisid_map(multipoint_obs: ET.Element) -> dict[tuple[float, float], int]:
    """Construct a map from (lat, lon)-coordinates to fmisid."""
    locs_path = "om:featureOfInterest/sams:SF_SpatialSamplingFeature"
    locs = extract_elem(multipoint_obs, "sampling feature", locs_path, MP_NS)
    feature_id = extract_attrib_ns(locs, "id", "gml", MP_NS)
    if feature_id != "sampling-feature-1-1-fmisid":
        msg = f"invalid sampling feature '{feature_id}'"
        raise ValueError(msg)

    mapping = {}
    pt_path = "sams:shape/gml:MultiPoint/gml:pointMember/gml:Point"
    for obs in locs.findall(pt_path, MP_NS):
        id_ = extract_attrib_ns(obs, "id", "gml", MP_NS)
        fmisid = int(id_.split("-")[1])
        lat, lon = extract_elem_text(obs, "position", "gml:pos", MP_NS).split()
        mapping[(float(lat), float(lon))] = fmisid
    return mapping


def get_lat_lons(
    multipoint_data: ET.Element,
) -> Iterator[tuple[float, float, datetime]]:
    """Get latitudes and longitueds from space-separated list."""
    pos_path = "gml:domainSet/gmlcov:SimpleMultiPoint/gmlcov:positions"
    for record in get_space_separated(multipoint_data, pos_path, "data block"):
        ts = datetime.fromtimestamp(int(record[2]), UTC)
        yield float(record[0]), float(record[1]), ts


def get_fmisids(
    multipoint_data: ET.Element, fmisid_map: dict[tuple[float, float], int]
) -> Iterator[tuple[int, datetime]]:
    """Get fmisids using the mapping from latitudes and longitudes."""
    for lat, lon, ts in get_lat_lons(multipoint_data):
        if (fmisid := fmisid_map.get((lat, lon))) is None:
            msg = f"station not found for coordinate ({lat}, {lon})"
            raise ValueError(msg)
        yield fmisid, ts


def get_obs_types(multipoint_data: ET.Element) -> list[str]:
    """List observation types.

    These are assumed to be in the same order as the observations.
    """
    path = "gmlcov:rangeType/swe:DataRecord/swe:field"
    return [o.attrib["name"] for o in multipoint_data.findall(path, MP_NS)]


def get_data_block(multipoint_data: ET.Element) -> Iterator[list[tuple[str, float]]]:
    """Parse the data.

    The data is space-separated text block and contains the observations
    specified by `get_obs_types`.
    """
    obs_types = get_obs_types(multipoint_data)
    obs_path = "gml:rangeSet/gml:DataBlock/gml:doubleOrNilReasonTupleList"
    for record in get_space_separated(multipoint_data, obs_path, "data block"):
        yield [(obs_t, float(x)) for obs_t, x in zip(obs_types, record, strict=True)]


def _parse_multipoint(
    elem: ET.Element,
) -> Iterator[tuple[float, float, datetime, str, float]]:
    """Parse multipoint from XML."""
    mp_path = "wfs:member/omso:GridSeriesObservation"
    mp_path += "/om:result/gmlcov:MultiPointCoverage"
    if (mp_cov := elem.find(mp_path, MP_NS)) is None:
        return
    lat_lons = get_lat_lons(mp_cov)
    data = get_data_block(mp_cov)
    for (lat, lon, ts), obs in zip(lat_lons, data, strict=True):
        for obs_type, obs_val in obs:
            yield lat, lon, ts, obs_type, obs_val


def get_projection(multipoint_obs: ET.Element) -> str:
    """Get a projection from the points.

    Raises an error if there are multiple (or zero) choices as then it cannot
    be assumed to apply for all coordintaes.
    """
    pt_path = "om:featureOfInterest/sams:SF_SpatialSamplingFeature"
    pt_path += "/sams:shape/gml:MultiPoint/gml:pointMembers/gml:Point"
    projs = {p.attrib["srsName"] for p in multipoint_obs.findall(pt_path, MP_NS)}
    if len(projs) != 1:
        msg = f"Non-unique ({len(projs)}) value for projection"
        raise ValueError(msg)
    return next(iter(projs))


def parse_multipoint_points(
    elems: Iterable[ET.Element],
) -> Iterator[tuple[Point, datetime, str, float]]:
    """Parse multipoint from XML.

    Also adds projection information from the neighboring element to lat-lons.
    This is because e.g. for forecasts, the points are not necessary related to
    a station with fmisid.
    """
    for elem in elems:
        obs_path = "wfs:member/omso:GridSeriesObservation"
        if (mp_obs := elem.find(obs_path, MP_NS)) is None:
            continue
        projection = get_projection(mp_obs)
        for lat, lon, ts, obs_type, obs_val in _parse_multipoint(elem):
            yield Point(lat, lon, projection), ts, obs_type, obs_val


def parse_multipoint_fmisids(
    elems: Iterable[ET.Element],
) -> Iterator[tuple[int, datetime, str, float]]:
    """Parse multipoint from XML.

    Adds fmisid to the observations by mapping the lat-lons to a fmisid from the
    sampling feature information.
    """
    for elem in elems:
        obs_path = "wfs:member/omso:GridSeriesObservation"
        if (mp_obs := elem.find(obs_path, MP_NS)) is None:
            continue
        fmisid_map = get_fmisid_map(mp_obs)
        for lat, lon, ts, obs_type, obs_val in _parse_multipoint(elem):
            if (fmisid := fmisid_map.get((lat, lon))) is None:
                msg = f"station not found for coordinate ({lat}, {lon})"
                raise ValueError(msg)
            yield fmisid, ts, obs_type, obs_val
