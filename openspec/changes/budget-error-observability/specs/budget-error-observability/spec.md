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

### Requirement: Mutation endpoints carry business-context attributes
Every mutation endpoint (POST/PATCH/DELETE) across budget-service's routers SHALL set the relevant resource identifier(s) (e.g. `budget_id`, `report_id`, `budget_line_id`, `report_line_id`, `attachment_id`, `funding_receipt_id`, `conversion_id`, or a router-specific id such as `donor_template_id`/`ngo_id` for mapping endpoints) as attributes on the active span once known, so a trace for that endpoint can be correlated to the specific record involved without cross-referencing logs.

#### Scenario: Successful budget-with-lines creation is attributable
- **WHEN** `POST /api/v1/budgets/with-lines` succeeds
- **THEN** the request's span includes `budget_id` (the newly created budget's ID) as an attribute

#### Scenario: Failed budget-with-lines creation is attributable
- **WHEN** `POST /api/v1/budgets/with-lines` fails partway through (e.g. a budget line fails validation after the budget itself was created)
- **THEN** the request's span includes `budget_id` if the budget was created before the failure occurred, alongside the recorded exception

#### Scenario: Update/delete endpoints are attributable from the path parameter
- **WHEN** a request updates or deletes an existing resource (e.g. `PATCH /api/v1/budgets/{budget_id}`, `DELETE /api/v1/report-lines/{report_line_id}`)
- **THEN** the request's span includes that resource's id as an attribute, set from the path parameter before the underlying service call runs

#### Scenario: Create endpoints are attributable once the resource exists
- **WHEN** a request creates a new resource (e.g. `POST /api/v1/reports/`)
- **THEN** the request's span includes the newly created resource's id as an attribute, set immediately after creation succeeds

### Requirement: GET endpoints with a path-parameter resource id carry that id as a span attribute
Every GET endpoint across budget-service's routers whose path names a resource — either a single-resource fetch (e.g. `GET /{budget_id}`) or a `by-{parent}` filter (e.g. `GET /by-budget/{budget_id}`) — SHALL set that resource's id as an attribute on the active span before the underlying service call runs, so a slow or failing read can be correlated to the specific record without cross-referencing logs. GET endpoints with no resource id in their path (bare lists, dashboards, summaries) are unaffected — they still carry only `user_id`.

#### Scenario: Single-resource GET is attributable
- **WHEN** a request fetches a single resource by id (e.g. `GET /api/v1/budgets/{budget_id}`)
- **THEN** the request's span includes that resource's id as an attribute, set from the path parameter before the underlying service call runs

#### Scenario: by-parent filter GET is attributable
- **WHEN** a request lists resources filtered by a parent id in the path (e.g. `GET /api/v1/reports/by-budget/{budget_id}`)
- **THEN** the request's span includes the parent id as an attribute

#### Scenario: Bare list endpoints are unaffected
- **WHEN** a request has no resource id in its path (e.g. `GET /api/v1/budgets/`, `GET /api/v1/budgets/dashboard/summary`)
- **THEN** the request's span carries `user_id` as usual but no additional resource-id attribute

### Requirement: Every authenticated request carries user_id on its span
Any request across budget-service, users-service, or ai-service that resolves a user via the shared `get_validated_user` dependency SHALL have `user_id` set as an attribute on the active span, without each route setting it individually.

#### Scenario: user_id is set once for every authenticated endpoint
- **WHEN** an authenticated request to any of the three services passes through `get_validated_user`
- **THEN** the active span for that request has `user_id` set as an attribute
