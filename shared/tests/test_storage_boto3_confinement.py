"""
Guard test: boto3 must stay confined to shared/storage/s3_storage_service.py.

That module is the only place in the repo allowed to know it's talking to
S3 — everything else, including other services, only ever sees the
StorageService interface (save/open_stream/delete/exists). This is a pure
text scan (no boto3 import needed), so it runs in any CI job regardless of
whether boto3 happens to be installed there.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_FILE = REPO_ROOT / "shared" / "storage" / "s3_storage_service.py"
BOTO3_IMPORT_RE = re.compile(r"^\s*(import boto3\b|from boto3\b)")
EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "frontend-typescript",
    ".mypy_cache",
    ".pytest_cache",
}


def _python_files():
    for path in REPO_ROOT.rglob("*.py"):
        if not path.is_file():
            continue
        if EXCLUDED_DIR_NAMES.intersection(path.parts):
            continue
        yield path


def test_boto3_only_imported_in_storage_service():
    offenders = []
    for path in _python_files():
        if path == ALLOWED_FILE:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(BOTO3_IMPORT_RE.match(line) for line in text.splitlines()):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert (
        offenders == []
    ), f"boto3 imported outside shared/storage/s3_storage_service.py: {offenders}"
