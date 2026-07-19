## Context

`services/budget` currently models planned spend only (`Budget` → `BudgetLine` → `BudgetCategory`, sync SQLAlchemy, `AuditMixin`, GUID PKs — see `app/models/budget.py`). There is no `Grant` model in the repo; `Budget` itself represents the grant, with `owner_id` (grantee) and `funding_customer_id`/`external_funder_name` (funder) as cross-service UUID references (no FK — validated over HTTP via `customer_client.py`), not SQL relationships. No report/expense/receipt/payment/attachment concept, and no file-storage abstraction, exists anywhere in the repo today — the only precedent is `UploadedTemplateModel.file_path`, a hardcoded local path string with no abstraction behind it. Infra is Hetzner-only (Terraform), with no AWS/GCP/Azure object storage provisioned, so cloud-agnosticism is a real constraint, not aspirational. This capability lives entirely inside `services/budget` (explicit decision — no new microservice), following that service's existing conventions rather than the async pattern used by `services/chat`/`services/ai`.

## Goals / Non-Goals

**Goals:**
- Let a grantee submit report lines (receipts/payments) against specific budget lines, grouped into a report with a review workflow.
- Support multiple file attachments per report line via a storage layer with zero cloud-provider lock-in.
- Enforce evidence integrity: submitted/approved reports lock their lines and attachments from further edits.
- Enforce a real reviewer role: only the funder (`budget.funding_customer_id`) may approve/reject.

**Non-Goals:**
- Budget-line overspend validation (checking report-line totals against a budget line's planned `amount`) — schema supports it later without migration, but no enforcement ships in this change.
- Presigned/direct-to-storage uploads — all uploads proxy through the FastAPI app.
- Virus/malware scanning of uploaded files.
- A general-purpose reviewer/role system beyond the single funder-vs-owner distinction that already exists on `Budget`.

## Decisions

**Storage: `shared/storage/` built on `fsspec`, not a hand-rolled interface or a specific cloud SDK.**
`fsspec` is already present transitively (via ML dependencies) and provides a maintained, real cross-backend filesystem interface (`file://` today, `s3://`/`gs://`/`az://` later via install-time extras) — reusing it avoids reinventing a worse version of the same abstraction. This change promotes it to a direct, intentional dependency in `services/budget/requirements.txt` rather than leaving it as an accidental transitive one tied to unrelated ML-library churn. Default backend URI is `file:///app/uploads/reports`, a subdirectory of the already bind-mounted `uploads/` volume — no docker-compose changes needed; the storage service lazily creates the subdirectory on first `save()`.

**Uploads proxy through the app; no presigned URLs.**
Presigned URLs earn their complexity when there's a real object-store endpoint to presign against and upload volume is large enough that app-proxy bandwidth matters. Neither is true here (Hetzner disk today, receipt/invoice-scale files). Proxying keeps size/content-type validation and auth in one place. Revisit only if real object storage is provisioned and volume grows.

**Retrieval is a streaming download route behind auth, not a public/signed URL.**
`GET /attachments/{id}/content` re-checks the same ownership chain (attachment → report line → report → budget → owner/funder) used everywhere else in the service, rather than issuing a URL that bypasses that check.

**Reviewer authorization: funder-only (`budget.funding_customer_id`).**
Budget already distinguishes owner (grantee) from funder (donor). Approval by the party actually disbursing funds matches the real-world grant reporting relationship and avoids an NGO self-approving its own report. Considered "any authenticated user with budget access can approve" — rejected because it defeats the purpose of a review step.

**Lock-on-submit: `ReportLine`s (and attachments) become read-only once a `Report` leaves `draft`; `rejected → draft` reopens for edits.**
Preserves audit integrity of submitted evidence. A rejection is the only path back to an editable state, avoiding silent post-submission edits to what a funder is reviewing.

**Upload limits enforced from day one: 15MB max, content-type allowlist (PDF/JPEG/PNG/HEIC).**
No file-validation precedent exists anywhere in the repo (`python-multipart` is installed but nothing enforces limits today). Given this is a compliance-facing surface accepting arbitrary user-supplied files, shipping without limits was rejected as too large a risk to defer.

**Schema mirrors `Budget`/`BudgetLine`/`BudgetCategory` exactly**, rather than introducing a different modeling style: `ReportModel`/`ReportLineModel`/`AttachmentModel`, sync SQLAlchemy, `AuditMixin`, GUID PKs, one bundled Alembic migration (consistent with how the initial migration bundles all budget tables together, since none of the three new tables is independently useful).

## Risks / Trade-offs

- **[Risk]** No overspend enforcement — users will likely expect it immediately after this ships, given the worked example (£1000 admin cost line, multiple receipts). → **Mitigation**: schema (`ReportLine.budget_line_id` + `.amount`) supports computing totals later without a migration; flagged as an immediate fast-follow, not silently dropped.
- **[Risk]** No two-phase commit between the Postgres attachment row and the blob in storage — a delete or upload failure partway through can leave an orphaned blob or a dangling row. → **Mitigation**: acceptable for v1 given local-disk storage and low volume; note need for a periodic reconciliation job if this becomes an issue.
- **[Risk]** The `uploads/` bind mount is not currently part of any backup/DR story on Hetzner, and will now hold compliance-relevant receipts. → **Mitigation**: flagged explicitly as an infra follow-up, out of scope for this change.
- **[Trade-off]** Proxying all uploads through the FastAPI app instead of presigned direct-upload adds app-server bandwidth/memory pressure for large files. Accepted given expected file sizes (receipts/invoices, capped at 15MB) and no object-store endpoint to presign against today.

## Migration Plan

One new Alembic revision chained off the current head (`000002_add_ai_draft_budget_status`), adding `reports`, `report_lines`, `attachments` in a single migration (`downgrade()` drops in reverse order). No data backfill needed — purely additive tables. Rollback is a straight `alembic downgrade -1`.

## Open Questions

- Exact table name for the attachment entity (`attachments` vs `report_line_attachments`) — leaning `attachments` as the more generic, less scope-implying name; not a blocking decision.
- Whether budget-line overspend validation should become a hard cap or just a warning when it is eventually built — deferred to that fast-follow's own design.
