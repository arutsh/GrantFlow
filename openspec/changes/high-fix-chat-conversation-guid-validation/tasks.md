Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Fix GUID/str mismatch in chat schemas

- [ ] 1.1 In `services/chat/app/schemas/chat.py`, change `ConversationOut.id` from `str` to `UUID` (import from `uuid`).
- [ ] 1.2 In the same file, change `MessageOut.id` from `str` to `UUID`.
- [ ] 1.3 Scan `services/chat/app/schemas/chat.py` for any other `str`-typed field backed by a GUID column (e.g. foreign keys like `conversation_id`) and fix the same way if found.
- [ ] 1.4 Add or adjust a regression test in `services/chat` that validates `ConversationOut`/`MessageOut` against a Postgres-backed session (not just the SQLite fixture), so this dialect-specific mismatch is caught in CI.
- [ ] 1.5 Run `services/chat` test suite and lint clean; PR merged (`Closes #<ticket>`).
