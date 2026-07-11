from unittest.mock import MagicMock, patch

from app.services.provider import ResolvedModel, resolve_model


def _make_user_key(provider_name="anthropic", model_name="claude-sonnet-4-6", encrypted_key="enc"):
    user_key = MagicMock()
    user_key.provider.name = provider_name
    user_key.model_name = model_name
    user_key.encrypted_key = encrypted_key
    user_key.base_url = None
    return user_key


class TestResolveModel:
    def test_anthropic_key_returns_resolved_model(self):
        user_key = _make_user_key()
        with patch("app.utils.encryption.decrypt", return_value="sk-ant-api03-test"):
            resolved = resolve_model(user_key=user_key)
        assert resolved is not None
        assert isinstance(resolved, ResolvedModel)
        assert resolved.provider_name == "anthropic"
        assert resolved.model_name == "claude-sonnet-4-6"

    def test_anthropic_key_uses_model_name(self):
        user_key = _make_user_key(model_name="claude-haiku-4-5-20251001")
        with patch("app.utils.encryption.decrypt", return_value="sk-ant-api03-test"):
            resolved = resolve_model(user_key=user_key)
        assert resolved is not None
        assert resolved.model_name == "claude-haiku-4-5-20251001"

    def test_missing_model_name_returns_none(self):
        user_key = _make_user_key(model_name=None)
        resolved = resolve_model(user_key=user_key)
        assert resolved is None

    def test_no_key_returns_none(self):
        assert resolve_model(user_key=None) is None

    def test_no_args_returns_none(self):
        assert resolve_model() is None

    def test_ollama_key_returns_resolved_model(self):
        user_key = _make_user_key(provider_name="ollama", model_name="llama3.2", encrypted_key=None)
        user_key.base_url = "http://localhost:11434"
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.OLLAMA_URL = "http://localhost:11434"
            mock_settings.ENCRYPTION_KEY = "key"
            resolved = resolve_model(user_key=user_key)
        assert resolved is not None
        assert resolved.provider_name == "ollama"
        assert resolved.model_name == "llama3.2"
