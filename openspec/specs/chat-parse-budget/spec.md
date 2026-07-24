# chat-parse-budget Specification

## Purpose
TBD - created by archiving change ai-chat-agent-host-migration. Update Purpose after archive.
## Requirements
### Requirement: Parse flow served by chat
The chat service SHALL expose `POST /chat/parse-budget/stream` which consumes ai's `/ai/parse-budget/stream` (via `AiClient.stream_parse_budget`), then creates the budget through budget's public `POST /budgets/with-lines` REST endpoint, re-emitting the frontend's existing SSE events: `progress`, `created {budget_id}`, `error`, `unavailable`.

#### Scenario: Successful parse and create
- **WHEN** ai's parse stream completes with a parsed budget payload
- **THEN** chat calls budget `/budgets/with-lines` with the user's JWT and emits `created` with the new budget id

#### Scenario: AI unavailable passthrough
- **WHEN** ai's parse stream reports unavailable
- **THEN** chat emits `unavailable` and makes no budget call

