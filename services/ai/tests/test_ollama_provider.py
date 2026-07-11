"""Tests for the Ollama path in resolve_model (replaces OllamaProvider unit tests).

OllamaProvider was removed in Phase 8. Ollama is now wired through
PydanticAI's OpenAIModel with an Ollama-compatible base_url.
"""
from unittest.mock import MagicMock, patch

from app.services.provider import ResolvedModel, resolve_model


def _make_ollama_key(model_name="llama3.2", base_url="http://ollama:11434"):
    user_key = MagicMock()
    user_key.provider.name = "ollama"
    user_key.model_name = model_name
    user_key.encrypted_key = None
    user_key.base_url = base_url
    return user_key


class TestResolveModelOllama:
    def test_ollama_key_returns_resolved_model(self):
        user_key = _make_ollama_key()
        resolved = resolve_model(user_key=user_key)
        assert isinstance(resolved, ResolvedModel)
        assert resolved.provider_name == "ollama"
        assert resolved.model_name == "llama3.2"

    def test_ollama_uses_base_url_from_key(self):
        user_key = _make_ollama_key(base_url="http://custom-ollama:11434")
        resolved = resolve_model(user_key=user_key)
        assert resolved is not None

    def test_ollama_falls_back_to_settings_url_when_no_base_url(self):
        user_key = _make_ollama_key()
        user_key.base_url = None
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.OLLAMA_URL = "http://settings-ollama:11434"
            mock_settings.ENCRYPTION_KEY = "key"
            resolved = resolve_model(user_key=user_key)
        assert resolved is not None
        assert resolved.provider_name == "ollama"

    def test_ollama_returns_none_when_no_url_available(self):
        user_key = _make_ollama_key()
        user_key.base_url = None
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.OLLAMA_URL = None
            mock_settings.ENCRYPTION_KEY = "key"
            resolved = resolve_model(user_key=user_key)
        assert resolved is None
