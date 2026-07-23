from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatStreamRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    context_id: str | None = None
    page: str | None = None


class ParseBudgetStreamRequest(BaseModel):
    text: str


class ConversationOut(BaseModel):
    id: str
    title: str | None
    message_count: int
    last_activity_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    tool_name: str | None
    tool_params: dict | None
    tool_result: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
