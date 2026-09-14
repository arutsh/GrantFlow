## Why

`services/{budget,users,ai,chat}/app/services/privileged_access_audit.py` each open a second, fully separate synchronous `create_engine`/`sessionmaker` just to write one audit row per privileged request — because `get_validated_user` (`shared/security/dependencies.py`) and `log_privileged_access` (`shared/security/privileged_access.py`) are synchronous, even though all four services' primary sessions are already async (`create_async_engine`/`AsyncSessionLocal`). This is now four duplicated connection pools to four Postgres instances, hand-copied service to service (budget's copy was added in the async-sqlalchemy-migration group 2 diff, mirroring the same workaround users added in group 1, and ai/chat carried it from before either migration). A `/code-review` pass on the budget migration flagged this duplication; tracing it found the same pattern already repeated 4x with no shared abstraction.

## What Changes

- Make `PrivilegedAccessSink` and `log_privileged_access` async in `shared/security/privileged_access.py`; `make_privileged_access_sink` builds an `async def` sink over an async `session_factory`.
- **BREAKING**: `get_validated_user` in `shared/security/dependencies.py` becomes `async def` (awaits `log_privileged_access`). FastAPI resolves async dependencies transparently, so every existing `Depends(get_validated_user)` call site keeps working with no changes; there are no direct (non-`Depends`) callers in the codebase.
- Each of `services/{budget,users,ai,chat}/app/services/privileged_access_audit.py` drops its dedicated `create_engine`/`sessionmaker` and registers a sink built from that service's own existing `AsyncSessionLocal` (`app/db/session.py`).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `privileged-access-audit`: no requirement wording changes; delta spec reaffirms the existing requirements to record that this internals-only (sync→async transport) change was verified against them

## Impact

- `shared/security/privileged_access.py`, `shared/security/dependencies.py` (auth-critical, used by all 4 services)
- `services/budget/app/services/privileged_access_audit.py`
- `services/users/app/services/privileged_access_audit.py`
- `services/ai/app/services/privileged_access_audit.py`
- `services/chat/app/services/privileged_access_audit.py`
- Removes 4 duplicate synchronous connection pools; no schema or API change.
