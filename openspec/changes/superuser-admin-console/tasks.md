One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Admin console shell + customer list (read-only)

- [ ] 1.1 `services/users`: add `GET /users/admin/customers` — superuser-gated (no `resolve_customer_id`/impersonation dependency), returns every customer (name, country, `is_ngo`, `is_donor`, currency, deactivated status).
- [ ] 1.2 `services/users`: write a `privileged_access_logs` entry for this request (actor, request, timestamp), per the `privileged-access-audit` delta.
- [ ] 1.3 Wire `/users/admin/customers` into `nginx-dev.conf`, `nginx.conf`, and `Caddyfile` under the existing `/api/v1/users/` prefix — see [[project_three_gateway_configs]], easy to miss the `Caddyfile`.
- [ ] 1.4 `frontend-typescript`: add `/admin` route, gated on `role === "superuser"` (mirror how `ImpersonatePicker` gates its own visibility); add nav entry visible only to superusers.
- [ ] 1.5 `frontend-typescript`: add `src/pages/Admin/` customer list page + API client method, rendering name/country/is_ngo/is_donor/currency/deactivated status as a plain table (mobile: card layout per [[feedback_mobile_responsive_cards]]).
- [ ] 1.6 Tests: non-superuser gets 403 from `GET /users/admin/customers` and cannot reach `/admin` in the frontend; superuser sees every customer, not scoped to one tenant.
- [ ] 1.7 Run `services/users` backend tests + flake8, and frontend vitest/eslint/tsc, clean; PR merged (`Closes #<ticket>`).

## 2. Platform-AI-fallback toggle from the customer list — depends on 1

- [ ] 2.1 `services/ai`: add `PUT /ai/admin/customers/{customer_id}/platform-fallback` — superuser-gated, calls the existing `set_platform_fallback` CRUD function directly with the path `customer_id` (no impersonation/token-derived `customer_id`).
- [ ] 2.2 `services/ai`: write a `privileged_access_logs` entry for this request (actor, target `customer_id`, request, timestamp).
- [ ] 2.3 Wire the new route into `nginx-dev.conf`, `nginx.conf`, and `Caddyfile` under the existing `/api/v1/ai/` prefix.
- [ ] 2.4 `frontend-typescript`: extend the customer list page to show current platform-fallback status per customer and add an inline toggle calling the new endpoint.
- [ ] 2.5 Tests: non-superuser gets 403; toggling via the new route produces the same resolved default as the existing impersonation-scoped `PUT /platform-fallback` route (cross-check via `get_customer_ai_defaults`).
- [ ] 2.6 Run `services/ai` backend tests + flake8, and frontend vitest/eslint/tsc, clean; PR merged (`Closes #<ticket>`).

## 3. User list (read-only) — depends on 1

- [ ] 3.1 `services/users`: add `GET /users/admin/users` — superuser-gated, returns every user across every customer (name, email, `customer_id`/customer name, role, status).
- [ ] 3.2 `services/users`: write a `privileged_access_logs` entry for this request.
- [ ] 3.3 Wire `/users/admin/users` into all three gateway configs.
- [ ] 3.4 `frontend-typescript`: add a user list view/tab on the `/admin` page (name/email/customer/role/status), reusing the page shell from group 1.
- [ ] 3.5 Tests: non-superuser gets 403; superuser sees users across every customer, not scoped to one tenant.
- [ ] 3.6 Run `services/users` backend tests + flake8, and frontend vitest/eslint/tsc, clean; PR merged (`Closes #<ticket>`).

## 4. User role/admin-status update from the user list — depends on 3

- [ ] 4.1 `services/users`: add `PUT /users/admin/users/{user_id}/role` — superuser-gated, calls the same guarded path `update_user_role_service` uses (last-admin quorum check + row locking), addressed by explicit `user_id` instead of a token-derived company scope.
- [ ] 4.2 `services/users`: write a `privileged_access_logs` entry for this request (actor, target `user_id`, request, timestamp).
- [ ] 4.3 Wire the new route into all three gateway configs.
- [ ] 4.4 `frontend-typescript`: add an inline role/admin-status control to the user list rows, calling the new endpoint.
- [ ] 4.5 Tests: non-superuser gets 403; a superuser can promote/demote a user directly; attempting to demote a company's sole active admin via this endpoint is rejected, same as the existing impersonation-based path.
- [ ] 4.6 Run `services/users` backend tests + flake8, and frontend vitest/eslint/tsc, clean; PR merged (`Closes #<ticket>`).
