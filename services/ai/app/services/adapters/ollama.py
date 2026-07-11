from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.services.provider import ProviderAdapter, ResolvedModel, register


@register("ollama")
class OllamaAdapter(ProviderAdapter):
    def build(self, user_key) -> ResolvedModel | None:
        from app.core.config import settings

        base_url = user_key.base_url or settings.OLLAMA_URL
        if not base_url:
            return None
        return ResolvedModel(
            model=OpenAIChatModel(
                user_key.model_name,
                provider=OpenAIProvider(
                    base_url=f"{base_url.rstrip('/')}/v1",
                    api_key="ollama",
                ),
            ),
            provider_name="ollama",
            model_name=user_key.model_name,
        )

    # validate_key not overridden — Ollama requires no live key validation
