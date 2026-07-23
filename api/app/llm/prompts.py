"""Prompt templates for every LLM call in the audit pipeline.

All prompt text lives here and only here. Prompts must not name any AI
vendor or assistant product: shopping assistants are referenced only
generically. Each builder returns a (system, user) pair for
LLMProvider.complete with json_mode=True.
"""

INTENT_TYPES = ("budget", "use_case", "material_spec", "comparison", "trust")

QUERY_GENERATION_SYSTEM = (
    "You write realistic shopping queries that real buyers type into AI "
    "shopping assistants. Queries are short, natural, and grounded in the "
    "product category, not in this specific product's marketing copy."
)

_QUERY_GENERATION_USER = """Product category: {category}
Product being audited: {title}

Write {count} short queries a real buyer might ask an AI shopping assistant when looking for a product in this category. Spread them across these intent types: budget (price constrained), use_case (a concrete context or scenario), material_spec (materials or specifications), comparison (weighing options), trust (certifications, warranty, reliability).

Return JSON in exactly this shape:
{{"queries": [{{"query": "...", "intent_type": "budget"}}]}}
intent_type must be one of: budget, use_case, material_spec, comparison, trust."""

QUERY_EVALUATION_SYSTEM = (
    "You act as the retrieval and reasoning step of an AI shopping "
    "assistant. You decide whether a product would be surfaced for a "
    "query using only the structured product data provided. You never "
    "assume facts that are not in the data."
)

_QUERY_EVALUATION_USER = """Product data:
{product_json}

Shopper queries:
{queries_json}

For each query, decide whether this product would be surfaced as a recommendation, using only the product data above. Return JSON in exactly this shape:
{{"evaluations": [{{"query": "...", "would_surface": true, "confidence": 0.8, "missing_info": ["attribute_name"], "reason": "one short sentence"}}]}}
confidence is between 0 and 1. missing_info lists attribute names you needed but could not find in the data, use canonical names where possible. Keep each reason to one sentence."""

REWRITE_SYSTEM = (
    "You rewrite weak ecommerce product attributes into clean, specific, "
    "structured values using only information already present in the "
    "product data. You never invent facts: no fabricated certifications, "
    "measurements, materials, or claims. If a value cannot be derived "
    "from the data provided, return null for it with a short needs_human "
    "note saying what a human must supply."
)

_REWRITE_USER = """Product data:
{product_json}

Attributes to rewrite because they are missing or vague: {attributes}

Return JSON in exactly this shape:
{{"rewrites": [{{"attribute": "attribute_name", "value": "rewritten value or null", "needs_human": "note when value is null, else null"}}]}}
Values must be derivable from the product data above. Prefer concrete nouns, numbers, and units over adjectives. Do not repeat filler wording."""

VAGUENESS_SYSTEM = (
    "You judge whether an ecommerce attribute value is specific enough "
    "for a shopping assistant to act on."
)

_VAGUENESS_USER = """Attribute name: {attribute}
Attribute value: {value}

Is this value specific and informative for this attribute, or vague filler? Return JSON in exactly this shape:
{{"vague": true}}"""


def query_generation_prompt(category: str, title: str, count: int) -> tuple[str, str]:
    user = _QUERY_GENERATION_USER.format(category=category, title=title, count=count)
    return QUERY_GENERATION_SYSTEM, user


def query_evaluation_prompt(product_json: str, queries_json: str) -> tuple[str, str]:
    user = _QUERY_EVALUATION_USER.format(
        product_json=product_json, queries_json=queries_json
    )
    return QUERY_EVALUATION_SYSTEM, user


def rewrite_prompt(product_json: str, attributes: list[str]) -> tuple[str, str]:
    user = _REWRITE_USER.format(
        product_json=product_json, attributes=", ".join(attributes)
    )
    return REWRITE_SYSTEM, user


def vagueness_prompt(attribute: str, value: str) -> tuple[str, str]:
    user = _VAGUENESS_USER.format(attribute=attribute, value=value)
    return VAGUENESS_SYSTEM, user
