"""Canonical attribute schema the audit scores against.

Each attribute carries a weight reflecting how heavily AI shopping agents
rely on it when deciding whether to surface and recommend a product. The
weights drive both the completeness score and the gap ranking, so this
rubric is the scoring baseline for the whole tool.
"""

from dataclasses import dataclass
from enum import Enum


class AttributeType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    ENUM = "enum"
    LIST = "list"
    STRUCTURED = "structured"
    QUANTITY = "quantity"


@dataclass(frozen=True)
class CanonicalAttribute:
    name: str
    weight: int
    type: AttributeType
    agent_need: str


CANONICAL_ATTRIBUTES: tuple[CanonicalAttribute, ...] = (
    CanonicalAttribute("title", 10, AttributeType.TEXT, "primary match target"),
    CanonicalAttribute("category", 8, AttributeType.TEXT, "filters the candidate set"),
    CanonicalAttribute("price", 10, AttributeType.NUMBER, "agents filter on budget constraints"),
    CanonicalAttribute("currency", 3, AttributeType.TEXT, "required to interpret price"),
    CanonicalAttribute("availability", 9, AttributeType.ENUM, "agents drop unavailable items"),
    CanonicalAttribute("brand", 5, AttributeType.TEXT, "trust and disambiguation"),
    CanonicalAttribute("description", 6, AttributeType.TEXT, "fallback reasoning source"),
    CanonicalAttribute("material", 7, AttributeType.TEXT, 'common "what is it made of" query'),
    CanonicalAttribute("dimensions", 7, AttributeType.STRUCTURED, '"will it fit" queries'),
    CanonicalAttribute("weight", 5, AttributeType.QUANTITY, '"lightweight" queries'),
    CanonicalAttribute("color", 4, AttributeType.TEXT, "filter attribute"),
    CanonicalAttribute("usage_scenario", 8, AttributeType.TEXT, 'context match for "in a high-traffic hallway" style queries'),
    CanonicalAttribute("care_instructions", 4, AttributeType.TEXT, '"machine washable" filters'),
    CanonicalAttribute("certifications", 6, AttributeType.LIST, "trust signals that break ties"),
    CanonicalAttribute("key_features", 7, AttributeType.LIST, "outcome-based matching"),
    CanonicalAttribute("target_audience", 5, AttributeType.TEXT, '"for a minimalist apartment" style matching'),
    CanonicalAttribute("warranty", 4, AttributeType.TEXT, "recourse and trust signal"),
    CanonicalAttribute("shipping_info", 6, AttributeType.TEXT, "agents estimate delivery"),
)

ATTRIBUTES_BY_NAME: dict[str, CanonicalAttribute] = {
    attr.name: attr for attr in CANONICAL_ATTRIBUTES
}

TOTAL_WEIGHT: int = sum(attr.weight for attr in CANONICAL_ATTRIBUTES)

AVAILABILITY_VALUES: tuple[str, ...] = ("in_stock", "out_of_stock", "preorder")

DIMENSION_FIELDS: tuple[str, ...] = ("length", "width", "height")
