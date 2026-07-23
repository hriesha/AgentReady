"""CSV exports: the audit report and the rewritten catalog.

Both are built from stored results, so exporting never recomputes scores
and never calls the LLM. A partial run exports whatever completed.
"""

import csv
import io

from app.catalog.canonical import CANONICAL_ATTRIBUTES

AUDIT_COLUMNS = (
    "sku_id",
    "title",
    "readiness",
    "completeness_score",
    "projected_after_score",
    "surface_rate",
    "revenue_at_risk",
    "revenue_is_estimate",
    "simulation_status",
    "rewrite_status",
    "top_gap",
    "missing_attributes",
    "vague_attributes",
)


def audit_report_csv(results: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(AUDIT_COLUMNS)
    for result in results:
        completeness = result.get("completeness", {})
        simulation = result.get("simulation", {})
        gaps = result.get("gaps", [])
        after_score = result.get("after_score")
        surface_rate = simulation.get("surface_rate")
        writer.writerow(
            [
                result.get("sku_id", ""),
                result.get("title") or "",
                result.get("readiness", ""),
                completeness.get("score", ""),
                "" if after_score is None else after_score,
                "" if surface_rate is None else surface_rate,
                result.get("revenue_at_risk", ""),
                "yes" if result.get("revenue_is_estimate") else "no",
                simulation.get("status", ""),
                result.get("rewrite", {}).get("status", ""),
                gaps[0]["attribute"] if gaps else "",
                ", ".join(completeness.get("missing", [])),
                ", ".join(completeness.get("vague", [])),
            ]
        )
    return buffer.getvalue()


def _format_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        if {"length", "width"} <= set(value):
            parts = [str(value[f]) for f in ("length", "width", "height") if f in value]
            text = " x ".join(parts)
            unit = value.get("unit")
            return f"{text} {unit}" if unit else text
        if {"value", "unit"} <= set(value):
            return f"{value['value']} {value['unit']}"
        return "; ".join(f"{key}: {item}" for key, item in value.items())
    return str(value)


def rewritten_catalog_csv(skus: list[dict], results: list[dict]) -> str:
    """The stored catalog with every derivable rewrite applied. Attributes
    the model could not derive keep their original value and are listed in
    the needs_human column."""
    outcomes_by_sku: dict[str, list[dict]] = {
        str(result.get("sku_id", "")): result.get("rewrite", {}).get("outcomes", [])
        for result in results
    }
    canonical_names = [attribute.name for attribute in CANONICAL_ATTRIBUTES]
    extra_columns = sorted(
        {key for sku in skus for key in (sku.get("extra_attributes") or {})}
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["sku_id", *canonical_names, *extra_columns, "needs_human"])
    for sku in skus:
        sku_id = str(sku.get("sku_id", ""))
        rewritten = dict(sku)
        notes = []
        for outcome in outcomes_by_sku.get(sku_id, []):
            if outcome.get("value") is not None:
                rewritten[outcome["attribute"]] = outcome["value"]
            elif outcome.get("needs_human"):
                notes.append(f"{outcome['attribute']}: {outcome['needs_human']}")
        extras = rewritten.get("extra_attributes") or {}
        row = [sku_id]
        row.extend(_format_cell(rewritten.get(name)) for name in canonical_names)
        row.extend(_format_cell(extras.get(column)) for column in extra_columns)
        row.append("; ".join(notes))
        writer.writerow(row)
    return buffer.getvalue()
