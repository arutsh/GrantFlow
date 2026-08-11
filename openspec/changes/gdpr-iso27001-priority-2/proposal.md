## Why

Beyond the user-facing rights and access-control fixes in priority 1, the audit found no retention limit on stored chat/AI-prompt content, no production database backup or restore procedure, no encryption for internal service-to-service traffic, and no automated dependency-vulnerability scanning in CI. These are ISO 27001 operational baseline items (A.12, A.13, A.17) — not blocking the public GDPR claim priority 1 unlocks, but required for a credible "ISO 27001-aligned" posture and for basic production resilience (an unrecoverable DB today is a business risk independent of any compliance framework).

## What Changes

- Add automated retention/purge for `AIAuditLog.input_text`, chat `Message`/`Conversation` rows, and expired sessions, beyond the existing 30-day AI-session job.
- Add production Postgres backup/restore procedure and document RPO/RTO.
- Add dependency/SAST scanning (Dependabot or equivalent) to CI across all service workflows.
- Enable TLS/mTLS for internal service-to-service traffic behind Caddy (currently plain HTTP inside the Docker network).

## Capabilities

### New Capabilities
- `data-retention-policy`: automated, configurable purge of chat messages, AI audit prompt text, and expired sessions.
- `compliance-operations`: production backup/restore procedure, CI dependency/SAST scanning, internal service-to-service TLS.

### Modified Capabilities
(none — all changes are additive; no existing spec's requirements are being altered)

## Impact

- **services/ai**: `models/audit_log.py` retention job, new Celery beat task alongside `cleanup_sessions.py`.
- **services/chat**: retention job for `Message`/`Conversation`.
- **services/worker**: `celery_app.py` beat schedule registration.
- **Infra/CI**: all `.github/workflows/*.yml` (add scanning step), `terraform/` or deploy scripts (backup schedule), `Caddyfile`/`nginx.conf`/`nginx-dev.conf` (internal TLS).
- **New docs**: backup/restore runbook, RPO/RTO documentation.

## Dependencies

None on `gdpr-iso27001-priority-1` — this change is independently mergeable and can proceed in parallel.
