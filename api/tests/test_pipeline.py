"""Simulation, gaps, rewrite, and pipeline against the sample catalog.
The provider is always mocked, no real LLM calls."""

import json
from pathlib import Path

import pytest
from fakes import CANNED_EVALUATIONS, FakeProvider, RateLimitedProvider

from app.catalog.ingest import ingest_catalog
from app.scoring.completeness import score_sku
from app.scoring.gaps import catalog_gap_rollup, detect_gaps
from app.scoring.pipeline import audit_sku, run_audit
from app.scoring.rewrite import rewrite_attributes
from app.scoring.simulate import simulate_queries

SAMPLE_CATALOG = Path(__file__).parent / "sample_catalog.csv"


@pytest.fixture(scope="module")
def sample_skus():
    return ingest_catalog(SAMPLE_CATALOG).skus


def test_simulate_confidence_weighted_surface_rate(sample_skus):
    result = simulate_queries(sample_skus[0], FakeProvider())
    assert len(result.queries) == 3
    assert result.surface_rate == round(0.9 / (0.9 + 0.7 + 0.6), 3)
    assert result.queries[1].missing_info == ("usage_scenario", "dimensions")


def test_simulate_defaults_when_evaluation_is_partial(sample_skus):
    class PartialProvider(FakeProvider):
        def complete(self, system, user, json_mode=False):
            if "retrieval and reasoning" in system:
                return json.dumps({"evaluations": CANNED_EVALUATIONS[:1]})
            return super().complete(system, user, json_mode)

    result = simulate_queries(sample_skus[0], PartialProvider())
    assert len(result.queries) == 3
    assert result.queries[1].would_surface is False
    assert result.queries[1].confidence == 0.0


def test_gaps_ranked_by_impact_with_query_boost():
    completeness = score_sku({"title": "Towel", "price": 10})
    simulation = simulate_queries({"title": "Towel", "price": 10}, FakeProvider())
    gaps = detect_gaps(completeness, simulation)
    by_name = {gap.attribute: gap for gap in gaps}
    assert by_name["usage_scenario"].impact == 8 * (1 + 1)
    assert by_name["availability"].impact == 9.0
    assert by_name["usage_scenario"].frequency_in_failed_queries == 1
    impacts = [gap.impact for gap in gaps]
    assert impacts == sorted(impacts, reverse=True)


def test_gap_for_non_canonical_query_attribute():
    completeness = score_sku({"title": "Towel", "price": 10})

    class BatteryProvider(FakeProvider):
        def complete(self, system, user, json_mode=False):
            if "retrieval and reasoning" in system:
                evaluation = dict(CANNED_EVALUATIONS[1])
                evaluation["missing_info"] = ["battery life"]
                return json.dumps({"evaluations": [CANNED_EVALUATIONS[0], evaluation, CANNED_EVALUATIONS[2]]})
            return super().complete(system, user, json_mode)

    simulation = simulate_queries({"title": "Towel", "price": 10}, BatteryProvider())
    gaps = detect_gaps(completeness, simulation)
    battery = next(gap for gap in gaps if gap.attribute == "battery_life")
    assert battery.status == "query_missing"
    assert battery.weight == 5


def test_catalog_gap_rollup_shares():
    gap_a = {"attribute": "material", "impact": 14.0}
    gap_b = {"attribute": "usage_scenario", "impact": 8.0}
    rollup = catalog_gap_rollup([[gap_a, gap_b], [gap_a], []])
    assert rollup[0]["attribute"] == "material"
    assert rollup[0]["sku_count"] == 2
    assert rollup[0]["share"] == round(2 / 3, 3)
    assert rollup[0]["total_impact"] == 28.0


def test_rewrite_applies_derivable_values_only(sample_skus):
    sku = sample_skus[1]
    result = rewrite_attributes(sku, ["description", "certifications", "price"], FakeProvider())
    by_name = {outcome.attribute: outcome for outcome in result.outcomes}
    assert "price" not in by_name
    assert by_name["description"].value == "specific rewritten description content"
    assert by_name["certifications"].value is None
    assert by_name["certifications"].needs_human == "certification documents required"
    rewritten = result.apply(sku)
    assert rewritten["description"] == "specific rewritten description content"
    assert "certifications" not in rewritten
    assert sku["description"] != rewritten["description"]


def test_audit_sku_readiness_blends_completeness_and_visibility(sample_skus):
    result = audit_sku(sample_skus[1], FakeProvider())
    surface_rate = result["simulation"]["surface_rate"]
    expected = round(0.6 * result["before_score"] + 0.4 * surface_rate * 100, 1)
    assert result["readiness"] == expected
    assert result["after_score"] >= result["before_score"]


def test_run_audit_over_sample_catalog(sample_skus):
    progress = []
    persisted = []
    outcome = run_audit(
        sample_skus,
        provider=FakeProvider(),
        on_progress=lambda index, total, sku_id, status: progress.append(
            (index, total, sku_id, status)
        ),
        persist=persisted.append,
    )
    results = outcome["sku_results"]
    aggregates = outcome["aggregates"]
    assert len(results) == 20
    assert len(persisted) == 20
    assert progress[0] == (1, 20, results[0]["sku_id"], "done")
    assert progress[-1][0] == 20
    for result in results:
        assert 0.0 <= result["before_score"] <= 100.0
        assert 0.0 <= result["readiness"] <= 100.0
        assert result["simulation"]["status"] == "ok"
        impacts = [gap["impact"] for gap in result["gaps"]]
        assert impacts == sorted(impacts, reverse=True)
    assert aggregates["sku_count"] == 20
    assert 0.0 <= aggregates["readiness_unweighted"] <= 100.0
    assert 0.0 <= aggregates["readiness_revenue_weighted"] <= 100.0
    assert aggregates["rate_limited_skus"] == 0
    assert aggregates["top_gaps"]
    assert aggregates["top_gaps"][0]["sku_count"] >= aggregates["top_gaps"][-1]["sku_count"]


def test_run_audit_results_are_json_serializable(sample_skus):
    outcome = run_audit(sample_skus[:2], provider=FakeProvider())
    assert json.loads(json.dumps(outcome))


def test_rate_limit_degrades_gracefully(sample_skus):
    outcome = run_audit(sample_skus, provider=RateLimitedProvider())
    results = outcome["sku_results"]
    assert len(results) == 20
    for result in results:
        assert result["before_score"] == score_sku(
            next(s for s in sample_skus if s["sku_id"] == result["sku_id"])
        ).score
        assert result["simulation"]["status"] == "unavailable_rate_limited"
        assert result["simulation"]["queries"] == []
        assert result["readiness"] == result["before_score"]
        assert result["gaps"] or result["before_score"] == 100.0
    assert outcome["aggregates"]["rate_limited_skus"] == 20
