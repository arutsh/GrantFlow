One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Data Retention — AI Audit & Chat Message Purge Jobs

- [ ] 1.1 Add `cleanup_ai_audit_logs` Celery beat task (`services/worker/tasks/`) that redacts/removes `AIAuditLog.input_text` past a configurable retention window, keeping metadata fields
- [ ] 1.2 Add `cleanup_chat_messages` Celery beat task that purges `chat.Message` rows for conversations inactive past a configurable window
- [ ] 1.3 Register both tasks in `services/worker/celery_app.py`
- [ ] 1.4 Add unit tests for both jobs: records past the window are purged/redacted, records within the window are untouched
- [ ] 1.5 Run worker-service tests clean; PR merged

## 2. Backup & Recovery for Production Database

- [ ] 2.1 Write a scheduled `pg_dump`-based backup script that encrypts the artifact and uploads it to the existing S3/MinIO-compatible storage
- [ ] 2.2 Schedule the backup job (GitHub Actions cron or equivalent) and document RPO/RTO in `docs/`
- [ ] 2.3 Perform and document a restore drill: restore the latest backup to a scratch database and verify data integrity
- [ ] 2.4 Add alerting/notification for backup job failure
- [ ] 2.5 Run the backup and restore scripts end-to-end against a non-production database; PR merged

## 3. Internal Transport Encryption

- [ ] 3.1 Enable TLS (or mTLS) for Caddy's internal `reverse_proxy` hops to `users`/`budget`/`ai`/`chat` services
- [ ] 3.2 Update `Caddyfile`, and mirror the equivalent config in `nginx.conf`/`nginx-dev.conf` where applicable, per the existing three-gateway-config pattern
- [ ] 3.3 Verify inter-service requests fail closed (not silently fall back to plaintext) if the internal TLS handshake fails
- [ ] 3.4 Deploy to a staging/prod-like environment and confirm all services remain reachable; PR merged

## 4. CI Dependency Vulnerability Scanning

- [ ] 4.1 Add `.github/dependabot.yml` covering each service's Python dependency file and `frontend-typescript/package.json`
- [ ] 4.2 Configure scan frequency and PR grouping to avoid noise across the 8 existing per-service workflows
- [ ] 4.3 Triage and resolve or explicitly defer (with a tracked ticket) any vulnerabilities surfaced by the initial scan
- [ ] 4.4 PR merged
