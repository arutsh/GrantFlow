One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. API client layer

- [ ] 1.1 Add `frontend-typescript/src/api/donorGranteeApi.ts`: `listDonorGrantees(role: "donor" | "grantee")`, `createDonorGrantee(granteeId: string)`, `deleteDonorGrantee(id: string)`, typed response interfaces, wrapping `gatewayApi` against `/api/v1/donor-grantees/`, mirroring `donorDashboardApi.ts`'s style.
- [ ] 1.2 Extend the customer-facing API client with `searchCustomers({ is_ngo, search })` against `/api/v1/customers/` (new file `customerApi.ts`, or extend an existing users-api client if one already wraps `/api/v1/customers/` or `/api/v1/users/` — check `frontend-typescript/src/api/` before adding a new file).
- [ ] 1.3 Manually verify both clients against the live dev stack once `donor-grantee-relationship-backend` is merged (list/create/delete relationship; search customers by name and `is_ngo`).
- [ ] 1.4 Run frontend lint/typecheck clean; PR merged (`Closes` the ticket for this group).

## 2. Donor grantee management UI — ticket depends on 1

- [ ] 2.1 Add `frontend-typescript/src/pages/DonorDashboard/components/ManageGrantees.tsx`: approved-grantee list (card layout, following `GranteeCard`'s visual style) with a revoke action per entry, plus a name-search input + explicit search trigger and per-result "Add" action, excluding customers already in the donor's approved list.
- [ ] 2.2 Wire an explicit empty state ("no approved grantees yet") when the donor's approved list is empty.
- [ ] 2.3 Mount `ManageGrantees` in `frontend-typescript/src/pages/DonorDashboard/DonorDashboard.tsx`, above the existing funded-budget-derived "Grantees" section, using `useQuery`/`useMutation` with query invalidation so add/revoke reflect immediately without a manual page reload.
- [ ] 2.4 Add/update component tests (e.g. `DonorDashboard.test.tsx` or a new `ManageGrantees.test.tsx`) covering: list renders, empty state, add flow, revoke flow, search excludes already-approved grantees.
- [ ] 2.5 Manually verify in the browser: add a grantee, confirm it appears without reload; revoke it, confirm it disappears; confirm the empty state renders for a donor with none.
- [ ] 2.6 Run frontend tests and lint clean; PR merged (`Closes` the ticket for this group).

## 3. Grantee donor picker — ticket depends on 1

- [ ] 3.1 In `frontend-typescript/src/pages/Budgets/components/AddBudget.tsx`, add a donor `<select>` populated from `listDonorGrantees("grantee")`, submitting the chosen id as `funding_customer_id` in the `createBudget` call.
- [ ] 3.2 Make the donor `<select>` and the existing free-text `funderName` input mutually exclusive: selecting one clears the other's local state before submission.
- [ ] 3.3 Add an explicit empty state ("no approved donors yet") in place of the picker when the grantee's approved-donor list is empty, instead of an empty `<select>`.
- [ ] 3.4 Add/update component tests (e.g. a new or extended `AddBudget.test.tsx`) covering: picker renders options from the approved-donor list, selecting a donor sets `funding_customer_id` on submit, mutual exclusivity with the free-text field, empty-state rendering, and budget creation with neither field set still works.
- [ ] 3.5 Manually verify in the browser: as a grantee with at least one approved donor, create a budget via the picker and confirm `funding_customer_id` is set on the created budget; confirm the empty state for a grantee with none.
- [ ] 3.6 Run frontend tests and lint clean; PR merged (`Closes` the ticket for this group).
