from unittest.mock import MagicMock

import factory

from app.services.provider import ResolvedModel


class ResolvedModelFactory(factory.Factory):
    """Real ResolvedModel dataclass with a mocked inner PydanticAI model.

    Route tests patch build_agent, so nothing ever calls into `model`.
    """

    class Meta:
        model = ResolvedModel

    model = factory.LazyFunction(MagicMock)
    provider_name = "anthropic"
    model_name = "claude-test"
