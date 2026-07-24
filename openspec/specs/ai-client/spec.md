# ai-client Specification

## Purpose
TBD - created by archiving change ai-chat-agent-host-migration. Update Purpose after archive.
## Requirements
### Requirement: Typed decision API
`AiClient.decide(message, history, tools, domain_context, user_token)` SHALL POST to `{base_url}/ai/decide` with the user's JWT and SHALL return a typed `AiDecision` (`ToolCall {name, params}` or `Reply {text}`).

#### Scenario: Tool-call response parsed
- **WHEN** ai responds with a `tool_call` decision
- **THEN** `decide` returns a `ToolCall` carrying the name and params unmodified

#### Scenario: Reply response parsed
- **WHEN** ai responds with a `reply` decision
- **THEN** `decide` returns a `Reply` with the text

### Requirement: Error taxonomy
The client SHALL raise `AiUnavailableError` on 503/no-provider, `AiRateLimitedError` (carrying `retry_after`) on 429, and `AiClientError` for other failures — never leaking raw httpx exceptions to callers.

#### Scenario: Provider unavailable
- **WHEN** ai returns 503 with code `no_provider`
- **THEN** `decide` raises `AiUnavailableError`

#### Scenario: Rate limited
- **WHEN** ai returns 429 with `Retry-After: 120`
- **THEN** `decide` raises `AiRateLimitedError` with `retry_after == 120`

### Requirement: Retry semantics
The client SHALL retry connection errors up to its configured limit and SHALL NOT retry read timeouts or HTTP error responses (LLM calls are not cheap to repeat).

#### Scenario: Connect error retried
- **WHEN** the first connection attempt fails with a connect error and the second succeeds
- **THEN** `decide` returns the successful result

#### Scenario: Read timeout not retried
- **WHEN** the request times out while awaiting the response body
- **THEN** `decide` raises without re-sending the request

