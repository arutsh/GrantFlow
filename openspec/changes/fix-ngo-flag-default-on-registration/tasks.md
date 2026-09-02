Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Fix is_ngo default on self-service company registration

- [x] 1.1 Change `create_customer`'s `is_ngo` parameter default in `services/users/app/crud/customer_crud.py` from `False` to `True`, matching `CustomerModel.is_ngo`'s intended default.
- [x] 1.2 In `services/users/app/api/user_routes.py`, confirm/update the onboarding call site so a self-registered company is created with `is_ngo=True` (explicit `is_ngo=True` at the call site is fine for readability even once the CRUD default is fixed).
- [x] 1.3 Confirm `services/users/app/api/customer_routes.py`'s admin-only `POST /customers/` still requires/passes `is_ngo` explicitly from its request schema, so flipping the CRUD default doesn't change behavior on that path.
- [x] 1.4 Add an Alembic migration in `services/users/migrations/versions/` setting `server_default="true"` on `customers.is_ngo` (schema-only, no data backfill of existing rows).
- [x] 1.5 Add/update a test covering self-service onboarding (`new_customer_name` path) asserting the created company has `is_ngo=True`.
- [x] 1.6 Add/update a test covering admin-created customers (`POST /customers/`) asserting `is_ngo` still reflects the request body value, unaffected by the default change.
- [ ] 1.7 Run the users service's test suite and flake8 (max-line-length=100) clean; PR merged.
