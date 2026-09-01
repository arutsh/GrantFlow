One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. ai service catalog models — depends on audit-mixin-auto-population being merged

- [ ] 1.1 Add Alembic migration adding nullable `created_at`/`updated_at`/`created_by`/`updated_by` to `AIProvider`, `AIProviderModel`.
- [ ] 1.2 Update both model classes to inherit `AuditMixin`; confirm existing `id` column definitions are unaffected (mixin attribute override, per design.md decision 1).
- [ ] 1.3 Add/update tests confirming the new columns populate correctly for authenticated admin-driven creation, and stay `NULL` for unauthenticated seed/migration inserts.
- [ ] 1.4 Run `services/ai`'s test suite clean; PR merged.

## 2. budget service DonorTemplateModel — depends on 1

- [ ] 2.1 Add Alembic migration adding nullable `created_at`/`updated_at`/`created_by`/`updated_by` to `DonorTemplateModel`.
- [ ] 2.2 Update the model class to inherit `AuditMixin`.
- [ ] 2.3 Add/update a test confirming `created_by` is populated on template upload via the authenticated route.
- [ ] 2.4 Run `services/budget`'s test suite clean; PR merged.

## 3. users service CustomerModel and UserModel — depends on 1, 2

- [ ] 3.1 Add Alembic migration adding nullable `created_at`/`updated_at`/`created_by`/`updated_by` to `CustomerModel` and `UserModel`.
- [ ] 3.2 Update both model classes to inherit `AuditMixin`; confirm existing `id` column definitions (including `UserModel`'s `str(uuid.uuid4())` default) are unaffected.
- [ ] 3.3 Audit admin-management and company-onboarding flows to confirm they pass an authenticated actor context so `created_by` populates correctly there (per design.md's open question); self-registration is expected to leave `created_by` `NULL`.
- [ ] 3.4 Add/update tests: self-registration leaves `created_by` `NULL`; admin-created accounts get a non-NULL `created_by`; updating a user/customer sets `updated_by`.
- [ ] 3.5 Manually verify login, self-registration, and admin-management flows on staging before merge, per this repo's standard practice for auth-adjacent schema changes.
- [ ] 3.6 Run `services/users`'s test suite clean; PR merged.
