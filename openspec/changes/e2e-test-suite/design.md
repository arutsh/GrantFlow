## Context

Today's test pyramid stops at the service boundary: each of `users`, `budget`, `ai`, `chat`, `worker` has its own pytest suite running against mocked/aiosqlite dependencies, and the frontend has Vitest component tests. Nothing runs a real request through the API gateway across service and database boundaries, and nothing drives the actual built frontend. Issue #61 proposed closing this gap with Postman/Newman but was explicitly blocked on "having a staging environment or Docker Compose CI setup" — that blocker no longer holds: `docker-compose.local.yml` (driven by `local.sh up`) already boots the *entire* stack in Docker — Postgres, Redis, RabbitMQ, every backend service, the built frontend container, and an nginx gateway — with `.env.local` committed to the repo (safe placeholder values only, per `.gitignore`'s explicit carve-out). Each backend service's `entrypoint.sh` already waits for its DB and runs `alembic upgrade head` before serving, so the stack is self-migrating.

Two other changes are mid-flight against this codebase: `donor-dashboard` (new routes, new `is_ngo`/`is_donor` login fields) and `ai-chat-agent-host-migration` (chat/ai surfaces still being retired/rebuilt per tickets #94-97). Per the scoping decision for this change, e2e coverage targets only the stable, already-merged **auth + budget CRUD** journey, so this suite won't need rework as those other changes land.

## Goals / Non-Goals

**Goals:**
- Stand up a repeatable, single-command full-stack environment for e2e runs, reusing `docker-compose.local.yml` rather than inventing a parallel compose file.
- Phase 1: a Postman/Newman collection asserting the auth + budget CRUD chain works across real service/DB boundaries (status codes + response shape), runnable locally and in CI.
- Phase 2: a Playwright suite driving the same journey through the real built frontend UI, reusing the same compose stack.
- Wire both into a new CI workflow, path-filtered so it only runs when relevant services/frontend change (plus `workflow_dispatch` for manual runs).
- Keep the suite fully self-contained: no external test data, no manual seeding step, no reliance on the OVH/Hetzner staging host.

**Non-Goals:**
- AI chat, donor-dashboard, or reports flows (out of scope until those changes stabilize — tracked as a fast-follow).
- Contract/schema validation beyond status code + response shape (no OpenAPI diffing).
- Automated post-deploy smoke tests against production (`opengrantflow.com`) — the CI environment file is structured so a future staging Postman environment could point at it, but wiring that trigger is explicitly deferred.
- Visual regression testing.
- Parallel/sharded test execution — the initial suite is small enough to run serially.

## Decisions

**1. Reuse `docker-compose.local.yml` as the e2e harness, scoped to only the services under test.**
`local.sh up` already builds and runs the full containerized stack with a committed, safe env file — no new compose topology needed. For CI, the workflow calls `docker compose -f docker-compose.local.yml --env-file .env.local up -d --build grandflow-db redis rabbitmq users budget frontend nginx`, explicitly excluding `ai`, `chat`, `worker`, `beat` since they're out of scope and some require provider API keys/RabbitMQ consumers not needed for this journey. Alternative considered: a dedicated `docker-compose.e2e.yml` — rejected as duplicate topology to maintain in parallel with `local.yml`.

**2. Ephemeral state per run — no seeding/cleanup logic.**
Each CI run does `docker compose ... up -d --build` against fresh, unnamed volumes (CI runners are always clean) and `docker compose down -v` in an `if: always()` step. Tests generate their own unique fixture data (e.g. `e2e-${{ timestamp/uuid }}@example.com` emails) rather than relying on pre-seeded rows, so there's no cross-run collision risk and no separate teardown/reset script to maintain. Local runs get the same guarantee by convention (`docker compose down -v` documented in the suite's README) rather than enforced tooling, since local iteration benefits from being able to inspect state between runs.

**3. Postman/Newman targets the nginx gateway (`localhost:9082`), not individual services.**
This exercises the actual path-mapping (`/api/v1/users/`, `/api/v1/budget/`, etc. per `nginx/nginx.conf`) the frontend depends on, not just the services in isolation — closer to what "integration" means here. Collection: `postman/auth-budget.postman_collection.json`, environments `postman/environments/{local,ci}.postman_environment.json` (identical values today; kept separate so a future staging environment is a drop-in third file rather than a refactor). Chain: register → login (capture JWT via `pm.environment.set`) → create budget → add line → update line → delete line → get budget (assert totals) → delete budget.

**4. Playwright targets the containerized frontend build (`localhost:4000`), not `vite dev`.**
Testing the actual production-style build (already what `frontend` container in `docker-compose.local.yml` serves) catches build-time issues (env var baking, asset paths) that `npm run dev` would mask. Config lives at `frontend-typescript/e2e/playwright.config.ts`, specs under `frontend-typescript/e2e/specs/`, with a minimal page-object layer (`e2e/pages/`) for login and budget pages to keep specs readable — kept intentionally thin (no framework) since the suite starts with ~2-3 spec files.

**5. Single new CI workflow, path-filtered like the existing per-service workflows.**
`.github/workflows/e2e.yml` follows the existing `dorny/paths-filter` pattern (see `budget.yml`/`frontend.yml`) triggering on changes under `services/users/**`, `services/budget/**`, `shared/**`, `frontend-typescript/**`, or the workflow file itself, plus `workflow_dispatch`. One job: build stack → wait-for-healthy (poll gateway `/health` or equivalent) → `newman run` → `npx playwright test` → `docker compose down -v` (always). Keeping Postman and Playwright in one job (not two) avoids booting the stack twice; if build times become a problem later, splitting is a cheap follow-up.

**6. `@playwright/test` added to `frontend-typescript/devDependencies`; Newman lives in a small standalone `postman/package.json`.**
Playwright belongs with the frontend since specs may eventually import frontend types/fixtures. Newman has no frontend dependency, so a separate minimal `package.json` (or `npx newman` with no repo-level install) avoids bloating frontend's dependency tree with an unrelated CLI tool.

## Risks / Trade-offs

- **[Risk] Full-stack container builds are slow (5 services + frontend), inflating CI time on every relevant PR.** → Mitigation: path-filtering already limits *when* it runs; Docker layer caching via `actions/cache` or GHA's built-in Docker layer cache can be added if measured build time becomes painful — deferred until real numbers exist rather than pre-optimized.
- **[Risk] `ai`/`chat` services excluded from the e2e compose run — if `users`/`budget` gain a hard runtime dependency on them (health checks, startup calls) the stack could fail to boot.** → Mitigation: verify during Phase 1 implementation that `users`/`budget` boot and serve auth+budget routes with `ai`/`chat` absent; if a hidden dependency exists, either start those services too (accepting the extra boot cost) or fix the coupling (arguably a bug either way, per the chat migration's stated goal of decoupled services).
- **[Risk] Flaky Playwright runs from timing (SSE/streaming, redirects) even outside the excluded chat flows.** → Mitigation: use Playwright's built-in auto-waiting/assertions (`expect(...).toBeVisible()` etc.) rather than manual sleeps; keep Phase 2 scope to simple CRUD forms/navigation where this risk is low.
- **[Trade-off] No contract/schema validation.** Newman assertions are status-code + shape (field presence), not full JSON-schema diffing — cheaper to write and maintain, but won't catch a field silently changing type. Acceptable for the current scope; can be tightened later if a real regression slips through.
- **[Trade-off] Ephemeral-state approach means no test data persists for manual debugging after a CI run.** Mitigated by keeping local runs (`docker compose down -v` is a manual, documented step, not automatic) able to leave state up for inspection.

## Migration Plan

Purely additive — no existing service or CI job is modified besides adding one new workflow file. Rollback is deleting the new files (`postman/`, `frontend-typescript/e2e/`, `.github/workflows/e2e.yml`, the added `devDependency`) with no runtime impact, since nothing else depends on this suite existing.

## Open Questions

- Does the gateway (nginx) or any service expose a `/health` (or equivalent) endpoint suitable for a CI wait-for-healthy step, or does one need to be added? To confirm during Phase 1 implementation.
- Should the Postman environment for a future staging/post-deploy smoke run be scaffolded now (empty values) or added only when that follow-up is actually scheduled? Leaning toward the latter (YAGNI) but flagging since the proposal's "Impact" section mentions preparing for it.
