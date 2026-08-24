from datetime import datetime, timezone

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AIAuditLog


async def write_audit_log(
    *,
    customer_id: str,
    user_id: str,
    prompt_version: str,
    input_text: str,
    output_json: dict | None = None,
    provider: str,
    model: str,
    funding_source: str = "byok",
    input_tokens: int = 0,
    output_tokens: int = 0,
    success: bool,
    error_message: str | None = None,
    duration_ms: int,
) -> None:
    async with AsyncSessionLocal() as db:
        log = AIAuditLog(
            customer_id=customer_id,
            user_id=user_id,
            prompt_version=prompt_version,
            input_text=input_text,
            output_json=output_json,
            provider=provider,
            model=model,
            funding_source=funding_source,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()
