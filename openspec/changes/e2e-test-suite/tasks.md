## 1. Environment groundwork

- [ ] 1.1 Verify `docker compose -f docker-compose.local.yml --env-file .env.local up -d --build grandflow-db redis rabbitmq users budget frontend nginx` boots cleanly (migrations run, all containers healthy) with `ai`, `chat`, `worker`, `beat` excluded; fix any hidden dependency uncovered (Risk #2 in design.md)
- [ ] 1.2 Confirm or add a health-check endpoint suitable for a CI wait-for-healthy step (gateway and/or users/budget `/health`); document the exact URL(s) and expected response
- [ ] 1.3 Write a short `postman/README.md` / `frontend-typescript/e2e/README.md` note documenting the manual `docker compose down -v` convention for local runs

## 2. Postman/Newman API-chain suite (Phase 1)

- [ ] 2.1 Create `postman/auth-budget.postman_collection.json` with the chain: register → login (capture JWT) → create budget → add budget line → update budget line → get budget (assert totals reflect lines) → delete budget line → delete budget
- [ ] 2.2 Create `postman/environments/local.postman_environment.json` and `postman/environments/ci.postman_environment.json` (gateway base URL, initially identical values)
- [ ] 2.3 Add unique-fixture-data generation (e.g. `pm.variables.replaceIn('{{$randomUUID}}')` in the register step) so repeated runs never collide
- [ ] 2.4 Add a minimal `postman/package.json` (or documented `npx newman` invocation) so the collection is runnable with no repo-wide install
- [ ] 2.5 Run the collection locally against a `local.sh up` stack and confirm all assertions pass twice in a row with no manual cleanup between runs

## 3. Playwright browser suite (Phase 2)

- [ ] 3.1 Add `@playwright/test` to `frontend-typescript/devDependencies`; scaffold `frontend-typescript/e2e/playwright.config.ts` pointed at `http://localhost:4000`
- [ ] 3.2 Add a thin page-object layer: `e2e/pages/LoginPage.ts`, `e2e/pages/BudgetListPage.ts`, `e2e/pages/BudgetDetailPage.ts`
- [ ] 3.3 Write `e2e/specs/auth-budget-crud.spec.ts`: register/login through the real form, create a budget, add and edit a budget line, verify totals in the UI, delete the budget — using Playwright's auto-waiting assertions only (no manual sleeps)
- [ ] 3.4 Run the spec locally against a `local.sh up` stack and confirm it passes twice in a row with no manual cleanup between runs

## 4. CI wiring

- [ ] 4.1 Create `.github/workflows/e2e.yml` following the existing `dorny/paths-filter` pattern (see `budget.yml`), filtered on `services/users/**`, `services/budget/**`, `shared/**`, `frontend-typescript/**`, plus `workflow_dispatch`
- [ ] 4.2 Add the boot step (`docker compose ... up -d --build` for the scoped service list) and a wait-for-healthy step using the endpoint(s) confirmed in 1.2
- [ ] 4.3 Add the `newman run` step against the `ci` Postman environment
- [ ] 4.4 Add the `npx playwright test` step
- [ ] 4.5 Add an `if: always()` teardown step (`docker compose down -v`) so failed runs don't leak containers/volumes on the runner
- [ ] 4.6 Push a throwaway branch touching `services/budget/**` to confirm the workflow triggers, boots the stack, runs both suites, and tears down correctly; confirm a branch touching only `services/ai/**` does NOT trigger it

## 5. Documentation

- [ ] 5.1 Update root `README.md` (or `docs/setup/`) with a short "Running e2e tests locally" section pointing at `local.sh up`, the Postman collection, and the Playwright suite
- [ ] 5.2 Note the explicit scope boundary (auth + budget CRUD only; AI chat and donor-dashboard excluded until those changes stabilize) so future contributors know where to extend coverage
