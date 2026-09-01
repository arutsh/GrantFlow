## MODIFIED Requirements

### Requirement: Provider resolution and key isolation
The endpoint SHALL resolve the caller's customer BYOK provider per request with a per-request agent (keys never shared across requests). When no BYOK provider is configured, the endpoint SHALL use the platform-funded model if the customer's default has been explicitly set to it by a superuser (see `ai-provider-settings`); otherwise it SHALL return 503 with `{"detail": {"code": "no_provider"}}`.

#### Scenario: No provider key configured, no platform fallback set
- **WHEN** the authenticated customer has no active provider key and has not had the platform-funded model set as its default
- **THEN** the endpoint returns 503 with code `no_provider`

#### Scenario: No provider key configured, platform fallback set
- **WHEN** the authenticated customer has no active provider key, but a superuser has set the platform-funded model as that customer's default
- **THEN** the endpoint resolves and uses the platform-funded model instead of returning 503
