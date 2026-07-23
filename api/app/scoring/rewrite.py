"""Attribute rewriting: turn weak values into clean structured data using
only information already present in the product data, never inventing
facts. One LLM call per SKU covers every flagged attribute. Values the
model cannot derive come back null with a needs_human note instead of a
guess. Price is never rewritten: a model must not set prices.
"""

import json
from dataclasses import dataclass

from app.llm import prompts
from app.llm.provider import LLMBadResponse, LLMProvider
from app.scoring.simulate import product_data_json

NEVER_REWRITE = ("price",)


@dataclass(frozen=True)
class RewriteOutcome:
    attribute: str
    original: object
    value: object
    needs_human: str | None


@dataclass(frozen=True)
class RewriteResult:
    outcomes: tuple[RewriteOutcome, ...]

    def apply(self, sku: dict) -> dict:
        """Original SKU with every derivable rewrite merged in."""
        rewritten = dict(sku)
        for outcome in self.outcomes:
            if outcome.value is not None:
                rewritten[outcome.attribute] = outcome.value
        return rewritten


def rewrite_attributes(
    sku: dict, attributes: list[str], provider: LLMProvider
) -> RewriteResult:
    targets = [name for name in attributes if name not in NEVER_REWRITE]
    if not targets:
        return RewriteResult(outcomes=())

    system, user = prompts.rewrite_prompt(product_data_json(sku), targets)
    raw = provider.complete(system, user, json_mode=True)
    data = json.loads(raw)
    items = data.get("rewrites") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise LLMBadResponse("rewrite response missing rewrites list")

    by_attribute: dict[str, tuple[object, str | None]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("attribute") or "").strip()
        if name not in targets:
            continue
        value = item.get("value")
        if isinstance(value, str):
            value = value.strip() or None
        note = item.get("needs_human")
        note = str(note).strip() or None if note else None
        by_attribute[name] = (value, note)

    outcomes = []
    for name in targets:
        value, note = by_attribute.get(name, (None, "no rewrite returned"))
        if value is None and note is None:
            note = "not derivable from existing data"
        outcomes.append(
            RewriteOutcome(
                attribute=name,
                original=sku.get(name),
                value=value,
                needs_human=None if value is not None else note,
            )
        )
    return RewriteResult(outcomes=tuple(outcomes))
