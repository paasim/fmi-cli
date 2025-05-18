"""Stored queries - ie. all the APIs that exist."""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Self

from fmi_cli.api import query_wfs
from fmi_cli.xml_helpers import extract_attrib, extract_text


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
        name = extract_attrib(xml, "Parameter", "name")
        type_ = extract_attrib(xml, "Parameter", "type")
        title = extract_text(xml, "Parameter", "Title")
        abstract = extract_text(xml, "Parameter", "Abstract")
        return cls(name, type_, title, abstract)

    def __str__(self) -> str:
        """Return a string representation."""
        return f"{self.name}: {self.type_}"


def _parse_stored_query(xml: ET.Element) -> tuple[str, tuple[str, str]]:
    id_ = extract_attrib(xml, "StoredQuery", "id")
    elem_name = f"StoredQuery for {id_}"
    title = extract_text(xml, elem_name, "Title")
    ret_type = extract_text(xml, elem_name, "ReturnFeatureType")
    return id_, (title, ret_type)


def _parse_description(
    xml: ET.Element,
) -> tuple[str, tuple[str, list[Param]]]:
    id_ = extract_attrib(xml, "StoredQueryDescription ", "id")
    elem_name = f"StoredQueryDescription for {id_}"
    abstract = extract_text(xml, elem_name, "Abstract")
    params = [Param.from_xml(p) for p in xml.findall("{*}Parameter")]
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
        queries = query_wfs({"request": "listStoredQueries"}).findall("{*}StoredQuery")
        descr = query_wfs({"request": "describeStoredQueries"})
        descr = map(_parse_description, descr.findall("{*}StoredQueryDescription"))
        descr = dict(descr)
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
