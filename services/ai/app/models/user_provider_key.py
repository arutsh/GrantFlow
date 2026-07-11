import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.models.base import Base
from app.models.ai_provider import AIModelName
import shared.db.type_decorators as t


class UserProviderKey(Base):
    __tablename__ = "user_provider_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider_id", name="uq_user_provider_keys_user_provider"),
    )

    id: Mapped[t.GUID] = mapped_column(
        t.GUID(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[t.GUID] = mapped_column(t.GUID(), nullable=False, index=True)
    customer_id: Mapped[t.GUID | None] = mapped_column(t.GUID(), nullable=True, index=True)
    provider_id: Mapped[t.GUID] = mapped_column(
        t.GUID(), ForeignKey("ai_providers.id"), nullable=False
    )
    encrypted_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    provider: Mapped["AIProvider"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AIProvider", lazy="joined"
    )

    @property
    def resolved_model(self) -> str:
        """Return configured model or the enum default for the provider."""
        if self.model_name:
            return self.model_name
        from app.core.config import settings

        return settings.OLLAMA_MODEL

    @property
    def model(self) -> AIModelName | None:
        if self.model_name:
            return AIModelName(self.model_name)
        return None
