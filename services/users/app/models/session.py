# app/models/session.py
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, validates, Mapped, mapped_column
import uuid
from app.utils.db import GUID
from datetime import datetime, timedelta, timezone
from app.models.user import Base
from app.utils.security import REFRESH_TOKEN_EXPIRE_DAYS


class SessionModel(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        # create_session() always passes expires_at explicitly (refresh-token
        # lifetime, not access-token lifetime) — this default only exists as
        # a safety net for any future insert path that doesn't.
        default=lambda: datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    user = relationship("UserModel", back_populates="sessions")

    @validates("issued_at", "expires_at")
    def _strip_tzinfo(self, key, value):
        if value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return value


# UserModel.sessions = relationship("SessionModel", back_populates="user", lazy="joined")
