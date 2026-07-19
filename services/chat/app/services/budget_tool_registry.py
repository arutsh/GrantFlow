"""Curated budget toolset — hand-written REST dispatch (pre-#97 bridge).

Tool schemas exposed to ai never contain a resource id — `budget_id` is
expected to already be present in `params` by the time `call_tool` runs
(the orchestrator injects it from the request's `context_id` for targeted
tools before calling here).
"""

from app.services.tool_registry import ToolRegistry, ToolResult, auth_headers, relay_domain_errors
from shared.ai_client.schemas import ToolDef

_TOOL_DEFS = [
    ToolDef(
        name="create_budget",
        description="Create a new, empty budget.",
        parameters={
            "type": "object",
            "properties": {
                "budget_name": {"type": "string"},
                "external_funder_name": {"type": "string"},
                "duration_months": {"type": "integer"},
            },
            "required": ["budget_name", "external_funder_name"],
        },
    ),
    ToolDef(
        name="add_budget_line",
        description="Add a line item to the budget currently in view.",
        parameters={
            "type": "object",
            "properties": {
                "category_name": {"type": "string"},
                "amount": {"type": "number"},
                "description": {"type": "string"},
            },
            "required": ["category_name", "amount"],
        },
    ),
    ToolDef(
        name="update_budget",
        description="Update fields on the budget currently in view.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "external_funder_name": {"type": "string"},
                "duration_months": {"type": "integer"},
                "local_currency": {"type": "string"},
            },
            "required": [],
        },
    ),
    ToolDef(
        name="get_budget_summary",
        description="Fetch a read-only summary of the budget currently in view.",
        parameters={"type": "object", "properties": {}, "required": []},
    ),
]


class BudgetToolRegistry(ToolRegistry):
    page_toolsets = {"budgets": _TOOL_DEFS}
    targeted_tools = {"add_budget_line", "update_budget", "get_budget_summary"}
    resource_id_param = "budget_id"
    creating_tools = {"create_budget"}
    no_active_resource_message = "There's no budget in progress in this conversation yet."

    @relay_domain_errors("create budget")
    async def _call_create_budget(self, params: dict, token: str) -> ToolResult:
        payload: dict = {
            "name": params["budget_name"],
            "external_funder_name": params["external_funder_name"],
        }
        if params.get("duration_months") is not None:
            payload["duration_months"] = params["duration_months"]
        resp = await self._http.post(
            self._url("/budgets/"), json=payload, headers=auth_headers(token)
        )
        resp.raise_for_status()
        data = resp.json()
        budget_id = data.get("id")
        # The id is surfaced structurally via ToolResult.created_resource_id (and
        # the SSE `done.budget_id` field) — never embedded in this prose, per
        # specs/chat-url-context.md: "the raw id SHALL NOT be rendered in the
        # chat transcript."
        return ToolResult(
            success=True,
            message=f"Budget '{payload['name']}' created successfully.",
            created_resource_id=budget_id,
        )

    @relay_domain_errors("add budget line")
    async def _call_add_budget_line(self, params: dict, token: str) -> ToolResult:
        description = params.get("description") or params["category_name"]
        payload = {
            "budget_id": params["budget_id"],
            "description": description,
            "amount": params["amount"],
            "category_name": params["category_name"],
        }
        resp = await self._http.post(
            self._url("/budget-lines/"), json=payload, headers=auth_headers(token)
        )
        resp.raise_for_status()
        data = resp.json()
        line_id = data.get("id", "unknown")
        return ToolResult(
            success=True,
            message=(
                f"Line '{description}' ({params['amount']}) added to budget "
                f"(line id: {line_id})."
            ),
        )

    @relay_domain_errors("update budget")
    async def _call_update_budget(self, params: dict, token: str) -> ToolResult:
        budget_id = params["budget_id"]
        payload = {k: v for k, v in params.items() if k != "budget_id" and v is not None}
        resp = await self._http.patch(
            self._url(f"/budgets/{budget_id}"), json=payload, headers=auth_headers(token)
        )
        resp.raise_for_status()
        return ToolResult(success=True, message=f"Budget {budget_id} updated successfully.")

    @relay_domain_errors("get budget summary")
    async def _call_get_budget_summary(self, params: dict, token: str) -> ToolResult:
        budget_id = params["budget_id"]
        resp = await self._http.get(self._url(f"/budgets/{budget_id}"), headers=auth_headers(token))
        resp.raise_for_status()
        data = resp.json()
        name = data.get("name", "unknown")
        lines = data.get("lines", [])
        total = sum(ln.get("amount", 0) for ln in lines)
        preview = ", ".join(
            f"{ln.get('description', '?')} ({ln.get('amount', 0)})" for ln in lines[:5]
        )
        suffix = f" … and {len(lines) - 5} more" if len(lines) > 5 else ""
        return ToolResult(
            success=True,
            message=f"Budget '{name}': {len(lines)} lines, total {total}. {preview}{suffix}",
        )
