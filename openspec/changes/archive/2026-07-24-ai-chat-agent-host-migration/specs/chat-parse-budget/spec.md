# chat-parse-budget

The paste-text-to-budget flow, served by the chat service so budget carries no AI knowledge.

## ADDED Requirements

### Requirement: Parse flow served by chat
The chat service SHALL expose `POST /chat/parse-budget/stream` which consumes ai's `/ai/parse-budget/stream` (via `AiClient.stream_parse_budget`), then creates the budget through budget's public `POST /budgets/with-lines` REST endpoint, re-emitting the frontend's existing SSE events: `progress`, `created {budget_id}`, `error`, `unavailable`.

#### Scenario: Successful parse and create
- **WHEN** ai's parse stream completes with a parsed budget payload
- **THEN** chat calls budget `/budgets/with-lines` with the user's JWT and emits `created` with the new budget id

#### Scenario: AI unavailable passthrough
- **WHEN** ai's parse stream reports unavailable
- **THEN** chat emits `unavailable` and makes no budget call

## REMOVED Requirements

### Requirement: Budget-hosted parse proxy
**Reason**: Budget must have zero AI references (polyglot-safe domain service).
**Migration**: Delete `POST /budgets/ai/stream` and `ai_service_url` from budget config after the frontend points `streamAiCreateBudget` at `/chat/parse-budget/stream` (ticket #96). The event protocol to the frontend is unchanged.
