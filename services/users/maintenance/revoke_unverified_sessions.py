"""One-time rollout: revoke every session belonging to an unverified user.

Run once, from the users service, after deploying this change:
    python -m maintenance.revoke_unverified_sessions
"""

from app.crud.sessions_curd import revoke_all_sessions_for_user
from app.db.session import SessionLocal
from app.models.user import UserModel
from app.utils.security import REFRESH_TOKEN_EXPIRE_DAYS
from shared.security.session_revocation import mark_session_revoked


def revoke_unverified_users_sessions() -> int:
    db = SessionLocal()
    revoked_count = 0
    try:
        unverified_user_ids = [
            user_id
            for (user_id,) in db.query(UserModel.id)
            .filter(UserModel.email_verified.is_(False))
            .all()
        ]
        for user_id in unverified_user_ids:
            sessions = revoke_all_sessions_for_user(db, user_id)
            for s in sessions:
                mark_session_revoked(str(s.id), ttl_seconds=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)
                revoked_count += 1
        return revoked_count
    finally:
        db.close()


if __name__ == "__main__":
    count = revoke_unverified_users_sessions()
    print(f"Revoked {count} session(s) belonging to unverified users.")
