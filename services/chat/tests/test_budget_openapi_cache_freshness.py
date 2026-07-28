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
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.mcp_bridge import fetch_cached_spec

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUDGET_SERVICE_ROOT = _REPO_ROOT / "services" / "budget"

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
    # Budget's `app` package has no __init__.py (a namespace package), while
    # chat's does (a regular package). Left to inherit this test run's own
    # PYTHONPATH (which CI sets to include services/chat, per chat.yml), the
    # subprocess's `from app.api import ...` resolves to chat's `app` instead
    # of budget's — a regular package always wins over a namespace portion,
    # regardless of `cwd` or path order. Overriding PYTHONPATH to mirror
    # budget.yml's own CI env (services/budget + repo root, for its `shared.*`
    # imports) avoids the collision entirely.
    budget_pythonpath = os.pathsep.join([str(_BUDGET_SERVICE_ROOT), str(_REPO_ROOT)])
    env = {**os.environ, "PYTHONPATH": budget_pythonpath}
    result = subprocess.run(
        [sys.executable, "-c", _FETCH_LIVE_SCHEMAS_SCRIPT],
        cwd=_BUDGET_SERVICE_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if result.returncode != 0:
        # chat.yml and budget.yml each install only their own service's
        # requirements.txt into separate CI environments — budget's runtime
        # deps (e.g. python-dateutil, redis, its DB driver) are never present
        # in chat's job, and installing budget/requirements.txt on top of
        # chat's own (13 overlapping pinned packages: fastapi, sqlalchemy,
        # uvicorn, ...) risks silently changing what chat's own suite runs
        # against. So: a missing-package import failure means this
        # environment structurally can't run the check (skip, not fail) —
        # it still catches real drift wherever budget's deps ARE available
        # (this repo's shared local dev env, or a future combined CI job).
        # Any other failure (e.g. a real syntax/schema error in budget's
        # code) still fails loudly.
        if "ModuleNotFoundError" in result.stderr:
            pytest.skip(
                "budget service dependencies aren't installed in this environment "
                f"(chat's CI job only installs services/chat/requirements.txt): "
                f"{result.stderr.strip().splitlines()[-1]}"
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
