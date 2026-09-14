Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Async privileged-access audit hook (shared + all 4 services)

Single group, not split further: `shared/security/privileged_access.py` and `shared/security/dependencies.py` are imported by all 4 services, and a sink registered as a plain sync callable cannot be awaited — if the shared code goes async while even one service still registers a sync sink, every privileged (impersonated) request in that service crashes. Shared code and all 4 services' sinks must land and deploy together; there is no smaller shippable slice.

- [ ] 1.1 In `shared/security/privileged_access.py`: change `PrivilegedAccessSink` to an async `Callable`; make the sink built by `make_privileged_access_sink` an `async def` that awaits `db.commit()`/`db.add()` against an async `session_factory`; make `log_privileged_access` `async def` and `await _sink(payload, request)`.
- [ ] 1.2 In `shared/security/dependencies.py`: change `get_validated_user` to `async def` and `await log_privileged_access(payload, request)`.
- [ ] 1.3 In `services/budget/app/services/privileged_access_audit.py`: remove the dedicated `create_engine`/`sessionmaker`; import `AsyncSessionLocal` from `app.db.session` and pass it to `make_privileged_access_sink`.
- [ ] 1.4 In `services/users/app/services/privileged_access_audit.py`: same change as 1.3, using users' own `AsyncSessionLocal`.
- [ ] 1.5 In `services/ai/app/services/privileged_access_audit.py`: same change as 1.3, using ai's own `AsyncSessionLocal`.
- [ ] 1.6 In `services/chat/app/services/privileged_access_audit.py`: same change as 1.3, using chat's own `AsyncSessionLocal`.
- [ ] 1.7 Audit the rest of `get_validated_user`'s body (JWT decode, claims lookup) for any blocking synchronous I/O now that it runs on the event loop instead of FastAPI's threadpool; confirm none exists or fix it.
- [ ] 1.8 Add/update a test exercising the impersonation-logging path (superuser impersonating a customer, read and write requests) for at least one service end-to-end against a real async session, confirming a `privileged_access_logs` row is written and the existing fail-open/fail-closed behavior (`log_privileged_access`'s `_SAFE_METHODS` handling) is unchanged.
- [ ] 1.9 Run the full test suite and lint for all 4 services (budget, users, ai, chat) clean; PR merged.
