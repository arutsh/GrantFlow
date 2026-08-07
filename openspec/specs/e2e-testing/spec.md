# e2e-testing Specification

## Purpose
TBD - created by archiving change e2e-test-suite. Update Purpose after archive.
## Requirements
### Requirement: API-chain e2e suite covers auth + budget CRUD
The system SHALL provide a Playwright `api` project (no browser, using the `request` fixture) that exercises the auth + budget CRUD journey — register, login, create budget, add budget line, update budget line, delete budget line, retrieve budget, delete budget — through the nginx API gateway against real backend services and a real Postgres database, asserting response status codes and expected response shape at each step.

#### Scenario: Full chain succeeds against a freshly booted stack
- **WHEN** the `api` project's spec is run against a docker-compose.local.yml stack that just finished booting (migrations applied, no prior test data)
- **THEN** every request in the chain returns its expected status code, the created budget's retrieved totals reflect the lines added/updated, and the spec reports zero failed assertions

#### Scenario: Auth failure is asserted, not silently ignored
- **WHEN** the login request in the chain is sent with valid credentials from the preceding registration step
- **THEN** the JWT returned is captured from the response body and successfully authorizes every subsequent request in the chain (no 401 responses on authenticated steps)

### Requirement: Browser e2e suite covers the same journey through the real UI
The system SHALL provide a Playwright `browser` project (chromium), in the same Playwright config as the `api` project, that drives the containerized, production-built frontend through the identical auth + budget CRUD journey using real UI interactions (form fills, clicks, navigation), against the same docker-compose.local.yml stack.

#### Scenario: User completes budget CRUD entirely through the UI
- **WHEN** a Playwright spec registers a new user, logs in through the login form, creates a budget, adds and edits a budget line, and deletes the budget — all via UI interactions, no direct API calls
- **THEN** each step's expected UI state is visible (e.g. redirect to dashboard after login, new budget appears in the budget list, line totals update in the UI) and the spec completes without manual waits/sleeps

### Requirement: e2e suites run against an ephemeral, self-contained environment
The system SHALL run both e2e suites against a stack booted fresh for each run (no pre-seeded or persisted test data required), with each test generating its own unique fixture data to avoid collisions across repeated runs.

#### Scenario: Suite passes on a repeated run without manual cleanup
- **WHEN** the full e2e suite (the `api` project, then the `browser` project) is run twice in a row against the same freshly booted stack, with no manual data cleanup between runs
- **THEN** both runs pass, because each run's test data (e.g. user emails) is uniquely generated and does not collide with data from the prior run

### Requirement: e2e suites run in CI, scoped to relevant changes
The system SHALL run both e2e suites in a dedicated CI workflow triggered on pull requests touching `services/users/**`, `services/budget/**`, `shared/**`, or `frontend-typescript/**`, and SHALL support manual invocation (workflow_dispatch) independent of path changes.

#### Scenario: PR touching an unrelated service does not trigger the e2e workflow
- **WHEN** a pull request only modifies files under `services/ai/**` or `services/worker/**`
- **THEN** the e2e CI workflow does not run

#### Scenario: PR touching budget CRUD code triggers the e2e workflow
- **WHEN** a pull request modifies a file under `services/budget/**`
- **THEN** the e2e CI workflow runs, boots the stack, runs both Playwright projects, and tears the stack down regardless of pass/fail outcome

### Requirement: e2e scope is deliberately narrow for the initial suite
The system SHALL NOT include AI chat, donor-dashboard, or donor-grantee-relationship user journeys in this initial e2e suite, even though all three capabilities are now stable (archived under `openspec/specs/`). The exclusion is a deliberate choice to keep the first cut of this suite small, not a technical blocker.

#### Scenario: Suite has no dependency on chat, donor-dashboard, or donor-grantee-relationship routes
- **WHEN** a future change extends e2e coverage to chat, donor-dashboard, or donor-grantee-relationship flows
- **THEN** that extension is scoped as a separate follow-on change, since neither Playwright project in this suite references those routes or flows today

