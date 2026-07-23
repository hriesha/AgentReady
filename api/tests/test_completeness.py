"""Completeness scoring: weighted math and deterministic vagueness checks."""

import pytest

from app.catalog.canonical import (
    ATTRIBUTES_BY_NAME,
    CANONICAL_ATTRIBUTES,
    TOTAL_WEIGHT,
)
from app.scoring.completeness import (
    MISSING,
    OK,
    VAGUE,
    check_text,
    score_attribute,
    score_sku,
)

COMPLETE_SKU = {
    "title": "Organic Cotton Waffle Bath Towel, 70x140 cm, Slate Gray",
    "category": "home textiles",
    "price": 34.99,
    "currency": "USD",
    "availability": "in_stock",
    "brand": "Loomline",
    "description": "Waffle weave bath towel in 400 gsm organic cotton, absorbs fast and dries quickly.",
    "material": "100% organic cotton",
    "dimensions": {"length": 140, "width": 70, "height": 0.5, "unit": "cm"},
    "weight": "550 g",
    "color": "slate gray",
    "usage_scenario": "daily family bathroom use, folds small for a gym bag",
    "care_instructions": "machine wash at 40C, tumble dry low",
    "certifications": ["OEKO-TEX Standard 100", "GOTS"],
    "key_features": ["quick drying waffle weave", "double stitched hems"],
    "target_audience": "households replacing worn towels",
    "warranty": "2 year warranty against manufacturing defects",
    "shipping_info": "ships in 2 business days, free over 50 USD",
}


def test_rubric_shape():
    assert len(CANONICAL_ATTRIBUTES) == 18
    assert TOTAL_WEIGHT == 114
    names = [a.name for a in CANONICAL_ATTRIBUTES]
    assert len(names) == len(set(names))


def test_complete_sku_scores_100():
    result = score_sku(COMPLETE_SKU)
    assert result.score == 100.0
    assert result.missing == []
    assert result.vague == []


def test_empty_sku_scores_0():
    result = score_sku({})
    assert result.score == 0.0
    assert len(result.missing) == 18


def test_title_only_weighted_math():
    result = score_sku({"title": "Organic Cotton Waffle Bath Towel"})
    assert result.score == round(100 * 10 / TOTAL_WEIGHT, 1)


def test_vague_value_earns_half_credit():
    sku = {
        "title": "Organic Cotton Waffle Bath Towel",
        "price": 34.99,
        "description": "high quality, durable",
    }
    result = score_sku(sku)
    expected = round(100 * (10 * 1.0 + 10 * 1.0 + 6 * 0.5) / TOTAL_WEIGHT, 1)
    assert result.score == expected
    assert result.vague == ["description"]


def test_scoring_is_deterministic():
    first = score_sku(COMPLETE_SKU)
    second = score_sku(COMPLETE_SKU)
    assert first == second


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "n/a",
        "N/A",
        "TBD",
        "-",
        "...",
        "ab",
        "high quality",
        "High Quality, Durable",
        "premium",
        "good and durable",
        "durable / reliable",
    ],
)
def test_check_text_flags_vague(value):
    status, reason = check_text(value)
    assert status == VAGUE
    assert reason


@pytest.mark.parametrize(
    "value",
    [
        "100% organic cotton",
        "machine wash cold",
        "red",
        "waffle weave, quick drying",
        "premium cotton with reinforced hems",
    ],
)
def test_check_text_accepts_specific(value):
    assert check_text(value) == (OK, "")


@pytest.mark.parametrize(
    "value, expected",
    [
        (34.99, OK),
        ("34.99", OK),
        ("$34.99", OK),
        (0, VAGUE),
        (-5, VAGUE),
        ("cheap", VAGUE),
        (None, MISSING),
    ],
)
def test_price_scoring(value, expected):
    assert score_attribute(ATTRIBUTES_BY_NAME["price"], value).status == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("in_stock", OK),
        ("In Stock", OK),
        ("preorder", OK),
        ("out_of_stock", OK),
        ("yes", VAGUE),
        ("", VAGUE),
        (None, MISSING),
    ],
)
def test_availability_scoring(value, expected):
    assert score_attribute(ATTRIBUTES_BY_NAME["availability"], value).status == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (["OEKO-TEX Standard 100"], OK),
        ("OEKO-TEX, GOTS", OK),
        (["good"], VAGUE),
        ([], MISSING),
        (None, MISSING),
    ],
)
def test_list_scoring(value, expected):
    assert score_attribute(ATTRIBUTES_BY_NAME["certifications"], value).status == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ({"length": 140, "width": 70, "height": 0.5, "unit": "cm"}, OK),
        ({"length": 140, "width": 70, "unit": "cm"}, VAGUE),
        ("70 x 140 cm", VAGUE),
        ({}, MISSING),
        (None, MISSING),
    ],
)
def test_dimensions_scoring(value, expected):
    assert score_attribute(ATTRIBUTES_BY_NAME["dimensions"], value).status == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("550 g", OK),
        ("1.2 kg", OK),
        ({"value": 1.2, "unit": "kg"}, OK),
        (550, VAGUE),
        ("heavy", VAGUE),
        (None, MISSING),
    ],
)
def test_weight_scoring(value, expected):
    assert score_attribute(ATTRIBUTES_BY_NAME["weight"], value).status == expected


def test_scores_stay_in_range():
    skus = [
        {},
        {"title": "ab"},
        COMPLETE_SKU,
        {"title": "Towel", "price": "not a price", "certifications": []},
    ]
    for sku in skus:
        result = score_sku(sku)
        assert 0.0 <= result.score <= 100.0
