"""One-time rollout: revoke every session belonging to an unverified user.

Run once, from the users service, after deploying this change:
    python -m maintenance.revoke_unverified_sessions
"""

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.session import SessionModel
from app.models.user import UserModel
from app.utils.security import REFRESH_TOKEN_EXPIRE_DAYS
from shared.security.session_revocation import mark_session_revoked


async def revoke_unverified_users_sessions() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SessionModel.id)
            .join(UserModel, UserModel.id == SessionModel.user_id)
            .where(UserModel.email_verified.is_(False), SessionModel.revoked.is_(False))
        )
        session_ids = [row[0] for row in result.all()]
        if not session_ids:
            return 0

        await db.execute(
            SessionModel.__table__.update()
            .where(SessionModel.id.in_(session_ids))
            .values(revoked=True)
        )
        await db.commit()

        for session_id in session_ids:
            await mark_session_revoked(
                str(session_id), ttl_seconds=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
            )

        return len(session_ids)


if __name__ == "__main__":
    count = asyncio.run(revoke_unverified_users_sessions())
    print(f"Revoked {count} session(s) belonging to unverified users.")
