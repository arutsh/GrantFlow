Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Fix GUID/str mismatch in chat schemas

- [x] 1.1 In `services/chat/app/schemas/chat.py`, change `ConversationOut.id` from `str` to `UUID` (import from `uuid`).
- [x] 1.2 In the same file, change `MessageOut.id` from `str` to `UUID`.
- [x] 1.3 Scan `services/chat/app/schemas/chat.py` for any other `str`-typed field backed by a GUID column (e.g. foreign keys like `conversation_id`) and fix the same way if found.
- [x] 1.4 Add a regression test in `services/chat` that validates `ConversationOut`/`MessageOut` against real ORM rows via the existing SQLite async fixture pattern (`test_conversation_crud.py`'s `db` fixture) — verified this reproduces the exact `uuid.UUID`-vs-`str` mismatch without needing new Postgres CI infra (see design.md risk note).
- [x] 1.5 Run `services/chat` test suite and lint clean; PR merged (`Closes #248`).
