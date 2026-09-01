## Context

`user_provider_keys` currently enforces one row per `(customer_id, provider_id)` (migration `003_create_user_ai_settings.py`, model `UserProviderKey`). `settings_routes.py` exposes `GET/PUT/DELETE /ai/settings` keyed by provider name, and `_require_admin` treats `admin` and `superuser` identically for every operation. `get_active_key_for_customer` (`user_provider_key.py`) picks "the most recently updated row with a key or base_url set" — there is no explicit default concept.

Two consumption paths exist for a resolved model:
- `/ai/extract-budget-excel` — falls back to `resolve_platform_funded_model()` unconditionally when no BYOK key resolves (spec'd, shipped, unrelated to this change).
- `/ai/decide` and `/ai/parse-budget/stream` — fail closed (503 / `unavailable`) when no BYOK key resolves; no fallback path today.

This change is driven by a UI redesign (mockup: multiple saved provider configs per org, one marked Default) that requires the schema and resolution logic to actually support more than one key per provider, plus an explicit default, plus a role-gated way to make the platform-funded model that default.

## Goals / Non-Goals

**Goals:**
- Support multiple saved configs per provider per org, each independently nameable and deletable.
- Make "default" explicit and queryable, with exactly one default per org at all times (never zero, once at least one config exists).
- Let `/ai/decide` and `/ai/parse-budget/stream` use the platform-funded model, but only when a superuser has explicitly chosen it as the org's default.
- Keep `/ai/extract-budget-excel`'s existing unconditional fallback behavior untouched.

**Non-Goals:**
- Changing which providers are supported (still Anthropic + Ollama).
- Per-user (vs. per-org) key ownership — configs remain customer-scoped, per the existing `ai-provider-settings` requirement.
- Building a general "which role can do what" policy engine — this adds one specific superuser check, not a new authorization framework.

## Decisions

**1. `is_default` as a boolean column with app-enforced exclusivity, not a separate "defaults" table.**
A partial unique index (`WHERE is_default`) on `customer_id` is the DB-level guarantee; `set_default(config_id)` runs inside a transaction that unsets the previous default and sets the new one in the same commit. Simpler than a separate join table for a 1:1 relationship, and the partial index makes "exactly one default" enforceable even if application logic has a bug.

**2. Deleting the default is a two-step API, not an implicit reassignment.**
`DELETE /ai/settings/keys/{id}` on a non-default config just deletes it. Deleting the default config requires the request body to carry either `new_default_id` (another existing config to promote) or `fallback_to_platform: true` (superuser only — see Decision 4). Deleting the org's *last* remaining config always leaves the org with zero configs and no default; that's allowed (it's the current no-key state) and doesn't require the platform-fallback body param. This mirrors the mockup's confirmation step and avoids ever silently leaving an org with a stale/wrong implicit default.

**3. Platform-funded-as-default is a property of the org (`customer_id`), not a config row.**
Rather than inserting a fake `UserProviderKey` row for "platform-funded", the org's setting is a nullable `customer_ai_defaults.platform_fallback_enabled` flag (new small table, one row per customer, or reuse an existing per-customer settings row if one exists — check before adding a new table) set only via a superuser-only endpoint. `get_active_key_for_customer` returns either the `is_default=true` row, or (if none exists and the flag is set) a sentinel meaning "use `resolve_platform_funded_model()`". This keeps the encrypted-key table free of rows that never hold a key, and keeps the superuser check on one narrow write path instead of threaded through the general config CRUD.

**4. Superuser-only gate is a dedicated dependency, not a role-set bump.**
`_require_admin` (admin-or-superuser) stays as-is for config CRUD (add/remove/list/set-default-among-owned-configs). A new `_require_superuser` guards only the endpoint that flips `platform_fallback_enabled` on. This keeps the blast radius of the new restriction to exactly the one action the user called out, rather than tightening everything AI-settings-related to superuser.

**5. `/ai/extract-budget-excel`'s existing fallback is untouched.**
It doesn't consult `platform_fallback_enabled` — it already falls back unconditionally per the shipped `budget-excel-import` spec. Making it consult the new flag would be a silent behavior *narrowing* (some zero-key orgs would stop getting import fallback until a superuser opts them in) that nothing in this proposal asked for. `/ai/decide` and `/ai/parse-budget/stream` are different: they currently have *no* fallback at all, so adding one gated by an explicit superuser choice is a pure addition, not a narrowing of existing behavior.

## Risks / Trade-offs

- **[Risk]** A new small table (`customer_ai_defaults`) adds one more join to `get_resolved_model`. → **Mitigation**: it's a single-row-per-customer lookup, same shape as the existing `get_active_key_for_customer` query; negligible cost, and keeps the encrypted-key table's rows meaning "an actual stored key."
- **[Risk]** `AIModelName` enum expansion (Haiku, Opus) must stay in sync with the frontend's `SUPPORTED_MODELS` list, which has drifted before (known backlog item). → **Mitigation**: no runtime fix in scope here beyond adding the two values in both places; flagged in tasks.md as a checklist item, not solved architecturally.
- **[Trade-off]** Removing the provider-keyed `PUT/DELETE /ai/settings` routes is a breaking API change for the frontend in the same release. → Acceptable since `AiIntegrationsSection.tsx` is being replaced in this same change; no external API consumers exist for this internal settings endpoint.

## Deployment Prerequisite

**`ANTHROPIC_API_KEY` must be set in prod for any platform-funded fallback path to work — confirmed missing, live, on 2026-08-25.** Diagnosed via prod SSH: an org with zero `user_provider_keys` rows hit `no_active_provider_key` on `/ai/extract-budget-excel`, which should have silently recovered via the already-shipped `resolve_platform_funded_model()` fallback (Decision 5) but returned 503 `no_provider` instead — `os.environ.get('ANTHROPIC_API_KEY')` inside the running prod `ai` container is empty. `docs/deployment/DEPLOYMENT_MODES.md`'s required GitHub Actions secrets list does not include it. This is a real, already-hit gap in the existing excel fallback, not a hypothetical — and this change adds a second consumer of the same env var (the superuser-gated `/ai/decide` / `/ai/parse-budget/stream` fallback), so it must be fixed before or alongside this change's rollout or the new fallback will silently fail closed the same way. See tasks.md task 0.

## Migration Plan

1. Alembic migration: drop `uq_user_provider_keys_customer_provider`, add `label` (nullable string) and `is_default` (boolean, default false) to `user_provider_keys`; add partial unique index on `(customer_id) WHERE is_default`; create `customer_ai_defaults` table (`customer_id` PK, `platform_fallback_enabled` boolean default false).
2. Data backfill: for every customer with exactly one existing row, set `is_default = true` on that row (preserves current behavior for all existing orgs with a configured key).
3. Ship backend (CRUD, routes, resolution, superuser gate) behind the same deploy as the frontend replacement — no need for a feature flag since the old routes are removed in the same change.
4. Rollback: re-add the unique constraint only after confirming no customer has >1 row (would need manual cleanup first); straightforward since this is a young, low-traffic table.

## Open Questions

- Should `platform_fallback_enabled` have a global (not per-customer) kill switch for cost control, independent of any single superuser's per-org choice? Out of scope here; flag for a future change if GrantFlow-funded usage grows.
