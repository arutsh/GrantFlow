from datetime import datetime, timedelta, timezone
from uuid import uuid4

import factory

from app.models.conversation import Conversation
from app.models.message import Message

BASE_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


class ConversationFactory(factory.Factory):
    class Meta:
        model = Conversation

    id = factory.LazyFunction(lambda: str(uuid4()))
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid4()))
    title = factory.Faker("sentence", nb_words=2)
    message_count = 0
    last_activity_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class MessageFactory(factory.Factory):
    class Meta:
        model = Message

    id = factory.LazyFunction(lambda: str(uuid4()))
    conversation_id = factory.LazyFunction(lambda: str(uuid4()))
    role = "user"
    content = "placeholder"
    tool_name = None
    tool_params = None
    tool_result = None
    created_at = factory.Sequence(lambda n: BASE_TS + timedelta(seconds=n))
