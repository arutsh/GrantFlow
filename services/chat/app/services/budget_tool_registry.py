"""Curated budget toolset — dispatched via the in-process OpenAPI -> MCP
bridge (mcp_bridge.py) rather than hand-written REST calls, per the
"OpenAPI bridge equivalence" requirement in specs/chat-tool-registry.md
(ticket #97). Message-building/error-relay behavior for each tool is
preserved exactly from the pre-bridge hand-written dispatchers — this is an
internal swap, not a UX change.
"""

import httpx

from app.services import mcp_bridge
from app.services.tool_registry import ToolRegistry, ToolResult
from shared.ai_client.schemas import ToolDef


class BudgetToolRegistry(ToolRegistry):
    targeted_tools = {"add_budget_line", "update_budget", "get_budget_summary"}
    resource_id_param = "budget_id"
    creating_tools = {"create_budget"}
    no_active_resource_message = "There's no budget in progress in this conversation yet."

    def __init__(self, http: httpx.AsyncClient, base_url: str):
        super().__init__(http, base_url)
        self._service_root = mcp_bridge.service_root(base_url)
        self._spec: dict | None = None

    async def initialize(self) -> None:
        """One-time startup call (see main.py's lifespan): fetch — or fall
        back to the cached copy of — budget's OpenAPI spec, and cache the
        model-facing tool schemas into page_toolsets. call_tool() never
        touches this again; it builds its own short-lived bridge per call.
        """
        self._spec = await mcp_bridge.load_spec(self._service_root, self._http)

        schema_client = httpx.AsyncClient(base_url=self._service_root)
        try:
            schema_mcp = mcp_bridge.build_schema_bridge(self._spec, schema_client)
            tools = await schema_mcp.list_tools()
        finally:
            await schema_client.aclose()

        self.page_toolsets = {
            "budgets": [
                ToolDef(name=t.name, description=t.description, parameters=t.parameters)
                for t in tools
            ]
        }

    async def call_tool(self, name: str, params: dict, *, token: str) -> ToolResult:
        assert self._spec is not None, "BudgetToolRegistry.initialize() was not awaited"

        builder = _RESULT_BUILDERS.get(name)
        if builder is None:
            return ToolResult(success=False, message=f"Unknown tool: {name}")

        dispatch_params = dict(params)
        budget_id = dispatch_params.pop(self.resource_id_param, None)

        # Reuse self._http's transport (not just its default headers) so a
        # test's MockTransport — or, in prod, the shared connection pool —
        # carries over; only the per-turn bearer token actually needs to
        # vary per call. httpx has no public "clone with different headers"
        # API, so this reaches into the one private attribute that matters.
        client = httpx.AsyncClient(
            base_url=self._service_root,
            transport=self._http._transport,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            mcp = mcp_bridge.build_dispatch_bridge(self._spec, client, budget_id=budget_id)
            result = await mcp.call_tool(name, dispatch_params)
            # The OpenAPI bridge never raises on a 2xx with an unparseable
            # body (e.g. a proxy returning an HTML error page with status
            # 200) — it returns structured_content=None instead (see
            # fastmcp's components.py: `except json.JSONDecodeError: return
            # ToolResult(content=response.text)`). Must be caught explicitly
            # or this silently reports success, the exact bug #93's code
            # review fixed in the old hand-written dispatchers.
            if result.structured_content is None:
                return ToolResult(
                    success=False,
                    message=f"Failed to {_VERBS[name]}: received an unreadable response",
                )
            return builder(dispatch_params, result.structured_content)
        except Exception as exc:
            # FastMCP wraps every HTTP failure (4xx/5xx, timeouts, connect
            # errors) into its own ValueError before it ever reaches here —
            # never a raw httpx.HTTPStatusError — so one generic handler
            # covers all of them; str(exc) already carries the useful detail.
            return ToolResult(success=False, message=f"Failed to {_VERBS[name]}: {exc}")
        finally:
            await client.aclose()


def _build_create_budget_result(params: dict, data: dict) -> ToolResult:
    budget_id = data.get("id")
    # The id is surfaced structurally via ToolResult.created_resource_id (and
    # the SSE `done.budget_id` field) — never embedded in this prose, per
    # specs/chat-url-context.md: "the raw id SHALL NOT be rendered in the
    # chat transcript."
    return ToolResult(
        success=True,
        message=f"Budget '{params['budget_name']}' created successfully.",
        created_resource_id=budget_id,
    )


def _build_add_budget_line_result(params: dict, data: dict) -> ToolResult:
    # add_budget_line isn't a creating_tool, so its id is never surfaced
    # structurally or in the message (same "raw id SHALL NOT be rendered"
    # rule create_budget follows). `data` is intentionally unused — a
    # malformed/unparseable 2xx body never reaches this builder at all,
    # call_tool() checks result.structured_content and reports failure
    # before dispatching to any builder.
    return ToolResult(
        success=True,
        message=f"Line '{params['description']}' ({params['amount']}) added to budget.",
    )


def _build_update_budget_result(params: dict, data: dict) -> ToolResult:
    # Same "raw id SHALL NOT be rendered" rule — the budget_id here is the
    # already-in-view context id, not a newly created one, but the rule
    # applies regardless.
    return ToolResult(success=True, message="Budget updated successfully.")


def _build_get_budget_summary_result(params: dict, data: dict) -> ToolResult:
    name = data.get("name", "unknown")
    lines = data.get("lines", [])
    total = sum(ln.get("amount", 0) for ln in lines)
    preview = ", ".join(f"{ln.get('description', '?')} ({ln.get('amount', 0)})" for ln in lines[:5])
    suffix = f" … and {len(lines) - 5} more" if len(lines) > 5 else ""
    return ToolResult(
        success=True,
        message=f"Budget '{name}': {len(lines)} lines, total {total}. {preview}{suffix}",
    )


_RESULT_BUILDERS = {
    "create_budget": _build_create_budget_result,
    "add_budget_line": _build_add_budget_line_result,
    "update_budget": _build_update_budget_result,
    "get_budget_summary": _build_get_budget_summary_result,
}

_VERBS = {
    "create_budget": "create budget",
    "add_budget_line": "add budget line",
    "update_budget": "update budget",
    "get_budget_summary": "get budget summary",
}
