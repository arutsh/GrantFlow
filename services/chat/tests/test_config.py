import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestHttpClientTimeoutValidation:
    def test_rejects_zero(self):
        with pytest.raises(ValidationError):
            Settings(chat_database_url="postgresql://x", HTTP_CLIENT_TIMEOUT_SECONDS=0)

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            Settings(chat_database_url="postgresql://x", HTTP_CLIENT_TIMEOUT_SECONDS=-5)

    def test_accepts_positive(self):
        settings = Settings(chat_database_url="postgresql://x", HTTP_CLIENT_TIMEOUT_SECONDS=180)
        assert settings.HTTP_CLIENT_TIMEOUT_SECONDS == 180
