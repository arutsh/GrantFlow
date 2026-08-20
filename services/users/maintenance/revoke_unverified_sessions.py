"""One-time rollout: revoke every session belonging to an unverified user.

Run once, from the users service, after deploying this change:
    python -m maintenance.revoke_unverified_sessions
"""

from app.db.session import SessionLocal
from app.models.session import SessionModel
from app.models.user import UserModel
from app.utils.security import REFRESH_TOKEN_EXPIRE_DAYS
from shared.security.session_revocation import mark_session_revoked


def revoke_unverified_users_sessions() -> int:
    db = SessionLocal()
    try:
        session_ids = [
            session_id
            for (session_id,) in db.query(SessionModel.id)
            .join(UserModel, UserModel.id == SessionModel.user_id)
            .filter(UserModel.email_verified.is_(False), SessionModel.revoked.is_(False))
            .all()
        ]
        if not session_ids:
            return 0

        db.query(SessionModel).filter(SessionModel.id.in_(session_ids)).update(
            {"revoked": True}, synchronize_session=False
        )
        db.commit()

        for session_id in session_ids:
            mark_session_revoked(str(session_id), ttl_seconds=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

        return len(session_ids)
    finally:
        db.close()


if __name__ == "__main__":
    count = revoke_unverified_users_sessions()
    print(f"Revoked {count} session(s) belonging to unverified users.")
