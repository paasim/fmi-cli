"""2d-point."""

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Self


@dataclass
class Point:
    """Represents a point in 2d: a lat lon -pair with a given projection."""

    lat: float
    lon: float
    projection: str

    @classmethod
    def from_xml(cls, xml: ET.Element, namespace: dict[str, str]) -> Self:
        """Parse point from XML."""
        # don't use xml_helpers to avoid circular import
        pos = xml.find("ns3:pos", namespace)
        if pos is None or pos.text is None:
            msg = "'Point' does not contain 'pos' with coordinates"
            raise ValueError(msg)
        coords = pos.text.split(" ")
        return cls(float(coords[0]), float(coords[1]), xml.attrib["srsName"])

    def __iter__(self) -> Iterator[float | str]:
        """Iterate over the fields."""
        yield self.lat
        yield self.lon
        yield self.projection
