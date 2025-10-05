"""Stored queries - ie. all the APIs that exist."""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Self

from fmi_cli.api import query_wfs
from fmi_cli.xml_helpers import extract_elem_text

QUERY_NS = {
    "ns0": "http://www.opengis.net/wfs/2.0",
}


def _get_attrib(elem: ET.Element, attrib_name: str, elem_name: str) -> str:
    if (x := elem.attrib.get(attrib_name)) is None:
        msg = f"{attrib_name} missing for {elem_name}"
        raise ValueError(msg)
    return x


@dataclass
class Param:
    """A query parameter."""

    name: str
    type_: str
    title: str
    abstract: str

    @classmethod
    def from_xml(cls, xml: ET.Element) -> Self:
        """Parse from XML."""
        name = _get_attrib(xml, "name", "Parameter")
        type_ = _get_attrib(xml, "type", "Parameter")
        title = extract_elem_text(xml, "title", "ns0:Title", QUERY_NS)
        abstract = extract_elem_text(xml, "abstract", "ns0:Abstract", QUERY_NS)
        return cls(name, type_, title, abstract)

    def __iter__(self) -> Iterator[str]:
        """Iterate over the fields."""
        yield self.name
        yield self.type_
        yield self.title
        yield self.abstract

    def __str__(self) -> str:
        """Return a string representation."""
        return f"{self.name}: {self.type_}"


def _parse_stored_query(xml: ET.Element) -> tuple[str, tuple[str, str]]:
    id_ = _get_attrib(xml, "id", "StoredQuery")
    title = extract_elem_text(xml, "title", "ns0:Title", QUERY_NS)
    ret_type = extract_elem_text(xml, "return type", "ns0:ReturnFeatureType", QUERY_NS)
    return id_, (title, ret_type)


def _parse_description(
    xml: ET.Element,
) -> tuple[str, tuple[str, list[Param]]]:
    id_ = _get_attrib(xml, "id", "StoredQueryDescription")
    abstract = extract_elem_text(xml, "description", "ns0:Abstract", QUERY_NS)
    params = [Param.from_xml(p) for p in xml.findall("ns0:Parameter", QUERY_NS)]
    return id_, (abstract, params)


@dataclass
class StoredQuery:
    """Essentially a queryable API."""

    id: str
    title: str
    abstract: str
    params: list[Param]
    return_feature_type: str

    @classmethod
    def from_xml(
        cls,
        xml: ET.Element,
        descriptions: dict[str, tuple[str, list[Param]]],
    ) -> Self:
        """Parse from XML."""
        id_, (title, ret_type) = _parse_stored_query(xml)
        abstr_par = descriptions.get(id_)
        if abstr_par is None:
            err = f"StoredQueryDescription missing for {id_}"
            raise ValueError(err)
        return cls(id_, title, abstr_par[0], abstr_par[1], ret_type)

    def matches(self, query: re.Pattern) -> bool:
        """Check if id, title or abstract matches the query."""
        if query.search(self.id) is not None:
            return True
        if query.search(self.title) is not None:
            return True
        return query.search(self.abstract) is not None

    def __str__(self) -> str:
        """Return string representation."""
        return f"[{self.id}]: {self.title}"


@dataclass
class StoredQueries:
    """List of the queryable APIs."""

    queries: dict[str, StoredQuery]

    @classmethod
    def get(cls) -> Self:
        """Construct the element by querying the API."""
        descr = query_wfs({"request": "describeStoredQueries"})
        descr_path = "ns0:StoredQueryDescription"
        descr = dict(map(_parse_description, descr.findall(descr_path, QUERY_NS)))
        queries_elem = query_wfs({"request": "listStoredQueries"})
        queries = queries_elem.findall("ns0:StoredQuery", QUERY_NS)
        qs = (StoredQuery.from_xml(e, descr) for e in queries)
        return cls({q.id: q for q in qs})

    def find_by_id(self, id_: str) -> None | StoredQuery:
        """Find stored query by id."""
        return next(p for id__, p in self.queries.items() if id_ in id__)

    def find_matches(self, query: str | re.Pattern) -> list[StoredQuery]:
        """Find API using a query."""
        query_re = re.compile(query, re.IGNORECASE)
        return [p for p in self._iter_all() if p.matches(query_re)]

    def _iter_all(self) -> Iterator[StoredQuery]:
        yield from self.queries.values()
