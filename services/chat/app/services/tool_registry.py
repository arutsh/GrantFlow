"""Generic REST-dispatch registry mechanics shared by every domain, per
specs/chat-tool-registry.md.

`ToolRegistry` is the only surface the orchestrator depends on. A new domain
(e.g. reports) lives in its own `<domain>_tool_registry.py`, subclasses
`ToolRegistry`, sets the class attributes below, and adds one
`_call_<tool_name>` method per tool (decorated with `@relay_domain_errors`)
— see budget_tool_registry.py for the pattern. Nothing here needs
overriding, and nothing budget-specific belongs in the orchestrator: guard
behavior, resource-id injection, and the "resource created" signal are all
driven off these per-registry attributes instead of hardcoded tool names.
"""

import functools
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

import httpx

from app.core.logging import get_logger
from shared.ai_client.schemas import ToolDef

logger = get_logger(__name__)

_F = TypeVar("_F", bound=Callable[..., Awaitable["ToolResult"]])


@dataclass
class ToolResult:
    success: bool
    message: str
    created_resource_id: str | None = None


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def relay_domain_errors(verb: str) -> Callable[[_F], _F]:
    """Wrap a `_call_*` dispatch method so domain 4xx/5xx and unexpected
    failures come back as `ToolResult(success=False, ...)` instead of
    raising — the orchestrator relays these to the user in plain language
    rather than surfacing a raw `error` SSE event. Collapses the same
    try/except shape that every dispatch method would otherwise repeat.
    """

    def decorator(fn: _F) -> _F:
        @functools.wraps(fn)
        async def wrapper(self, *args, **kwargs):
            try:
                return await fn(self, *args, **kwargs)
            except httpx.HTTPStatusError as exc:
                logger.warning(f"{verb}_error", status=exc.response.status_code)
                return ToolResult(
                    success=False, message=f"Failed to {verb}: {exc.response.text[:200]}"
                )
            except Exception as exc:
                logger.error(f"{verb}_exception", error=str(exc))
                return ToolResult(success=False, message=f"Unexpected error during {verb}: {exc}")

        return wrapper  # type: ignore[return-value]

    return decorator


class ToolRegistry:
    page_toolsets: dict[str, list[ToolDef]] = {}

    # Tools that operate on an existing resource: blocked without context_id,
    # and have `resource_id_param` injected into their params at dispatch time.
    targeted_tools: set[str] = set()
    resource_id_param: str = "resource_id"
    no_active_resource_message: str = "There's nothing in progress in this conversation yet."

    # Tools whose successful ToolResult.created_resource_id should surface on
    # the turn (e.g. so the SSE `done` event can carry the new resource id).
    creating_tools: set[str] = set()

    def __init__(self, http: httpx.AsyncClient, base_url: str):
        self._http = http
        self._base = base_url.rstrip("/")

    def list_tools(self, page: str | None) -> list[ToolDef]:
        if page is None:
            return []
        return self.page_toolsets.get(page, [])

    def _url(self, path: str) -> str:
        return f"{self._base}/{path.lstrip('/')}"

    async def call_tool(self, name: str, params: dict, *, token: str) -> ToolResult:
        dispatcher = getattr(self, f"_call_{name}", None)
        if dispatcher is None:
            return ToolResult(success=False, message=f"Unknown tool: {name}")
        return await dispatcher(params, token)
