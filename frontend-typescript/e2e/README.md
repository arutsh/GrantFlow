# E2E suite

Playwright suite covering the auth + budget CRUD journey, both at the API layer (`specs/api/`) and through the real browser UI (`specs/browser/`). See `openspec/changes/e2e-test-suite/` for the full proposal/design/tasks.

## Running locally

The suite targets the `docker-compose.local.yml` stack (`./local.sh up`), not `docker-compose.dev.yml` — they're different environments (see the design doc's Decision 1). From the repo root:

```bash
./local.sh up
# once containers are healthy:
npx playwright test --config=frontend-typescript/e2e/playwright.config.ts
```

## Cleanup convention

Each run generates its own unique fixture data (unique emails, etc.), so nothing needs to be cleaned up between runs — but state does accumulate across runs (unnamed volumes persist locally, unlike a fresh CI runner). When you're done iterating locally, tear the stack down and drop its volumes so the next run starts clean:

```bash
docker compose -f docker-compose.local.yml --env-file .env.local down -v
```

This is a manual step, not automated — local iteration benefits from being able to inspect state between runs (e.g. `local.sh down` alone, without `-v`, leaves the data volumes in place). CI always runs against a fresh runner and tears down with `-v` unconditionally (see `.github/workflows/e2e.yml`).

## A note on `local` vs `dev`

`docker-compose.local.yml` and `docker-compose.dev.yml` are separate environments with separate container names, ports, and volumes, so they can run side by side without colliding — you don't need to stop your `dev` stack to run the `local` stack for an e2e run. (`local`'s `users`/`budget` host ports used to collide with `dev`'s MinIO on 9000/9001; they've since been remapped to 9020/9021 to fix that.)

## A note on the frontend's API base URL

The `frontend` service's Vite build inlines `import.meta.env.VITE_API_GATEWAY` at `npm run build` time, inside the Dockerfile's build stage — a `docker-compose environment:` entry never reaches it, since the served output is a static bundle with no process left to read env from at runtime. It has to be passed as a `build.args` entry (`FRONTEND_API_GATEWAY` in `.env.local`, see `docker-compose.local.yml`'s `frontend.build.args`). If you change that value, `docker compose ... up -d --build frontend` (or `./local.sh up`, which always rebuilds) is required — restarting the container alone won't pick it up.
