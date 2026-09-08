# shared/db/audit_mixin.py
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, event

from shared.db.type_decorators import GUID


class AuditMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=lambda: uuid.uuid4())

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), nullable=True)

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), nullable=True)


@event.listens_for(AuditMixin, "before_update", propagate=True)
def _set_updated_at(mapper, connection, target: AuditMixin) -> None:
    target.updated_at = datetime.now(timezone.utc)
