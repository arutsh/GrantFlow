# chat-tool-registry Specification

## Purpose
TBD - created by archiving change ai-chat-agent-host-migration. Update Purpose after archive.
## Requirements
### Requirement: MCP-shaped registry interface
The registry SHALL expose only `list_tools() -> list[ToolDef]` and `call_tool(name, params, *, token) -> ToolResult` to the orchestrator. Dispatch internals (REST helpers or MCP bridge) SHALL be swappable without changing the orchestrator, guards, SSE, or persistence.

#### Scenario: Implementation swap is invisible
- **WHEN** the hand-written dispatchers are replaced by the OpenAPI→MCP bridge
- **THEN** the chat service's endpoint/orchestrator test suite passes unchanged

### Requirement: Curated budget toolset
The budget registry SHALL offer exactly `create_budget` (budget_name required, external_funder_name required, duration_months optional), `add_budget_line` (category_name required, amount required, description optional), `update_budget`, and `get_budget_summary`, dispatching to budget's public REST API with the user's JWT.

#### Scenario: Create dispatch
- **WHEN** `call_tool("create_budget", {...})` runs with valid params
- **THEN** the registry POSTs to budget `/budgets/` with the user's Authorization header and returns the outcome including the new budget id

### Requirement: Model never supplies resource IDs
Tool schemas sent to ai SHALL NOT contain resource-id parameters; `budget_id` SHALL be injected from the request's `context_id` at dispatch time.

#### Scenario: budget_id injected
- **WHEN** ai returns `add_budget_line` params without any budget id
- **THEN** the dispatcher targets the budget identified by `context_id`

### Requirement: Page-scoped toolsets
The registry SHALL select which domain toolset accompanies a decide request based on the request's `page` (budgets → budget tools), so new domains add toolsets without touching existing ones.

#### Scenario: Budget page toolset
- **WHEN** a `/chat/stream` request arrives with `page: "budgets"`
- **THEN** the decide request carries exactly the budget toolset

### Requirement: OpenAPI bridge equivalence
When registry internals move to the in-process FastMCP `from_openapi` bridge, generated tool schemas SHALL match the curated ones field-for-field (renames applied, hidden fields absent, `budget_id` stripped), and chat SHALL boot with a cached spec when budget's live spec is unreachable.

#### Scenario: Generated schema parity
- **WHEN** the bridge builds tools from budget's OpenAPI spec
- **THEN** `list_tools()` output is field-for-field identical to the curated definitions

#### Scenario: Spec fetch fails at boot
- **WHEN** budget's `/openapi.json` is unreachable at chat startup
- **THEN** chat starts using the cached spec

