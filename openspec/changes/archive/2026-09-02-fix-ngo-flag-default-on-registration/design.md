## Context

`CustomerModel.is_ngo` (`services/users/app/models/customer.py`) declares `default=True` at the ORM level, expressing the intent that a company is an NGO unless told otherwise. In practice, no caller relies on that default: `create_customer` in `services/users/app/crud/customer_crud.py` has its own `is_ngo: bool = False` parameter default, and since `CustomerModel(...)` is always constructed with an explicit `is_ngo=is_ngo` keyword, the CRUD function's default silently wins over the model's.

The self-service founder-onboarding path (`PATCH /users/{user_id}/` → `user_routes.py` → `create_customer(db, new_customer_name)`) never passes `is_ngo`, so every self-registered company ends up `is_ngo=False`. Downstream, donor grantee search (`GET /customers/?is_ngo=true`) and the budget service's grant-receiving check (`customer_client.py`) both require `is_ngo=true`, so these companies are invisible to donors and blocked from receiving grants until an admin manually flips the Settings checkbox.

The admin-only `POST /customers/` path is not affected — it already forwards `is_ngo` explicitly from the request body, so a superuser/admin creating a donor org there still gets correct behavior.

A DB migration (`000001_replace_customer_type_with_flags.py`) set `server_default="false"` when `is_ngo` was introduced, predating the model's `default=True`. This server_default isn't the proximate cause (ORM inserts always pass an explicit value), but it's a latent inconsistency worth closing so schema and ORM intent agree.

## Goals / Non-Goals

**Goals:**
- Every company created through self-service onboarding (`new_customer_name`) gets `is_ngo=True`.
- Close the CRUD-level default mismatch so future callers of `create_customer` that omit `is_ngo` get `True`, consistent with the model.
- Align the DB `server_default` with the intended `True` default.

**Non-Goals:**
- Changing the admin-only `POST /customers/` path — it already handles `is_ngo` correctly via explicit request-body values, since that's the path used to create non-NGO donor orgs.
- Backfilling `is_ngo` on companies that already self-registered with the bug live. Which existing `is_ngo=False` companies are actually NGOs (vs. legitimately donor-only orgs created some other way) can't be inferred from the flag alone — this needs a deliberate data review, tracked as an open question below, not a blanket migration in this change.
- Changing how donor search or the budget service consume `is_ngo` — those are correct today; only the value being written at creation time is wrong.

## Decisions

**Fix at the CRUD default, not just the call site.** Changing `customer_crud.create_customer`'s default from `False` to `True` (or removing the default and requiring callers to be explicit) fixes the bug for the onboarding call site and prevents the same mistake for any future caller that forgets to pass `is_ngo`. Fixing only `user_routes.py`'s call site would leave the misleading `False` default in place as a trap.
- Alternative considered: fix only the onboarding call site by passing `is_ngo=True` explicitly. Rejected as insufficient on its own — the CRUD default is the actual root cause per the investigation, and leaving it `False` keeps the model's `default=True` permanently dead code.

**Align `server_default` via a new migration rather than editing the historical one.** Migrations that have already run in prod are not edited in place; a new migration sets the column's `server_default` to `true` going forward.

## Risks / Trade-offs

- [Risk] A future admin-created donor org (via `POST /customers/`) that omits `is_ngo` in the request body would now default to `True` instead of `False` once the CRUD default flips. → Mitigation: `customer_routes.py`'s admin endpoint already requires/passes `is_ngo` explicitly from the validated request schema, so this path is unaffected either way; confirm the Pydantic schema still makes the field non-optional there as part of implementation.
- [Risk] Existing companies with the bug (`is_ngo=False` when they should be `True`) remain broken until someone backfills them. → Mitigation: explicitly out of scope here; raised as an open question for the user to decide on a remediation approach.

## Migration Plan

1. Fix `create_customer`'s `is_ngo` default in `customer_crud.py`.
2. Update the onboarding call site if needed for clarity (explicit `is_ngo=True` at the call site is optional once the CRUD default is correct, but may be kept for readability).
3. Add a new Alembic migration setting `server_default="true"` on `customers.is_ngo` (schema-only change, no data backfill).
4. No rollback complexity: this is a forward-only default-value fix; reverting the code change is sufficient if needed, no destructive migration involved.

## Open Questions

- Should existing self-registered companies with `is_ngo=False` be backfilled to `True`? Needs a decision on how to distinguish "should be NGO but bugged" from "correctly not an NGO" among existing rows — deferred to the user.
