## Context

This is priority 2 of a two-part compliance program (see `gdpr-iso27001-priority-1` for the user-facing/access-control half, which this does not depend on). It covers the operational/ISO 27001 baseline: retention limits, backups, internal transport security, and dependency scanning — items that matter for real compliance readiness and production resilience but aren't what an outside party would check first.

## Goals / Non-Goals

**Goals:**
- Bound the retention of raw AI chat content and chat messages the same way `cleanup_sessions.py` already bounds AI sessions.
- Close the production single-point-of-failure gap: there is currently no backup of the production database at all.
- Encrypt internal service-to-service traffic, currently plain HTTP inside the Docker network.
- Get automated visibility into vulnerable dependencies instead of relying on manual awareness.
- Reuse existing patterns (Celery beat jobs, GitHub Actions, the three-gateway-config setup) rather than introducing new infrastructure.

**Non-Goals:**
- Data-subject rights, consent, session security, password policy — tracked in `gdpr-iso27001-priority-1`.
- Migrating to a managed Postgres service with built-in backups/PITR (flagged as a possible future replacement for the `pg_dump` approach here, not undertaken in this change).
- Full field-level encryption-at-rest for all PII.

## Decisions

**1. Retention jobs follow the existing `cleanup_sessions.py` Celery-beat pattern exactly.**
New beat tasks `cleanup_ai_audit_logs` (purge/redact `AIAuditLog.input_text` after N days, configurable via env, default 90) and `cleanup_chat_messages` (purge `chat.Message` rows after N days of conversation inactivity) are added next to the existing job in `services/worker/tasks/`, scheduled in `services/worker/celery_app.py`. Chosen over ad-hoc cron/scripts because the beat scheduler and its observability (logging, retries) already exist and are proven for exactly this kind of job. No dry-run/staged rollout — there's no production chat or audit data yet, so the jobs enable real deletion from the first deploy.

**2. Backups via `pg_dump` + off-host storage, not managed DB failover.**
A scheduled job (GitHub Actions cron or a script triggered from the existing deploy pipeline) runs `pg_dump`, encrypts the artifact, and ships it to the S3/MinIO-compatible storage already integrated for attachments (`cloud-agnostic-storage` capability). Rejected: migrating to a managed Postgres (Hetzner managed DB, RDS) with built-in backups — bigger infra change, out of scope here; can be revisited later.

**3. Internal TLS via Caddy, mirrored across all three gateway configs.**
Enable TLS (or mTLS) for Caddy's internal `reverse_proxy` hops to `users`/`budget`/`ai`/`chat`. This repo maintains three parallel gateway configs (`nginx-dev.conf`, `nginx.conf`, `Caddyfile` — per existing project memory, easy to update one and forget the others), so this must be applied consistently across all three, with dev/local configs allowed to stay plain HTTP since they don't cross a real network boundary.

**4. Dependency scanning via GitHub Dependabot config, not a custom CI step.**
A single `.github/dependabot.yml` covering all `requirements*.txt`/`pyproject.toml` per service plus `frontend-typescript/package.json` is lower-maintenance than wiring `safety`/`npm audit` into 8 separate workflow files, and produces PRs directly.

## Risks / Trade-offs

- [Retention purge of `AIAuditLog.input_text` reduces forensic/debugging value of that audit trail] → Mitigation: redact/hash instead of hard-delete where feasible, keep metadata (timestamps, user id, token counts) indefinitely, only the raw text is time-boxed.
- [`pg_dump`-based backup has no tested restore procedure yet] → Mitigation: tasks include an explicit restore-drill task, not just "write a backup script."
- [Internal TLS adds certificate management complexity inside the Docker network] → Mitigation: use Caddy's internal CA (already used for its external auto-HTTPS) rather than standing up a separate PKI.
- [Forgetting to mirror a gateway-config change across all three files (a known recurring mistake in this repo)] → Mitigation: task list explicitly calls out updating all three configs as one task, not three separate ones.

## Migration Plan

No production users or production data exist yet, so there's no live data at risk from these jobs running immediately — this ships as a direct cutover, not a phased rollout.

1. Retention jobs ship enabled from the first deploy; validate purge logic against a seeded/staging dataset before merging, since there's no dry-run safety net in prod.
2. Backup job ships and runs for at least one full cycle with a verified restore drill before being considered "done."
3. Internal TLS rollout: stand up certs and verify inter-service connectivity in a staging/prod-like environment before merging the config change that removes the plain-HTTP fallback.
4. Rollback: infra config changes (TLS, backups, retention schedule) revert via git if issues arise.

## Open Questions

- What retention window (days) is actually appropriate for `AIAuditLog.input_text` and chat messages? Default of 90 days proposed — needs a product/legal decision, not just an engineering one.
- Is a managed Postgres migration planned soon enough that the `pg_dump` approach here is worth building, or should backup work wait for that migration?
