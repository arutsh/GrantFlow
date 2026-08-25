## Why

An organization can only save one key per AI provider today (`user_provider_keys` has a unique `(customer_id, provider_id)` constraint), so there's no way to keep, say, a Sonnet key for quality work and a Haiku key for cheap/fast tasks side by side, and no explicit notion of which configured key is "the" one used when a caller doesn't specify a model. Separately, `/ai/decide` and `/ai/parse-budget/stream` fail closed (503/`unavailable`) for any org with no BYOK key, while `/ai/extract-budget-excel` silently falls back to a GrantFlow-funded model for anyone — an inconsistency the org-level UI redesign (mockup: multiple saved keys, one marked Default) surfaces and forces a decision on.

## What Changes

- Allow multiple `user_provider_keys` rows per `(customer_id, provider)`, each with an optional nickname (`label`) and an `is_default` flag; exactly one row per customer may be default at a time.
- Add `claude-haiku-4-5` and `claude-opus-4-5` to `AIModelName` (and the frontend's mirrored model list) so they're selectable per saved key.
- Replace provider-keyed upsert semantics (`GET/PUT/DELETE /ai/settings`) with per-config CRUD: list configs, create a config, set a config as default, delete a config by id. **BREAKING**: existing `PUT /ai/settings` / `DELETE /ai/settings/{provider}/key` routes are removed in favor of id-based routes.
- Deleting the current default requires the caller to name a replacement default among the org's remaining configs, or explicitly choose the GrantFlow-funded fallback — the API rejects a delete that would leave the org with no default and no explicit fallback choice.
- `get_active_key_for_customer` resolves the row where `is_default = true` instead of "most recently updated key with a value set".
- Only a **superuser** may set "GrantFlow's platform-funded model" as an organization's explicit default (a global-cost decision, not a per-org admin one). Regular org admins may still add/remove/default among their own BYOK configs.
- `/ai/decide` and `/ai/parse-budget/stream` use the platform-funded model when that is the org's explicit (superuser-set) default, instead of always failing closed. This is layered on top of — and does not change — the existing unconditional, ungated platform fallback that `/ai/extract-budget-excel` already uses for zero-key orgs (spec'd in the not-yet-archived `budget-export-from-excel` change); that automatic path is deliberately left as-is.

## Capabilities

### New Capabilities
(none — this extends existing capabilities)

### Modified Capabilities
- `ai-provider-settings`: organizations can save multiple keys per provider with an optional label; exactly one config is the org's default at a time; deleting the default requires picking a replacement or an explicit platform-fallback choice; only superusers may set the platform-funded model as an org's default.
- `ai-decide`: when no BYOK key is configured but the org's superuser-set default is the platform-funded model, `/ai/decide` uses it instead of returning 503.

## Impact

- **services/ai**: `app/models/user_provider_key.py` (schema), `app/models/ai_provider.py` (enum), `app/crud/user_provider_key.py` (CRUD rewrite), `app/services/provider.py` (resolution + role-gated fallback), `app/api/settings_routes.py` (route rewrite), `app/api/decide_routes.py`, `app/api/parse_routes.py`; a new Alembic migration.
- **frontend-typescript**: `src/pages/Settings/components/AiIntegrationsSection.tsx` (replaced with multi-config list UI per mockup), `src/api/aiSettingsApi.ts`.
- No change to `/ai/extract-budget-excel`'s existing fallback behavior or its audit logging.
