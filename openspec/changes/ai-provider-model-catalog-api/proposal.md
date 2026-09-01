## Why

`AiIntegrationsSection.tsx` hardcodes `MODELS_BY_PROVIDER`, duplicating the `ai_provider_models` table added in `ai-provider-key-defaults` (migration 016). Anytime the catalog changes (new model, new provider), the frontend copy silently drifts out of sync with the backend's `exists_for_provider` validation — a model the UI offers can get rejected by the API, or vice versa.

## What Changes

- Add a `GET /ai/settings/models` (or similar) endpoint listing active `ai_provider_models` rows, grouped or filterable by provider.
- Have `AiIntegrationsSection.tsx` fetch this list instead of using the hardcoded `MODELS_BY_PROVIDER` map.
- Remove `MODELS_BY_PROVIDER` once the fetch path replaces it.

No admin UI/CRUD for the catalog itself is in scope here — same as the original table, models are still added via migration. This is purely wiring existing data through an API instead of duplicating it.
