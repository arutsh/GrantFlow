## Context

`services/budget/Dockerfile` and `services/users/Dockerfile` are near-identical: `FROM python:3.13`, `apt-get install postgresql-client`, then `pip install -r requirements.txt` against a single requirements file shared by prod and dev/local builds. Three compose files (`docker-compose.dev.yml`, `docker-compose.local.yml`, `docker-compose.prod.yml`) build these services to different image tags with no distinction in what gets installed — the prod build carries `black`, `mypy`, `pytest`, `ipython`, `debugpy`, `faker`, `factory_boy`, `flake8`, `types-requests` even though nothing in the prod container ever runs them.

## Goals / Non-Goals

**Goals:**
- Runtime (prod) images contain only what's needed to run the service.
- Dev/local images keep today's dev tooling (tests, linting, debugger) available inside the container.
- Base image is `python:3.13-slim` for both services, reducing base layer size.
- No change to service behavior, environment variables, or entrypoints.

**Non-Goals:**
- No change to the `ai` or `chat` service Dockerfiles (out of scope for this change; can be a follow-up using the same pattern).
- No multi-stage build restructuring beyond what's needed to gate dev deps (not chasing every last MB).
- No change to `docker-compose.prod.yml` deployment target/hosting.

## Decisions

- **Split requirements files over multi-stage Dockerfile targets**: add `requirements-dev.txt` per service (dev-only packages) alongside the now-runtime-only `requirements.txt`, rather than encoding dev/prod split purely as Docker build stages. Simpler to reason about, and compose files already select behavior per-environment via env files — extending that pattern with a build arg is consistent with existing conventions.
  - Alternative considered: multi-stage Dockerfile with a `dev` stage `FROM base` that adds dev deps, prod stops at `base`. Rejected only because it doesn't clearly generalize to "install extra requirements file" without extra `COPY`/`ARG` plumbing — but if the build-arg approach proves awkward during implementation, fall back to this.
- **Build arg `INSTALL_DEV_DEPS`** (default `false`) controls whether `requirements-dev.txt` is installed, set to `true` via `build.args` in `docker-compose.dev.yml` and `docker-compose.local.yml` only. `docker-compose.prod.yml` leaves it at the default.
- **Switch to `python:3.13-slim`** for both Dockerfiles. Slim drops the build toolchain (gcc, g++, autoconf, etc.) and VCS tools (git, mercurial, svn) baked into the full image, which this project doesn't need since `psycopg2-binary`, `numpy`, `pandas`, and other compiled deps in these requirements files ship manylinux wheels. If any package fails to build a wheel on slim, add the minimal required `apt-get install` for that one package in the same `RUN` layer that removes apt lists afterward — don't reintroduce the full build-essential set speculatively.
- **`postgresql-client` install stays as-is** — already scoped correctly.

## Risks / Trade-offs

- [Risk] A transitive dependency lacks a manylinux wheel and needs compilation → build fails on slim. Mitigation: run a build of both images during implementation before merging; if a wheel build fails, add only the specific `apt-get` packages needed (e.g. `gcc`) in the same layer, cleaned up after install.
- [Risk] Debugger/dev workflow inside `docker-compose.dev.yml`/`local.yml` breaks if `requirements-dev.txt` split misses a package a dev script depends on (e.g. `debugpy` for VS Code attach). Mitigation: smoke-test attaching the debugger and running `pytest`/`flake8`/`mypy` inside a dev container after the split.
- [Risk] `docker-compose.prod.yml` build cache invalidation from Dockerfile changes causes one full slow rebuild on next deploy. Mitigation: expected one-time cost, not a recurring issue.

## Migration Plan

1. Create `requirements-dev.txt` for both services, moving dev-only packages out of `requirements.txt`.
2. Update both Dockerfiles: base image → `python:3.13-slim`, add `ARG INSTALL_DEV_DEPS=false` and conditional install step for `requirements-dev.txt`.
3. Wire `build.args: INSTALL_DEV_DEPS: "true"` into `docker-compose.dev.yml` and `docker-compose.local.yml` for the `budget` and `users` services.
4. Build all three variants (prod, dev, local) locally, confirm services start, health checks pass, and dev tooling (pytest/mypy/flake8/debugpy) is present only where expected.
5. No rollback complexity beyond reverting the Dockerfile/compose changes — no data migration involved.

## Open Questions

- Should `services/ai` and `services/chat` get the same treatment in a follow-up change, given they likely share the same pattern? (Assumed yes, but out of scope here — flag for a future ticket.)
