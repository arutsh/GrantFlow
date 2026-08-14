## Context

`shared/observability/__init__.py` already initializes an OTLP `TracerProvider` per service and instruments FastAPI (auto-creates a root span per request) and SQLAlchemy. It exposes `get_tracer(name)` and a `traced()` decorator, but nothing in the request-error path uses them today.

`domain_error_handler` (identical in `services/budget/app/core/error_handlers.py` and `services/users/app/core/error_handlers.py`) just converts a `DomainError`/`PermissionDenied` into a `JSONResponse`. FastAPI's OTEL instrumentation marks the span as errored only for unhandled exceptions that propagate past the ASGI layer; once a registered `exception_handler` catches and converts the exception to a response, FastAPIInstrumentor has no exception object to record, so the span shows `error: true`/`http.status_code: 500` with no `error.type`, `error.message`, or exception event. `ai-service` has no `DomainError` handling at all — `services/ai/main.py:34` shows a bare `except Exception:` with no handler registration.

## Goals / Non-Goals

**Goals:**
- Every `DomainError`/`PermissionDenied` caught by `domain_error_handler` is recorded on the active span (`error.type`, `error.message`, `record_exception`).
- Unhandled (non-domain) exceptions on all three services are caught by a catch-all handler that records them to the span before returning a generic 500 — so bugs that aren't yet modeled as `DomainError` are still traceable, and FastAPI's default "leak the traceback to the client" behavior doesn't apply.
- Every mutation endpoint (POST/PATCH/DELETE) across budget-service's routers carries the relevant resource id (`budget_id`, `report_id`, `budget_line_id`, etc.) as a span attribute once known, so a Jaeger trace pinpoints which record failed — not just the original `create_budget_with_lines` endpoint from the issue.
- GET endpoints whose path already names a resource (single-resource fetches and `by-{parent}` filters) carry that same id, so "why is fetching budget X slow/failing" is answerable from the span — not just mutations.
- `user_id` is set on every authenticated request's span across all three services, via the shared `get_validated_user` dependency, not per-route.
- Same handler pattern ported to `users-service` (already has the domain handler, just needs the span-recording + catch-all) and `ai-service` (needs both from scratch).
- `error_handlers.py` exists once, in `shared/`, instead of three near-identical per-service copies.

**Non-Goals:**
- Not building a generic structured-logging-to-tracing bridge; `structlog` logging is untouched.
- Bare list/dashboard/summary GET endpoints with no resource id in their path (e.g. `GET /budgets/`, `GET /budgets/dashboard/summary`) still get nothing beyond `user_id` — there's no single record to attach, and query-param filters (e.g. `budget_id` on `GET /reports/`) are left for a future pass rather than folded in here.
- httpx and pika instrumentation are nice-to-haves; if dependency resolution or breakage risk is high, they can be dropped without blocking the rest of the change (tracked as separate tasks, not gating).

## Decisions

**1. Span recording lives in the exception handler, not scattered at raise sites.**
`domain_error_handler` and the new catch-all read the *current* span via `trace.get_current_span()` (OTEL's ambient-context API — FastAPIInstrumentor has already started the request span by the time the handler runs) rather than requiring every `raise DomainError(...)` call site to touch tracing. This keeps the fix centralized to one file per service and matches the issue's ask to reuse `get_tracer()`/existing helpers rather than importing `opentelemetry.trace` ad hoc in business code. Handlers do need `from opentelemetry import trace` directly (not `get_tracer`, which returns a `Tracer` for *creating* spans, not the current-span accessor) — this is the one place importing `opentelemetry.trace` directly is appropriate, since it's infrastructure code, not a business handler.

**2. Catch-all handler registered for `Exception`, ordered after `DomainError`/`PermissionDenied`.**
FastAPI dispatches to the most specific registered handler, so registering `app.add_exception_handler(Exception, catch_all_handler)` is safe alongside the existing `DomainError`/`PermissionDenied` handlers — it only fires for exceptions that aren't already domain errors. Response body stays a generic `{"detail": "Internal server error"}` (no stack trace to the client); the trace carries the detail instead.

**3. Business-context attributes are set via a shared `set_span_attributes(**kwargs)` helper, called at the point each id becomes known — not a decorator, not scattered ad hoc `set_attribute` calls.**
The first pass (single endpoint) called `trace.get_current_span().set_attribute(...)` directly, reasoning that one call site didn't justify a new helper. Widening coverage to every mutation endpoint across budget-service (~25 call sites) reverses that math: `shared/observability` gains a `set_span_attributes(**attributes)` helper (stringifies each value, skips `None`) that every call site — including the shared error handlers' `error.type`/`error.message` — uses instead of repeating the get-span/stringify/set-attribute pattern. Still no decorator and no second tracing pattern alongside `traced()`; just a thin wrapper around `trace.get_current_span()`.
- `user_id` is set once, centrally, in `shared/security/dependencies.py`'s `get_validated_user`, which every authenticated route in all three services already depends on — covering every endpoint for free instead of per-route. This makes the per-route `user_id` line added to `create_budget_with_lines_service` in the first pass redundant; it's removed.
- Resource-id attributes (`budget_id`, `report_id`, `budget_line_id`, `report_line_id`, `attachment_id`, `funding_receipt_id`, `conversion_id`, or `mapping_routes.py`'s own `donor_template_id`/`ngo_id`) are set at the route-handler level for update/delete/action endpoints (id already known from the path parameter, before the service is even called), and immediately after the service call returns for create endpoints (id only exists post-creation).
- GET endpoints get the same treatment as update/delete: any resource id already present as a path parameter (single-resource fetches like `GET /{budget_id}`, and `by-{parent}` filters like `GET /by-budget/{budget_id}`) is set at the top of the handler, before the service call. GETs with no resource id in their path (bare lists, dashboards, summaries) are left alone — see Non-Goals.

**4. `error_handlers.py` is deduplicated into `shared/exceptions/error_handlers.py` — reversing the original call to defer this.**
The first pass added a third near-identical copy for ai-service, explicitly deferring dedup as lower-risk-for-now. Revisited: `domain_error_handler` and `unhandled_exception_handler` move to `shared/exceptions/error_handlers.py`, next to `shared/exceptions/exceptions.py` (which all three services already import `DomainError`/`PermissionDenied` from). Each service's `main.py` imports the handlers directly from `shared.exceptions.error_handlers`; the three per-service `app/core/error_handlers.py` files are deleted rather than kept as re-export shims, since nothing else references that per-service path.

**5. httpx/pika instrumentation added defensively.**
`HTTPXClientInstrumentor().instrument()` and `PikaInstrumentor().instrument()` are called in `shared/observability/init_observability()` guarded the same way SQLAlchemy's is (only when OTEL isn't disabled), so services that don't use httpx/pika are unaffected by the added no-op instrumentation call. If the packages turn out to conflict with pinned `opentelemetry-*` versions in `requirements.txt`, this task can be dropped without affecting the rest of the change.

## Risks / Trade-offs

- [Catch-all `Exception` handler could mask a handler ordering bug and swallow exceptions FastAPI would otherwise convert to its own 500 with different behavior (e.g. `HTTPException` still needs to flow through Starlette's normal handling)] → Register the catch-all for `Exception` but verify `HTTPException`/`StarletteHTTPException` still gets its normal handling in practice (Starlette resolves the most specific registered exception type first, and `HTTPException` isn't caught by a bare `Exception` handler unless FastAPI's default handler is removed — it isn't here).
- [`trace.get_current_span()` returns a no-op span if called outside a FastAPI-instrumented request context (e.g. in a test or a background task)] → `set_attribute`/`record_exception` on a no-op span are safe no-ops, so no guard is needed, but this should be called out in tests so a missing span isn't mistaken for a bug.
- [New `opentelemetry-instrumentation-httpx`/`-pika` packages could pin transitive deps that conflict with the existing `opentelemetry-*==1.43.0`/`0.64b0` pins] → Nice-to-have scope; if `pip install` surfaces a conflict, drop these two tasks rather than force a version bump across all `opentelemetry-*` packages.
- [Adding `user_id`/`budget_id` as span attributes sends what could be considered PII-adjacent identifiers to the OTLP backend (Grafana Cloud, per [[project_grafana_cloud_observability]])] → These are internal UUIDs, not names/emails; consistent with what's already logged via `structlog` today, so no new exposure class.
- [Setting `user_id` inside `shared/security/dependencies.py` introduces a new `shared.security` → `shared.observability` import] → Not a new external dependency: all three services already call `init_observability()` at startup and already depend on the `opentelemetry-*` packages. `shared.observability` doesn't import `shared.security`, so there's no cycle.

## Migration Plan

No data migration. Deploy is a standard rolling service restart (budget, users, ai) since changes are code-only — no schema, no new env vars for the required scope (span recording, catch-all handler, business-context attributes). If httpx/pika instrumentation is included, no new env vars either; instrumentation is enabled unconditionally alongside existing SQLAlchemy instrumentation. Rollback is a plain revert/redeploy — no state to unwind.

## Open Questions

- Should the catch-all 500 handler's client-facing body match the existing `DomainError` `{"detail": ...}` shape exactly, or is a distinct shape (e.g. `{"detail": "Internal server error"}` without leaking exception internals) acceptable? Defaulting to the latter (generic message) since leaking internal exception text to clients is a minor info-disclosure smell — flag if this should instead match existing error-shape conventions elsewhere in the frontend error handling.
