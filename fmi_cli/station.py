"""Weather / Air quality / radiation stations."""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from itertools import chain
from typing import Self

from fmi_cli.api import query_wfs
from fmi_cli.point import Point
from fmi_cli.xml_helpers import extract_attrib_ns, extract_elem, extract_elem_text

STAT_NS = {
    "ns0": "http://www.opengis.net/wfs/2.0",
    "ns2": "http://inspire.ec.europa.eu/schemas/ef/4.0",
    "ns3": "http://www.opengis.net/gml/3.2",
    "ns5": "http://www.w3.org/1999/xlink",
}


@dataclass
class Station:
    """A (weather / solar radiation / air quality) station identified by `fmisid`.

    A station can support multiple kinds of observations - this is specified (in
    finnish) in `station_kind`. Stations also contain information about when it
    is/was operational at `begin` and `end` -fields.
    """

    fmisid: int
    name: str
    geoid: None | str
    region: None | str
    point: Point
    begin: datetime
    end: None | datetime
    station_kind: list[str]

    @classmethod
    def from_xml(cls, xml: ET.Element) -> Self:
        """Parse from XML."""
        fmisid = int(extract_elem_text(xml, "fmisid", "ns3:identifier", STAT_NS))
        (name, geoid, region) = _get_names(xml)

        pt = extract_elem(xml, "point", "ns2:representativePoint/ns3:Point", STAT_NS)
        point = Point.from_xml(pt, STAT_NS)

        period_path = "ns2:operationalActivityPeriod/ns2:OperationalActivityPeriod"
        period_path += "/ns2:activityTime/ns3:TimePeriod"
        period = extract_elem(xml, "point", period_path, STAT_NS)

        begin = extract_elem_text(period, "start time", "ns3:beginPosition", STAT_NS)
        begin = datetime.fromisoformat(begin)
        end_elem = extract_elem(period, "end time", "ns3:endPosition", STAT_NS)
        end = None
        if end_elem is not None and end_elem.text is not None:
            end = datetime.fromisoformat(end_elem.text)

        kinds = [
            extract_attrib_ns(x, "title", "ns5", STAT_NS)
            for x in xml.findall("ns2:belongsTo", STAT_NS)
        ]

        return cls(
            fmisid,
            name,
            geoid,
            region,
            point,
            begin,
            end,
            kinds,
        )

    def __str__(self) -> str:
        """Return a string representation."""
        return f"[{self.fmisid}]: {self.name}"


def _get_names(xml: ET.Element) -> tuple[str, None | str, None | str]:
    names = [n for n in xml.findall("ns3:name", STAT_NS) if "codeSpace" in n.attrib]
    names = {n.attrib["codeSpace"].split("/")[-1]: n.text for n in names}
    name = names.get("name")
    if name is None:
        msg = "station (EnvironmentalMonitoringFacility) does not contain 'name'"
        raise ValueError(msg)
    return name, names.get("geoid"), names.get("region")


@dataclass
class Stations:
    """All the available stations."""

    stations: list[Station]

    @classmethod
    def get(cls) -> Self:
        """Construct the element by querying the api."""
        stats_xml = _get_stations()
        stats_query = "ns0:member/ns2:EnvironmentalMonitoringFacility"
        return cls(
            [Station.from_xml(s) for s in stats_xml.findall(stats_query, STAT_NS)]
        )

    def _filter_kind(
        self, kind: str, name: None | str | re.Pattern
    ) -> Iterator[Station]:
        stations = (s for s in self.stations if kind in s.station_kind)
        if name is not None:
            name = re.compile(name, re.IGNORECASE)
            stations = (s for s in stations if name.search(s.name) is not None)
        return stations

    def airquality(self, name: None | str | re.Pattern = None) -> list[Station]:
        """All air quality stations (that optionall match to `name`-query)."""
        stations = self._filter_kind("Ilmanlaadun tausta-asema", name)
        kind3 = "Kolmannen osapuolen ilmanlaadun havaintoasema"
        stations3 = self._filter_kind(kind3, name)
        return sorted(chain(stations, stations3), key=lambda s: s.name)

    def radiation(self, name: None | str | re.Pattern = None) -> list[Station]:
        """All solar radiation stations (that optionall match to `name`-query)."""
        kind = "Auringonsäteilyasema"
        return sorted(self._filter_kind(kind, name), key=lambda s: s.name)

    def weather(self, name: None | str | re.Pattern = None) -> list[Station]:
        """All weather stations (that optionall match to `name`-query)."""
        kind = "Automaattinen sääasema"
        return sorted(self._filter_kind(kind, name), key=lambda s: s.name)


def _get_stations() -> ET.Element:
    params = {"request": "getFeature", "storedquery_id": "fmi::ef::stations"}
    return query_wfs(params)
