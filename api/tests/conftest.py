"""Shared fixtures: an API test client on a temporary database with the
provider mocked."""

from pathlib import Path

import pytest
from fakes import FakeProvider
from fastapi.testclient import TestClient

import app.main as main_module
from app import db

SAMPLE_CATALOG = Path(__file__).parent / "sample_catalog.csv"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db.configure(f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setattr(main_module, "get_provider", lambda: FakeProvider())
    with TestClient(main_module.app) as test_client:
        yield test_client


def upload_sample(client):
    with SAMPLE_CATALOG.open("rb") as handle:
        return client.post(
            "/api/catalog/upload",
            files={"file": ("catalog.csv", handle, "text/csv")},
        )
