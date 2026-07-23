"""Demo mode: fixture serving, disabled live audits, zero LLM calls."""

import pytest
from fakes import FakeProvider
from fastapi.testclient import TestClient

import app.main as main_module
from app import db, demo
from app.config import Settings
from app.scoring.pipeline import audit_sku

DEMO_SKU = {
    "sku_id": "TX-001",
    "title": "Organic Cotton Waffle Bath Towel",
    "category": "home textiles",
    "price": 34.99,
    "revenue_at_risk": 100.0,
    "revenue_is_estimate": False,
    "extra_attributes": {},
}


def build_fixture() -> dict:
    result = audit_sku(DEMO_SKU, FakeProvider())
    return {
        "run_id": "demo",
        "status": "complete",
        "sku_count": 1,
        "mapping_report": {"mapped": {"product_name": "title"}, "extra": []},
        "catalog": [DEMO_SKU],
        "aggregates": {
            "sku_count": 1,
            "readiness_revenue_weighted": result["readiness"],
            "readiness_unweighted": result["readiness"],
            "revenue_at_risk_total": 100.0,
            "rate_limited_skus": 0,
            "top_gaps": [
                {
                    "attribute": "material",
                    "sku_count": 1,
                    "share": 1.0,
                    "total_impact": 7.0,
                }
            ],
        },
        "sku_results": [result],
    }


@pytest.fixture()
def demo_client(tmp_path, monkeypatch):
    db.configure(f"sqlite:///{tmp_path}/demo.db")
    fixture = build_fixture()
    monkeypatch.setattr(demo, "get_fixture", lambda: fixture)
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(_env_file=None, demo_mode=True),
    )
    with TestClient(main_module.app) as test_client:
        yield test_client


def test_meta_reports_demo_mode(demo_client):
    body = demo_client.get("/api/meta").json()
    assert body == {"demo_mode": True, "demo_run_id": "demo"}


def test_meta_off_in_normal_mode(client):
    body = client.get("/api/meta").json()
    assert body["demo_mode"] is False
    assert body["demo_run_id"] is None


def test_live_audits_rejected_in_demo_mode(demo_client):
    upload = demo_client.post(
        "/api/catalog/upload",
        files={"file": ("c.csv", b"title,price\nTowel,10\n", "text/csv")},
    )
    assert upload.status_code == 403
    assert "saved demo" in upload.json()["detail"]
    assert demo_client.post("/api/audit/demo/start").status_code == 403


def test_demo_results_served_from_fixture(demo_client):
    body = demo_client.get("/api/audit/demo").json()
    assert body["status"] == "complete"
    assert body["sku_count"] == 1
    assert body["sku_results"][0]["sku_id"] == "TX-001"
    assert body["aggregates"]["top_gaps"][0]["attribute"] == "material"


def test_demo_sku_detail_and_missing_sku(demo_client):
    detail = demo_client.get("/api/audit/demo/sku/TX-001")
    assert detail.status_code == 200
    assert detail.json()["simulation"]["status"] == "ok"
    assert demo_client.get("/api/audit/demo/sku/NOPE").status_code == 404


def test_demo_stream_finishes_immediately(demo_client):
    stream = demo_client.get("/api/audit/demo/stream")
    assert stream.status_code == 200
    assert "event: done" in stream.text
    assert '"complete"' in stream.text


def test_demo_exports_serve_from_fixture(demo_client):
    audit = demo_client.get("/api/audit/demo/export/audit.csv")
    assert audit.status_code == 200
    assert "TX-001" in audit.text
    rewritten = demo_client.get("/api/audit/demo/export/rewritten.csv")
    assert rewritten.status_code == 200
    assert "TX-001" in rewritten.text


def test_unknown_runs_still_404_in_demo_mode(demo_client):
    assert demo_client.get("/api/audit/other").status_code == 404
