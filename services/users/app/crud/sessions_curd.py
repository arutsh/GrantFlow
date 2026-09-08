from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.session import SessionModel
from app.utils.security import (
    hash_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
from app.utils.redis import _cache_set


async def create_session(session: AsyncSession, user_id: UUID, refresh_token_hash) -> SessionModel:
    issued_at = datetime.now(ZoneInfo("UTC"))
    new_session = SessionModel(
        user_id=user_id,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        refresh_token_hash=hash_token(refresh_token_hash),
    )
    session.add(new_session)
    await session.commit()
    # Store mapping in Redis: refresh_token → session_id
    redis_key = f"refresh:{refresh_token_hash}"
    _cache_set(redis_key, str(new_session.id), ttl=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

    return new_session


async def get_non_revoked_sessions(session: AsyncSession):
    result = await session.execute(select(SessionModel).where(SessionModel.revoked.is_(False)))
    return list(result.scalars().all())


async def get_non_revoked_sessions_for_user(
    session: AsyncSession, user_id: UUID
) -> list[SessionModel]:
    result = await session.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user_id, SessionModel.revoked.is_(False))
        .order_by(SessionModel.issued_at.desc())
    )
    return list(result.scalars().all())


async def revoke_all_sessions_for_user(session: AsyncSession, user_id: UUID) -> list[SessionModel]:
    """Used by account deletion — revokes every active session for a user
    and returns them so the caller can also clear their Redis entries."""
    sessions = await get_non_revoked_sessions_for_user(session, user_id)
    for s in sessions:
        s.revoked = True
    await session.commit()
    return sessions


async def revoke_session(session: AsyncSession, db_session: SessionModel) -> SessionModel:
    db_session.revoked = True
    await session.commit()
    return db_session


async def get_session_by_id(session: AsyncSession, session_id: UUID) -> SessionModel | None:
    result = await session.execute(
        select(SessionModel)
        .options(joinedload(SessionModel.user))
        .where(SessionModel.id == session_id)
    )
    return result.scalar_one_or_none()
