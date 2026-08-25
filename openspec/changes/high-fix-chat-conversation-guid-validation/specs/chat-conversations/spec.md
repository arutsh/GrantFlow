## MODIFIED Requirements

### Requirement: Any-device retrieval
The chat service SHALL expose `GET /chat/conversations` and `GET /chat/conversations/{id}/messages`, scoped to the authenticated user, so history is reachable from any client.

#### Scenario: History readable from another client
- **WHEN** a user who chatted on one device requests their conversations from another authenticated client
- **THEN** the conversation list and its messages are returned

#### Scenario: Foreign conversation denied
- **WHEN** a user requests messages of a conversation belonging to another customer
- **THEN** the conversation is not returned

#### Scenario: Response is well-formed regardless of database backend
- **WHEN** `GET /chat/conversations` or `GET /chat/conversations/{id}/messages` is served against any supported database backend (Postgres in production, SQLite in dev/test)
- **THEN** each conversation/message `id` validates and serializes successfully, and the endpoint does not fail with a server error solely due to the backend's native identifier type
