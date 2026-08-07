## Why

Every service ships with unit/integration tests run against mocked dependencies (per-service pytest suites, Vitest for the frontend), but nothing today exercises a real request across service boundaries — through the API gateway, users → budget, real Postgres, real JWT auth — let alone through the actual browser UI. Regressions that only show up at integration boundaries (a proxy forwarding the wrong header, a route wired to the wrong gateway path, an auth flag not surviving a login round-trip) currently ship to production undetected until a human clicks through manually. GitHub issue #61 ("Backlog: Integration test strategy with Postman/Newman") captured this gap early but was blocked on having a runnable full-stack environment; that blocker is gone now that `docker-compose.dev.yml`/`local.yml` exist and a real staging-equivalent (Hetzner production) is live.

## What Changes

- **Phase 1 — Playwright API-chain suite** (closes #61 as originally scoped): an `api` Playwright project (no browser, uses the `request` fixture) covering the auth + budget CRUD chain — register/login → create budget → add/update/delete budget lines → verify list/detail responses — run against a docker-compose-launched stack (users + budget + grandflow-db + redis + rabbitmq), targeting the nginx gateway directly.
- **Phase 2 — Playwright browser E2E suite**: a `browser` Playwright project (chromium) driving the real React app against the same compose stack, covering the identical auth + budget CRUD user journey through actual UI interactions (login form, budget list/detail pages, add/edit/delete line dialogs). Both projects live in one `frontend-typescript/e2e/` Playwright project/config — one tool, one dependency, one CI step, rather than splitting the API-chain layer into a separate Postman/Newman toolchain.
- New CI workflow (`.github/workflows/e2e.yml`) that brings up the compose stack, runs the Playwright suite (`api` project, then `browser` project), and tears the stack down — triggered on PRs touching `services/users/**`, `services/budget/**`, `shared/**`, or `frontend-typescript/**`, plus manual dispatch.
- Explicitly scoped to **auth + budget CRUD only** for this change. AI chat and donor-dashboard flows are excluded: at the time this was originally scoped both were mid-migration (`ai-chat-agent-host-migration`, `donor-dashboard`); both have since stabilized (archived as complete capabilities under `openspec/specs/`), so the exclusion is now a deliberate choice to keep this first suite small rather than a technical blocker. Extending e2e coverage to those capabilities — donor-grantee-relationship and donor-dashboard are the natural first candidates — is a fast-follow, not a dependency of this change.

## Capabilities

### New Capabilities
- `e2e-testing`: the end-to-end test strategy itself — what the API-chain and browser suites cover, how they're run locally and in CI, environment/data setup and teardown, and the scope boundary (which user journeys are in vs. explicitly out for this change).

### Modified Capabilities
- None (this change doesn't alter product-behavior requirements of any existing capability; the `/health` endpoints added under Impact below are operational plumbing for the CI harness, not user-facing behavior).

## Impact

- **New code**: `frontend-typescript/e2e/` (Playwright config with `api` and `browser` projects, specs, fixtures/page objects); `.github/workflows/e2e.yml`.
- **Modified code**: `services/users` and `services/budget` each gain a minimal `/health` endpoint (mirroring `services/chat/app/api/health_routes.py`, the only service that currently has one) — required for the CI wait-for-healthy step. `docker-compose.dev.yml` may need a documented `--env-file .env.dev` recipe for CI use if it doesn't already boot cleanly headless (verify in design).
- **Dependencies**: `@playwright/test` only, added to `frontend-typescript/devDependencies`.
- **Out of scope / explicit fast-follows**: AI chat flows, donor-dashboard flows, contract/schema validation beyond status-code + shape assertions, staging smoke-test automation (environment file is prepared but not wired to a scheduled/post-deploy run), visual regression testing.
