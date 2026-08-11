import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_financial_record_refs(user_id: str, token: str) -> list[dict]:
    """Best-effort listing of budgets/reports the user created, for the
    data-export endpoint (data-subject-rights spec). Calls the budget
    service's /budgets/by-creator and /reports/by-creator endpoints — see
    services/budget/app/api/budget_routes.py.

    Deliberately refs only (id/name/type/created_at), never full budget or
    report content: a budget belongs to the customer (org), not the user
    who created it, and its contents may include other staff's edits or
    donor data. GDPR Art. 15 only entitles the user to their own personal
    data — here, the fact that they performed this action — not the org's
    business records, and Art. 15(4) bars exposing other people's data via
    someone else's access request. Do not expand this to full content.

    `token` is the requesting user's own access token, forwarded as-is —
    those endpoints are self-service only (they 403 unless the token's
    subject matches `user_id`), not a trusted-by-network-boundary internal
    endpoint like /customers/by_ids/, since the gateway forwards this
    service's whole path space with no internal/external distinction.

    Swallows failures: a budget-service hiccup shouldn't turn an otherwise
    complete export (profile + consent) into a 500. Returns [] on failure.
    """
    base_url = settings.BUDGET_SERVICE_URL
    headers = {"Authorization": f"Bearer {token}"}
    records: list[dict] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0, headers=headers) as client:
        for path in (f"/budgets/by-creator/{user_id}", f"/reports/by-creator/{user_id}"):
            try:
                resp = await client.get(path)
                resp.raise_for_status()
                records.extend(resp.json())
            except Exception:
                logger.exception("financial_record_export_lookup_failed", path=path)
    return records
