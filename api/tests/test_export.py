"""CSV exports: builder output shape and the download routes."""

import csv
import io

from conftest import upload_sample
from fakes import FakeProvider

from app.catalog.ingest import ingest_catalog
from app.export.csv_export import AUDIT_COLUMNS, audit_report_csv, rewritten_catalog_csv
from app.scoring.pipeline import audit_sku
from conftest import SAMPLE_CATALOG


def parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_audit_report_columns_and_values():
    sku = ingest_catalog(SAMPLE_CATALOG).skus[1]
    result = audit_sku(sku, FakeProvider())
    rows = parse_csv(audit_report_csv([result]))
    assert list(rows[0].keys()) == list(AUDIT_COLUMNS)
    row = rows[0]
    assert row["sku_id"] == "TX-002"
    assert float(row["readiness"]) == result["readiness"]
    assert row["revenue_is_estimate"] == "no"
    assert row["simulation_status"] == "ok"
    assert "description" in row["vague_attributes"]


def test_rewritten_catalog_applies_values_and_notes():
    skus = ingest_catalog(SAMPLE_CATALOG).skus
    sku = skus[1]
    result = audit_sku(sku, FakeProvider())
    rows = parse_csv(rewritten_catalog_csv([sku], [result]))
    row = rows[0]
    assert row["sku_id"] == "TX-002"
    assert row["description"] == "specific rewritten description content"
    assert "certifications:" in row["needs_human"]
    assert row["price"] == "49.99"


def test_rewritten_catalog_formats_structured_values():
    sku = {
        "sku_id": "X-1",
        "title": "Towel",
        "price": 10.0,
        "dimensions": {"length": 140.0, "width": 70.0, "height": 0.5, "unit": "cm"},
        "certifications": ["OEKO-TEX", "GOTS"],
        "extra_attributes": {"gift_wrap": "yes"},
    }
    rows = parse_csv(rewritten_catalog_csv([sku], []))
    row = rows[0]
    assert row["dimensions"] == "140.0 x 70.0 x 0.5 cm"
    assert row["certifications"] == "OEKO-TEX, GOTS"
    assert row["gift_wrap"] == "yes"
    assert row["needs_human"] == ""


def test_export_routes_download_csv(client):
    run_id = upload_sample(client).json()["run_id"]
    client.post(f"/api/audit/{run_id}/start")

    audit = client.get(f"/api/audit/{run_id}/export/audit.csv")
    assert audit.status_code == 200
    assert audit.headers["content-type"].startswith("text/csv")
    assert "attachment" in audit.headers["content-disposition"]
    assert len(parse_csv(audit.text)) == 20

    rewritten = client.get(f"/api/audit/{run_id}/export/rewritten.csv")
    assert rewritten.status_code == 200
    rows = parse_csv(rewritten.text)
    assert len(rows) == 20
    assert rows[0]["sku_id"] == "TX-001"
    assert "needs_human" in rows[0]


def test_export_unknown_run_returns_404(client):
    assert client.get("/api/audit/nope/export/audit.csv").status_code == 404
    assert client.get("/api/audit/nope/export/rewritten.csv").status_code == 404
