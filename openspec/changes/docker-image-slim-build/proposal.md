## Why

The `budget` and `users` service images are built `FROM python:3.13` (the full Debian variant) with a single `requirements.txt` that mixes runtime dependencies with dev-only tooling (`black`, `mypy`, `pytest`, `flake8`, `ipython`, `debugpy`, `faker`, `factory_boy`, `types-requests`). The `pip install` layer alone is 5.6GB in the budget image, and the prod-tagged build (used by `docker-compose.prod.yml`) ships all dev tooling too, producing ~7GB images that are near-duplicates of the separately-built local/dev images. This wastes disk (dangling images pile up on every rebuild across three compose files) and slows builds/pulls/deploys.

## What Changes

- Split `services/budget/requirements.txt` and `services/users/requirements.txt` into a runtime-only `requirements.txt` and a new `requirements-dev.txt` holding dev/test/lint tooling.
- Switch both Dockerfiles' base image from `python:3.13` to `python:3.13-slim`.
- Add a build arg/stage so `requirements-dev.txt` is installed only for dev/local builds (`docker-compose.dev.yml`, `docker-compose.local.yml`), never for the prod build (`docker-compose.prod.yml`).
- Re-verify each package in both requirements files still installs cleanly on the slim base (most ship prebuilt wheels; add back a minimal build toolchain only if a specific wheel build fails, and remove it in the same layer).

## Capabilities

### New Capabilities
- `docker-image-build`: build-time requirements for the budget and users service images — base image choice, and separation of runtime vs. dev-only dependencies between prod and dev/local builds.

### Modified Capabilities
(none — no application-level requirement changes)

## Impact

- Affected files: `services/budget/Dockerfile`, `services/users/Dockerfile`, `services/budget/requirements.txt`, `services/users/requirements.txt` (split), new `services/budget/requirements-dev.txt` and `services/users/requirements-dev.txt`, and `docker-compose.dev.yml`/`docker-compose.local.yml`/`docker-compose.prod.yml` (build args/target wiring).
- No API or runtime behavior change expected. Risk: base image switch must not break service startup, health checks, or existing dev workflows (e.g. `debugpy`/`pytest` availability inside dev containers).
- Expected outcome: smaller prod images (no dev tooling), smaller dev images (slim base), fewer/no near-duplicate multi-GB images, less disk churn from rebuilds.
