import fakeredis
import pytest

from shared.security import session_revocation

pytestmark = pytest.mark.anyio


class TestSessionRevocation:
    async def test_not_revoked_by_default(self, monkeypatch):
        fake = fakeredis.FakeAsyncRedis()
        monkeypatch.setattr(session_revocation, "_redis_client", fake)
        assert await session_revocation.is_session_revoked("session-1") is False

    async def test_marking_revoked_is_then_reflected(self, monkeypatch):
        fake = fakeredis.FakeAsyncRedis()
        monkeypatch.setattr(session_revocation, "_redis_client", fake)
        await session_revocation.mark_session_revoked("session-2", ttl_seconds=3600)
        assert await session_revocation.is_session_revoked("session-2") is True

    async def test_revoking_one_session_does_not_affect_another(self, monkeypatch):
        fake = fakeredis.FakeAsyncRedis()
        monkeypatch.setattr(session_revocation, "_redis_client", fake)
        await session_revocation.mark_session_revoked("session-3", ttl_seconds=3600)
        assert await session_revocation.is_session_revoked("session-3") is True
        assert await session_revocation.is_session_revoked("session-4") is False

    async def test_empty_session_id_is_never_revoked(self, monkeypatch):
        fake = fakeredis.FakeAsyncRedis()
        monkeypatch.setattr(session_revocation, "_redis_client", fake)
        assert await session_revocation.is_session_revoked("") is False
        assert await session_revocation.is_session_revoked(None) is False

    async def test_redis_unavailable_fails_open(self, monkeypatch):
        monkeypatch.setattr(session_revocation, "_get_client", lambda: None)
        assert await session_revocation.is_session_revoked("session-5") is False
        # Must not raise even though there's nothing to write to.
        await session_revocation.mark_session_revoked("session-5", ttl_seconds=60)
