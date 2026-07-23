"""Gap detection and ranking. Deterministic, no LLM calls.

Gaps come from two sources: attributes the completeness rubric found
missing or vague, and attributes the query simulation reported as needed
but not usable. Impact = weight * (1 + frequency in failed queries), so
gaps still rank by rubric weight when the simulation is unavailable and
get boosted by real query evidence when it exists.
"""

from dataclasses import dataclass

from app.catalog.canonical import ATTRIBUTES_BY_NAME
from app.scoring.completeness import MISSING, VAGUE, CompletenessResult
from app.scoring.simulate import SimulationResult

QUERY_ONLY_GAP_WEIGHT = 5

QUERY_MISSING = "query_missing"


@dataclass(frozen=True)
class Gap:
    attribute: str
    status: str
    weight: int
    frequency_in_failed_queries: int
    impact: float
    reason: str
    agent_need: str


def detect_gaps(
    completeness: CompletenessResult, simulation: SimulationResult | None
) -> list[Gap]:
    frequency: dict[str, int] = {}
    if simulation is not None:
        for query in simulation.queries:
            if query.would_surface:
                continue
            for name in query.missing_info:
                frequency[name] = frequency.get(name, 0) + 1

    gaps: list[Gap] = []
    flagged: set[str] = set()
    for attribute in completeness.attributes:
        if attribute.status not in (MISSING, VAGUE):
            continue
        flagged.add(attribute.name)
        count = frequency.get(attribute.name, 0)
        gaps.append(
            Gap(
                attribute=attribute.name,
                status=attribute.status,
                weight=attribute.weight,
                frequency_in_failed_queries=count,
                impact=round(attribute.weight * (1 + count), 1),
                reason=attribute.reason,
                agent_need=ATTRIBUTES_BY_NAME[attribute.name].agent_need,
            )
        )

    for name, count in frequency.items():
        if name in flagged:
            continue
        canonical = ATTRIBUTES_BY_NAME.get(name)
        weight = canonical.weight if canonical else QUERY_ONLY_GAP_WEIGHT
        gaps.append(
            Gap(
                attribute=name,
                status=QUERY_MISSING,
                weight=weight,
                frequency_in_failed_queries=count,
                impact=round(weight * (1 + count), 1),
                reason=f"needed by {count} failed queries but not usable in the data",
                agent_need=canonical.agent_need if canonical else "surfaced by real shopper queries",
            )
        )

    gaps.sort(key=lambda gap: (-gap.impact, -gap.weight, gap.attribute))
    return gaps


def catalog_gap_rollup(per_sku_gaps: list[list[dict]]) -> list[dict]:
    """Catalog-level rollup over serialized per-SKU gap lists: how many
    SKUs share each gap and the summed impact, so structural fixes stand
    out. Returns dicts ready for API responses."""
    total_skus = len(per_sku_gaps)
    counts: dict[str, int] = {}
    impacts: dict[str, float] = {}
    for gap_list in per_sku_gaps:
        seen: set[str] = set()
        for gap in gap_list:
            name = gap["attribute"]
            if name in seen:
                continue
            seen.add(name)
            counts[name] = counts.get(name, 0) + 1
            impacts[name] = impacts.get(name, 0.0) + float(gap["impact"])
    rollup = [
        {
            "attribute": name,
            "sku_count": counts[name],
            "share": round(counts[name] / total_skus, 3) if total_skus else 0.0,
            "total_impact": round(impacts[name], 1),
        }
        for name in counts
    ]
    rollup.sort(key=lambda item: (-item["sku_count"], -item["total_impact"], item["attribute"]))
    return rollup
