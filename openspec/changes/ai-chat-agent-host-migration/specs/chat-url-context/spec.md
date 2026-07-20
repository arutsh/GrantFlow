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

### Requirement: History survives a page reload
On an authenticated app load, the frontend SHALL fetch the user's most recent conversation (`GET /chat/conversations`) and its messages (`GET /chat/conversations/{id}/messages`), and rehydrate both the visible transcript and `conversationId` from it — chat history is not lost to a browser refresh, since the chat service (not browser state) is the source of truth.

#### Scenario: Reload with prior history
- **WHEN** an authenticated user reloads the page after a previous chat exchange
- **THEN** the transcript and `conversationId` are restored from the chat service, not reset to the welcome message

#### Scenario: No prior conversation or fetch failure
- **WHEN** the user has no prior conversation, or the history fetch fails
- **THEN** the panel falls back to the default welcome message with no error surfaced

### Requirement: Budget view reflects chat-driven mutations without a manual reload
When a tool call executes while a budget is the active `context_id`, the frontend SHALL invalidate that budget's query cache so the currently-viewed budget page reflects the change without requiring a manual page reload.

#### Scenario: Line added via chat while viewing the budget
- **WHEN** `add_budget_line` (or another targeted tool) completes while `/budgets/:id` is open for that same id
- **THEN** the budget detail view refetches and shows the new line without the user reloading
