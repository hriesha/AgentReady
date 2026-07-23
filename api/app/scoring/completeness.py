"""Deterministic rubric-based completeness scoring.

This module makes no LLM calls and must stay that way. The pipeline depends
on completeness always computing, even when every LLM-backed step is
unavailable because the free tier rate limit was hit.

Scoring rule per attribute: 1.0 when present and specific, 0.5 when present
but vague (filler wording, placeholders, empty-ish or too-short values,
unstructured or unit-less measurements), 0.0 when missing. The weighted
total is scaled to 0 to 100.
"""

import re
from dataclasses import dataclass

from app.catalog.canonical import (
    AVAILABILITY_VALUES,
    CANONICAL_ATTRIBUTES,
    DIMENSION_FIELDS,
    TOTAL_WEIGHT,
    AttributeType,
    CanonicalAttribute,
)

OK = "ok"
VAGUE = "vague"
MISSING = "missing"

STATUS_SCORES = {OK: 1.0, VAGUE: 0.5, MISSING: 0.0}

FILLER_PHRASES = frozenset({
    "high quality", "high-quality", "good quality", "top quality",
    "premium quality", "best quality", "quality", "premium", "durable",
    "great", "good", "nice", "amazing", "excellent", "awesome", "stylish",
    "modern", "elegant", "beautiful", "perfect", "versatile", "best",
    "luxury", "luxurious", "comfortable", "comfy", "sturdy", "reliable",
    "well made", "well-made", "long lasting", "long-lasting", "top notch",
    "top-notch", "very good", "super", "classic", "trendy",
})

PLACEHOLDER_VALUES = frozenset({
    "n/a", "na", "n.a.", "tbd", "tba", "todo", "none", "null", "nil",
    "unknown", "-", "--", "...", "xxx", "x", "?", "pending",
})

MIN_TEXT_LENGTH = 3

_CHUNK_SPLIT = re.compile(r"[,;/]|\band\b|&")
_BARE_NUMBER = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
_NUMBER_WITH_UNIT = re.compile(r"^\d+(?:[.,]\d+)?\s*[a-zA-Z]{1,12}\.?$")


def check_text(value: str) -> tuple[str, str]:
    """Classify a text value as OK or VAGUE, with a short reason.

    Deterministic on purpose: empty-ish, placeholder, too-short, and
    all-filler values are vague. Anything with a concrete term passes.
    """
    stripped = value.strip()
    if not stripped:
        return VAGUE, "empty value"
    if stripped.lower() in PLACEHOLDER_VALUES:
        return VAGUE, "placeholder value"
    if len(stripped) < MIN_TEXT_LENGTH:
        return VAGUE, "too short to be meaningful"
    chunks = [c.strip(" .!") for c in _CHUNK_SPLIT.split(stripped.lower())]
    chunks = [c for c in chunks if c]
    if chunks and all(c in FILLER_PHRASES for c in chunks):
        return VAGUE, "filler wording with no specifics"
    return OK, ""


def _is_positive_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        try:
            return float(value.strip()) > 0
        except ValueError:
            return False
    return False


def _check_number(value: object) -> tuple[str, str]:
    if isinstance(value, bool):
        return VAGUE, "not a number"
    if isinstance(value, (int, float)):
        return (OK, "") if value > 0 else (VAGUE, "not a positive number")
    if isinstance(value, str):
        stripped = value.strip().lstrip("$").replace(",", "").strip()
        if not stripped:
            return VAGUE, "empty value"
        try:
            number = float(stripped)
        except ValueError:
            return VAGUE, "not a parseable number"
        return (OK, "") if number > 0 else (VAGUE, "not a positive number")
    return VAGUE, "not a number"


def _check_enum(value: object) -> tuple[str, str]:
    if not isinstance(value, str):
        return VAGUE, "unrecognized availability value"
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    if not normalized:
        return VAGUE, "empty value"
    if normalized in AVAILABILITY_VALUES:
        return OK, ""
    return VAGUE, "unrecognized availability value"


def _check_list(value: object) -> tuple[str, str]:
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value]
    else:
        return VAGUE, "not a list"
    items = [item for item in items if item]
    if not items:
        return MISSING, "empty list"
    if any(check_text(item)[0] == OK for item in items):
        return OK, ""
    return VAGUE, "only filler or placeholder items"


def _check_dimensions(value: object) -> tuple[str, str]:
    if isinstance(value, dict):
        present = [f for f in DIMENSION_FIELDS if _is_positive_number(value.get(f))]
        unit = str(value.get("unit") or "").strip()
        if len(present) == len(DIMENSION_FIELDS) and unit:
            return OK, ""
        if present or unit:
            return VAGUE, "incomplete dimensions"
        return MISSING, "no usable dimension fields"
    if isinstance(value, str):
        status, reason = check_text(value)
        if status == VAGUE:
            return VAGUE, reason
        return VAGUE, "not structured into length, width, height and unit"
    return VAGUE, "not structured dimensions"


def _check_quantity(value: object) -> tuple[str, str]:
    if isinstance(value, dict):
        has_value = _is_positive_number(value.get("value"))
        has_unit = bool(str(value.get("unit") or "").strip())
        if has_value and has_unit:
            return OK, ""
        return VAGUE, "incomplete quantity"
    if isinstance(value, bool):
        return VAGUE, "not a number with a unit"
    if isinstance(value, (int, float)):
        return (VAGUE, "number without a unit") if value > 0 else (VAGUE, "not a positive number")
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return VAGUE, "empty value"
        if _NUMBER_WITH_UNIT.match(stripped):
            return OK, ""
        if _BARE_NUMBER.match(stripped):
            return VAGUE, "number without a unit"
        return VAGUE, "not a number with a unit"
    return VAGUE, "not a number with a unit"


_TYPE_CHECKS = {
    AttributeType.NUMBER: _check_number,
    AttributeType.ENUM: _check_enum,
    AttributeType.LIST: _check_list,
    AttributeType.STRUCTURED: _check_dimensions,
    AttributeType.QUANTITY: _check_quantity,
}


@dataclass(frozen=True)
class AttributeScore:
    name: str
    weight: int
    status: str
    score: float
    reason: str


@dataclass(frozen=True)
class CompletenessResult:
    score: float
    attributes: tuple[AttributeScore, ...]

    @property
    def missing(self) -> list[str]:
        return [a.name for a in self.attributes if a.status == MISSING]

    @property
    def vague(self) -> list[str]:
        return [a.name for a in self.attributes if a.status == VAGUE]


def score_attribute(attribute: CanonicalAttribute, value: object) -> AttributeScore:
    if value is None:
        status, reason = MISSING, "attribute not provided"
    else:
        check = _TYPE_CHECKS.get(attribute.type)
        if check is not None:
            status, reason = check(value)
        else:
            status, reason = check_text(value if isinstance(value, str) else str(value))
    return AttributeScore(
        name=attribute.name,
        weight=attribute.weight,
        status=status,
        score=STATUS_SCORES[status],
        reason=reason,
    )


def score_sku(sku: dict) -> CompletenessResult:
    """Score one normalized SKU dict against the canonical rubric."""
    attribute_scores = tuple(
        score_attribute(attribute, sku.get(attribute.name))
        for attribute in CANONICAL_ATTRIBUTES
    )
    weighted = sum(a.weight * a.score for a in attribute_scores)
    return CompletenessResult(
        score=round(100 * weighted / TOTAL_WEIGHT, 1),
        attributes=attribute_scores,
    )
