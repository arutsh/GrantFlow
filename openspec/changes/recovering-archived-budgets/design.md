## Context

Archiving (`services/budget/app/services/budget_services.py`) is a plain status flip to `archived`, reachable from any prior status via `PATCH /budgets/{id}` with `{"status": "archived"}` — it's what the frontend's "Delete" button calls (`archiveBudget` in `frontend-typescript/src/api/budgetApi.ts`). Nothing else about the row changes: `confirmed_at`, `start_date`, lines, ledger entries, and reports are left exactly as they were.

There is no reverse transition. `update_budget_service`'s confirm guard (`is_confirm_attempt` → status must currently be `draft`/`ai_draft`) exists to protect the *first* confirmation (it validates `start_date`, authorizes the matching funder, etc.), and an archived budget fails that guard unconditionally. The only way back today is a direct SQL `UPDATE`, done once already this session for `7b202d5b-f18e-4c1b-9784-36b5c5b672c1`.

The budget row does not record what status it held immediately before being archived — there's no status-history table (tracked separately as GitHub #138). `confirmed_at` being non-null is the only signal that a budget was ever confirmed.

## Goals / Non-Goals

**Goals:**
- Let an owner reverse an archive action from the UI, without direct database access.
- Restore to the correct status for the two cases that matter in practice: was `confirmed` before archiving, or was `draft`/`ai_draft` before archiving.
- Keep the restore transition's authorization and validation independent of the confirm-guard, since restoring isn't a fresh confirmation.

**Non-Goals:**
- Exact replay of the pre-archive status. Without #138's status history, `ai_draft` and `draft` are indistinguishable after the fact — this change collapses both to `draft` on restore.
- Arbitrary client-chosen restore targets. The restore action doesn't take a target status; the server derives it.
- Defining what happens to currency-ledger entries or reports tied to the budget across an archive/restore round trip — left as an open question below.

## Decisions

**Dedicated restore action, not an extension of `PATCH /budgets/{id}`.**
Considered reusing the generic PATCH endpoint (client sends `{"status": "confirmed"}` on an archived budget, backend special-cases it). Rejected: it would require threading a second "is this actually a restore, not a fresh confirm" branch through `is_confirm_attempt`'s guard, and it lets the client assert a target status the server can't fully validate against. Instead: `POST /budgets/{id}/restore` (no body). The server computes the target status itself, so there's one source of truth for "what does restore mean."

**Restore-target inference: `confirmed_at is not None` → `confirmed`, else → `draft`.**
This is the only signal available today. It's correct whenever a budget was archived from `confirmed`, and degrades gracefully (not incorrectly) for `draft`/`ai_draft` — both land on `draft`, which is a safe, edit-permitting state either way. Revisit once #138 (status history) exists and can supply the exact prior status.

**Owner-only authorization, matching revert-to-draft, not the funder-confirm flow.**
Restoring isn't a new confirmation decision for a funder to make — it's undoing the owner's own archive action. `_resolve_updatable_budget`'s funder-confirm branch does not apply here.

**Defensive re-check before restoring to `confirmed`.**
Even though archiving doesn't touch `start_date`, the restore path re-validates `start_date is not None` before setting `confirmed`, falling back to `draft` otherwise, rather than trusting the historical `confirmed_at` blindly. Cheap insurance against any future code path that clears `start_date` without also clearing `confirmed_at`.

## Risks / Trade-offs

- [Heuristic loses `ai_draft` vs `draft` distinction on restore] → Acceptable near-term; the real fix is #138 (status history). Document the limitation in the API response or UI copy if it proves confusing.
- [Restoring to `confirmed` skips the funder-authorization path that a fresh confirmation would go through] → Mitigation: owner-only restore means no funder-trust decision is being bypassed; the budget was already confirmed once.
- [Ledger entries and reports may be stale, orphaned, or otherwise inconsistent after an archive → restore round trip] → Not mitigated by this change; see Open Questions.

## Migration Plan

No data migration needed — every existing `archived` budget already carries the `confirmed_at`/`start_date` values the inference relies on. Ship backend (`POST /budgets/{id}/restore`) and the UI action together; there's no useful intermediate state where only one exists.

Rollback: revert the endpoint and UI action; no schema change to unwind.

## Open Questions

- **How should currency ledger entries (`budget-currency-ledger`) and reports (`budget-reports`) tied to a budget be handled across archive → restore?** Archiving today doesn't touch either — ledger rows and report rows sit untouched while the budget is `archived`. It's not yet decided whether restore should: (a) leave them exactly as-is and let the budget resume its prior lifecycle unchanged, (b) require some revalidation step (e.g. re-checking ledger totals still reconcile, or that no report was mutated by another process while archived), or (c) flag them for the owner to review post-restore. This needs a decision before backend implementation of the restore endpoint proceeds past the bare status flip.
