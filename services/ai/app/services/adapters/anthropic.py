import anthropic as anthropic_sdk
from fastapi import HTTPException
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.core.logging import get_logger
from app.services.provider import ProviderAdapter, ResolvedModel, register

logger = get_logger(__name__)


@register("anthropic")
class AnthropicAdapter(ProviderAdapter):
    # Cheapest model used only for key validation pings — not the user's chosen model
    _VALIDATION_MODEL = "claude-haiku-4-5-20251001"

    def build(self, user_key) -> ResolvedModel | None:
        from app.core.config import settings
        from app.utils.encryption import decrypt

        if not user_key.encrypted_key:
            return None
        api_key = decrypt(user_key.encrypted_key, settings.ENCRYPTION_KEY)
        return ResolvedModel(
            model=AnthropicModel(
                user_key.model_name,
                provider=AnthropicProvider(api_key=api_key),
            ),
            provider_name="anthropic",
            model_name=user_key.model_name,
        )

    async def validate_key(self, key: str) -> None:
        try:
            client = anthropic_sdk.AsyncAnthropic(api_key=key)
            await client.messages.create(
                model=self._VALIDATION_MODEL,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
        except anthropic_sdk.AuthenticationError:
            raise HTTPException(status_code=422, detail="Anthropic key is invalid or inactive")
        except anthropic_sdk.APIStatusError as e:
            # A response from Anthropic that isn't an auth failure (e.g. 400
            # Bad Request) means the key reached them fine — the request
            # itself was rejected. Log the real reason instead of masking it
            # as a generic connectivity failure.
            logger.error(
                "anthropic_key_validation_rejected",
                status_code=e.status_code,
                error_message=str(e),
            )
            raise HTTPException(status_code=502, detail="Could not reach Anthropic to validate key")
        except Exception as e:
            logger.error(
                "anthropic_key_validation_failed", error_type=type(e).__name__, error=str(e)
            )
            raise HTTPException(status_code=502, detail="Could not reach Anthropic to validate key")
