from uuid import UUID
from sqlalchemy.orm import Session
from app.models.session import SessionModel
from app.utils.security import (
    hash_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
from app.utils.redis import _cache_set


def create_session(session: Session, user_id: UUID, refresh_token_hash) -> SessionModel:
    issued_at = datetime.now(ZoneInfo("UTC"))
    new_session = SessionModel(
        user_id=user_id,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        refresh_token_hash=hash_token(refresh_token_hash),
    )
    session.add(new_session)
    session.commit()
    session.refresh(new_session)
    # Store mapping in Redis: refresh_token → session_id
    redis_key = f"refresh:{refresh_token_hash}"
    _cache_set(redis_key, str(new_session.id), ttl=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

    return new_session


def get_non_revoked_sessions(session: Session):
    return session.query(SessionModel).filter(SessionModel.revoked.is_(False)).all()


def get_non_revoked_sessions_for_user(session: Session, user_id: UUID) -> list[SessionModel]:
    return (
        session.query(SessionModel)
        .filter(SessionModel.user_id == user_id, SessionModel.revoked.is_(False))
        .order_by(SessionModel.issued_at.desc())
        .all()
    )


def revoke_all_sessions_for_user(session: Session, user_id: UUID) -> list[SessionModel]:
    """Used by account deletion — revokes every active session for a user
    and returns them so the caller can also clear their Redis entries."""
    sessions = get_non_revoked_sessions_for_user(session, user_id)
    for s in sessions:
        s.revoked = True
    session.commit()
    return sessions


def revoke_session(session: Session, db_session: SessionModel) -> SessionModel:
    db_session.revoked = True
    session.commit()
    session.refresh(db_session)
    return db_session


def get_session_by_id(session: Session, session_id: UUID) -> SessionModel | None:
    return session.query(SessionModel).filter(SessionModel.id == session_id).first()
