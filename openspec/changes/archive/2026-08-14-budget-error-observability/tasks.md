One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Budget-service span recording, catch-all handler, and business context (priority per issue #76)

- [x] 1.1 Update `domain_error_handler` in `services/budget/app/core/error_handlers.py` to call `trace.get_current_span()` and set `record_exception(exc)`, `error.type`, `error.message` before returning the existing `JSONResponse`
- [x] 1.2 Add a catch-all handler (e.g. `unhandled_exception_handler`) in the same file for exceptions not already caught by `DomainError`/`PermissionDenied`, recording the exception on the span and returning a generic `{"detail": "Internal server error"}` 500 without leaking exception internals
- [x] 1.3 Register the catch-all handler in `services/budget/main.py` via `app.add_exception_handler(Exception, unhandled_exception_handler)`, alongside the existing `DomainError`/`PermissionDenied` registrations
- [x] 1.4 In `create_budget_with_lines_service` (`services/budget/app/services/budget_services.py`), set `user_id` on the active span at the start of the function and `budget_id` once `new_budget` is created (including on the failure path, if the budget was created before a later step failed) — **partially superseded by task 5.2**: the `user_id` line is being replaced by centralized user_id-on-every-request; `budget_id` portion stands as-is
- [x] 1.5 Add/update unit tests covering: `DomainError` records span attributes, unhandled exception is caught and recorded without leaking details to the client, `HTTPException` still behaves as before, and `create_budget_with_lines` sets `budget_id`/`user_id` span attributes on both success and partial-failure paths
- [x] 1.6 Manually trigger a `DomainError` and an unhandled exception against local budget-service and confirm both show up correctly in Jaeger with exception events and the new attributes
- [x] 1.7 Run budget-service tests and lint clean; PR merged (`Closes #76` if this ticket covers the full issue, otherwise reference the sub-ticket) — tests/lint clean, PR not yet opened

## 2. Users-service parity — depends on 1

- [x] 2.1 Apply the same `domain_error_handler` span-recording change from 1.1 to `services/users/app/core/error_handlers.py`
- [x] 2.2 Add the same catch-all handler pattern from 1.2–1.3 to `services/users/app/core/error_handlers.py` and `services/users/main.py`
- [x] 2.3 Add/update unit tests mirroring 1.5 for users-service's `DomainError` and catch-all paths
- [x] 2.4 Run users-service tests and lint clean; PR merged — tests/lint clean, PR not yet opened

## 3. AI-service parity — depends on 1

- [x] 3.1 Create `services/ai/app/core/error_handlers.py` following the budget/users pattern (domain handler + catch-all), reusing `shared/exceptions/exceptions.py`'s `DomainError`/`PermissionDenied`
- [x] 3.2 Register both handlers in `services/ai/main.py`, replacing/complementing the existing bare `except Exception:` at `services/ai/main.py:34` where applicable so unhandled exceptions are recorded on the span instead of silently swallowed — the line-34 `except Exception:` is only a debugpy import guard (unrelated to request handling), left as-is; the catch-all handler now covers unhandled exceptions in the request path
- [x] 3.3 Add/update unit tests mirroring 1.5 for ai-service's `DomainError` and catch-all paths
- [x] 3.4 Run ai-service tests and lint clean; PR merged — tests/lint clean, PR not yet opened

## 4. Nice-to-have: httpx and RabbitMQ/pika trace instrumentation — depends on 1

- [x] 4.1 Add `opentelemetry-instrumentation-httpx` and `opentelemetry-instrumentation-pika` to `services/budget/requirements.txt` (and `services/users/requirements.txt`/`services/ai/requirements.txt` if those services make outbound httpx calls); verify no dependency conflicts with pinned `opentelemetry-*` versions — httpx instrumentor added to all 3 (all use httpx); pika instrumentor added to budget+users only (both depend on raw `pika`; ai-service has no RabbitMQ usage/dependency). Verified 0.64b0 resolves cleanly against the pinned `opentelemetry-api==1.43.0` train with no conflicts (`pip install --dry-run`).
- [x] 4.2 Call `HTTPXClientInstrumentor().instrument()` and `PikaInstrumentor().instrument()` in `shared/observability/init_observability()`, guarded by the existing `OTEL_SDK_DISABLED` check, alongside the existing `SQLAlchemyInstrumentor().instrument()` call — `PikaInstrumentor` import is additionally wrapped in `try/except ImportError` since `opentelemetry.instrumentation.pika` imports raw `pika` at module level, which isn't installed in ai-service; without the guard, `shared.observability` would fail to import there.
- [x] 4.3 Manually verify in Jaeger that a budget-service call to `user_client.py` (httpx) and an event-consumer message handling (pika) each produce a child span under the parent request/consumer trace
- [x] 4.4 Run affected services' tests and lint clean; PR merged — tests/lint clean (budget 283, users 115, ai 77 passed; all 3 services import cleanly with instrumentation wired in), PR not yet opened

## 5. Widen business-context attributes to all budget-service mutation endpoints + dedupe error_handlers.py — depends on 1, 2, 3

- [x] 5.1 Add `set_span_attributes(**attributes)` helper to `shared/observability/__init__.py` (stringifies each value via `trace.get_current_span().set_attribute(...)`, skips `None`); use it in `shared/exceptions/error_handlers.py` (task 5.4) and in every route/service call site added below instead of repeating the get-span/stringify/set-attribute pattern
- [x] 5.2 Set `user_id` centrally in `shared/security/dependencies.py`'s `get_validated_user`, using `set_span_attributes`; remove the now-redundant manual `user_id` line from `create_budget_with_lines_service` (`services/budget/app/services/budget_services.py`)
- [x] 5.3 Set the relevant resource-id attribute(s) on all mutation endpoints (POST/PATCH/DELETE) across budget-service's routers: `budget_routes.py` (create/update/delete/with-lines), `budget_line_routes.py` (create/update/delete), `report_routes.py` (create/update/delete/submit/review/reopen), `report_line_routes.py` (create/update/delete), `attachment_routes.py` (create/delete), `funding_receipt_routes.py` (create), `currency_conversion_routes.py` (create), `mapping_routes.py` (templates/fields/categories/mappings creation, using their own natural ids — not `budget_id`). Set at the route level from the path parameter for update/delete/action endpoints; immediately after the service call for create endpoints.
- [x] 5.4 Move `domain_error_handler` and `unhandled_exception_handler` into `shared/exceptions/error_handlers.py`; update `services/budget/main.py`, `services/users/main.py`, `services/ai/main.py` to import from there instead of the per-service copies; delete the three per-service `app/core/error_handlers.py` files
- [x] 5.5 Consolidate the three duplicated `test_error_handlers.py` files into a single `shared/tests/test_error_handlers.py` covering the shared handlers directly; keep a thin per-service smoke test (or rely on existing coverage) confirming each `main.py` still registers them correctly; add tests for `set_span_attributes` (in `shared/tests/test_observability.py`) and for the centralized `user_id`-on-every-request behavior (in `shared/tests/test_dependencies.py`)
- [x] 5.6 Add/update unit tests covering resource-id span attributes on a representative sample of the newly-covered mutation endpoints (at least one create + one update/delete per router) — 7 of 8 routers got create+update/delete; `mapping_routes.py` has no update/delete endpoints at all, so covered 2 representative creates (templates, fields) instead
- [x] 5.7 Run all three services' tests and lint clean; PR merged — tests/lint clean (budget 297, users 112, ai 74, shared 70 passed), PR not yet opened

## 6. Widen resource-id attributes to GET endpoints with a path-parameter resource id — depends on 5, found via manual Jaeger verification (task 1.6)

- [x] 6.1 Set the relevant resource-id attribute(s) on GET endpoints across budget-service's routers whose path names a resource — single-resource fetches and `by-{parent}` filters — from the path parameter, before the service call: `budget_routes.py` (`GET /{budget_id}`), `budget_line_routes.py` (`GET /by-budget/{budget_id}`, `GET /{budget_line_id}`), `report_routes.py` (`GET /by-budget/{budget_id}`, `GET /{report_id}`), `report_line_routes.py` (`GET /by-report/{report_id}`, `GET /{report_line_id}`), `attachment_routes.py` (`GET /by-report-line/{report_line_id}`, `GET /{attachment_id}/content`, `GET /{attachment_id}/download-url`), `funding_receipt_routes.py` (`GET /{receipt_id}`, `GET /by-budget/{budget_id}`), `currency_conversion_routes.py` (`GET /balance/{budget_id}`, `GET /{conversion_id}`, `GET /by-budget/{budget_id}`), `mapping_routes.py` (`GET /categories/{template_id}`, `GET /fields/{template_id}`, `GET /mappings/by-ngo/{ngo_id}`). Bare list/dashboard/summary GETs with no resource id in their path are left alone.
- [x] 6.2 Add/update unit tests covering a representative sample of the newly-covered GET endpoints (at least one single-resource fetch + one by-parent filter) — `budget_routes.py` GET/{budget_id}, `report_routes.py` GET/{report_id} + GET/by-budget/{budget_id}
- [x] 6.3 Run budget-service tests and lint clean; PR merged — tests/lint clean (300 passed), PR not yet opened
