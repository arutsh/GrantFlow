from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_provider_key import UserProviderKey


async def get_by_id(customer_id: str, config_id: str, db: AsyncSession) -> UserProviderKey | None:
    result = await db.execute(
        select(UserProviderKey).where(
            UserProviderKey.customer_id == customer_id,
            UserProviderKey.id == config_id,
        )
    )
    return result.unique().scalar_one_or_none()


async def get_by_ids(
    customer_id: str, config_ids: list[str], db: AsyncSession
) -> dict[str, UserProviderKey]:
    result = await db.execute(
        select(UserProviderKey).where(
            UserProviderKey.customer_id == customer_id,
            UserProviderKey.id.in_(config_ids),
        )
    )
    return {str(row.id): row for row in result.unique().scalars().all()}


async def list_for_customer(customer_id: str, db: AsyncSession) -> list[UserProviderKey]:
    result = await db.execute(
        select(UserProviderKey)
        .where(UserProviderKey.customer_id == customer_id)
        .order_by(UserProviderKey.created_at)
    )
    return list(result.unique().scalars().all())


async def get_active_key_for_customer(customer_id: str, db: AsyncSession) -> UserProviderKey | None:
    """Return the org's default BYOK config (looked up by customer_id).

    This is the preferred lookup for non-admin users so they benefit from the
    key set by their org admin without needing their own key.
    """
    result = await db.execute(
        select(UserProviderKey).where(
            UserProviderKey.customer_id == customer_id,
            UserProviderKey.is_default.is_(True),
        )
    )
    return result.unique().scalar_one_or_none()


async def _unset_default(customer_id: str, db: AsyncSession) -> None:
    current = await get_active_key_for_customer(customer_id, db)
    if current is not None:
        current.is_default = False
        current.updated_at = datetime.now(timezone.utc)


async def create(
    customer_id: str,
    user_id: str,
    provider_id: str,
    label: str | None,
    encrypted_key: str | None,
    model_name: str | None,
    base_url: str | None,
    is_default: bool,
    db: AsyncSession,
) -> UserProviderKey:
    now = datetime.now(timezone.utc)
    if is_default:
        await _unset_default(customer_id, db)
        await db.flush()
    row = UserProviderKey(
        user_id=user_id,
        customer_id=customer_id,
        provider_id=provider_id,
        label=label,
        encrypted_key=encrypted_key,
        model_name=model_name,
        base_url=base_url,
        is_default=is_default,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def set_default(customer_id: str, config_id: str, db: AsyncSession) -> UserProviderKey:
    target = await get_by_id(customer_id, config_id, db)
    if target is None:
        raise ValueError(f"Config {config_id} not found for customer {customer_id}")
    await _unset_default(customer_id, db)
    await db.flush()
    target.is_default = True
    target.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(target)
    return target


async def delete(
    customer_id: str,
    config_id: str,
    db: AsyncSession,
    *,
    new_default_id: str | None = None,
) -> None:
    """Deleting the default is always allowed; new_default_id is optional."""
    ids = [config_id, new_default_id] if new_default_id else [config_id]
    rows = await get_by_ids(customer_id, ids, db)
    target = rows.get(config_id)
    if target is None:
        return

    if target.is_default and new_default_id:
        replacement = rows.get(new_default_id)
        if replacement is None or replacement.id == target.id:
            raise ValueError(
                f"Replacement config {new_default_id} not found for customer {customer_id}"
            )
        # Flush target=False first or the partial unique index rejects
        # both rows being is_default=True in the same flush.
        target.is_default = False
        await db.flush()
        replacement.is_default = True
        replacement.updated_at = datetime.now(timezone.utc)

    await db.delete(target)
    await db.commit()
