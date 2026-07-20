import uuid
from enum import Enum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import mapped_column, Mapped

from app.models.base import Base
import shared.db.type_decorators as t


class AIModelName(str, Enum):
    claude_sonnet_4_6 = "claude-sonnet-4-6"
    llama3_2 = "llama3.2"
    gemma4 = "gemma4:12b"


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[t.GUID] = mapped_column(
        t.GUID(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
