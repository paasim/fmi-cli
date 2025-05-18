"""Query observable properties."""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Self

from fmi_cli.api import query_meta
from fmi_cli.xml_helpers import extract_attrib, extract_attrib_with_ns, extract_text


@dataclass
class ObservableProperty:
    """A quantity that is part of a measurement of a forecast.

    Most are described sufficiently, but ww-codes (a summary type of code for the
    present weather) can be found from e.g.
    [Manual on Codes, Volume I.1 - International Codes, page A-360](https://library.wmo.int/idurl/4/35713).
    """

    id: str
    label: str
    base_phenomenon: str
    unit_of_measurement: str | None

    @classmethod
    def from_xml(cls, xml: ET.Element) -> Self:
        """Parse from xml."""
        id_ = extract_attrib_with_ns(xml, "ObservableProperty", "id")
        label = extract_text(xml, "ObservableProperty", "label")
        base_phenomenon = extract_text(xml, "ObservableProperty", "basePhenomenon")
        uom_f = xml.find("{*}uom")
        unit_of_measurement = (
            None if uom_f is None else extract_attrib(uom_f, "uom", "uom")
        )
        return cls(id_, label, base_phenomenon, unit_of_measurement)

    def matches(self, query: re.Pattern) -> bool:
        """Check if any field matches the query."""
        if query.search(self.id) is not None:
            return True
        if query.search(self.label) is not None:
            return True
        if query.search(self.base_phenomenon) is not None:
            return True
        if self.unit_of_measurement is None:
            return False
        return query.search(self.unit_of_measurement) is not None

    def __str__(self) -> str:
        """Return string representation."""
        s = f"[{self.id}]: {self.label}"
        if self.unit_of_measurement is not None:
            s += f" ({self.unit_of_measurement})"
        return s


def _get_properties(prop: str) -> dict[str, ObservableProperty]:
    props = query_meta({"observableProperty": prop})
    props = props.findall("{*}component/{*}ObservableProperty")
    props = (ObservableProperty.from_xml(e) for e in props)
    return {p.id: p for p in props}


@dataclass
class ObservableProperties:
    """All the different types of observations and forecasts."""

    observation: dict[str, ObservableProperty]
    forecast: dict[str, ObservableProperty]

    @classmethod
    def get(cls) -> Self:
        """Construct the element by querying the api."""
        observation = _get_properties("observation")
        forecast = _get_properties("forecast")
        return cls(observation, forecast)

    def find_by_id(self, id_: str) -> None | ObservableProperty:
        """Find observable property by id."""
        return self.observation.get(id_, self.forecast.get(id_))

    def find_matches(
        self,
        query: str | re.Pattern,
        observations: bool = True,  # noqa: FBT001, FBT002
        forecasts: bool = True,  # noqa: FBT001, FBT002
    ) -> list[ObservableProperty]:
        """Find observable property using a string query."""
        query_re = re.compile(query, re.IGNORECASE)
        elems = self.iter_all(observations, forecasts)
        return [p for p in elems if p.matches(query_re)]

    def iter_all(
        self,
        observations: bool,  # noqa: FBT001
        forecasts: bool,  # noqa: FBT001
    ) -> Iterator[ObservableProperty]:
        """Iterate over all observable properties."""
        if observations:
            yield from self.observation.values()
        if forecasts:
            yield from self.forecast.values()

    def __str__(self) -> str:
        """Return string representation."""
        s = f"Descriptions for {len(self.observation)} observations"
        s += f" and {len(self.forecast)} forecasts."
        return s
