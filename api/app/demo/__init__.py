"""Demo mode: serve a precomputed audit of the sample catalog from a
committed JSON fixture, with zero live LLM calls. The public deployment
runs with DEMO_MODE=true so it always works and can never incur cost."""

import json
from pathlib import Path

DEMO_RUN_ID = "demo"
FIXTURE_PATH = Path(__file__).parent / "sample_audit.json"

_fixture: dict | None = None
_loaded = False


def get_fixture() -> dict | None:
    global _fixture, _loaded
    if not _loaded:
        _loaded = True
        if FIXTURE_PATH.exists():
            _fixture = json.loads(FIXTURE_PATH.read_text())
    return _fixture
