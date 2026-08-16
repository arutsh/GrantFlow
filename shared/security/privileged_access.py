"""Registry for the privileged-access audit hook (customer-impersonation /
privileged-access-audit capabilities). Each service registers its own
local-DB writer at startup; shared/security/dependencies.py fires it."""

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

PrivilegedAccessSink = Callable[[dict, Request], None]
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

_sink: Optional[PrivilegedAccessSink] = None


def register_privileged_access_sink(fn: Optional[PrivilegedAccessSink]) -> None:
    global _sink
    _sink = fn


def build_privileged_access_kwargs(payload: dict, request: Request) -> dict:
    return {
        "actor_user_id": payload.get("user_id"),
        "customer_id": payload.get("customer_id"),
        "method": request.method,
        "path": request.url.path,
        "created_at": datetime.now(timezone.utc),
    }


def make_privileged_access_sink(session_factory: Callable, model_cls: type) -> PrivilegedAccessSink:
    """Build a registrable sink for one service: opens a session via
    session_factory (sync SessionLocal for budget/users, a dedicated sync
    engine for ai/chat), writes a row, closes it."""

    def _sink(payload: dict, request: Request) -> None:
        db = session_factory()
        try:
            db.add(model_cls(**build_privileged_access_kwargs(payload, request)))
            db.commit()
        finally:
            db.close()

    return _sink


def log_privileged_access(payload: dict, request: Request) -> None:
    """Fail-closed for writes, fail-open for reads — a broken audit table
    shouldn't lock a superuser out of viewing during a live demo, but must
    block mutations (design.md Open Questions)."""
    if request is None:
        return
    try:
        if _sink is None:
            raise RuntimeError("no privileged-access sink registered")
        _sink(payload, request)
    except Exception:
        logger.exception("privileged_access_log_write_failed")
        if request.method not in _SAFE_METHODS:
            raise HTTPException(status_code=503, detail="Privileged-access audit log unavailable")
