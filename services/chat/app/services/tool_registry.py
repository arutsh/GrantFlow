"""Registry base shared by every domain; see budget_tool_registry.py for the subclass pattern."""

from dataclasses import dataclass

import httpx

from shared.ai_client.schemas import ToolDef


@dataclass
class ToolResult:
    success: bool
    message: str
    created_resource_id: str | None = None


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

    async def call_tool(self, name: str, params: dict, *, token: str) -> ToolResult:
        raise NotImplementedError
