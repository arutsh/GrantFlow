Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Promote company founders to admin on onboarding

- [ ] 1.1 In `services/users/app/api/user_routes.py::update_user_endpoint`, in the non-superuser `new_customer_name` branch (alongside the existing `update_data["status"] = "active"`), set `update_data["role"] = "admin"` so the field survives the `filter_dict_keys(update_data, allowed_fields)` call regardless of what's in `allowed_fields` — same bypass pattern already used for `customer_id` in this branch.
- [ ] 1.2 Confirm the `elif user_update.customer_id:` (join-existing-company) branch is untouched and does not set `role`.
- [ ] 1.3 Add `services/users/tests/test_user_routes.py` covering: (a) non-superuser onboarding with `new_customer_name` results in `role == "admin"`, `status == "active"`, and a new customer row; (b) non-superuser onboarding with an existing `customer_id` leaves `role` unchanged; (c) a non-superuser client-supplied `role` value in the request body is ignored/overridden by the forced `"admin"` when `new_customer_name` is used.
- [ ] 1.4 Manually verify (or add an integration check) that a freshly onboarded founder's refreshed token passes `services/ai/app/api/settings_routes.py`'s `_require_admin` check with no AI-service change — confirms the promotion is actually load-bearing, not just a stored value.
- [ ] 1.5 Run `flake8 --max-line-length=100` and the `services/users` test suite clean; PR merged (`Closes #<ticket>`).
