"""Per-SKU audit pipeline: completeness, simulation, gaps, rewrite, and
the projected after score, plus catalog-level aggregates.

Completeness is deterministic and always computes. When the provider
raises an LLMError (rate limited, unreachable, misconfigured), the LLM
backed steps are marked unavailable_rate_limited for that SKU and the run
continues: it never fails the whole audit and never falls back to a paid
path. Results are emitted per SKU through callbacks so callers can
persist partial runs and stream progress as the run advances.
"""

from dataclasses import asdict

from app.llm.provider import LLMError, LLMProvider, get_provider
from app.scoring.completeness import MISSING, VAGUE, score_sku
from app.scoring.gaps import catalog_gap_rollup, detect_gaps
from app.scoring.rewrite import RewriteResult, rewrite_attributes
from app.scoring.simulate import simulate_queries

STATUS_OK = "ok"
STATUS_RATE_LIMITED = "unavailable_rate_limited"

COMPLETENESS_SHARE = 0.6
VISIBILITY_SHARE = 0.4


def audit_sku(sku: dict, provider: LLMProvider) -> dict:
    """Audit one SKU and return a JSON-ready result dict."""
    completeness = score_sku(sku)

    simulation = None
    simulation_status = STATUS_OK
    try:
        simulation = simulate_queries(sku, provider)
    except LLMError:
        simulation_status = STATUS_RATE_LIMITED

    gap_list = detect_gaps(completeness, simulation)
    weak = [gap.attribute for gap in gap_list if gap.status in (MISSING, VAGUE)]

    rewrite_result = RewriteResult(outcomes=())
    rewrite_status = STATUS_OK
    if weak:
        try:
            rewrite_result = rewrite_attributes(sku, weak, provider)
        except LLMError:
            rewrite_result = None
            rewrite_status = STATUS_RATE_LIMITED

    before_score = completeness.score
    after_score = None
    if rewrite_result is not None:
        after_score = score_sku(rewrite_result.apply(sku)).score

    if simulation is not None:
        readiness = round(
            COMPLETENESS_SHARE * before_score
            + VISIBILITY_SHARE * simulation.surface_rate * 100,
            1,
        )
    else:
        readiness = before_score

    return {
        "sku_id": str(sku.get("sku_id") or ""),
        "title": sku.get("title"),
        "revenue_at_risk": float(sku.get("revenue_at_risk") or 0.0),
        "revenue_is_estimate": bool(sku.get("revenue_is_estimate", True)),
        "readiness": readiness,
        "before_score": before_score,
        "after_score": after_score,
        "completeness": {
            "score": before_score,
            "attributes": [asdict(a) for a in completeness.attributes],
            "missing": completeness.missing,
            "vague": completeness.vague,
        },
        "simulation": {
            "status": simulation_status,
            "surface_rate": simulation.surface_rate if simulation else None,
            "queries": [asdict(q) for q in simulation.queries] if simulation else [],
        },
        "gaps": [asdict(g) for g in gap_list],
        "rewrite": {
            "status": rewrite_status,
            "outcomes": [asdict(o) for o in rewrite_result.outcomes]
            if rewrite_result
            else [],
        },
    }


def run_audit(
    skus: list[dict],
    provider: LLMProvider | None = None,
    on_progress=None,
    persist=None,
) -> dict:
    """Audit a catalog SKU by SKU. on_progress(index, total, sku_id,
    status) fires after each SKU for streaming, persist(result) fires so
    partial runs survive interruption."""
    provider = provider or get_provider()
    total = len(skus)
    results: list[dict] = []
    for index, sku in enumerate(skus):
        result = audit_sku(sku, provider)
        results.append(result)
        if persist is not None:
            persist(result)
        if on_progress is not None:
            on_progress(index + 1, total, result["sku_id"], "done")

    return {"sku_results": results, "aggregates": compute_aggregates(results)}


def compute_aggregates(results: list[dict]) -> dict:
    """Catalog-level aggregates over per-SKU results. Also used to rebuild
    aggregates after individual results are replaced."""
    readiness_values = [result["readiness"] for result in results]
    unweighted = (
        round(sum(readiness_values) / len(readiness_values), 1) if results else 0.0
    )
    revenue_weights = [max(result["revenue_at_risk"], 0.0) for result in results]
    total_revenue = sum(revenue_weights)
    if total_revenue > 0:
        weighted = round(
            sum(value * weight for value, weight in zip(readiness_values, revenue_weights))
            / total_revenue,
            1,
        )
    else:
        weighted = unweighted
    rate_limited = sum(
        1
        for result in results
        if STATUS_RATE_LIMITED in (result["simulation"]["status"], result["rewrite"]["status"])
    )

    return {
        "sku_count": len(results),
        "readiness_revenue_weighted": weighted,
        "readiness_unweighted": unweighted,
        "revenue_at_risk_total": round(total_revenue, 2),
        "rate_limited_skus": rate_limited,
        "top_gaps": catalog_gap_rollup([result["gaps"] for result in results]),
    }
