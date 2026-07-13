import factory
from uuid import uuid4
from app.models.chat_session import AIChatSession
from app.models.chat_message import AIChatMessage
from datetime import datetime, timezone, timedelta

BASE_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


class AIChatSessionFactory(factory.Factory):
    class Meta:
        model = AIChatSession

    id = factory.LazyFunction(lambda: str(uuid4()))
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid4()))
    title = factory.Faker("sentence", nb_words=2)
    message_count = 0
    last_activity_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class AIChatMessageFactory(factory.Factory):

    class Meta:
        model = AIChatMessage

    id = factory.LazyFunction(lambda: str(uuid4()))
    session_id = factory.LazyFunction(lambda: str(uuid4()))
    role = "user"
    content = "placeholder"
    tool_name = None
    tool_call_id = None
    created_at = factory.Sequence(lambda n: BASE_TS + timedelta(seconds=n))
