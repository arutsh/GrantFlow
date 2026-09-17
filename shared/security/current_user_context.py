import uuid
from contextvars import ContextVar, Token

_current_user_id: ContextVar[uuid.UUID | None] = ContextVar("current_user_id", default=None)


def get_current_user_id() -> uuid.UUID | None:
    return _current_user_id.get()


def set_current_user_id(user_id: uuid.UUID | None) -> Token:
    return _current_user_id.set(user_id)


def reset_current_user_id(token: Token) -> None:
    _current_user_id.reset(token)
