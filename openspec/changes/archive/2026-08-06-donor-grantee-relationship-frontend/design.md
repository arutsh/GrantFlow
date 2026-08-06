## Context

`AddBudgetModal` (`frontend-typescript/src/pages/Budgets/components/AddBudget.tsx`) is the actual budget-creation entry point. Today it has exactly two fields — `budgetName` and `funderName` (patches `external_funder_name`) — and never sets `funding_customer_id`, even though the `Budget`/`BudgetCreate` types (`frontend-typescript/src/pages/Budgets/types/budget.ts`) already carry an optional `funding_customer_id` field. `DonorDashboard.tsx` is the donor-gated landing page (reached via `useAuth().isDonor`, decoded from the JWT); it shows funded-budget aggregates only (`getFundedBudgetsSummary`/`getFundedGrantees`/`getFundedBudgets` from `donorDashboardApi.ts`, a thin `gatewayApi` wrapper) — nothing about the relationship itself, and this change does not touch it. Its existing "Grantees" section (`GranteeCard`) is a different concept anyway: it lists grantees derived from actual funded budgets, not the raw approval list this change introduces. Instead, the grantee-management UI is placed on the Settings page (`Settings.tsx`), the existing single-page settings surface (currently just AI-provider key management), gated the same way (`useAuth().isDonor`) so it only renders for a donor customer.

This depends entirely on `donor-grantee-relationship-backend`: the `/api/v1/donor-grantees/` and `/api/v1/customers/` gateway routes, the donor-scoped and grantee-scoped list endpoints, and the customer search/filter params all need to exist first.

## Goals / Non-Goals

**Goals:**
- A donor can, without leaving Settings, search for an NGO customer by name, approve them as a grantee, see their current approved list, and revoke an entry.
- A grantee creating a budget can pick a donor from their own approved list and have it set `funding_customer_id` on create.
- Reuse existing patterns exactly: `gatewayApi` wrapper style for API clients, `useQuery`/`useMutation` for data fetching, the card-grid visual language already established for grantee/donor listings on `DonorDashboard`, the section-card layout already used by Settings' `ProviderCard`s, and the plain-input form style already used in `AddBudgetModal`.

**Non-Goals:**
- No new UI kit component (combobox/autocomplete library) — the donor's grantee search is a simple text input plus an explicit search trigger (button/Enter), not live-as-you-type filtering. This avoids adding a debounce utility that doesn't exist anywhere in this codebase today, for a flow that's used infrequently (approving a grantee is a rare action, not a hot path).
- No changes to `external_funder_name` / free-text funder support — it remains available for funders that aren't platform customers; the two are mutually exclusive per submission (picking a donor clears the free-text field and vice versa), not merged into one control.
- No changes to `GranteeCard`/the existing funded-budgets aggregates on `DonorDashboard` — the new "Manage Grantees" section lives on Settings instead, not alongside them (see Decision 3).
- ~~No retrofitting `BudgetViewHeader.tsx`'s existing (post-creation) funder-edit field to use the picker — flagged as a natural follow-up, not required here.~~ Done anyway (see Decision 7) — turned out to be needed for a grantee to actually "choose either from the donor list or a custom one" on an *existing* budget, not only at creation time.

## Decisions

**1. Grantee's donor picker is a plain `<select>`, not a search box.** A grantee's own approved-donor list (`GET /donor-grantees/?request_type=grantee`) is expected to be small (a handful of donors at most), fetched once via `useQuery`, no search needed. This matches `AddBudgetModal`'s existing plain-input style — no new component.

**2. Donor's "add grantee" is a manual-trigger search, not live filtering.** Text input for an NGO name + a search action (button or Enter-to-submit) fires `useQuery` with the search string as part of the query key (or a `useMutation`/manual `refetch`), calling `GET /customers/?is_ngo=true&search=...`. Chosen over live-as-you-type to avoid needing a debounce utility that doesn't exist in this codebase, for a low-frequency action.

**3. "Manage Grantees" is a new donor-gated section on the Settings page (`Settings.tsx`), not on `DonorDashboard.tsx`.** Revised from the original plan (a `DonorDashboard` section) after implementation review: approving/revoking a grantee is an account-configuration action — closer in kind to Settings' existing AI-provider key management than to the dashboard's funded-budget reporting — and keeping it off `DonorDashboard` avoids any risk of it reading as a funding commitment next to the funded-budget-derived "Grantees"/`GranteeCard` section, which answers a different question ("who do I currently fund" vs. "who have I approved to apply"). New component `frontend-typescript/src/pages/Settings/components/ManageGrantees.tsx`, rendered as a `<section>` card matching Settings' existing `ProviderCard` styling, gated by `useAuth().isDonor` in `SettingsPage` itself. The approved-grantee list still uses the same card-grid visual language as `DonorDashboard`'s `GranteeCard` for consistency (not a table — the mobile-card-over-table convention for new/touched sections applies here directly, and a small approval list doesn't need tabular density anyway).

**4. `funding_customer_id` and `external_funder_name` are mutually exclusive in `AddBudgetModal`'s submission**, not simultaneously settable. Selecting a donor from the picker clears/disables the free-text field and vice versa, mirroring the fact that a budget is either funded by a platform donor (relationship-gated) or an external, unaffiliated funder (free text, no relationship check applies server-side).

**5. Empty states are explicit, not a blank/disabled control.** If a grantee has zero approved donors, the picker area shows a message ("No approved donors yet — ask a donor to add you before selecting them here") rather than an empty `<select>`, since a silently-empty dropdown would look broken rather than explain the actual (correct) gating behavior.

**6. New API client `donorGranteeApi.ts` mirrors `donorDashboardApi.ts` exactly** — thin async functions wrapping `gatewayApi`, typed response interfaces, no abstraction beyond that (no generic CRUD client, no React Query hook factory — this codebase doesn't have one and three call sites doesn't justify introducing one).

**7. `BudgetViewHeader.tsx`'s existing (post-creation) funder-edit field gets the same donor-picker + free-text mutual-exclusivity treatment as `AddBudgetModal`, including a real backend fix.** Reversed from the original Non-Goal after the user asked for full "pick a donor or write a custom name" support, which only makes sense if it also works on an *already-created* budget, not just at creation. Implementing this surfaced a real gap: `services/budget/app/crud/budget_crud.py`'s `update_budget` treated an incoming `funding_customer_id=None` the same as "field omitted" (no `_set` flag, unlike `donor_total_amount`/`estimated_exchange_rate`), so a grantee switching a budget from a donor-linked funder back to a free-text one could never actually clear the stale `funding_customer_id` — the backend would silently keep both set. Fixed by adding the same `funding_customer_id_set` kwarg pattern already used for the other two clearable fields (`services/budget/app/crud/budget_crud.py`, `services/budget/app/services/budget_services.py`), and widening `BudgetUpdate.funding_customer_id`/`BudgetPatched.funding_customer_id` on the frontend to `string | null` so the edit form can send an explicit clear. On entering edit mode, the picker preselects the donor option when `budget.funder.id` is set (a real customer lookup) and preselects the free-text field otherwise (an `external_funder_name`-only funder, no `id`).

## Risks / Trade-offs

- **[Risk] Grantee's donor picker silently offers nothing if the backend gateway routes from `donor-grantee-relationship-backend` ticket 3 aren't live yet.** → Mitigation: this change is explicitly sequenced after that backend change is fully merged (see proposal's Impact section); not something this change's code needs to guard against defensively.
- **[Risk] Donor search-by-name UX is weaker than live-filtering (extra click/Enter required).** → Mitigation: acceptable per Non-Goals — this is a rare action, and matches the "don't add infrastructure beyond what's needed" principle over a marginal UX gain.
- **[Trade-off] Mutually-exclusive donor-picker vs. free-text funder adds one more piece of form state/logic to `AddBudgetModal`** (clearing one when the other is set) vs. leaving both independently settable and letting the backend's existing behavior (relationship check only applies when `funding_customer_id` is set) sort it out. Chosen anyway because letting a user fill in both fields with no visible relationship between them in the UI would be confusing, even though the backend would handle it correctly either way.

## Migration Plan

1. Hard dependency: `donor-grantee-relationship-backend` fully merged (all 3 ticket groups), including gateway routes — verify by hitting `/api/v1/donor-grantees/` and `/api/v1/customers/?is_ngo=true` manually before starting frontend work.
2. Ship `donorGranteeApi.ts` + customer-search client extension first (no UI yet) so both frontend tickets below can build against real types.
3. Ship the two UI tickets (donor management, grantee picker) — independently mergeable, no ordering dependency between them beyond both needing step 2.
4. No feature flag needed: until a donor actually approves a grantee, the picker simply shows the empty state (decision 5) — there's no broken intermediate state to gate behind a flag.

## Open Questions

- Should the donor's grantee search also let them search by country or other `CustomerModel` fields, or is name-only sufficient for v1? Current plan: name-only, matching what the backend change's `search` param covers; broadening it is additive if needed later.
- Should an already-approved grantee be excluded from donor search results, or shown with an "Already added" state instead of the "Add" action? Current plan: exclude them (cross-reference against the donor's own already-fetched approved list client-side) — simpler than adding a new backend query shape, and the donor's approved list is already being fetched for the section itself.
