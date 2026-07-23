"""Agent-query simulation: generate realistic shopper queries for a SKU
and test whether its current data would satisfy them.

Two LLM calls per SKU, batched to respect the free tier request budget:
one call generates all queries, one call evaluates all of them together.
The confidence-weighted share of surfaced queries becomes the SKU's agent
visibility component.
"""

import json
import re
from dataclasses import dataclass

from app.llm import prompts
from app.llm.provider import LLMBadResponse, LLMProvider

QUERIES_PER_SKU = 6
MAX_QUERIES_PER_SKU = 8

INTERNAL_FIELDS = ("revenue_at_risk", "revenue_is_estimate", "monthly_revenue", "units_sold")


def product_data_json(sku: dict) -> str:
    """The SKU as the model sees it: product data only, no internal
    metrics. Keys are sorted so identical SKUs hit the provider cache."""
    data = {key: value for key, value in sku.items() if key not in INTERNAL_FIELDS}
    if not data.get("extra_attributes"):
        data.pop("extra_attributes", None)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)


@dataclass(frozen=True)
class QueryResult:
    query: str
    intent_type: str
    would_surface: bool
    confidence: float
    missing_info: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class SimulationResult:
    queries: tuple[QueryResult, ...]
    surface_rate: float


def _normalize_attribute_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _parse_queries(raw: str) -> list[tuple[str, str]]:
    data = json.loads(raw)
    items = data.get("queries") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise LLMBadResponse("query generation response missing queries list")
    queries: list[tuple[str, str]] = []
    for item in items[:MAX_QUERIES_PER_SKU]:
        if not isinstance(item, dict):
            continue
        query = str(item.get("query") or "").strip()
        if not query:
            continue
        intent = str(item.get("intent_type") or "use_case").strip().lower()
        queries.append((query, intent))
    return queries


def _parse_evaluations(raw: str, queries: list[tuple[str, str]]) -> list[QueryResult]:
    data = json.loads(raw)
    items = data.get("evaluations") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise LLMBadResponse("evaluation response missing evaluations list")
    by_query = {}
    for item in items:
        if isinstance(item, dict):
            by_query[str(item.get("query") or "").strip()] = item
    results = []
    for index, (query, intent) in enumerate(queries):
        if len(items) == len(queries) and isinstance(items[index], dict):
            item = items[index]
        else:
            item = by_query.get(query, {})
        confidence = item.get("confidence")
        try:
            confidence = min(1.0, max(0.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        missing = item.get("missing_info") or []
        if not isinstance(missing, list):
            missing = []
        missing_info = tuple(
            name for name in (_normalize_attribute_name(m) for m in missing) if name
        )
        results.append(
            QueryResult(
                query=query,
                intent_type=intent,
                would_surface=bool(item.get("would_surface")),
                confidence=confidence,
                missing_info=missing_info,
                reason=str(item.get("reason") or "no evaluation returned").strip(),
            )
        )
    return results


def _surface_rate(results: list[QueryResult]) -> float:
    if not results:
        return 0.0
    total_confidence = sum(result.confidence for result in results)
    if total_confidence > 0:
        rate = (
            sum(result.confidence for result in results if result.would_surface)
            / total_confidence
        )
    else:
        rate = sum(1 for result in results if result.would_surface) / len(results)
    return round(rate, 3)


def simulate_queries(sku: dict, provider: LLMProvider) -> SimulationResult:
    category = str(sku.get("category") or "general merchandise")
    title = str(sku.get("title") or sku.get("sku_id") or "unnamed product")

    system, user = prompts.query_generation_prompt(category, title, QUERIES_PER_SKU)
    queries = _parse_queries(provider.complete(system, user, json_mode=True))
    if not queries:
        raise LLMBadResponse("query generation returned no usable queries")

    queries_json = json.dumps(
        [{"query": query, "intent_type": intent} for query, intent in queries],
        ensure_ascii=False,
    )
    system, user = prompts.query_evaluation_prompt(product_data_json(sku), queries_json)
    results = _parse_evaluations(provider.complete(system, user, json_mode=True), queries)
    return SimulationResult(queries=tuple(results), surface_rate=_surface_rate(results))
