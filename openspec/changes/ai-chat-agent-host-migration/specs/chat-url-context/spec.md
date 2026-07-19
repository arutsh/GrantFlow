# chat-url-context

Frontend behavior: the chat's domain context comes from the current URL, and creation results navigate instead of surfacing IDs in chat.

## ADDED Requirements

### Requirement: Context derived from the current route
The chat panel SHALL derive its context from the URL at send time — on `/budgets/:id`, `context_id` is that id; elsewhere it is null — and SHALL derive `page` from the first path segment. No budget/context state SHALL be stored in `AiChatContext`.

#### Scenario: On a budget detail page
- **WHEN** the user sends a message while on `/budgets/<uuid>`
- **THEN** the request carries `context_id = <uuid>` and `page = "budgets"`

#### Scenario: Outside a budget page
- **WHEN** the user sends a message while on `/dashboard`
- **THEN** the request carries `context_id = null` and `page = "dashboard"`

### Requirement: Navigate on creation, never surface IDs
When a turn completes with a new `budget_id`, the app SHALL navigate to `/budgets/<id>` via the router; the raw id SHALL NOT be rendered in the chat transcript. The new URL then supplies context for subsequent turns.

#### Scenario: Budget created via chat
- **WHEN** the `done` event carries a `budget_id`
- **THEN** the app navigates to that budget's page, and the follow-up message "add a line" targets it via the URL-derived `context_id`

### Requirement: Generic chat payload
The chat API client SHALL send `{message, conversation_id, context_id, page}` (domain-neutral names) to `POST /chat/stream` and track the conversation via the `X-Conversation-Id` response header.

#### Scenario: Payload field names
- **WHEN** any chat message is sent after the cutover
- **THEN** the request body uses `context_id`/`page`, not budget-specific field names
