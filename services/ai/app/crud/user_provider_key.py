from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_provider_key import UserProviderKey


async def get_key(user_id: str, provider_id: str, db: AsyncSession) -> UserProviderKey | None:
    result = await db.execute(
        select(UserProviderKey).where(
            UserProviderKey.user_id == user_id,
            UserProviderKey.provider_id == provider_id,
        )
    )
    return result.unique().scalar_one_or_none()


async def get_active_key_for_customer(
    customer_id: str, db: AsyncSession
) -> UserProviderKey | None:
    """Return the active BYOK key for any admin in the org (looked up by customer_id).

    This is the preferred lookup for non-admin users so they benefit from the
    key set by their org admin without needing their own key.
    """
    result = await db.execute(
        select(UserProviderKey)
        .where(
            UserProviderKey.customer_id == customer_id,
            or_(
                UserProviderKey.encrypted_key.isnot(None),
                UserProviderKey.base_url.isnot(None),
            ),
        )
        .order_by(UserProviderKey.updated_at.desc())
    )
    return result.unique().scalars().first()


async def upsert_key(
    user_id: str,
    provider_id: str,
    encrypted_key: str | None,
    model_name: str | None,
    base_url: str | None,
    db: AsyncSession,
    customer_id: str | None = None,
) -> UserProviderKey:
    now = datetime.now(timezone.utc)
    existing = await get_key(user_id, provider_id, db)
    if existing:
        existing.encrypted_key = encrypted_key
        existing.model_name = model_name
        existing.base_url = base_url
        existing.updated_at = now
        if customer_id is not None:
            existing.customer_id = customer_id
        await db.commit()
        await db.refresh(existing)
        return existing
    row = UserProviderKey(
        user_id=user_id,
        provider_id=provider_id,
        customer_id=customer_id,
        encrypted_key=encrypted_key,
        model_name=model_name,
        base_url=base_url,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_key(user_id: str, provider_id: str, db: AsyncSession) -> None:
    existing = await get_key(user_id, provider_id, db)
    if existing:
        existing.encrypted_key = None
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
