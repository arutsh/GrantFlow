# ai-decide

ai's stateless decision endpoint: the only way domain-facing services obtain LLM reasoning. Provider knowledge (BYOK, rate limits) stays here; domain knowledge never does.

## ADDED Requirements

### Requirement: Stateless decision endpoint
The ai service SHALL expose `POST /ai/decide` accepting `{message, conversation_history: [{role, content}], available_tools: [{name, description, parameters}], domain_context: object|null}` and SHALL return exactly one decision: `{"decision": {"type": "tool_call", "name", "params"}}` or `{"decision": {"type": "reply", "text"}}`. The endpoint SHALL NOT persist any conversation state.

#### Scenario: Tool call when all required parameters are known
- **WHEN** the message plus history contain every required parameter of an available tool matching the user's intent
- **THEN** the response is a `tool_call` decision naming that tool with the extracted params

#### Scenario: Reply when information is missing
- **WHEN** the user's intent matches a tool but required parameters are absent from the conversation
- **THEN** the response is a `reply` decision asking for the missing information, and no tool_call is returned

### Requirement: No domain knowledge or outbound domain calls
The ai service SHALL make decisions using only the tools supplied in the request. It SHALL NOT hold configuration for, or make network calls to, any domain service (no `BUDGET_SERVICE_URL` or equivalent).

#### Scenario: Decision uses only supplied tools
- **WHEN** `/ai/decide` is called with an arbitrary toolset
- **THEN** any tool_call decision names one of the supplied tools, and the ai service performs no outbound HTTP call to execute it

### Requirement: Provider resolution and key isolation
The endpoint SHALL resolve the caller's customer BYOK provider per request with a per-request agent (keys never shared across requests). When no provider is configured it SHALL return 503 with `{"detail": {"code": "no_provider"}}`.

#### Scenario: No provider key configured
- **WHEN** the authenticated customer has no active provider key
- **THEN** the endpoint returns 503 with code `no_provider`

### Requirement: Rate limiting
The endpoint SHALL enforce the existing per-customer rate limit and return 429 with a `Retry-After` header when exceeded.

#### Scenario: Over the hourly limit
- **WHEN** a customer exceeds `AI_RATE_LIMIT_PER_HOUR`
- **THEN** the endpoint returns 429 with `Retry-After`

## REMOVED Requirements

### Requirement: Legacy chat stream endpoint and session storage
**Reason**: ai must be stateless and domain-agnostic; orchestration and conversation state move to the chat service.
**Migration**: `/ai/chat/stream`, the intent-extraction agent, orchestrator, budget REST helpers, and `ai_chat_sessions`/`ai_chat_messages` tables are deleted (ticket #95) after the frontend cutover (#93) and users-proxy retirement (#94). Historical chat data is intentionally not migrated.
