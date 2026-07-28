"""Drift detection for the checked-in fallback spec (services/chat/app/services/
cache/budget_openapi.json). fetch_cached_spec's docstring claims "the
schema-parity tests are what catch it going stale relative to budget's real
routes" — but TestSchemaParity (test_mcp_bridge.py) only validates the cached
spec against a hand-curated allowlist, never against budget's actual current
schema. This test is the missing half: it runs budget's own app.openapi() in
a subprocess (avoiding a `app.*` package name collision between the two
services) and compares the BudgetCreate/BudgetUpdate schemas — the two models
mcp_bridge's create_budget/update_budget tools are built from — against what's
cached. A mismatch here means someone changed budget's schema without
re-running `fetch_cached_spec`'s manual refresh step.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.mcp_bridge import fetch_cached_spec

_BUDGET_SERVICE_ROOT = Path(__file__).resolve().parents[2] / "budget"

_FETCH_LIVE_SCHEMAS_SCRIPT = """
import os
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
import json
from main import app
schemas = app.openapi()["components"]["schemas"]
picked = {"BudgetCreate": schemas["BudgetCreate"], "BudgetUpdate": schemas["BudgetUpdate"]}
print(json.dumps(picked))
"""


@pytest.mark.skipif(
    not (_BUDGET_SERVICE_ROOT / "main.py").exists(),
    reason="budget service checkout not found alongside chat",
)
def test_cached_spec_budget_schemas_match_live_budget_app():
    result = subprocess.run(
        [sys.executable, "-c", _FETCH_LIVE_SCHEMAS_SCRIPT],
        cwd=_BUDGET_SERVICE_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    # budget's settings module prints debug banner lines to stdout on import
    # (unrelated to this test) — the schema JSON is always the last line.
    last_line = result.stdout.strip().splitlines()[-1]
    live_schemas = json.loads(last_line)

    cached_schemas = fetch_cached_spec()["components"]["schemas"]

    assert live_schemas["BudgetCreate"] == cached_schemas["BudgetCreate"], (
        "budget_openapi.json's BudgetCreate is stale relative to budget's live "
        "schema — re-run app.openapi() in services/budget and overwrite the "
        "cache (see fetch_cached_spec's docstring), then re-check "
        "mcp_bridge's create_budget arg transform for any newly-added field."
    )
    assert live_schemas["BudgetUpdate"] == cached_schemas["BudgetUpdate"], (
        "budget_openapi.json's BudgetUpdate is stale relative to budget's live "
        "schema — re-run app.openapi() in services/budget and overwrite the "
        "cache (see fetch_cached_spec's docstring), then re-check "
        "mcp_bridge's update_budget arg transform for any newly-added field."
    )
