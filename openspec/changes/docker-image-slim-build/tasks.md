Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Budget service slim image

- [ ] 1.1 Split `services/budget/requirements.txt`: move `black`, `mypy`, `pytest`, `flake8`, `ipython`, `debugpy`, `faker`, `factory_boy`, `types-requests` (and any other dev/test/lint-only packages) into a new `services/budget/requirements-dev.txt`.
- [ ] 1.2 Update `services/budget/Dockerfile`: change base image to `python:3.13-slim`, add `ARG INSTALL_DEV_DEPS=false`, and conditionally install `requirements-dev.txt` when the arg is true (after the existing `requirements.txt` install step).
- [ ] 1.3 Wire `build.args: { INSTALL_DEV_DEPS: "true" }` for the `budget` service in `docker-compose.dev.yml` and `docker-compose.local.yml`.
- [ ] 1.4 Build the prod variant (`docker-compose.prod.yml` build config) and confirm the image starts, health check passes, and `pip list` shows no dev-only packages.
- [ ] 1.5 Build the dev/local variant and confirm the container starts, health check passes, and `pytest`, `mypy`, `flake8`, `debugpy` are all present and runnable inside it.
- [ ] 1.6 If any package fails to install on the slim base, add the minimal `apt-get` packages needed for that wheel build in the same Dockerfile `RUN` layer (with apt list cleanup) — do not reintroduce the full build toolchain speculatively.
- [ ] 1.7 Run budget service tests/lint clean; PR merged.

## 2. Users service slim image — depends on 1

- [ ] 2.1 Split `services/users/requirements.txt`: move `black`, `mypy`, `pytest`, `flake8`, `ipython`, `debugpy`, `faker`, `factory_boy`, `types-requests` (and any other dev/test/lint-only packages) into a new `services/users/requirements-dev.txt`.
- [ ] 2.2 Update `services/users/Dockerfile`: change base image to `python:3.13-slim`, add `ARG INSTALL_DEV_DEPS=false`, and conditionally install `requirements-dev.txt` when the arg is true (mirroring the budget service pattern from group 1).
- [ ] 2.3 Wire `build.args: { INSTALL_DEV_DEPS: "true" }` for the `users` service in `docker-compose.dev.yml` and `docker-compose.local.yml`.
- [ ] 2.4 Build the prod variant and confirm the image starts, health check passes, and `pip list` shows no dev-only packages.
- [ ] 2.5 Build the dev/local variant and confirm the container starts, health check passes, and `pytest`, `mypy`, `flake8`, `debugpy` are all present and runnable inside it.
- [ ] 2.6 If any package fails to install on the slim base, add the minimal `apt-get` packages needed for that wheel build in the same Dockerfile `RUN` layer (with apt list cleanup).
- [ ] 2.7 Run users service tests/lint clean; PR merged.
