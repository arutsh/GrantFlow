import fakeredis

from app.services import login_rate_limiter as limiter


class TestLoginRateLimiter:
    def test_not_locked_out_before_threshold(self, monkeypatch):
        fake = fakeredis.FakeStrictRedis()
        monkeypatch.setattr(limiter, "redis_client", fake)
        monkeypatch.setattr(limiter.settings, "LOGIN_MAX_ATTEMPTS", 5)

        for _ in range(4):
            limiter.record_failed_attempt("user@example.com", "1.2.3.4")

        assert limiter.is_locked_out("user@example.com", "1.2.3.4") is False

    def test_locked_out_after_threshold(self, monkeypatch):
        fake = fakeredis.FakeStrictRedis()
        monkeypatch.setattr(limiter, "redis_client", fake)
        monkeypatch.setattr(limiter.settings, "LOGIN_MAX_ATTEMPTS", 3)

        for _ in range(3):
            limiter.record_failed_attempt("user@example.com", "1.2.3.4")

        assert limiter.is_locked_out("user@example.com", "1.2.3.4") is True

    def test_lockout_is_per_account_and_per_ip(self, monkeypatch):
        fake = fakeredis.FakeStrictRedis()
        monkeypatch.setattr(limiter, "redis_client", fake)
        monkeypatch.setattr(limiter.settings, "LOGIN_MAX_ATTEMPTS", 2)

        for _ in range(2):
            limiter.record_failed_attempt("victim@example.com", "9.9.9.9")

        # Different account, same IP — still locked (per-IP limit hit).
        assert limiter.is_locked_out("someone-else@example.com", "9.9.9.9") is True
        # Different account, different IP — untouched.
        assert limiter.is_locked_out("someone-else@example.com", "1.1.1.1") is False

    def test_clearing_resets_account_lockout(self, monkeypatch):
        fake = fakeredis.FakeStrictRedis()
        monkeypatch.setattr(limiter, "redis_client", fake)
        monkeypatch.setattr(limiter.settings, "LOGIN_MAX_ATTEMPTS", 2)

        # Two different IPs so only the account counter crosses the threshold.
        limiter.record_failed_attempt("user@example.com", "1.2.3.4")
        limiter.record_failed_attempt("user@example.com", "5.6.7.8")
        assert limiter.is_locked_out("user@example.com", "9.9.9.9") is True

        limiter.clear_failed_attempts("user@example.com")
        assert limiter.is_locked_out("user@example.com", "9.9.9.9") is False

    def test_clearing_does_not_reset_ip_lockout(self, monkeypatch):
        fake = fakeredis.FakeStrictRedis()
        monkeypatch.setattr(limiter, "redis_client", fake)
        monkeypatch.setattr(limiter.settings, "LOGIN_MAX_ATTEMPTS", 2)

        # Two accounts failing from the same IP trips the IP-wide counter.
        limiter.record_failed_attempt("attacker1@example.com", "9.9.9.9")
        limiter.record_failed_attempt("attacker2@example.com", "9.9.9.9")
        assert limiter.is_locked_out("attacker2@example.com", "9.9.9.9") is True

        # One account's success must not reset the shared IP counter.
        limiter.clear_failed_attempts("attacker2@example.com")
        assert limiter.is_locked_out("victim@example.com", "9.9.9.9") is True

    def test_redis_unavailable_fails_open(self, monkeypatch):
        monkeypatch.setattr(limiter, "redis_client", None)
        assert limiter.is_locked_out("user@example.com", "1.2.3.4") is False
        # Must not raise.
        limiter.record_failed_attempt("user@example.com", "1.2.3.4")
        limiter.clear_failed_attempts("user@example.com")
