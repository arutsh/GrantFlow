## Context

`shared/db/type_decorators.py`'s `GUID` TypeDecorator was fixed today (commit `7e12519`) so `process_result_value` returns the driver's native value instead of forcing `str(value)`. That fix was correct and necessary (it resolved a batched-insert/JWT-encoding bug), but it changed what Postgres hands back for every GUID column: previously always `str`, now `uuid.UUID` (SQLite already returned `UUID` via its own branch, unchanged). `services/chat/app/schemas/chat.py` is the one place that assumed the old, incorrect `str` behavior — `ConversationOut.id: str` and `MessageOut.id: str` — and `chat_routes.py` validates ORM rows straight into these schemas, so Postgres-backed prod now 500s while SQLite-backed dev/tests stayed green.

## Goals / Non-Goals

**Goals:**
- Restore `GET /api/v1/chat/conversations` (and any equivalent message-listing path) to working on Postgres.
- Add coverage that would catch this class of dialect-specific mismatch (Postgres-only) in CI, not just SQLite.

**Non-Goals:**
- Auditing every schema in the codebase for the same pattern — already done as part of diagnosis; only `services/chat/app/schemas/chat.py` had it (users/budget schemas already type these fields as `UUID`).
- Any change to the `GUID` decorator itself — it's correct as of today's fix; this change only fixes the one caller that relied on its old, wrong behavior.

## Decisions

**Type the fields as `UUID`, not as `str` with a validator.** Change `ConversationOut.id` and `MessageOut.id` from `str` to `UUID` (from `uuid`), matching the existing convention in `services/users` and `services/budget` schemas. Considered adding a `field_validator` to coerce `UUID` → `str` instead, but that would just be re-introducing the old, incorrect assumption in a different form — the DB genuinely returns a `UUID`, and Pydantic serializes `UUID` to the same JSON string on the wire either way, so there's no external contract reason to force `str` internally.

## Risks / Trade-offs

- **[Risk]** A test running only against SQLite (as most of this suite does) won't catch a Postgres-only mismatch like this again. → **Mitigation**: add/adjust a regression test that validates these schemas against a real Postgres-backed session (test infra for this already exists per the shared aiosqlite/Postgres fixture pattern used elsewhere in the repo).
- **[Trade-off]** None beyond the type change itself — no wire-format change, no migration needed.
