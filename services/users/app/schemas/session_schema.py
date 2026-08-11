from pydantic import BaseModel, field_serializer
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import UUID


class Session(BaseModel):
    id: UUID
    user_id: UUID
    issued_at: datetime
    expires_at: datetime
    revoked: bool

    @field_serializer("issued_at", "expires_at")
    def serialize_utc(self, value: datetime, _info) -> datetime:
        # Assume naive datetime from DB is in UTC. `_info` must be declared
        # even though unused — pydantic-core miscounts a 2-arg serializer
        # as the unbound (value, info) form and passes info as `value`.
        return value.replace(tzinfo=ZoneInfo("UTC"))

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    """Active-session-listing shape for GET /auth/sessions — deliberately
    excludes user_id/revoked (redundant: the endpoint only ever returns the
    caller's own non-revoked sessions) and adds `current` so the frontend
    can flag the session backing the request that fetched the list."""

    id: UUID
    issued_at: datetime
    expires_at: datetime
    current: bool

    @field_serializer("issued_at", "expires_at")
    def serialize_utc(self, value: datetime, _info) -> datetime:
        # `_info` must be declared — see Session.serialize_utc above.
        return value.replace(tzinfo=ZoneInfo("UTC"))

    class Config:
        from_attributes = True
