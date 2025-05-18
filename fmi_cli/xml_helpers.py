"""Helpers for working with xml."""

import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from datetime import datetime

from fmi_cli.point import Point


def extract_attrib(xml: ET.Element, elem_name: str, attrib_name: str) -> str:
    """Extract attribute from xml element."""
    attrib = xml.attrib.get(f"{attrib_name}")
    if attrib is None:
        err = f"{elem_name} {attrib_name} missing"
        raise ValueError(err)
    return attrib.strip()


def extract_attrib_with_ns(xml: ET.Element, elem_name: str, attrib_name: str) -> str:
    """Extract attribute from xml element, ignoring namespaces."""
    attribs = xml.attrib
    attrib = None
    for k, v in attribs.items():
        if k.endswith(attrib_name) and (
            len(k) == len(attrib_name) or k[-len(attrib_name) - 1] == "}"
        ):
            attrib = v
            break
    if attrib is None:
        err = f"{elem_name} {attrib_name} missing"
        raise ValueError(err)
    return attrib.strip()


def extract_text(xml: ET.Element, elem_name: str, field_name: str) -> str:
    """Extract text from xml element, ignoring namespaces."""
    field = xml.find(f"{{*}}{field_name}")
    if field is None or (text := field.text) is None:
        err = f"{elem_name} {field_name} missing"
        raise ValueError(err)
    return text.strip()


def extract_child(xml: ET.Element, elem_name: str, child_name: str) -> ET.Element:
    """Extract text from xml element, ignoring namespaces."""
    child = xml.find(f"{{*}}{child_name}")
    if child is None:
        err = f"{elem_name} {child_name} missing"
        raise ValueError(err)
    return child


def parse_simple_features(
    xmls: Iterable[ET.Element],
) -> Iterator[tuple[Point, datetime, str, float]]:
    """Parse XML documents that contain a list of simple features."""
    for xml in xmls:
        yield from (parse_simple(e) for e in xml.findall("{*}member/{*}BsWfsElement"))


def parse_simple(elem: ET.Element) -> tuple[Point, datetime, str, float]:
    """Parse simple feature from XML."""
    elem_name = "BsWfsElement"
    point = Point.from_xml(extract_child(elem, elem_name, "Location/{*}Point"))
    time = extract_text(elem, elem_name, "Time")
    param_name = extract_text(elem, elem_name, "ParameterName")
    param_value = extract_text(elem, elem_name, "ParameterValue")
    return point, datetime.fromisoformat(time), param_name, float(param_value)
