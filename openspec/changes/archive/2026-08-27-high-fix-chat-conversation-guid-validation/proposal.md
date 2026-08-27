## Why

`GET /api/v1/chat/conversations` is 500ing in prod on Postgres. Today's GUID-decoder fix (`shared/db/type_decorators.py`, commit `7e12519`) changed `process_result_value` from `return str(value)` to `return value` — Postgres's `UUID(as_uuid=True)` now hands back a `uuid.UUID` object for GUID columns instead of a `str`. `services/chat/app/schemas/chat.py` declares `ConversationOut.id: str` and `MessageOut.id: str`, and `chat_routes.py:206` validates ORM rows straight into that schema, so Pydantic v2 now rejects the `UUID` against the `str`-typed field. SQLite (dev/test) already went through a `uuid.UUID(value)` branch, so this was invisible locally and only broke in prod.

## What Changes

- `ConversationOut.id` and `MessageOut.id` change type from `str` to `UUID` in `services/chat/app/schemas/chat.py`, matching how equivalent GUID-backed id fields are already typed in `services/users` and `services/budget` schemas.
- Add/adjust a regression test that exercises these schemas against a Postgres-backed session (not just SQLite), so this class of dialect-specific mismatch is caught in CI going forward.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `chat-conversations`: adds an explicit scenario to "Any-device retrieval" that conversation/message ids must validate and serialize regardless of database backend — codifying the guarantee this bug violated, not a new behavior once fixed

## Impact

- **services/chat**: `app/schemas/chat.py` (`ConversationOut.id`, `MessageOut.id`), test suite (new/adjusted Postgres-backed regression test).
- No API contract change (the wire format for `id` is unaffected — Pydantic serializes both `str` and `UUID` the same way in JSON); this only fixes server-side validation blowing up before serialization.
