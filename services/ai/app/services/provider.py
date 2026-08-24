from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from fastapi import Depends
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.core.logging import get_logger
from app.utils.security import get_validated_user, resolve_customer_id

logger = get_logger(__name__)

# Cheapest current Claude model — used only for the GrantFlow-funded fallback
# path (no BYOK key configured), never the user's own choice of model.
_PLATFORM_FUNDED_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class ResolvedModel:
    """PydanticAI model ready for use in an Agent, plus metadata for audit logging."""

    model: AnthropicModel | OpenAIChatModel
    provider_name: str
    model_name: str


def build_agent(model: AnthropicModel | OpenAIChatModel, **kwargs: Any) -> Agent:
    """Construct a PydanticAI Agent with OTEL instrumentation enabled.

    Every Agent in this service must go through here — `agent.run()` produces
    no spans at all unless `instrument = True` is set, so a forgotten call site
    turns the entire model call (provider request, retries, errors) into a gap
    in the trace with no explanation. See excel-import trace investigation,
    2026-08-21.
    """
    agent = Agent(model, **kwargs)
    agent.instrument = True
    return agent


class ProviderAdapter(ABC):
    @abstractmethod
    def build(self, user_key) -> ResolvedModel | None: ...

    async def validate_key(self, key: str) -> None:
        pass  # default: no live validation needed (e.g. Ollama)


_REGISTRY: dict[str, ProviderAdapter] = {}


def register(name: str):
    def decorator(cls: type[ProviderAdapter]) -> type[ProviderAdapter]:
        _REGISTRY[name] = cls()
        return cls

    return decorator


def resolve_model(user_key=None, *, customer_id: str = "") -> ResolvedModel | None:
    """Return a PydanticAI model for the active provider key, or None if unavailable."""
    if user_key is None:
        return None

    if not user_key.provider:
        logger.warning("provider_key_no_provider", customer_id=customer_id)
        return None

    provider_name = user_key.provider.name

    if user_key.model_name is None:
        logger.warning(
            "provider_key_missing_model",
            customer_id=customer_id,
            provider=provider_name,
        )
        return None

    adapter = _REGISTRY.get(provider_name)
    if adapter is None:
        logger.warning(
            "provider_not_registered",
            customer_id=customer_id,
            provider=provider_name,
        )
        return None

    resolved = adapter.build(user_key)
    if resolved is None:
        logger.warning(
            "provider_adapter_build_failed",
            customer_id=customer_id,
            provider=provider_name,
            model=user_key.model_name,
        )
        return None

    logger.debug(
        "provider_resolved",
        customer_id=customer_id,
        provider=resolved.provider_name,
        model=resolved.model_name,
    )
    return resolved


def resolve_platform_funded_model() -> ResolvedModel | None:
    """GrantFlow-funded fallback for organizations with no configured provider
    key. A deliberate, scoped carve-out from the platform's BYOK-only/no-fallback
    policy — see budget-export-from-excel design.md Decision 5. Returns None if
    the platform's own key isn't configured, so callers can fail closed."""
    from app.core.config import settings

    if not settings.ANTHROPIC_API_KEY:
        return None
    return ResolvedModel(
        model=AnthropicModel(
            _PLATFORM_FUNDED_MODEL,
            provider=AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY),
        ),
        provider_name="anthropic",
        model_name=_PLATFORM_FUNDED_MODEL,
    )


async def get_resolved_model(
    valid_user: dict = Depends(get_validated_user),
) -> ResolvedModel | None:
    """FastAPI dependency — injects a resolved provider model into route handlers."""
    from app.crud.user_provider_key import get_active_key_for_customer
    from app.db.session import AsyncSessionLocal

    customer_id = resolve_customer_id(valid_user)

    async with AsyncSessionLocal() as db:
        user_key = await get_active_key_for_customer(customer_id, db)

    if user_key is None:
        logger.info("no_active_provider_key", customer_id=customer_id)
        return None

    return resolve_model(user_key, customer_id=customer_id)


# Import adapters to trigger their @register decorators
from app.services.adapters.anthropic import AnthropicAdapter  # noqa: E402, F401
from app.services.adapters.ollama import OllamaAdapter  # noqa: E402, F401
