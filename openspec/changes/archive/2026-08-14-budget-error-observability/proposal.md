## Why

When a 500 error occurs on endpoints like `POST /api/v1/budgets/with-lines`, Jaeger traces only show `error: true` and `http.status_code: 500` with no context about what failed or why. Debugging requires manually correlating a trace ID with log files. `domain_error_handler` returns a JSON response but never records the exception on the active span, there is no catch-all handler for unhandled 500s, and inter-service HTTP/RabbitMQ calls are invisible in traces.

## What Changes

- Record exceptions on the active OTEL span (`error.type`, `error.message`, `span.record_exception`) in a shared `domain_error_handler`/`unhandled_exception_handler` pair, deduplicated into `shared/exceptions/error_handlers.py` and used by all three services (see dedup bullet below).
- Add a catch-all handler for unhandled (non-`DomainError`) exceptions that records the exception to the active span before returning a generic 500, so unexpected bugs are also traceable.
- Add business-context span attributes at the route/service boundary for every mutation endpoint (POST/PATCH/DELETE) across budget-service's routers — not just `create_budget_with_lines` — using a new `set_span_attributes()` helper in `shared/observability/__init__.py`. `user_id` is set once, centrally, in the shared `get_validated_user` dependency (`shared/security/dependencies.py`), covering every authenticated endpoint in all three services automatically.
- Extend the same resource-id attributes to GET endpoints whose path already names a resource (single-resource fetches and `by-{parent}` filters), found missing during manual Jaeger verification of the mutation-only pass. Bare list/dashboard/summary GETs are left alone.
- Apply the same domain-error and catch-all handler pattern to `users-service` and `ai-service`.
- Deduplicate `error_handlers.py` — byte-identical across budget/users, and now ai-service — into a single `shared/exceptions/error_handlers.py`; delete the three per-service copies.
- (Nice to have) Instrument outbound `httpx` calls (used by `user_client.py` for inter-service calls) via `opentelemetry-instrumentation-httpx`.
- (Nice to have) Instrument `pika` RabbitMQ consumer operations (`event_consumer.py`) via `opentelemetry-instrumentation-pika`.

## Capabilities

### New Capabilities
- `budget-error-observability`: error/exception recording on OTEL spans (domain errors and unhandled exceptions), plus business-context span attributes, for budget-service, users-service, and ai-service.

### Modified Capabilities
(none — no existing spec covers error/observability behavior)

## Impact

- Code: `shared/exceptions/error_handlers.py` (new, moved from the three per-service copies), `shared/observability/__init__.py` (new `set_span_attributes()` helper, httpx/pika instrumentation), `shared/security/dependencies.py` (`user_id` span attribute), `services/{budget,users,ai}/main.py` (import shared handlers), the three per-service `app/core/error_handlers.py` (deleted), `services/budget/app/api/*_routes.py` (all 8 routers — resource-id span attributes on mutation endpoints), `services/budget/app/services/budget_services.py` (drop the now-redundant manual `user_id` line), `services/budget/app/services/user_client.py` and `event_consumer.py` (nice-to-have instrumentation).
- Dependencies: `opentelemetry-instrumentation-httpx`, `opentelemetry-instrumentation-pika` added to `services/budget/requirements.txt` (nice-to-have scope only).
- No API contract or database changes; purely observability/tracing behavior. No breaking changes.
