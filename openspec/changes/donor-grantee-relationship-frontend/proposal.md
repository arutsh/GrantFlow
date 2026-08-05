## Why

The `donor-grantee-relationship-backend` change adds the API and enforcement for donor-approved grantees, but there is no UI to use it: donors have no way to add/revoke a grantee, and grantees have no way to pick from their approved donors when creating a budget — `AddBudgetModal` only has a free-text funder-name field and never sets `funding_customer_id`. Without this UI, the backend gate simply blocks funded-budget creation with no way for a real user to satisfy it.

## What Changes

- Add a "Manage Grantees" section to `DonorDashboard.tsx`: donor sees their approved grantees, can search NGO customers by name and add one, and can revoke an existing approval.
- Add a real donor picker to `AddBudgetModal` (`AddBudget.tsx`): grantee selects from their own approved donors (via the new list endpoint) and the selection is submitted as `funding_customer_id`, alongside the existing free-text funder-name field for unaffiliated funders.
- Add `frontend-typescript/src/api/donorGranteeApi.ts` (list/create/delete against `/api/v1/donor-grantees/`) and extend the customer API surface with a name-search lookup (against `/api/v1/customers/`) for the donor's "add grantee" picker.
- **BREAKING** (UI-visible, not API): grantees attempting to fund a budget from a donor that hasn't approved them will see a rejected request from the picker's own scoped list — in practice this means the picker only ever offers valid donors, so this manifests as "no donors available yet" rather than a runtime error, once used as designed.

## Capabilities

### New Capabilities
(none — this change adds UI-observable requirements to the `donor-grantee-relationship` capability proposed by `donor-grantee-relationship-backend`. That capability is not yet archived into `openspec/specs/`, so from this change's perspective it is still introduced via `ADDED Requirements` in the same capability file, layered on top of the backend change's delta.)

### Modified Capabilities
(none)

## Impact

- **Frontend**: `frontend-typescript/src/pages/DonorDashboard/DonorDashboard.tsx` (+ new `components/ManageGrantees.tsx`), `frontend-typescript/src/pages/Budgets/components/AddBudget.tsx`, new `frontend-typescript/src/api/donorGranteeApi.ts`, extension to the customer-facing API client for search.
- **Gateway**: depends on `/api/v1/donor-grantees/` and `/api/v1/customers/` gateway routes, added in `donor-grantee-relationship-backend` ticket group 3 (nginx.conf, nginx-dev.conf, Caddyfile) — this change cannot ship ahead of that.
- **Backend dependency**: depends on all of `donor-grantee-relationship-backend` being merged (donor-grantee CRUD + internal check + customer search/filter params + auth + gateway routes). No backend code changes in this change.
- **Tests**: new/updated frontend component tests for `DonorDashboard` and `AddBudgetModal`.
