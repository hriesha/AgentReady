"""CSV catalog ingest: column mapping, validation, and type coercion.

Reads a catalog with pandas, fuzzy-maps incoming column names onto the
canonical attribute schema, coerces values into the shapes the scorer
expects, and computes revenue at risk per SKU. Fully deterministic, no LLM.
"""

import re
from dataclasses import dataclass

import pandas as pd

REQUIRED_ATTRIBUTES = ("title", "price")

ASSUMED_MONTHLY_UNITS = 1.0

COLUMN_SYNONYMS: dict[str, set[str]] = {
    "title": {"title", "name", "product_name", "product_title", "item_name", "product"},
    "category": {"category", "product_category", "product_type", "department"},
    "price": {"price", "cost", "msrp", "unit_price", "sale_price", "price_usd", "retail_price"},
    "currency": {"currency", "currency_code"},
    "availability": {"availability", "avail", "stock", "stock_status", "inventory_status", "in_stock"},
    "brand": {"brand", "manufacturer", "brand_name", "vendor", "maker"},
    "description": {"description", "desc", "product_description", "long_description", "details"},
    "material": {"material", "materials", "fabric", "composition", "made_of"},
    "dimensions": {"dimensions", "dims", "size", "dimension", "measurements", "product_dimensions"},
    "weight": {"weight", "item_weight", "product_weight", "wt"},
    "color": {"color", "colour", "color_name", "colour_name"},
    "usage_scenario": {"usage_scenario", "usage", "use_case", "intended_use", "scenario"},
    "care_instructions": {"care_instructions", "care", "washing_instructions", "maintenance"},
    "certifications": {"certifications", "certification", "certs", "certificates", "compliance"},
    "key_features": {"key_features", "features", "highlights", "bullet_points", "selling_points"},
    "target_audience": {"target_audience", "audience", "target_market", "for_whom"},
    "warranty": {"warranty", "guarantee", "warranty_info"},
    "shipping_info": {"shipping_info", "shipping", "delivery", "delivery_info", "shipping_details"},
}

SPECIAL_SYNONYMS: dict[str, set[str]] = {
    "sku_id": {"sku", "sku_id", "sku_code", "product_id", "item_id", "item_number", "id"},
    "monthly_revenue": {"monthly_revenue", "revenue", "monthly_sales", "sales_revenue"},
    "units_sold": {"units_sold", "units", "monthly_units", "qty_sold", "quantity_sold", "unit_sales"},
}

AVAILABILITY_SYNONYMS: dict[str, set[str]] = {
    "in_stock": {"in stock", "instock", "available", "yes", "true", "y", "1"},
    "out_of_stock": {"out of stock", "outofstock", "oos", "unavailable", "sold out", "soldout", "no", "false", "n", "0"},
    "preorder": {"preorder", "pre order", "backorder", "back order", "coming soon"},
}


def _normalize_column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


_TARGET_BY_SYNONYM: dict[str, str] = {
    _normalize_column(synonym): target
    for target, synonyms in {**COLUMN_SYNONYMS, **SPECIAL_SYNONYMS}.items()
    for synonym in synonyms
}


class CatalogValidationError(ValueError):
    """Catalog cannot be audited. Carries the missing required fields so the
    API layer can return a clear 422."""

    def __init__(self, message: str, missing_required: list[str] | None = None):
        super().__init__(message)
        self.missing_required = missing_required or []


@dataclass(frozen=True)
class MappingReport:
    mapped: dict[str, str]
    extra: tuple[str, ...]


@dataclass(frozen=True)
class IngestResult:
    skus: list[dict]
    mapping_report: MappingReport

    @property
    def sku_count(self) -> int:
        return len(self.skus)


def map_columns(columns) -> tuple[dict[str, str], list[str]]:
    """Map incoming column names to canonical targets, first match wins.

    Unmapped columns are retained per SKU under extra_attributes.
    """
    mapped: dict[str, str] = {}
    extra: list[str] = []
    claimed: set[str] = set()
    for column in columns:
        target = _TARGET_BY_SYNONYM.get(_normalize_column(str(column)))
        if target is not None and target not in claimed:
            mapped[str(column)] = target
            claimed.add(target)
        else:
            extra.append(str(column))
    return mapped, extra


def parse_price(value: str) -> float | None:
    cleaned = value.strip().lstrip("$€£").replace(" ", "")
    if not cleaned:
        return None
    if "," in cleaned and "." not in cleaned:
        whole, _, fraction = cleaned.partition(",")
        cleaned = f"{whole}.{fraction}" if len(fraction) == 2 else cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


_DIMENSIONS_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:x|×|\*|by)\s*(\d+(?:[.,]\d+)?)"
    r"(?:\s*(?:x|×|\*|by)\s*(\d+(?:[.,]\d+)?))?"
    r"\s*(inches|inch|in|feet|ft|cm|mm|m)?",
    re.IGNORECASE,
)


def _to_float(number_text: str) -> float:
    return float(number_text.replace(",", "."))


def parse_dimensions(value: str) -> dict | str:
    """Parse "140 x 70 x 0.5 cm" style strings into length, width, height
    and unit. Returns the original string when no structure is found, so
    the scorer can still flag it as present but unstructured."""
    match = _DIMENSIONS_RE.search(value)
    if match is None:
        return value
    length, width, height, unit = match.groups()
    dimensions: dict = {"length": _to_float(length), "width": _to_float(width)}
    if height:
        dimensions["height"] = _to_float(height)
    if unit:
        dimensions["unit"] = unit.lower()
    return dimensions


def normalize_availability(value: str) -> str:
    normalized = re.sub(r"[\s_\-]+", " ", value.strip().lower())
    for canonical_value, synonyms in AVAILABILITY_SYNONYMS.items():
        if normalized in synonyms:
            return canonical_value
    return value


def split_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;|]", value) if item.strip()]


def coerce_value(target: str, value: str):
    """Coerce one cell into the canonical shape. Unparseable prices and
    dimensions keep their raw value so completeness can score them vague
    instead of missing. Unparseable revenue inputs return None and are
    dropped, they are metrics rather than product data."""
    if target == "price":
        parsed = parse_price(value)
        return parsed if parsed is not None else value
    if target == "dimensions":
        return parse_dimensions(value)
    if target == "availability":
        return normalize_availability(value)
    if target in ("certifications", "key_features"):
        return split_list(value)
    if target in ("monthly_revenue", "units_sold"):
        return parse_price(value)
    return value


def _attach_revenue(sku: dict, assumed_monthly_units: float) -> None:
    price = sku.get("price")
    price_value = price if isinstance(price, float) else None
    monthly_revenue = sku.get("monthly_revenue")
    units_sold = sku.get("units_sold")
    if isinstance(monthly_revenue, float):
        revenue, estimated = monthly_revenue, False
    elif isinstance(units_sold, float) and price_value is not None:
        revenue, estimated = units_sold * price_value, False
    elif price_value is not None:
        revenue, estimated = price_value * assumed_monthly_units, True
    else:
        revenue, estimated = 0.0, True
    sku["revenue_at_risk"] = round(revenue, 2)
    sku["revenue_is_estimate"] = estimated


def ingest_catalog(source, assumed_monthly_units: float = ASSUMED_MONTHLY_UNITS) -> IngestResult:
    """Read a CSV catalog from a path or file-like object and return
    normalized SKU dicts plus the column mapping report."""
    try:
        frame = pd.read_csv(source, dtype=str)
    except pd.errors.EmptyDataError as error:
        raise CatalogValidationError("catalog file is empty") from error

    mapped, extra = map_columns(frame.columns)
    targets = set(mapped.values())
    missing = [attribute for attribute in REQUIRED_ATTRIBUTES if attribute not in targets]
    if missing:
        raise CatalogValidationError(
            "missing required columns: " + ", ".join(missing),
            missing_required=missing,
        )
    if frame.empty:
        raise CatalogValidationError("catalog has no rows")

    skus: list[dict] = []
    for index, row in enumerate(frame.to_dict(orient="records")):
        sku: dict = {"extra_attributes": {}}
        for column, raw in row.items():
            if pd.isna(raw):
                continue
            text = str(raw).strip()
            if not text:
                continue
            target = mapped.get(str(column))
            if target is None:
                sku["extra_attributes"][str(column)] = text
                continue
            value = coerce_value(target, text)
            if value is None or value == []:
                continue
            sku[target] = value
        if "sku_id" not in sku:
            sku["sku_id"] = f"sku-{index + 1:03d}"
        _attach_revenue(sku, assumed_monthly_units)
        skus.append(sku)

    return IngestResult(
        skus=skus,
        mapping_report=MappingReport(mapped=mapped, extra=tuple(extra)),
    )
