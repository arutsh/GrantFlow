One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Budget-service span recording, catch-all handler, and business context (priority per issue #76)

- [ ] 1.1 Update `domain_error_handler` in `services/budget/app/core/error_handlers.py` to call `trace.get_current_span()` and set `record_exception(exc)`, `error.type`, `error.message` before returning the existing `JSONResponse`
- [ ] 1.2 Add a catch-all handler (e.g. `unhandled_exception_handler`) in the same file for exceptions not already caught by `DomainError`/`PermissionDenied`, recording the exception on the span and returning a generic `{"detail": "Internal server error"}` 500 without leaking exception internals
- [ ] 1.3 Register the catch-all handler in `services/budget/main.py` via `app.add_exception_handler(Exception, unhandled_exception_handler)`, alongside the existing `DomainError`/`PermissionDenied` registrations
- [ ] 1.4 In `create_budget_with_lines_service` (`services/budget/app/services/budget_services.py`), set `user_id` on the active span at the start of the function and `budget_id` once `new_budget` is created (including on the failure path, if the budget was created before a later step failed)
- [ ] 1.5 Add/update unit tests covering: `DomainError` records span attributes, unhandled exception is caught and recorded without leaking details to the client, `HTTPException` still behaves as before, and `create_budget_with_lines` sets `budget_id`/`user_id` span attributes on both success and partial-failure paths
- [ ] 1.6 Manually trigger a `DomainError` and an unhandled exception against local budget-service and confirm both show up correctly in Jaeger with exception events and the new attributes
- [ ] 1.7 Run budget-service tests and lint clean; PR merged (`Closes #76` if this ticket covers the full issue, otherwise reference the sub-ticket)

## 2. Users-service parity — depends on 1

- [ ] 2.1 Apply the same `domain_error_handler` span-recording change from 1.1 to `services/users/app/core/error_handlers.py`
- [ ] 2.2 Add the same catch-all handler pattern from 1.2–1.3 to `services/users/app/core/error_handlers.py` and `services/users/main.py`
- [ ] 2.3 Add/update unit tests mirroring 1.5 for users-service's `DomainError` and catch-all paths
- [ ] 2.4 Run users-service tests and lint clean; PR merged

## 3. AI-service parity — depends on 1

- [ ] 3.1 Create `services/ai/app/core/error_handlers.py` following the budget/users pattern (domain handler + catch-all), reusing `shared/exceptions/exceptions.py`'s `DomainError`/`PermissionDenied`
- [ ] 3.2 Register both handlers in `services/ai/main.py`, replacing/complementing the existing bare `except Exception:` at `services/ai/main.py:34` where applicable so unhandled exceptions are recorded on the span instead of silently swallowed
- [ ] 3.3 Add/update unit tests mirroring 1.5 for ai-service's `DomainError` and catch-all paths
- [ ] 3.4 Run ai-service tests and lint clean; PR merged

## 4. Nice-to-have: httpx and RabbitMQ/pika trace instrumentation — depends on 1

- [ ] 4.1 Add `opentelemetry-instrumentation-httpx` and `opentelemetry-instrumentation-pika` to `services/budget/requirements.txt` (and `services/users/requirements.txt`/`services/ai/requirements.txt` if those services make outbound httpx calls); verify no dependency conflicts with pinned `opentelemetry-*` versions
- [ ] 4.2 Call `HTTPXClientInstrumentor().instrument()` and `PikaInstrumentor().instrument()` in `shared/observability/init_observability()`, guarded by the existing `OTEL_SDK_DISABLED` check, alongside the existing `SQLAlchemyInstrumentor().instrument()` call
- [ ] 4.3 Manually verify in Jaeger that a budget-service call to `user_client.py` (httpx) and an event-consumer message handling (pika) each produce a child span under the parent request/consumer trace
- [ ] 4.4 Run affected services' tests and lint clean; PR merged
