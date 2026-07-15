# GrantFlow Deployment Modes

GrantFlow supports three deployment modes to suit different use cases and deployment targets:

## 1. 🚀 DEV MODE (Development)

**Use case:** Local development with hot-reload capabilities.

**What runs:**
- ✅ PostgreSQL (Docker)
- ✅ Redis (Docker)
- ✅ API Gateway (Docker)
- ✅ Nginx Proxy (Docker)
- ❌ Frontend (runs locally)
- ❌ Users Service (runs locally)
- ❌ Budget Service (runs locally)

**Benefits:**
- Hot-reload for backend code changes
- Frontend assets compiled in real-time
- Faster local development iteration
- Reduced Docker container overhead

### Quick Start

```bash
# Start infrastructure
./dev.sh up

# In separate terminals, start local services:
cd services/users && python -m uvicorn main:app --reload
cd services/budget && python -m uvicorn main:app --reload
cd frontend-typescript && npm run dev
```

### Available Commands

```bash
./dev.sh up           # Start infrastructure
./dev.sh down         # Stop infrastructure
./dev.sh logs         # View logs
./dev.sh status       # Show container status
./dev.sh rebuild      # Rebuild containers without cache
./dev.sh clean        # Stop and remove volumes
```

### Endpoints (Dev Mode)

| Service | URL |
|---------|-----|
| Database | localhost:5432 |
| Redis | localhost:6379 |
| API Gateway | http://localhost:8080 |
| Nginx Proxy | http://localhost:8082 |
| Users Service | http://localhost:8000 |
| Budget Service | http://localhost:8001 |
| Frontend | http://localhost:3000 |

---

## 2. 🏠 LOCAL MODE (Production-like Local)

**Use case:** Complete local testing, demo for non-technical users, CI/CD testing.

**What runs:**
- ✅ PostgreSQL (Docker)
- ✅ Redis (Docker)
- ✅ API Gateway (Docker)
- ✅ Nginx Proxy (Docker)
- ✅ Frontend (Docker)
- ✅ Users Service (Docker)
- ✅ Budget Service (Docker)

**Benefits:**
- Everything runs in Docker
- No local dependencies required
- Production-like environment
- Perfect for demos and non-technical users
- Easy to share and reproduce

### Quick Start

```bash
# Start everything
./local.sh up

# Open browser
open http://localhost:3000
```

### Available Commands

```bash
./local.sh up              # Start all services
./local.sh down            # Stop all services
./local.sh logs [SERVICE]  # View logs (optional: specific service)
./local.sh status          # Show container status
./local.sh rebuild         # Rebuild containers without cache
./local.sh clean           # Stop and remove volumes
./local.sh shell [SERVICE] # Open shell in container
```

### Endpoints (Local Mode)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Nginx Proxy | http://localhost:8082 |
| API Gateway | http://localhost:8080 |
| Users Service | http://localhost:8000 |
| Budget Service | http://localhost:8001 |
| Database | localhost:5432 |

### Database Access (Local Mode)

```
Host: localhost
Port: 5432
User: postgres
Password: postgres
Databases: 
  - grantflow_users
  - grantflow_budget
```

---

## 3. ☁️ CLOUD MODE (SaaS - Future)

**Use case:** Scalable cloud deployment (AWS, Azure, GCP, etc.).

**What runs:**
- Kubernetes or orchestration platform
- Managed databases
- Load-balanced services
- Auto-scaling replicas
- CDN & monitoring

**Status:** 🚧 Under development

### Show Architecture Info

```bash
./cloud.sh info
```

### Future Implementation

The codebase is designed to support cloud deployment:
- ✅ Environment-based configuration
- ✅ Health checks implemented
- ✅ Stateless services
- ✅ Database migrations automated
- 🔄 Kubernetes manifests (TODO)
- 🔄 CI/CD pipelines (TODO)
- 🔄 Infrastructure-as-Code (TODO)

---

## 4. 🖥️ PRODUCTION MODE (OVH VPS)

**Use case:** Real production deployment. Backend runs on a VPS; frontend is hosted separately on Vercel.

**What runs:**
- ✅ PostgreSQL, Redis, RabbitMQ (Docker)
- ✅ Users, Budget, AI services (Docker)
- ✅ Celery worker + beat (Docker)
- ✅ Caddy (Docker) — reverse proxy + automatic Let's Encrypt TLS for `api.opengrantflow.com`
- ❌ Frontend (hosted on Vercel, not part of this stack)

Compose file: `docker-compose.prod.yml`. Reverse proxy config: `Caddyfile`.

### One-time server bootstrap

Deploys log in as a dedicated non-root `deploy` user (sudo + docker group), not root — limits blast radius if the CI deploy key is ever compromised. Run once, by hand, over SSH (as root, with the initial OVH password) as the server is first set up:

```bash
ssh root@51.68.212.86

# Docker + Compose plugin (Ubuntu 26.04)
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin gettext-base ufw

# Firewall — only SSH/HTTP/HTTPS reach this box; everything else
# (Postgres, Redis, RabbitMQ, raw service ports) stays internal to the
# Docker network and is never published to the host.
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable

# Dedicated deploy user — sudo for admin tasks, docker group so it can
# run `docker compose` without sudo.
adduser --disabled-password --gecos "" deploy
usermod -aG sudo,docker deploy

# Authorize the CI deploy key (public half only — safe to paste, it's
# not the secret half) for the deploy user.
mkdir -p /home/deploy/.ssh
cat >> /home/deploy/.ssh/authorized_keys <<'PUBKEY'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFwx+pb2+mTW+jIVitpWIZ9ZRUvnv4mqWKQDxrDmHKrd github-actions-deploy@grantflow
PUBKEY
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# Clone the repo as the deploy user — this checkout is deploy-only. The
# GitHub Actions deploy workflow runs `git reset --hard` against it on
# every push to main, so never hand-edit files here.
mkdir -p /opt/grandflow
chown deploy:deploy /opt/grandflow
su - deploy -c "git clone https://github.com/arutsh/GrantFlow.git /opt/grandflow"
```

Verify from your own machine before relying on it: `ssh -i <path-to-private-key> deploy@51.68.212.86` should log in with no password prompt.

### DNS

Add an A record at your registrar (no Terraform — see the deploy ticket's notes on why): `api.opengrantflow.com` → `51.68.212.86`. Give it a few minutes to propagate before the first deploy, since Caddy requests a Let's Encrypt cert on first boot and needs the domain to already resolve.

### GitHub Actions secrets required

All set already (generated during Ticket 1/2 hardening): `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `RABBITMQ_USER`, `RABBITMQ_PASS`, `RABBITMQ_URL`, `USERS_DATABASE_URL`, `BUDGET_DATABASE_URL`, `AI_DATABASE_URL`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `VPS_HOST` (`51.68.212.86`), `VPS_USER` (`deploy`), `VPS_SSH_KEY` (private half of the deploy keypair; public half goes in `deploy`'s `authorized_keys` above, generated once and never reused elsewhere).

### Ongoing deploys

Every push to `main` triggers `.github/workflows/deploy.yml`, which SSHes in, resets the checkout to `origin/main`, regenerates the real `.env.prod` / `services/*/.env.*.prod` files in place from the secrets above (the committed versions are `${VAR}` templates, never real values), and runs:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Manual redeploy (e.g. to pick up a secret rotation without a new commit): re-run the workflow from the Actions tab (`workflow_dispatch`).

---

## Switching Between Modes

### Dev → Local

```bash
# Stop dev infrastructure
./dev.sh down

# Start local mode
./local.sh up
```

### Local → Dev

```bash
# Stop local stack
./local.sh down

# Start dev infrastructure
./dev.sh up
```

---

## Performance & Caching

All modes use Docker BuildKit with persistent cache mounts for faster builds:

```bash
DOCKER_BUILDKIT=1 docker compose build
```

**Benefits:**
- Python packages cached between builds
- No re-downloading of pip dependencies
- Builds ~10x faster on subsequent runs

---

## Troubleshooting

### Services won't start (Dev Mode)

**Problem:** Services exit immediately

**Solution:**
```bash
# Check logs
./dev.sh logs

# Make sure DB is healthy
docker compose -f docker-compose.dev.yml exec grantflow-db pg_isready
```

### Port already in use

**Solution:**
```bash
# Find service using port
lsof -i :8000

# Or use different dev file
docker compose -f docker-compose.dev.yml down
```

### Rebuild without cache

All modes support clean rebuild:

```bash
# Dev mode
./dev.sh rebuild

# Local mode
./local.sh rebuild
```

### Reset everything

```bash
# Dev mode
./dev.sh clean

# Local mode
./local.sh clean
```

---

## Default Environment Files

Each mode uses environment files for configuration:

- **Dev Mode:** `.env.*.dev` files
- **Local Mode:** `.env.*.dev` files
- **Production Mode:** `.env.prod` / `.env.*.prod` files — committed as `${VAR}` templates, real values generated in place on the server from GitHub Actions secrets at deploy time (see section 4)
- **Cloud Mode:** To be defined per cloud provider

Example:
```
./services/users/.env.users.dev
./services/budget/.env.budget.private.dev
./api-gateway/.env.gateway.dev
```

---

## Architecture Comparison

| Feature | Dev | Local | Cloud |
|---------|-----|-------|-------|
| Hot-reload | ✅ | ❌ | ❌ |
| Docker only | ❌ | ✅ | ✅* |
| Local deps | ✅ | ❌ | ❌ |
| Scale-ready | ❌ | ❌ | ✅ |
| Non-tech user | ❌ | ✅ | ✅ |
| Dev speed | ⚡⚡ | ⚡ | 🔄 |

*Cloud mode requires cloud provider setup

---

## For Maintainers

### Modifying Docker Compose Files

1. **Dev mode:** `docker-compose.dev.yml`
2. **Local mode:** `docker-compose.local.yml`
3. **Cloud mode:** Define `docker-compose.cloud.yml` or K8s manifests

### Adding New Services

If adding a new service:
1. Add to `docker-compose.dev.yml` for dev testing
2. Add to `docker-compose.local.yml` for production-like local
3. Keep services stateless for cloud portability

### Environment Variables

Use `env_file` directive in compose files:
```yaml
env_file:
  - ./services/users/.env.users.dev
```

Keep `.env` files in `.gitignore` and provide `.env.example` templates.

---

## Quick Reference

```bash
# Start developing
./dev.sh up

# Run services locally (in separate terminals)
cd services/users && python -m uvicorn main:app --reload
cd services/budget && python -m uvicorn main:app --reload
cd frontend-typescript && npm run dev

# Test local mode
./local.sh up

# Check cloud readiness
./cloud.sh info
```
