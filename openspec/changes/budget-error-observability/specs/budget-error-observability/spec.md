## ADDED Requirements

### Requirement: Domain errors are recorded on the active trace span
When a `DomainError` or `PermissionDenied` exception is caught by a service's `domain_error_handler`, the system SHALL record the exception on the currently active OpenTelemetry span, including the exception object (`record_exception`), `error.type` (the exception class name), and `error.message` (the exception's message), before returning the JSON error response.

#### Scenario: Budget validation error is recorded on the span
- **WHEN** a request to `budget-service` raises a `DomainError` (e.g. "Budget line amount cannot be negative")
- **THEN** the active span for that request has an exception event and `error.type`/`error.message` attributes matching the raised error, and the client still receives the existing `{"detail": ...}` JSON response with the error's status code

#### Scenario: Permission denial is recorded on the span
- **WHEN** a request raises `PermissionDenied`
- **THEN** the active span records the exception and `error.type` = `PermissionDenied`, with the client receiving the existing JSON error response unchanged

### Requirement: Unhandled exceptions are caught and recorded before returning a generic 500
Each of `budget-service`, `users-service`, and `ai-service` SHALL register a catch-all exception handler for exceptions not already handled by a more specific handler (i.e. not `DomainError`/`PermissionDenied`). This handler SHALL record the exception on the active span (exception event, `error.type`, `error.message`) and return a generic 500 JSON response without leaking internal exception details to the client.

#### Scenario: Unexpected exception is traceable
- **WHEN** a route handler raises an exception that is not a `DomainError` or `PermissionDenied` (e.g. an unexpected `AttributeError`)
- **THEN** the active span records the exception with `error.type` and `error.message` reflecting the actual exception, and the client receives a generic 500 response that does not include the raw exception message or stack trace

#### Scenario: Existing HTTPException handling is unaffected
- **WHEN** a route handler raises a Starlette/FastAPI `HTTPException`
- **THEN** the response and status code behave exactly as before this change (the catch-all handler does not intercept `HTTPException`)

### Requirement: Budget mutation traces carry business-context attributes
The `create_budget_with_lines_service` request flow SHALL set `budget_id` and `user_id` as attributes on the active span once those values are known, so a trace for that endpoint can be correlated to the specific budget and user involved without cross-referencing logs.

#### Scenario: Successful budget-with-lines creation is attributable
- **WHEN** `POST /api/v1/budgets/with-lines` succeeds
- **THEN** the request's span includes `budget_id` (the newly created budget's ID) and `user_id` (the requesting user's ID) as attributes

#### Scenario: Failed budget-with-lines creation is attributable
- **WHEN** `POST /api/v1/budgets/with-lines` fails partway through (e.g. a budget line fails validation after the budget itself was created)
- **THEN** the request's span includes `user_id`, and `budget_id` if the budget was created before the failure occurred, alongside the recorded exception
