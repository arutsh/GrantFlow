## Why

When a 500 error occurs on endpoints like `POST /api/v1/budgets/with-lines`, Jaeger traces only show `error: true` and `http.status_code: 500` with no context about what failed or why. Debugging requires manually correlating a trace ID with log files. `domain_error_handler` returns a JSON response but never records the exception on the active span, there is no catch-all handler for unhandled 500s, and inter-service HTTP/RabbitMQ calls are invisible in traces.

## What Changes

- Record exceptions on the active OTEL span in `domain_error_handler` (`error.type`, `error.message`, `span.record_exception`) in `services/budget/app/core/error_handlers.py`.
- Add a catch-all handler for unhandled (non-`DomainError`) exceptions that records the exception to the active span before returning a generic 500, so unexpected bugs are also traceable.
- Add business-context span attributes (`budget_id`, `user_id`) at the route/service boundary for the priority endpoint (`create_budget_with_lines`) and other budget mutation endpoints, using the existing `get_tracer()`/`traced()` helpers in `shared/observability/__init__.py`.
- Apply the same domain-error and catch-all handler pattern to `users-service` (which already has an identical `error_handlers.py`) and `ai-service` (which has none yet).
- (Nice to have) Instrument outbound `httpx` calls (used by `user_client.py` for inter-service calls) via `opentelemetry-instrumentation-httpx`.
- (Nice to have) Instrument `pika` RabbitMQ consumer operations (`event_consumer.py`) via `opentelemetry-instrumentation-pika`.

## Capabilities

### New Capabilities
- `budget-error-observability`: error/exception recording on OTEL spans (domain errors and unhandled exceptions), plus business-context span attributes, for budget-service, users-service, and ai-service.

### Modified Capabilities
(none — no existing spec covers error/observability behavior)

## Impact

- Code: `services/budget/app/core/error_handlers.py`, `services/budget/main.py`, `services/users/app/core/error_handlers.py`, `services/users/main.py`, `services/ai/main.py` (new `error_handlers.py`), `services/budget/app/services/budget_services.py` (span attributes), `services/budget/app/services/user_client.py` and `event_consumer.py` (nice-to-have instrumentation).
- Dependencies: `opentelemetry-instrumentation-httpx`, `opentelemetry-instrumentation-pika` added to `services/budget/requirements.txt` (nice-to-have scope only).
- No API contract or database changes; purely observability/tracing behavior. No breaking changes.
