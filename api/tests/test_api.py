"""API routes: upload, audit lifecycle, SSE progress, sample catalog.
Runs against a temporary database with the provider mocked. The client
fixture and upload helper live in conftest.py."""

import io

from conftest import upload_sample
from fakes import RateLimitedProvider

import app.main as main_module


def test_upload_returns_run_and_mapping_report(client):
    response = upload_sample(client)
    assert response.status_code == 200
    body = response.json()
    assert body["sku_count"] == 20
    assert body["run_id"]
    assert body["mapping_report"]["mapped"]["product_name"] == "title"
    assert body["mapping_report"]["mapped"]["size"] == "dimensions"


def test_upload_without_price_column_returns_422(client):
    response = client.post(
        "/api/catalog/upload",
        files={"file": ("bad.csv", io.BytesIO(b"name,category\nTowel,textiles\n"), "text/csv")},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["missing_required"] == ["price"]


def test_start_unknown_run_returns_404(client):
    response = client.post("/api/audit/nope/start")
    assert response.status_code == 404


def test_full_audit_flow(client):
    run_id = upload_sample(client).json()["run_id"]

    start = client.post(f"/api/audit/{run_id}/start")
    assert start.status_code == 200
    assert start.json()["status"] == "running"

    results = client.get(f"/api/audit/{run_id}")
    assert results.status_code == 200
    body = results.json()
    assert body["status"] == "complete"
    assert len(body["sku_results"]) == 20
    aggregates = body["aggregates"]
    assert aggregates["sku_count"] == 20
    assert 0.0 <= aggregates["readiness_revenue_weighted"] <= 100.0
    assert aggregates["top_gaps"]

    detail = client.get(f"/api/audit/{run_id}/sku/TX-001")
    assert detail.status_code == 200
    assert detail.json()["completeness"]["score"] == 100.0

    assert client.get(f"/api/audit/{run_id}/sku/NOPE").status_code == 404

    again = client.post(f"/api/audit/{run_id}/start")
    assert again.status_code == 409


def test_stream_replays_progress_events(client):
    run_id = upload_sample(client).json()["run_id"]
    client.post(f"/api/audit/{run_id}/start")

    stream = client.get(f"/api/audit/{run_id}/stream")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    lines = stream.text.splitlines()
    data_lines = [line for line in lines if line.startswith("data: ")]
    assert len(data_lines) == 21
    assert '"sku_index": 1' in data_lines[0]
    assert '"sku_total": 20' in data_lines[0]
    assert "event: done" in lines
    assert '"status": "complete"' in data_lines[-1]


def test_stream_for_pending_run_before_start(client):
    run_id = upload_sample(client).json()["run_id"]
    stream = client.get(f"/api/audit/{run_id}/stream")
    assert stream.status_code == 200
    assert '"status": "pending"' in stream.text
    assert "event: done" in stream.text


def test_rate_limited_run_still_completes(client, monkeypatch):
    monkeypatch.setattr(main_module, "get_provider", lambda: RateLimitedProvider())
    csv = b"title,price,units_sold\nTowel,10,5\nRug,20,3\n"
    run_id = client.post(
        "/api/catalog/upload",
        files={"file": ("small.csv", io.BytesIO(csv), "text/csv")},
    ).json()["run_id"]
    client.post(f"/api/audit/{run_id}/start")

    body = client.get(f"/api/audit/{run_id}").json()
    assert body["status"] == "complete"
    assert body["aggregates"]["rate_limited_skus"] == 2
    for result in body["sku_results"]:
        assert result["simulation"]["status"] == "unavailable_rate_limited"
        assert result["before_score"] > 0
        assert result["readiness"] == result["before_score"]


def test_sample_catalog_endpoint(client):
    response = client.get("/api/sample-catalog")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("sku,product_name")
    assert len(lines) == 21
