Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 0. Prod prerequisite (found via live incident, 2026-08-25) — blocks rollout, no dependency on 1-5

- [ ] 0.1 Add `ANTHROPIC_API_KEY` to the required prod GitHub Actions secrets list in `docs/deployment/DEPLOYMENT_MODES.md`.
- [ ] 0.2 Set `ANTHROPIC_API_KEY` as a GitHub Actions secret and confirm it lands in `services/ai/.env.ai.prod` after the next deploy (`docker compose exec ai python -c "import os; print(bool(os.environ.get('ANTHROPIC_API_KEY')))"` should print `True`).
- [ ] 0.3 Re-verify `/ai/extract-budget-excel` recovers for a zero-key org in prod (currently broken — see design.md Deployment Prerequisite).

## 1. Schema and model foundation

- [ ] 1.1 Alembic migration: drop `uq_user_provider_keys_customer_provider`; add `label` (nullable `String`) and `is_default` (`Boolean`, `server_default=false`) to `user_provider_keys`; add a partial unique index on `user_provider_keys.customer_id WHERE is_default`.
- [ ] 1.2 In the same migration, backfill: for every `customer_id` with exactly one existing row, set `is_default = true` on that row.
- [ ] 1.3 New Alembic migration: create `customer_ai_defaults` table (`customer_id` GUID primary key, `platform_fallback_enabled` `Boolean` `server_default=false`, `updated_at`).
- [ ] 1.4 Update `UserProviderKey` model (`app/models/user_provider_key.py`) with `label` and `is_default` columns; add `CustomerAiDefaults` model (`app/models/customer_ai_defaults.py`).
- [ ] 1.5 Add `claude-haiku-4-5` and `claude-opus-4-5` to `AIModelName` (`app/models/ai_provider.py`).
- [ ] 1.6 Run `services/ai` migrations against a local DB and confirm existing single-key customers backfill to `is_default=true`; run `services/ai` test suite and lint clean; PR merged.

## 2. CRUD and resolution rewrite — depends on 1

- [ ] 2.1 Rewrite `app/crud/user_provider_key.py`: `list_for_customer(customer_id)`, `create(customer_id, user_id, provider_id, label, encrypted_key, model_name, base_url, is_default)`, `set_default(customer_id, config_id)` (transactional: unset current default, set new one), `delete(customer_id, config_id)`.
- [ ] 2.2 Implement the delete-default guard in `delete`/a wrapping service function: reject deletion of the current default unless caller supplies `new_default_id` (must belong to the same customer) or `fallback_to_platform=True`; deleting an org's last remaining config is always allowed with no default set afterward.
- [ ] 2.3 Add `app/crud/customer_ai_defaults.py`: `get(customer_id)`, `set_platform_fallback(customer_id, enabled)`.
- [ ] 2.4 Update `get_active_key_for_customer` (`app/services/provider.py`) to resolve the `is_default=true` row instead of most-recently-updated.
- [ ] 2.5 Update `get_resolved_model` (`app/services/provider.py`): when no default `UserProviderKey` exists, check `customer_ai_defaults.platform_fallback_enabled`; if set, return `resolve_platform_funded_model()`; otherwise return `None` as today.
- [ ] 2.6 Unit tests: multiple configs per provider, default switching, delete-default-rejected-without-replacement, delete-default-with-replacement, delete-last-config-allowed, resolution prefers `is_default` over recency, resolution falls through to platform-funded model only when the flag is set.
- [ ] 2.7 Run `services/ai` test suite and lint clean; PR merged.

## 3. Superuser-gated platform fallback endpoint — depends on 1, 2

- [ ] 3.1 Add `_require_superuser` check (role must be exactly `superuser`) alongside the existing `_require_admin` in `app/api/settings_routes.py`.
- [ ] 3.2 Add `PUT /ai/settings/platform-fallback` (superuser only) toggling `customer_ai_defaults.platform_fallback_enabled` for the acting user's resolved customer.
- [ ] 3.3 Update `app/api/decide_routes.py`: on `resolved is None`, still return 503 `no_provider` (unchanged) — the fallback now happens inside `get_resolved_model` itself (task 2.5), so no route-level change needed beyond confirming the dependency covers it.
- [ ] 3.4 Update `app/api/parse_routes.py` similarly — confirm the `unavailable` SSE event now only fires when neither a BYOK key nor an enabled platform fallback resolves.
- [ ] 3.5 Confirm `app/api/excel_extraction_routes.py` is unchanged — it already calls `resolve_platform_funded_model()` unconditionally and must keep doing so regardless of `platform_fallback_enabled`.
- [ ] 3.6 Tests: admin gets 403 on the platform-fallback endpoint; superuser succeeds; `/ai/decide` and `/ai/parse-budget/stream` use the platform model once enabled and fail closed when not; `/ai/extract-budget-excel` behavior unchanged regardless of the flag.
- [ ] 3.7 Run `services/ai` test suite and lint clean; PR merged.

## 4. Settings API surface — depends on 2, 3

- [ ] 4.1 Replace `GET /ai/settings` with a response listing all configs for the customer (`id`, `provider`, `label`, `model`, masked key/base_url, `is_default`) plus the customer's `platform_fallback_enabled` flag.
- [ ] 4.2 Add `POST /ai/settings/keys` (create a config; admin-or-superuser) replacing the old provider-keyed `PUT /ai/settings`.
- [ ] 4.3 Add `POST /ai/settings/keys/{id}/default` (admin-or-superuser; sets an existing BYOK config as default — does not touch `platform_fallback_enabled`).
- [ ] 4.4 Add `DELETE /ai/settings/keys/{id}` (admin-or-superuser) accepting optional `new_default_id` / `fallback_to_platform` per the design's delete-default guard; remove the old `DELETE /ai/settings/{provider}/key` route.
- [ ] 4.5 Update `shared/ai_client` or any internal client referencing the removed routes, if any.
- [ ] 4.6 Tests: full CRUD flow through the new routes including the delete-default guard's 4xx response shape.
- [ ] 4.7 Run `services/ai` test suite and lint clean; PR merged.

## 5. Frontend: multi-key settings UI — depends on 4

- [ ] 5.1 Update `frontend-typescript/src/api/aiSettingsApi.ts` for the new list/create/set-default/delete-by-id endpoints and response shape.
- [ ] 5.2 Rebuild `AiIntegrationsSection.tsx` per the approved mockup: list of configs with a default badge/"Set as default" action, an "Add key" modal, and a delete-default confirmation flow (replacement picker or, superuser only, the platform-fallback option).
- [ ] 5.3 Add `claude-haiku-4-5` and `claude-opus-4-5` to the frontend's mirrored model list, matching task 1.5.
- [ ] 5.4 Gate the platform-fallback option in the delete-confirmation and settings UI to render only for users with the `superuser` role; non-superusers seeing an org whose default is already platform-funded see it as read-only info, not an editable choice.
- [ ] 5.5 Manually verify in the running app: add two configs for the same provider, switch default, attempt to delete the default without a replacement (rejected in UI), delete the default with a replacement chosen, and (as superuser) enable the platform fallback.
- [ ] 5.6 Run frontend lint/typecheck/tests clean; PR merged.
