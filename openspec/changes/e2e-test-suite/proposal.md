## Why

Every service ships with unit/integration tests run against mocked dependencies (per-service pytest suites, Vitest for the frontend), but nothing today exercises a real request across service boundaries — through the API gateway, users → budget, real Postgres, real JWT auth — let alone through the actual browser UI. Regressions that only show up at integration boundaries (a proxy forwarding the wrong header, a route wired to the wrong gateway path, an auth flag not surviving a login round-trip) currently ship to production undetected until a human clicks through manually. GitHub issue #61 ("Backlog: Integration test strategy with Postman/Newman") captured this gap early but was blocked on having a runnable full-stack environment; that blocker is gone now that `docker-compose.dev.yml`/`local.yml` exist and a real staging-equivalent (Hetzner production) is live.

## What Changes

- **Phase 1 — Postman/Newman API-chain suite** (closes #61 as originally scoped): a versioned `postman/` collection covering the auth + budget CRUD chain — register/login → create budget → add/update/delete budget lines → verify list/detail responses — run via Newman against a docker-compose-launched stack (users + budget + grandflow-db + redis + rabbitmq), with environments for local/CI and a manual staging target.
- **Phase 2 — Playwright browser E2E suite**: a `frontend-typescript/e2e/` Playwright project driving the real React app against the same compose stack, covering the identical auth + budget CRUD user journey through actual UI interactions (login form, budget list/detail pages, add/edit/delete line dialogs).
- New CI workflow (`.github/workflows/e2e.yml`) that brings up the compose stack, runs Newman, then Playwright, and tears the stack down — triggered on PRs touching `services/users/**`, `services/budget/**`, `shared/**`, or `frontend-typescript/**`, plus manual dispatch.
- Explicitly scoped to **auth + budget CRUD only** for this change. AI chat and donor-dashboard flows are deliberately excluded: both are mid-migration (`ai-chat-agent-host-migration`, `donor-dashboard` changes are in active development) and adding e2e coverage against moving surfaces would mean rewriting the suite mid-flight. Extending e2e coverage to those capabilities is a natural follow-up once they stabilize.

## Capabilities

### New Capabilities
- `e2e-testing`: the end-to-end test strategy itself — what the API-chain and browser suites cover, how they're run locally and in CI, environment/data setup and teardown, and the scope boundary (which user journeys are in vs. explicitly out for this change).

### Modified Capabilities
- None (`openspec/specs/` has no archived capabilities yet to delta against; this change only adds new test infrastructure, no product-behavior requirements change).

## Impact

- **New code**: `postman/auth-budget.postman_collection.json` + `postman/environments/{local,ci}.postman_environment.json`; `frontend-typescript/e2e/` (Playwright config, specs, fixtures/page objects); `.github/workflows/e2e.yml`.
- **Modified code**: none in application services — this is additive test infrastructure only. `docker-compose.dev.yml` may need a documented `--env-file .env.dev` recipe for CI use if it doesn't already boot cleanly headless (verify in design).
- **Dependencies**: Newman (npm, CI-only or a small `postman/` package.json), `@playwright/test` (added to `frontend-typescript/devDependencies`).
- **Out of scope / explicit fast-follows**: AI chat flows, donor-dashboard flows, contract/schema validation beyond status-code + shape assertions, staging smoke-test automation (environment file is prepared but not wired to a scheduled/post-deploy run), visual regression testing.
