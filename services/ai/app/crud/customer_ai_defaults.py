from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_ai_defaults import CustomerAiDefaults


async def get(customer_id: str, db: AsyncSession) -> CustomerAiDefaults | None:
    result = await db.execute(
        select(CustomerAiDefaults).where(CustomerAiDefaults.customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def set_platform_fallback(
    customer_id: str, enabled: bool, db: AsyncSession
) -> CustomerAiDefaults:
    now = datetime.now(timezone.utc)
    existing = await get(customer_id, db)
    if existing:
        existing.platform_fallback_enabled = enabled
        existing.updated_at = now
        await db.commit()
        await db.refresh(existing)
        return existing
    row = CustomerAiDefaults(
        customer_id=customer_id,
        platform_fallback_enabled=enabled,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
