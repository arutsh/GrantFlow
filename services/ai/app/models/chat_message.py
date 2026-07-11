import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.models.base import Base
import shared.db.type_decorators as t


class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id: Mapped[t.GUID] = mapped_column(
        t.GUID(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[t.GUID] = mapped_column(
        t.GUID(), ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
