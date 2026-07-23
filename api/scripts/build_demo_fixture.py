"""Build the committed demo fixture: one full audit of the sample catalog
using the configured free-tier key, run locally, written to
app/demo/sample_audit.json. Run it via make demo-fixture.

A hard request budget aborts the run long before the free daily cap is at
risk. A normal 20-SKU build uses roughly 60 requests.
"""

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from app.catalog.ingest import ingest_catalog  # noqa: E402
from app.llm.provider import LLMProvider  # noqa: E402
from app.scoring.pipeline import audit_sku, compute_aggregates, run_audit  # noqa: E402

SAMPLE_CATALOG = API_DIR / "tests" / "sample_catalog.csv"
FIXTURE_PATH = API_DIR / "app" / "demo" / "sample_audit.json"

MAX_REQUESTS = 150

DEGRADED = "unavailable_rate_limited"


def _is_degraded(result: dict) -> bool:
    return DEGRADED in (result["simulation"]["status"], result["rewrite"]["status"])


def retry_degraded() -> int:
    """Re-audit only the SKUs a previous build left degraded, merge them
    into the existing fixture, and rebuild the aggregates. Cheaper than a
    full rebuild, protects the free daily cap."""
    fixture = json.loads(FIXTURE_PATH.read_text())
    catalog = {str(sku["sku_id"]): sku for sku in fixture["catalog"]}
    provider = LLMProvider()
    replaced = 0
    for index, result in enumerate(fixture["sku_results"]):
        if not _is_degraded(result):
            continue
        sku = catalog.get(str(result["sku_id"]))
        if sku is None:
            continue
        if provider.usage()["requests"] > MAX_REQUESTS:
            print("request budget exceeded, stopping early")
            break
        fresh = audit_sku(sku, provider)
        if _is_degraded(fresh):
            print(f"{result['sku_id']} still rate limited, keeping previous result", flush=True)
            continue
        fixture["sku_results"][index] = fresh
        replaced += 1
        print(f"{result['sku_id']} replaced, {provider.usage()['requests']} requests so far", flush=True)

    fixture["aggregates"] = compute_aggregates(fixture["sku_results"])
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
    usage = provider.usage()
    remaining = sum(1 for result in fixture["sku_results"] if _is_degraded(result))
    print(f"replaced {replaced} results, {remaining} still degraded")
    print(f"total this run: {usage['requests']} requests")
    return 1 if remaining else 0


def main() -> int:
    ingested = ingest_catalog(SAMPLE_CATALOG)
    provider = LLMProvider()

    def on_progress(index: int, total: int, sku_id: str, status: str) -> None:
        usage = provider.usage()
        print(f"[{index}/{total}] {sku_id} {status}, {usage['requests']} requests so far", flush=True)
        if usage["requests"] > MAX_REQUESTS:
            print("request budget exceeded, aborting to protect the free daily cap")
            raise SystemExit(2)

    outcome = run_audit(ingested.skus, provider=provider, on_progress=on_progress)

    fixture = {
        "run_id": "demo",
        "status": "complete",
        "sku_count": ingested.sku_count,
        "mapping_report": {
            "mapped": ingested.mapping_report.mapped,
            "extra": list(ingested.mapping_report.extra),
        },
        "catalog": ingested.skus,
        "aggregates": outcome["aggregates"],
        "sku_results": outcome["sku_results"],
    }
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")

    usage = provider.usage()
    print(f"wrote {FIXTURE_PATH}")
    print(
        f"total: {usage['requests']} requests, {usage['prompt_tokens']} prompt tokens, "
        f"{usage['completion_tokens']} completion tokens"
    )
    degraded = outcome["aggregates"]["rate_limited_skus"]
    if degraded:
        print(f"warning: {degraded} SKUs were degraded by rate limits, rerun later for a full fixture")
        return 1
    return 0


if __name__ == "__main__":
    if "--retry-degraded" in sys.argv:
        raise SystemExit(retry_degraded())
    raise SystemExit(main())
