## ADDED Requirements

### Requirement: Runtime images exclude dev-only dependencies
The `budget` and `users` service Docker images built for production (`docker-compose.prod.yml`) SHALL install only runtime dependencies (`requirements.txt`). Dev-only tooling (`black`, `mypy`, `pytest`, `flake8`, `ipython`, `debugpy`, `faker`, `factory_boy`, `types-requests`) SHALL live in a separate `requirements-dev.txt` and SHALL NOT be installed in the prod build.

#### Scenario: Building the prod image
- **WHEN** `docker-compose.prod.yml` builds the `budget` or `users` service
- **THEN** the resulting image's Python environment contains the packages listed in `requirements.txt` and does not contain any package listed only in `requirements-dev.txt`

### Requirement: Dev and local images retain dev tooling
The `budget` and `users` service images built for dev/local workflows (`docker-compose.dev.yml`, `docker-compose.local.yml`) SHALL install both `requirements.txt` and `requirements-dev.txt`, preserving today's ability to run tests, linting, type-checking, and the debugger inside the container.

#### Scenario: Building the dev image
- **WHEN** `docker-compose.dev.yml` or `docker-compose.local.yml` builds the `budget` or `users` service
- **THEN** the resulting image's Python environment contains all packages from both `requirements.txt` and `requirements-dev.txt`

#### Scenario: Running tests inside the dev container
- **WHEN** a developer runs `pytest`, `mypy`, or `flake8` inside a container built from `docker-compose.dev.yml` or `docker-compose.local.yml`
- **THEN** the command runs successfully because the corresponding tool is installed

### Requirement: Base image is python:3.13-slim
The `budget` and `users` service Dockerfiles SHALL use `python:3.13-slim` as the base image instead of the full `python:3.13` image, and SHALL only add system packages beyond `postgresql-client` if a specific dependency's wheel build requires them.

#### Scenario: Building either image variant
- **WHEN** any of the three compose files builds the `budget` or `users` service
- **THEN** the build succeeds using `python:3.13-slim` as the base image and the resulting container starts and passes its health check

## MODIFIED Requirements

(none — no existing requirements changed)
