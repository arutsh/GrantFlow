"""E2E: does the contextvar set in get_current_user survive to the flush over a real auth chain."""

import uuid

import fakeredis
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from shared.db.audit_mixin import AuditMixin
from shared.security import session_revocation
from shared.security.dependencies import get_validated_user
from shared.security.jwt_utils import create_access_token

pytestmark = pytest.mark.anyio


class _Base(DeclarativeBase):
    pass


class _WidgetModel(_Base, AuditMixin):
    """Throwaway audited model, distinct table from test_audit_mixin.py's."""

    __tablename__ = "e2e_widgets"

    name: Mapped[str] = mapped_column(default="widget")


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(session_revocation, "_redis_client", fake)
    return fake


@pytest.fixture
async def engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def app(engine):
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    fastapi_app = FastAPI()

    @fastapi_app.post("/widgets")
    async def create_widget(valid_user: dict = Depends(get_validated_user)):
        async with session_maker() as session:
            widget = _WidgetModel()
            session.add(widget)
            await session.commit()
            return {"created_by": str(widget.created_by) if widget.created_by else None}

    return fastapi_app


def _token_for(user_id: str) -> str:
    return create_access_token(
        {"user_id": user_id, "session_id": "e2e-session", "role": "user", "email_verified": True}
    )


class TestContextPropagationThroughARealRequest:
    async def test_created_by_populated_via_real_auth_dependency_and_async_engine(self, app):
        """Covers design.md's greenlet_spawn + threadpool risks (all 4 services are async now)."""
        user_id = str(uuid.uuid4())
        client = TestClient(app)

        response = client.post(
            "/widgets", headers={"Authorization": f"Bearer {_token_for(user_id)}"}
        )

        assert response.status_code == 200
        assert response.json()["created_by"] == user_id

    async def test_missing_auth_header_is_rejected_before_any_insert(self, app):
        client = TestClient(app)

        response = client.post("/widgets")

        assert response.status_code == 401
