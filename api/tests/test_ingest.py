"""Catalog ingest: column mapping, validation, coercion, revenue at risk."""

import io
from pathlib import Path

import pytest

from app.catalog.canonical import CANONICAL_ATTRIBUTES
from app.catalog.ingest import (
    COLUMN_SYNONYMS,
    CatalogValidationError,
    ingest_catalog,
    normalize_availability,
    parse_dimensions,
    parse_price,
)
from app.scoring.completeness import score_sku

SAMPLE_CATALOG = Path(__file__).parent / "sample_catalog.csv"


def ingest_text(csv_text: str, **kwargs):
    return ingest_catalog(io.StringIO(csv_text), **kwargs)


def test_synonym_table_covers_every_canonical_attribute():
    assert set(COLUMN_SYNONYMS) == {attr.name for attr in CANONICAL_ATTRIBUTES}


def test_column_mapping_normalizes_case_spaces_and_punctuation():
    result = ingest_text("Product Name,MSRP,Avail,Price (USD)\nTowel,10,In Stock,12\n")
    assert result.mapping_report.mapped == {
        "Product Name": "title",
        "MSRP": "price",
        "Avail": "availability",
    }
    assert result.mapping_report.extra == ("Price (USD)",)


def test_synonym_resolution():
    result = ingest_text("name,cost,dims,stock\nTowel,10,70 x 140 cm,yes\n")
    assert result.mapping_report.mapped == {
        "name": "title",
        "cost": "price",
        "dims": "dimensions",
        "stock": "availability",
    }


def test_unmapped_columns_kept_as_extra_attributes():
    result = ingest_text("title,price,gift_wrap\nTowel,10,yes\n")
    assert result.mapping_report.extra == ("gift_wrap",)
    assert result.skus[0]["extra_attributes"] == {"gift_wrap": "yes"}


def test_duplicate_synonyms_first_column_wins():
    result = ingest_text("title,price,msrp\nTowel,10,12\n")
    assert result.mapping_report.mapped["price"] == "price"
    assert "msrp" in result.mapping_report.extra
    assert result.skus[0]["price"] == 10.0


def test_missing_price_column_raises_with_field_named():
    with pytest.raises(CatalogValidationError) as excinfo:
        ingest_text("title,category\nTowel,textiles\n")
    assert excinfo.value.missing_required == ["price"]
    assert "price" in str(excinfo.value)


def test_missing_both_required_columns():
    with pytest.raises(CatalogValidationError) as excinfo:
        ingest_text("category,brand\ntextiles,Loomline\n")
    assert excinfo.value.missing_required == ["title", "price"]


def test_catalog_with_no_rows_raises():
    with pytest.raises(CatalogValidationError):
        ingest_text("title,price\n")


def test_empty_file_raises():
    with pytest.raises(CatalogValidationError):
        ingest_text("")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("$1,299.00", 1299.0),
        ("24.99", 24.99),
        ("24,99", 24.99),
        ("189", 189.0),
        ("call us", None),
    ],
)
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


def test_unparseable_price_keeps_raw_value():
    result = ingest_text("title,price\nTowel,call us\n")
    assert result.skus[0]["price"] == "call us"


def test_dimensions_parsed_into_structured_fields():
    assert parse_dimensions("140 x 70 x 0.5 cm") == {
        "length": 140.0,
        "width": 70.0,
        "height": 0.5,
        "unit": "cm",
    }


def test_two_dimensional_size_has_no_height():
    parsed = parse_dimensions("70 x 140 cm")
    assert parsed == {"length": 70.0, "width": 140.0, "unit": "cm"}


def test_unparseable_dimensions_stay_raw():
    assert parse_dimensions("irregular shape") == "irregular shape"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("In Stock", "in_stock"),
        ("Sold Out", "out_of_stock"),
        ("Pre-Order", "preorder"),
        ("maybe", "maybe"),
    ],
)
def test_availability_normalization(raw, expected):
    assert normalize_availability(raw) == expected


def test_list_attributes_split_on_separators():
    result = ingest_text(
        'title,price,certs,features\nTowel,10,"OEKO-TEX, GOTS","soft; absorbent | washable"\n'
    )
    assert result.skus[0]["certifications"] == ["OEKO-TEX", "GOTS"]
    assert result.skus[0]["key_features"] == ["soft", "absorbent", "washable"]


def test_empty_cells_are_absent_not_empty_strings():
    result = ingest_text("title,price,material\nTowel,10,\n")
    assert "material" not in result.skus[0]


def test_revenue_uses_monthly_revenue_when_present():
    result = ingest_text("title,price,monthly_revenue\nTowel,10,500\n")
    sku = result.skus[0]
    assert sku["revenue_at_risk"] == 500.0
    assert sku["revenue_is_estimate"] is False


def test_revenue_from_units_sold_times_price():
    result = ingest_text("title,price,units_sold\nTowel,20,10\n")
    sku = result.skus[0]
    assert sku["revenue_at_risk"] == 200.0
    assert sku["revenue_is_estimate"] is False


def test_revenue_falls_back_to_labeled_estimate():
    result = ingest_text("title,price\nTowel,20\n")
    sku = result.skus[0]
    assert sku["revenue_at_risk"] == 20.0
    assert sku["revenue_is_estimate"] is True


def test_sku_ids_from_column_or_generated():
    with_column = ingest_text("sku,title,price\nTX-9,Towel,10\n")
    assert with_column.skus[0]["sku_id"] == "TX-9"
    generated = ingest_text("title,price\nTowel,10\nRug,20\n")
    assert [s["sku_id"] for s in generated.skus] == ["sku-001", "sku-002"]


def test_sample_catalog_ingests_with_expected_spread():
    result = ingest_catalog(SAMPLE_CATALOG)
    assert result.sku_count == 20
    assert {"title", "price"} <= set(result.mapping_report.mapped.values())
    assert len({sku["category"] for sku in result.skus}) == 3
    out_of_stock = [s for s in result.skus if s.get("availability") == "out_of_stock"]
    assert len(out_of_stock) == 2
    scores = [score_sku(sku).score for sku in result.skus]
    assert max(scores) > 90
    assert min(scores) < 45
