One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. API client layer

- [x] 1.1 Add `frontend-typescript/src/api/donorGranteeApi.ts`: `listDonorGrantees(requestType: "donor" | "grantee")`, `createDonorGrantee(granteeId: string)`, `deleteDonorGrantee(id: string)`, typed response interfaces, wrapping `gatewayApi` against `/api/v1/donor-grantees/`, mirroring `donorDashboardApi.ts`'s style.
- [x] 1.2 Extend the customer-facing API client with `searchCustomers({ is_ngo, search })` against `/api/v1/customers/` (new file `customerApi.ts`, or extend an existing users-api client if one already wraps `/api/v1/customers/` or `/api/v1/users/` — check `frontend-typescript/src/api/` before adding a new file). Also added `getCustomersByIds` (wraps `POST /customers/by_ids/`) — needed to resolve donor-grantee rows (id-only) into displayable names for groups 2 and 3, not called out explicitly in this task but required by them.
- [ ] 1.3 Manually verify both clients against the live dev stack once `donor-grantee-relationship-backend` is merged (list/create/delete relationship; search customers by name and `is_ngo`).
- [ ] 1.4 Run frontend lint/typecheck clean; PR merged (`Closes` the ticket for this group). (lint/typecheck clean — done; PR not yet opened/merged)

## 2. Donor grantee management UI — ticket depends on 1

Revised during implementation: placed on the Settings page instead of `DonorDashboard.tsx` (see design.md Decision 3) — an account-configuration action fits better alongside Settings' existing AI-provider management than next to the dashboard's funded-budget reporting.

- [x] 2.1 Add `frontend-typescript/src/pages/Settings/components/ManageGrantees.tsx`: approved-grantee list (card layout, following `GranteeCard`'s visual style) with a revoke action per entry, plus a name-search input + explicit search trigger and per-result "Add" action, excluding customers already in the donor's approved list.
- [x] 2.2 Wire an explicit empty state ("no approved grantees yet") when the donor's approved list is empty.
- [x] 2.3 Mount `ManageGrantees` in `frontend-typescript/src/pages/Settings/Settings.tsx`, gated on `useAuth().isDonor`, using `useQuery`/`useMutation` with query invalidation so add/revoke reflect immediately without a manual page reload.
- [x] 2.4 Add/update component tests (`Settings.test.tsx` covering the `isDonor` gate, and `ManageGrantees.test.tsx`) covering: list renders, empty state, add flow, revoke flow, search excludes already-approved grantees.
- [ ] 2.5 Manually verify in the browser: add a grantee, confirm it appears without reload; revoke it, confirm it disappears; confirm the empty state renders for a donor with none.
- [ ] 2.6 Run frontend tests and lint clean; PR merged (`Closes` the ticket for this group). (tests/lint clean — done; PR not yet opened/merged)

## 3. Grantee donor picker — ticket depends on 1

- [x] 3.1 In `frontend-typescript/src/pages/Budgets/components/AddBudget.tsx`, add a donor `<select>` populated from `listDonorGrantees("grantee")`, submitting the chosen id as `funding_customer_id` in the `createBudget` call.
- [x] 3.2 Make the donor `<select>` and the existing free-text `funderName` input mutually exclusive: selecting one clears the other's local state before submission.
- [x] 3.3 Add an explicit empty state ("no approved donors yet") in place of the picker when the grantee's approved-donor list is empty, instead of an empty `<select>`.
- [x] 3.4 Add/update component tests (e.g. a new or extended `AddBudget.test.tsx`) covering: picker renders options from the approved-donor list, selecting a donor sets `funding_customer_id` on submit, mutual exclusivity with the free-text field, empty-state rendering, and budget creation with neither field set still works.
- [ ] 3.5 Manually verify in the browser: as a grantee with at least one approved donor, create a budget via the picker and confirm `funding_customer_id` is set on the created budget; confirm the empty state for a grantee with none.
- [ ] 3.6 Run frontend tests and lint clean; PR merged (`Closes` the ticket for this group). (tests/lint clean — done; PR not yet opened/merged)

## 4. Grantee donor picker on the existing-budget edit form — ticket depends on 1, added during implementation (see design.md Decision 7)

Reverses the original Non-Goal ("no retrofitting `BudgetViewHeader.tsx`") after the user asked for full donor-or-custom-name support, which only makes sense if it also works on an already-created budget. Includes a real backend fix: `funding_customer_id` previously had no way to be explicitly cleared via PATCH.

- [x] 4.1 Backend: add `funding_customer_id_set` flag to `update_budget` (`services/budget/app/crud/budget_crud.py`) and pass it from `update_budget_service` (`services/budget/app/services/budget_services.py`), mirroring the existing `donor_total_amount_set`/`estimated_exchange_rate_set` pattern — lets PATCH explicitly clear a previously-set `funding_customer_id`.
- [x] 4.2 Widen `funding_customer_id` to `string | null` on `BudgetUpdate`/`BudgetPatched` (`frontend-typescript/src/pages/Budgets/types/budget.ts`) so the edit form can send an explicit clear.
- [x] 4.3 In `frontend-typescript/src/pages/Budgets/components/BudgetViewHeader.tsx`, add the same donor `<select>` + free-text mutual-exclusivity control as `AddBudgetModal` to the existing funder-edit field. On entering edit mode, preselect the donor option when `budget.funder.id` is set, otherwise prefill the free-text field.
- [x] 4.4 `saveEdit` always sends both `funding_customer_id` (explicit `null` when unset) and `external_funder_name` (cleared to `""` when a donor is selected) — same "full metadata every save" convention already used for `donor_total_amount`/`estimated_exchange_rate` in this form.
- [x] 4.5 Backend tests (`services/budget/tests/test_budget_donor_commitment.py`): `funding_customer_id` clears via explicit `null`, stays unchanged when omitted, and can be set from unset.
- [x] 4.6 Frontend tests (`BudgetViewHeader.test.tsx`): no picker when zero approved donors, preselects donor for a donor-linked funder, prefills free text for a custom-named funder, switching either direction sends the correct explicit-clear payload.
- [ ] 4.7 Manually verify in the browser: edit a donor-linked budget's funder to a custom name and confirm it saves and persists after reload (not silently reverted); edit a custom-funded budget to an approved donor and confirm the same.
- [ ] 4.8 Run backend + frontend tests and lint clean; PR merged (`Closes` the ticket for this group). (tests/lint clean — done; PR not yet opened/merged)
