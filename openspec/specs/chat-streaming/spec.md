# chat-streaming Specification

## Purpose
TBD - created by archiving change ai-chat-agent-host-migration. Update Purpose after archive.
## Requirements
### Requirement: SSE event protocol preserved
`POST /chat/stream` (body `{message, conversation_id?, context_id?, page?}`) SHALL emit the exact event protocol the frontend already parses: `thinking` first; optional `tool_call {tool_name}` and `action_result {tool_name, output}` around a tool execution; `text {delta}`; terminal `done {response, budget_id?}`; `error {message}` on failure; `unavailable` when no provider is configured. Responses SHALL carry `X-Conversation-Id`.

#### Scenario: Reply-only turn
- **WHEN** ai returns a reply decision
- **THEN** the stream is `thinking` → `text` → `done` with the reply text and no tool events

#### Scenario: Tool-executing turn
- **WHEN** ai returns a tool_call decision and dispatch succeeds
- **THEN** the stream includes `tool_call`, then `action_result`, then `done`; a `create_budget` success carries the new `budget_id` in `done`

### Requirement: Context guards precede dispatch
Tools targeting an existing resource (`add_budget_line`, `update_budget`, `get_budget_summary`) SHALL NOT be dispatched when `context_id` is null; the turn SHALL instead reply with guidance. Guard decisions live in code, never in the model.

#### Scenario: Targeted tool without context
- **WHEN** ai returns `add_budget_line` and the request has no `context_id`
- **THEN** no domain call is made and the reply explains there is no budget in progress

### Requirement: Tool parameters validated before dispatch
Tool-call params SHALL be validated against per-tool models before any domain call; validation failure yields a clarifying reply, not an error event.

#### Scenario: Invalid params
- **WHEN** ai returns a tool_call with a missing required parameter
- **THEN** no domain call is made and the turn replies asking for the missing value

### Requirement: Failures relayed politely
Domain-service error responses (4xx/5xx) SHALL be relayed as `action_result` + `text` in plain language; `AiUnavailableError` maps to the `unavailable` event; `AiRateLimitedError` maps to 429 with `Retry-After`. Unexpected exceptions map to the `error` event.

#### Scenario: Domain rejection relayed
- **WHEN** budget rejects a create with a 422
- **THEN** the stream completes with an `action_result`/`text` describing the rejection, not an `error` event

#### Scenario: No provider configured
- **WHEN** ai reports no provider for the customer
- **THEN** the stream emits `unavailable`

