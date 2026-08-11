## Context

Onboarding is a two-step flow: `POST /register` (email + password only, role defaults to `user`, no customer) followed by `PATCH /users/{user_id}/` from `Onboarding.tsx`, which carries `first_name`, `last_name`, and either `new_customer_name` or `customer_id`.

In `update_user_endpoint` (`services/users/app/api/user_routes.py`), the non-superuser branch already special-cases `new_customer_name`: it calls `create_customer(...)`, flips `status` to `active`, and attaches the new `customer_id` — bypassing the normal `allowed_fields` whitelist for non-superusers the same way `customer_id` is bypassed today. `role` is not part of that bypass, so the founder keeps the registration-default `user` role and cannot manage the company they just created (e.g. `services/ai/app/api/settings_routes.py` gates org AI settings on `role in {"admin", "superuser"}`).

## Goals / Non-Goals

**Goals:**
- A user who creates a brand-new company during onboarding ends that request with `role = admin`.
- Leave the "join an existing company via `customer_id`" path untouched — role stays whatever it was (default `user`).
- No new endpoint, schema, or migration — this is a one-branch behavior fix in existing, already-trusted server-side logic.

**Non-Goals:**
- Not introducing per-company membership/multi-role models (e.g. a user belonging to several companies with different roles). One user still has exactly one `customer_id` and one `role`, as today.
- Not changing what `admin` is allowed to do elsewhere in the system — that's already defined (e.g. the AI settings gate) and this change simply makes the founder eligible for it sooner.
- Not building an invite-teammates / promote-a-teammate-to-admin capability. Today, only a superuser can set another user's `customer_id`/`role` (via `PATCH /users/{id}`'s superuser branch) — there is no self-service "invite someone to my company" flow at all. That's a real, larger feature (needs an invitation/membership model, email delivery, an acceptance flow) and is tracked as follow-on work, not part of this change.
- Not touching the `role` field accepted by `POST /register` itself. That field is a pre-existing, separate concern (a caller of `/register` can already request an arbitrary role, including `superuser`) and is out of scope for this change — flagged below as a risk, not fixed here.

## Decisions

- **Set `role = "admin"` inline in the existing `new_customer_name` branch**, right next to where `status` is forced to `active`, rather than adding a new field to `UserUpdate` or a new endpoint. This is the smallest change that matches "creating a company" and "becoming its admin" as one atomic transition, and reuses the bypass-of-`allowed_fields` pattern already established for `customer_id` in the same branch — no new precedent introduced.
- **Scope the promotion strictly to the `new_customer_name` (brand-new customer) branch**, not the `elif user_update.customer_id` (join-existing) branch. Every `new_customer_name` call creates a fresh `CustomerModel` row (no name-based dedup in `create_customer`), so the founder is always, by construction, that company's only member at the moment of creation — there's no scenario where two onboarding requests race to become admin of the same new company.
- **Promote to `admin`, never `superuser`.** `superuser` is platform staff, unrelated to owning a company; hardcode the literal `"admin"` rather than deriving it from input.
- **No JWT-issuance changes needed.** `Onboarding.tsx` already calls `/auth/refresh` after the PATCH succeeds, and `/auth/refresh` already re-reads `s.user.role` from the DB (not the old JWT claim) when minting the new token, so the refreshed token will carry `admin` automatically once the DB row is updated.
- **No changes needed in `services/ai` either.** `_require_admin`/`_ALLOWED_ROLES` in `settings_routes.py` already reads the `role` claim off the validated JWT; once the refreshed token carries `admin`, the founder passes that check with zero AI-service changes.

## Risks / Trade-offs

- **[Pre-existing] `POST /register` accepts a client-supplied `role` field directly, unrelated to this change.** → Out of scope here; worth a separate hardening ticket, noted but not addressed in this change.
- **[Low] A non-superuser could in principle call `PATCH /users/{id}` with `new_customer_name` repeatedly to re-trigger the branch.** → Already guarded by the existing `db_user.status == "pending"` condition: once onboarding completes, `status` becomes `active` and the branch can't fire again for that user.
- **[Low] Frontend currently only exposes the "create new company" path (`Onboarding.tsx` always sends `new_customer_name`), never `customer_id`-based joining.** → No frontend change required by this proposal; the `customer_id` join path is exercised only by direct API calls today, and this change doesn't alter its behavior.

## Migration Plan

Single-file backend change, no data migration. Deploy as a normal PR; no rollback complexity — reverting the code reverts the behavior, and no already-created rows need to be un-promoted (existing users who onboarded before this change keep their current role, which is consistent with "not retroactive").

## Open Questions

- When team invitation eventually gets built, should a newly invited teammate default to `user` (today's implicit behavior for the `customer_id`-join path) or should the founder be able to choose the invitee's role at invite time? Not decided here — noted so the future design doesn't have to rediscover this change's scoping decision.
