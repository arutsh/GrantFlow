# chat-conversations

Server-side conversation state owned by the chat service — provider-neutral, per-user, accessible from any device.

## ADDED Requirements

### Requirement: Provider-neutral persistence
The chat service SHALL persist conversations (`id`, `customer_id`, `user_id`, `title`, `message_count`, `last_activity_at`, `created_at`) and messages (`role: user|assistant`, plain-text `content`, optional `tool_name`/`tool_params`/`tool_result`, `created_at`) in its own database. Message content SHALL NOT be stored in any LLM-provider wire format.

#### Scenario: Turn persisted
- **WHEN** a chat turn completes (with or without a tool execution)
- **THEN** the user message and assistant message are stored as role/content rows, with tool metadata populated on the assistant row when a tool ran

### Requirement: Any-device retrieval
The chat service SHALL expose `GET /chat/conversations` and `GET /chat/conversations/{id}/messages`, scoped to the authenticated user, so history is reachable from any client.

#### Scenario: History readable from another client
- **WHEN** a user who chatted on one device requests their conversations from another authenticated client
- **THEN** the conversation list and its messages are returned

#### Scenario: Foreign conversation denied
- **WHEN** a user requests messages of a conversation belonging to another customer
- **THEN** the conversation is not returned

### Requirement: Get-or-create conversation semantics
`POST /chat/stream` SHALL accept an optional `conversation_id`; an unknown or foreign id SHALL result in a new conversation rather than an error, and the effective id SHALL be returned via the `X-Conversation-Id` response header.

#### Scenario: Stale id degrades gracefully
- **WHEN** a client sends a `conversation_id` that does not exist for this customer
- **THEN** a new conversation is created and its id returned in `X-Conversation-Id`

### Requirement: Bounded history replay
When calling ai, the chat service SHALL replay at most the 50 most recent messages as role/content pairs.

#### Scenario: Long conversation capped
- **WHEN** a conversation exceeds 50 stored messages
- **THEN** the decide request contains only the most recent 50, oldest first
