## Context

`shared/observability/__init__.py` already initializes an OTLP `TracerProvider` per service and instruments FastAPI (auto-creates a root span per request) and SQLAlchemy. It exposes `get_tracer(name)` and a `traced()` decorator, but nothing in the request-error path uses them today.

`domain_error_handler` (identical in `services/budget/app/core/error_handlers.py` and `services/users/app/core/error_handlers.py`) just converts a `DomainError`/`PermissionDenied` into a `JSONResponse`. FastAPI's OTEL instrumentation marks the span as errored only for unhandled exceptions that propagate past the ASGI layer; once a registered `exception_handler` catches and converts the exception to a response, FastAPIInstrumentor has no exception object to record, so the span shows `error: true`/`http.status_code: 500` with no `error.type`, `error.message`, or exception event. `ai-service` has no `DomainError` handling at all — `services/ai/main.py:34` shows a bare `except Exception:` with no handler registration.

## Goals / Non-Goals

**Goals:**
- Every `DomainError`/`PermissionDenied` caught by `domain_error_handler` is recorded on the active span (`error.type`, `error.message`, `record_exception`).
- Unhandled (non-domain) exceptions on all three services are caught by a catch-all handler that records them to the span before returning a generic 500 — so bugs that aren't yet modeled as `DomainError` are still traceable, and FastAPI's default "leak the traceback to the client" behavior doesn't apply.
- `create_budget_with_lines_service` (the priority endpoint from the issue) carries `budget_id`/`user_id` as span attributes so a Jaeger trace pinpoints which budget/user failed.
- Same handler pattern ported to `users-service` (already has the domain handler, just needs the span-recording + catch-all) and `ai-service` (needs both from scratch).

**Non-Goals:**
- Not building a generic structured-logging-to-tracing bridge; `structlog` logging is untouched.
- Not adding span attributes to every route — only the endpoint called out in the issue (`with-lines`) plus other budget mutation endpoints reached opportunistically, not an exhaustive sweep of every handler in every service.
- httpx and pika instrumentation are nice-to-haves; if dependency resolution or breakage risk is high, they can be dropped without blocking the rest of the change (tracked as separate tasks, not gating).
- Not deduplicating the (already duplicated) `error_handlers.py` between budget and users into `shared/` — noted as a pre-existing duplication this change increases, tracked separately, not part of this change's scope.

## Decisions

**1. Span recording lives in the exception handler, not scattered at raise sites.**
`domain_error_handler` and the new catch-all read the *current* span via `trace.get_current_span()` (OTEL's ambient-context API — FastAPIInstrumentor has already started the request span by the time the handler runs) rather than requiring every `raise DomainError(...)` call site to touch tracing. This keeps the fix centralized to one file per service and matches the issue's ask to reuse `get_tracer()`/existing helpers rather than importing `opentelemetry.trace` ad hoc in business code. Handlers do need `from opentelemetry import trace` directly (not `get_tracer`, which returns a `Tracer` for *creating* spans, not the current-span accessor) — this is the one place importing `opentelemetry.trace` directly is appropriate, since it's infrastructure code, not a business handler.

**2. Catch-all handler registered for `Exception`, ordered after `DomainError`/`PermissionDenied`.**
FastAPI dispatches to the most specific registered handler, so registering `app.add_exception_handler(Exception, catch_all_handler)` is safe alongside the existing `DomainError`/`PermissionDenied` handlers — it only fires for exceptions that aren't already domain errors. Response body stays a generic `{"detail": "Internal server error"}` (no stack trace to the client); the trace carries the detail instead.

**3. Business-context attributes set at the route/service boundary via a small helper, not a new decorator.**
Rather than inventing a new attribute-setting convention, use `get_tracer(__name__).start_as_current_span(...)` is unnecessary here since FastAPI already owns the request span — instead call `trace.get_current_span().set_attribute("budget_id", str(new_budget.id))` etc. directly in `create_budget_with_lines_service` at the point the ID becomes known (and in a `except` block for `user_id`, which is known from `valid_user` up front). This avoids adding a second tracing pattern alongside `traced()`.

**4. `ai-service` gets the same two-file pattern (`exceptions.py` re-export + `error_handlers.py`) copied from `users-service`/`budget-service`, not a shared abstraction.**
Given the existing duplication between budget and users, introducing a third copy now and centralizing all three later (tracked separately) is lower-risk than a mid-change refactor to `shared/`.

**5. httpx/pika instrumentation added defensively.**
`HTTPXClientInstrumentor().instrument()` and `PikaInstrumentor().instrument()` are called in `shared/observability/init_observability()` guarded the same way SQLAlchemy's is (only when OTEL isn't disabled), so services that don't use httpx/pika are unaffected by the added no-op instrumentation call. If the packages turn out to conflict with pinned `opentelemetry-*` versions in `requirements.txt`, this task can be dropped without affecting the rest of the change.

## Risks / Trade-offs

- [Catch-all `Exception` handler could mask a handler ordering bug and swallow exceptions FastAPI would otherwise convert to its own 500 with different behavior (e.g. `HTTPException` still needs to flow through Starlette's normal handling)] → Register the catch-all for `Exception` but verify `HTTPException`/`StarletteHTTPException` still gets its normal handling in practice (Starlette resolves the most specific registered exception type first, and `HTTPException` isn't caught by a bare `Exception` handler unless FastAPI's default handler is removed — it isn't here).
- [`trace.get_current_span()` returns a no-op span if called outside a FastAPI-instrumented request context (e.g. in a test or a background task)] → `set_attribute`/`record_exception` on a no-op span are safe no-ops, so no guard is needed, but this should be called out in tests so a missing span isn't mistaken for a bug.
- [New `opentelemetry-instrumentation-httpx`/`-pika` packages could pin transitive deps that conflict with the existing `opentelemetry-*==1.43.0`/`0.64b0` pins] → Nice-to-have scope; if `pip install` surfaces a conflict, drop these two tasks rather than force a version bump across all `opentelemetry-*` packages.
- [Adding `user_id`/`budget_id` as span attributes sends what could be considered PII-adjacent identifiers to the OTLP backend (Grafana Cloud, per [[project_grafana_cloud_observability]])] → These are internal UUIDs, not names/emails; consistent with what's already logged via `structlog` today, so no new exposure class.

## Migration Plan

No data migration. Deploy is a standard rolling service restart (budget, users, ai) since changes are code-only — no schema, no new env vars for the required scope (span recording, catch-all handler, business-context attributes). If httpx/pika instrumentation is included, no new env vars either; instrumentation is enabled unconditionally alongside existing SQLAlchemy instrumentation. Rollback is a plain revert/redeploy — no state to unwind.

## Open Questions

- Should the catch-all 500 handler's client-facing body match the existing `DomainError` `{"detail": ...}` shape exactly, or is a distinct shape (e.g. `{"detail": "Internal server error"}` without leaking exception internals) acceptable? Defaulting to the latter (generic message) since leaking internal exception text to clients is a minor info-disclosure smell — flag if this should instead match existing error-shape conventions elsewhere in the frontend error handling.
