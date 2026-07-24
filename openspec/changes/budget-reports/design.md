## Context

`services/budget` currently models planned spend only (`Budget` → `BudgetLine` → `BudgetCategory`, sync SQLAlchemy, `AuditMixin`, GUID PKs — see `app/models/budget.py`). There is no `Grant` model in the repo; `Budget` itself represents the grant, with `owner_id` (grantee) and `funding_customer_id`/`external_funder_name` (funder) as cross-service UUID references (no FK — validated over HTTP via `customer_client.py`), not SQL relationships. No report/expense/receipt/payment/attachment concept, and no file-storage abstraction, exists anywhere in the repo today — the only precedent is `UploadedTemplateModel.file_path`, a hardcoded local path string with no abstraction behind it. Infra is Hetzner-only (Terraform), with no AWS/GCP/Azure object storage provisioned, so cloud-agnosticism is a real constraint, not aspirational. This capability lives entirely inside `services/budget` (explicit decision — no new microservice), following that service's existing conventions rather than the async pattern used by `services/chat`/`services/ai`.

## Goals / Non-Goals

**Goals:**
- Let a grantee submit report lines (receipts/payments) against specific budget lines, grouped into a report with a review workflow.
- Support multiple file attachments per report line via a storage layer with zero cloud-provider lock-in.
- Enforce evidence integrity: submitted/approved reports lock their lines and attachments from further edits.
- Enforce a real reviewer role: only the funder (`budget.funding_customer_id`) may approve/reject.
- Track the grantee's actual local currency and this specific contract's wire-transfer currency independently, backed by an auditable conversion ledger — not a single project-wide FX rate — so reported amounts always reconcile against real bank transactions.

**Non-Goals:**
- Budget-line overspend validation (checking report-line totals against a budget line's planned `amount`) — schema supports it later without migration, but no enforcement ships in this change.
- Presigned/direct-to-storage uploads — all uploads proxy through the FastAPI app.
- Virus/malware scanning of uploaded files.
- A general-purpose reviewer/role system beyond the single funder-vs-owner distinction that already exists on `Budget`.
- Automatic multi-hop rollup or currency conversion across a funding chain (grantee → donor → donor's own upstream funder). Linking a report line to the downstream report backing it is supported (`ReportLine.source_report_id`), but deciding what amount/description represents that downstream activity in the intermediate donor's own report is a manual decision by that donor, not something the system computes.
- A second, donor-specific ledger mechanism — not needed. See the "reused, not duplicated" decision below.

## Decisions

**Storage: `shared/storage/` built on `boto3` against an S3-compatible backend, not `fsspec` or a hand-rolled multi-protocol interface.**
`fsspec`'s generality (`file://`, `s3://`, `gs://`, `az://`, `sftp`, ...) solves a broader problem than this project has — nothing here needs GCS or Azure, and testing against `fsspec`'s `file://` backend locally wouldn't exercise the same code path that runs against a real object store in production. Narrowing to "any S3-compatible provider" (AWS S3, MinIO, Cloudflare R2, Backblaze B2, ...) via a thin `boto3`-backed `StorageService` keeps the abstraction genuinely simple — one client type, real S3 semantics exercised in every environment including local dev — while staying just as vendor-agnostic in the sense that actually matters: no single provider lock-in. All `boto3` calls are confined to `shared/storage/storage_service.py`; nothing else in the repo imports `boto3` directly, so callers only ever see `save`/`open_stream`/`delete`/`exists`.

**Local dev runs MinIO via docker-compose; production targets Cloudflare R2.**
A `open-grantflow-reports` bucket already exists on Cloudflare R2's free tier. Both MinIO and R2 speak the S3 API, so the same `boto3` client code path runs unmodified in both environments — only `STORAGE_ENDPOINT_URL`/`STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY`/`STORAGE_BUCKET_NAME` differ between `.env.budget.*` files. This trades "zero external services needed for local dev" (the original `fsspec`/`file://` design's main property) for dev/prod parity — accepted deliberately, since exercising real S3 semantics locally catches bugs a local-filesystem stand-in would otherwise hide until production. The storage service lazily creates the configured bucket on first `save()` if it doesn't already exist.

**Uploads proxy through the app; no presigned URLs (v1).**
A real S3-compatible endpoint now exists (MinIO locally, Cloudflare R2 in production), so the original "no object-store endpoint to presign against" half of this decision's rationale no longer holds. Proxying still keeps size/content-type validation and auth in one place, and receipt/invoice-scale upload volume doesn't yet justify a presigned-URL auth scheme (signed tokens, a frontend upload-then-confirm flow). Direct-to-bucket presigned upload and download is now a concrete, well-motivated fast-follow rather than a hypothetical one — deferred to keep this version simple, not because it lacks a real target to presign against.

**Retrieval is a streaming download route behind auth, not a public/signed URL.**
`GET /attachments/{id}/content` re-checks the same ownership chain (attachment → report line → report → budget → owner/funder) used everywhere else in the service, rather than issuing a URL that bypasses that check.

**Reviewer authorization: funder-only (`budget.funding_customer_id`), falling back to the budget owner when no funder exists.**
Budget already distinguishes owner (grantee) from funder (donor). Approval by the party actually disbursing funds matches the real-world grant reporting relationship and avoids an NGO self-approving its own report — whenever a real in-system funder exists. But `Budget.funding_customer_id` is optional: `Budget.external_funder_name` already covers the case where the funder isn't a system user at all (a grantee tracking their own budget/reports for later export to a donor template, a not-yet-built feature). For those budgets, the owner is the only party who could ever review a report, so the owner self-reviews instead. No role-based restriction on this fallback in v1 — deferred to a future iteration once a finer-grained role model exists for grantee-side users (today the service only distinguishes `superuser` from everyone else). Considered "any authenticated user with budget access can approve" as the general rule — rejected because it defeats the purpose of a review step whenever a real funder does exist.

**Report cardinality: multiple `Report`s may exist per `Budget`, constrained by non-overlapping reporting periods rather than by status.**
An earlier version of this design considered "at most one active (non-terminal) report per budget," but that blocks a normal workflow: a grantee submitting an interim report and immediately starting to draft the next period's report while the first is still under review. The real constraint is periods, not statuses — two reports for the same budget may coexist in any combination of statuses as long as their `period_start`/`period_end` ranges don't overlap. A rejected report still "owns" its period until reopened and edited; a grantee resolves a rejection by fixing the existing report, not by forking a new one over the same span, keeping one continuous evidence trail per period. Enforced at the application layer (not a DB exclusion constraint) for v1 — see Risks.

**Report period is required, defaulting to the budget's full span.**
Requiring an explicit period on every report would burden the common case — most budgets only ever have one report, covering the whole grant. Defaulting `period_start`/`period_end` to `budget.start_date` through `budget.start_date + duration_months` when omitted means a grantee filing a single whole-project report never has to think about periods at all — the non-overlap rule then naturally reduces to "at most one report" for them, since a second report of any period would overlap the first's full-span claim. Grantees who want interim/final splits just narrow the period explicitly; the same rule permits it.

**Report creation requires `Budget.status == confirmed`.**
Reports should not be created against a budget whose planned amounts are still mutable (`draft`/`ai_draft`) or already closed out (`archived`). This is the first place `confirmed` status gates any behavior in the budget service — today it exists purely as an enum value with no enforcement anywhere else.

**New `Budget.start_date` field, required by application logic (not a DB constraint) before a budget can be confirmed.**
Needed to compute the default report period above. Kept nullable at the DB level so it doesn't break existing `draft`/`ai_draft` budgets that predate this field; enforced instead at the point a budget transitions to `confirmed`, mirroring how other "required for state X" business rules are handled here rather than a blanket NOT NULL.

**Lock-on-submit: `ReportLine`s (and attachments) become read-only once a `Report` leaves `draft`; `rejected → draft` reopens for edits.**
Preserves audit integrity of submitted evidence. A rejection is the only path back to an editable state, avoiding silent post-submission edits to what a funder is reviewing.

**Upload limits enforced from day one: 15MB max, content-type allowlist (PDF/JPEG/PNG/HEIC).**
No file-validation precedent exists anywhere in the repo (`python-multipart` is installed but nothing enforces limits today). Given this is a compliance-facing surface accepting arbitrary user-supplied files, shipping without limits was rejected as too large a risk to defer.

**Schema mirrors `Budget`/`BudgetLine`/`BudgetCategory` exactly**, rather than introducing a different modeling style: `ReportModel`/`ReportLineModel`/`AttachmentModel`, sync SQLAlchemy, `AuditMixin`, GUID PKs, one bundled Alembic migration (consistent with how the initial migration bundles all budget tables together, since none of the three new tables is independently useful).

**Currency ledger: `FundingReceipt` → `CurrencyConversion` → FIFO consumption by `ReportLine`, not a single stored FX rate.**
A worked real-world example (a grantee receiving EUR from a donor, converting to local currency in irregular tranches at whatever rate the bank offered that day) showed that a single project-wide exchange rate can never reconcile against real bank records — the grantee ends up reverse-engineering a "fake fixed rate" (spent-local ÷ received-donor-currency) just to make a summary sheet balance, which is exactly the discrepancy this design needs to eliminate. Instead: `FundingReceiptModel` records a donor-currency payment landing (`amount`, `received_at`); `CurrencyConversionModel` records a real bank FX event (`donor_amount` converted, `local_amount` received, `converted_at` — the rate is derived from these two, never entered directly); expenses (`ReportLine`) draw down against unconsumed conversion lots FIFO (oldest first), splitting across lots via a hidden allocation join row when one expense straddles two lots. The reported donor-currency equivalent of any expense is then always exactly reconstructible from real bank transactions.

**Overspend against unconverted balance is allowed to go negative.**
Grantees legitimately spend ahead of converting more money (e.g. weekend spending when bank conversion is only available the next business day). Blocking the expense would misrepresent real cash-flow timing. The FIFO balance can go negative and trues up automatically on the next `CurrencyConversion`.

**`Budget.actual_currency` (new field) alongside the existing `Budget.local_currency`; no fixed/global bridge currency.**
`local_currency` already correctly scopes per-`Budget` rather than per-customer (the same grantee can run different budgets in different countries/currencies). `actual_currency` is the wire-transfer currency for this specific budget/contract — freely chosen per contract, not a project-wide constant. Confirmed by a real three-budget chain example where the grantee-donor leg transferred in EUR but the donor's own upstream leg's wire currency was contract-specific and undetermined in advance ("whatever they decide") — so no code should assume EUR, or any single currency, bridges every contract.

**Donor's own reporting currency is derived via optional `Budget.parent_budget_id`, never stored redundantly.**
When an intermediate donor is itself a sub-grantee of another, upstream donor (i.e. they have their own `Budget` in the system representing that upstream contract), the "donor's currency" shown on the downstream budget is simply `parent_budget.local_currency` — confirmed by a concrete example where the upstream contract's `local_currency` (SEK) exactly equalled what the two downstream contracts would separately need to show as "donor's currency." Storing that value redundantly on every downstream budget would drift silently if the upstream contract's currency ever changed; deriving it through the link cannot drift. When no `parent_budget_id` is set — no upstream hop tracked in the system — there is simply no third currency to display, matching that this figure is never actually used for grantee-facing reporting today.

**Cross-hop rollup is manual; `ReportLine.source_report_id` is a traceability link only, with zero computed logic.**
An intermediate donor decides by hand what line, amount, and description represents a downstream grantee's approved report inside their own upstream report — the system does not auto-aggregate or auto-convert amounts across hops. `ReportLine` gains an optional `source_report_id` (nullable FK to another `Report`) so that link can be recorded as backing evidence (alongside or instead of a file attachment). Rejected building automatic cascading rollup because hop depth is unbounded in principle, and each intermediate donor may have their own accounting policy for characterizing downstream spend in their own books — a business decision by that donor, not something this system should compute on their behalf.

**Multi-currency aggregation always groups by currency; never coerces to one.**
Already-shipped precedent (PR #141, `total_allocated_by_currency` on the donor-dashboard summary endpoints) fixed exactly this bug class: summing amounts across a currency-varying set and mislabeling the result with an arbitrary currency. The same rule applies to every new aggregation this change introduces (receipts, conversions, cross-budget rollups) — always list per-currency, never silently blend.

**The currency ledger is reused, not duplicated, at every hop of a funding chain.**
`FundingReceiptModel`/`CurrencyConversionModel` are scoped to a `Budget`, not to a "grantee" role. An intermediate donor's own upstream contract (e.g. Donor1↔Donor2) is just another `Budget` with the same `local_currency`/`actual_currency` shape as any grantee-facing one — so if that donor wants the same FIFO rigor for their own conversion (their receipt currency → whatever they report upstream in), they use the *same* ledger mechanism against that budget. No second ledger type exists to design or build; it's a reuse question, not a new-capability question.

**Negative FIFO balances surface transparently, as a normal figure — never blocked or flagged as an error.**
Spend-ahead-of-conversion is expected real-world timing (e.g. weekend spending, next-business-day bank conversion), not a fault condition. The running FIFO balance is simply allowed to go negative and trues up automatically the moment the next `CurrencyConversion` is recorded — no warning UI or approval gate around it.

**Funding-chain depth is deliberately irrelevant to the design — each `Budget` only knows its own immediate parent, never the chain as a whole.**
`Budget.parent_budget_id` is a local, one-hop link (a node knows only whether it reports to someone, and — via reverse relationship — whether someone reports to it); nothing in the schema counts or caps hops. A two-hop chain (the deepest confirmed real example) and a hypothetical deeper one are handled identically, node by node, so no chain-depth decision was ever actually required.

## Risks / Trade-offs

- **[Risk]** No overspend enforcement — users will likely expect it immediately after this ships, given the worked example (£1000 admin cost line, multiple receipts). → **Mitigation**: schema (`ReportLine.budget_line_id` + `.amount`) supports computing totals later without a migration; flagged as an immediate fast-follow, not silently dropped.
- **[Risk]** No two-phase commit between the Postgres attachment row and the blob in storage — a delete or upload failure partway through can leave an orphaned blob or a dangling row. → **Mitigation**: acceptable for v1 given local-disk storage and low volume; note need for a periodic reconciliation job if this becomes an issue.
- **[Risk]** Report attachments now live on Cloudflare R2's free tier (`open-grantflow-reports` bucket), which carries its own storage/bandwidth caps and no contractual DR guarantee at the free tier. → **Mitigation**: acceptable for current scale; revisit (paid tier, or a backup/export job) if usage approaches free-tier limits — flagged as an infra follow-up, out of scope for this change.
- **[Trade-off]** Proxying all uploads through the FastAPI app instead of presigned direct-upload adds app-server bandwidth/memory pressure for large files. Accepted given expected file sizes (receipts/invoices, capped at 15MB) and no object-store endpoint to presign against today.
- **[Trade-off]** `Budget.parent_budget_id` models the funding chain as a simple self-referential link rather than a dedicated `Grant`/hierarchy entity. Accepted deliberately: each node only needs to know its own immediate parent (and, via reverse relationship, its own children), never the chain as a whole — so this scales to any depth without a redesign.
- **[Risk]** The report-period overlap check on creation is enforced in application code (query existing periods, compare, then insert), not a DB-level exclusion constraint — two concurrent report-creation requests with overlapping periods on the same budget could both pass the check before either commits. → **Mitigation**: acceptable for v1 given low concurrency on this compliance-review workflow (not a checkout flow); a Postgres `EXCLUDE USING gist` range constraint (via the `btree_gist` extension) is the correct fix if this becomes a real issue.

## Migration Plan

One new Alembic revision chained off the current head (`000002_add_ai_draft_budget_status`), adding `reports`, `report_lines`, `attachments` in a single migration (`downgrade()` drops in reverse order). No data backfill needed — purely additive tables. Rollback is a straight `alembic downgrade -1`.

Currency-ledger tables (`funding_receipts`, `currency_conversions`, plus `Budget.actual_currency`/`parent_budget_id` and `ReportLine.source_report_id`) are additive to this same migration or a follow-on one — no backfill needed, no change to existing columns.

## Open Questions

- Exact table name for the attachment entity (`attachments` vs `report_line_attachments`) — leaning `attachments` as the more generic, less scope-implying name; not a blocking decision.
- Whether budget-line overspend validation should become a hard cap or just a warning when it is eventually built — deferred to that fast-follow's own design.
- Whether "final report" should be inferred (e.g. all of a budget's reports, together, cover its full span and are all `approved`) or stored as an explicit `report_type` field — deferred as a business decision, not designed further here. Needed for the "refund owed to funder" calculation some donor report templates require.
- Role-scoped restriction on owner self-review (when a budget has no in-system funder) — deferred to a future iteration; v1 allows any budget owner to self-review with no finer-grained role check.
- The `budget-currency-ledger` capability (declared in this proposal's New Capabilities) has no `specs/budget-currency-ledger/spec.md` file yet — should be authored before ticket #148 starts.
- Rollup/spreadsheet-style summary reporting (budget-vs-actual by category and by line, combined across all of a budget's reports, with a deviation column) is not scoped in any current ticket. The schema supports computing it — validated against a real donor report template — but the endpoint that generates it is new, unscoped work, not part of tickets #144–148.
