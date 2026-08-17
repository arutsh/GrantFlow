## Context

`shared/schemas/auth_schema.py::RegisterRequest` has `role: Optional[str] = "user"` with no validation, even though `shared/schemas/user_schema.py::UserRole` (an enum: `superuser`/`admin`/`user`) already exists in the same package. `register_endpoint` (`services/users/app/api/auth_routes.py`) forwards `req.role` unchanged into `create_user()` (`services/users/app/crud/user_crud.py`), which assigns it straight to `UserModel.role`, a plain `String` column with no DB check constraint. The value then round-trips into the JWT (`role` claim) issued at the end of registration.

`POST /auth/impersonate` trusts that claim directly (`if current_user.get("role") != "superuser": raise 403`) to authorize minting an admin-role token for an arbitrary `customer_id`. Confirmed exploitable end-to-end in local dev: register with `role: "superuser"` → call `/auth/impersonate` → read another tenant's budget data.

`company-onboarding`'s existing spec already asserts `role` defaults to `user` at registration and that no self-service path grants `superuser` — this change brings the code back in line with that documented invariant rather than introducing a new one.

## Goals / Non-Goals

**Goals:**
- Make `role` fully non-client-controllable at registration — the server decides it, always `user`.
- Add a DB-level backstop (CHECK constraint) so no future code path can silently write an invalid/unauthorized role string.
- Bring `/api/register` in line with the other unauthenticated-input endpoints (`login`, `verify-email`, `change-password`) that already rate-limit via `app/services/login_rate_limiter.py`.
- Stop leaking account existence through registration's duplicate-email error.

**Non-Goals:**
- Redesigning the `admin`/`superuser` promotion paths themselves (admin-management endpoints, `company-onboarding`) — those are already gated correctly; this change only removes the bypass at registration.
- Changing `/auth/impersonate`'s authorization logic — it's correct once `role` can be trusted.
- Adding CAPTCHA or other bot-detection to registration — out of scope, rate limiting is sufficient for this fix.

## Decisions

**Drop `role` from `RegisterRequest` entirely, rather than validating it against the enum.** Accepting `role` and validating it against `UserRole` would still let a client request `role: "admin"` and get it — the actual invariant we want is "registration always produces `user`," matching what `company-onboarding` already assumes. Removing the field is simpler than allowlisting a subset, and Pydantic will reject any `role` key outright if the model is also set to forbid extra fields consistent with the rest of the schema (otherwise FastAPI/Pydantic v2 silently ignores unknown fields by default, which is an acceptable outcome here since the server hardcodes `user` regardless).

**Hardcode `role=UserRole.user` at the `register_endpoint` call site, not inside `create_user()`.** `create_user()` is also called by the admin-invite/admin-management flow (per recent "Implement admin and superuser management capabilities" work), which legitimately needs to set a caller-chosen role. Changing `create_user()`'s signature/default would risk silently breaking that path. Instead, `register_endpoint` stops forwarding `req.role` and passes `role="user"` (or drops the kwarg, relying on `create_user`'s own default) explicitly.

**DB CHECK constraint as defense in depth.** Even with the app-layer fix, nothing today stops a future direct DB write, a bug in the admin-management path, or a different service, from writing an arbitrary string into `role`. A CHECK constraint (`role IN ('superuser', 'admin', 'user')`) makes an invalid role a hard DB error instead of a silent data integrity problem. Requires an Alembic migration; existing rows are already known-valid (`superuser`/`admin`/`user` per `UserRole`), so no backfill needed.

**Reuse `is_locked_out`/`record_failed_attempt` for registration, keyed by source IP only (no email key).** Login/verify-email/change-password key on account identifier because the concern is credential-guessing against one account. Registration has no existing account to key on — the risk is volumetric abuse (mass account creation, and reducing friction for exploiting the role-escalation bug before it's patched everywhere). IP-only keying, same bucket mechanism, new `"register"` bucket name.

**Generic duplicate-email handling: keep the distinct error, but rate-limit it away.** A fully generic "registration submitted" response regardless of outcome would be a bigger UX/behavior change (register_endpoint currently returns tokens synchronously on success) and isn't necessary once registration is rate-limited — enumeration requires volume, and volume is now throttled. Documented as accepted residual risk rather than fixed with response-shape changes, keeping this change scoped to the critical/medium items.

## Risks / Trade-offs

- [Any external caller currently sends `role` at registration expecting it to be honored] → None known (no test or frontend code references it going into `/register`); `company-onboarding` spec already documents `user` as the expected default, so this is a bug fix, not a behavior change from spec's point of view. Grep frontend registration form before merging to confirm no `role` field is submitted.
- [CHECK constraint migration fails if any existing row has a role outside the three valid values] → Run a read-only audit query (`SELECT DISTINCT role FROM users`) before writing the migration; abort and handle data cleanup first if anything unexpected turns up.
- [IP-based rate limiting on registration can false-positive shared-IP users (NAT, corporate networks)] → Same trade-off already accepted for login/verify-email; use the same threshold/window conventions already tuned for those endpoints rather than inventing new ones.

## Migration Plan

1. Ship the schema/endpoint fix (`role` no longer accepted from the client) and rate limiting together — the rate limiting reduces exploitability of any window between deploying this fix and it reaching all environments.
2. Ship the DB CHECK constraint as a separate, immediately-following migration once the audit query confirms no bad data.
3. No rollback complexity: reverting the app-layer change re-opens the vulnerability (acceptable rollback since it returns to the current shipped state), and the CHECK constraint can be dropped independently if it ever blocks a legitimate future role value being added (e.g. a new tier) — in which case add the value to the constraint rather than dropping it.

## Open Questions

- Should `POST /api/register` also reject an attacker-supplied `customer_id` pointing at an existing company (letting a stranger attach themselves to any org, with role forced to `user`)? Out of scope for this change (not part of the pentest findings — `role` was the escalation vector) but worth a follow-up look, since `company-onboarding` treats `customer_id`-at-registration as the "join an existing company" path with no membership verification.
