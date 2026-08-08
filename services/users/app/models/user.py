# /services/users/app/models/user.py
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import Base

# import enum
import uuid
from datetime import datetime
from app.utils.db import GUID
from shared.schemas.user_schema import UserStatus, UserRole


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False, index=True
    )

    # Name fields with default empty string
    first_name: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    last_name: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))

    # Email and role
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(String, nullable=False)

    # Password hash
    hashed_password: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # can be changed to nullable=False later

    # Foreign key to customers
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("customers.id"), nullable=True  # or UUID type if PostgreSQL
    )

    # Enum status with default
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        nullable=False,
        default=UserStatus.pending,
        server_default=text(f"'{UserStatus.pending.value}'"),
    )
    # Email verification
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    email_verification_token_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer = relationship("CustomerModel", lazy="joined")
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
