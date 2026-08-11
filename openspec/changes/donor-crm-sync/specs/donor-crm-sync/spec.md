## ADDED Requirements

### Requirement: Donor-org CRM connection
A donor organization admin SHALL be able to connect a supported external CRM (Salesforce Nonprofit Cloud Grantmaking) to their GrantFlow organization via an OAuth2 authorization-code flow, and disconnect it at any time.

#### Scenario: Successful connection
- **WHEN** a donor-org admin initiates "Connect Salesforce" and completes the OAuth2 consent screen
- **THEN** GrantFlow stores an encrypted access token and refresh token scoped to that donor org, and the connection status shows "Connected"

#### Scenario: Disconnect revokes future sync
- **WHEN** a donor-org admin disconnects a previously connected CRM
- **THEN** GrantFlow stops sending future report/disbursement events to that CRM and marks the connection status "Disconnected", without deleting past sync history

#### Scenario: No connection configured
- **WHEN** a donor org has no CRM connection configured
- **THEN** GrantFlow's report/budget lifecycle behaves exactly as it does today, with no outbound calls attempted

### Requirement: Outbound report sync to Salesforce
When a donor org has an active Salesforce connection, GrantFlow SHALL push report submission and review events to that org's Salesforce Nonprofit Cloud Grantmaking instance, mapping GrantFlow's budget/report schema onto the standard Funding Award / GAU Expenditure / Funding Award Requirement / Funding Disbursement objects.

#### Scenario: Report submitted
- **WHEN** a grantee submits a `ReportModel` (status transitions to `submitted`) for a budget whose donor org has an active Salesforce connection
- **THEN** GrantFlow creates or updates a corresponding Funding Disbursement record (and associated Funding Award Requirement, if configured) in that org's Salesforce instance via an async worker task

#### Scenario: Sync failure does not block the in-app workflow
- **WHEN** the outbound Salesforce API call fails (network error, expired token, Salesforce-side validation error)
- **THEN** the report submission in GrantFlow still succeeds, the sync failure is recorded against the connection's sync status, and the failure is surfaced via GrantFlow's existing observability pipeline

#### Scenario: Token refresh
- **WHEN** a stored Salesforce access token has expired and a valid refresh token is available
- **THEN** GrantFlow automatically refreshes the access token before attempting the sync call, without requiring the donor-org admin to reconnect

### Requirement: Provider adapter extensibility
The sync mechanism SHALL be implemented behind a provider-adapter interface so that additional CRM providers can be added without changing the core sync-triggering logic.

#### Scenario: Adding a new provider
- **WHEN** a new CRM adapter is registered via the provider registry
- **THEN** the existing report-submission and connection-management flows work against the new provider without modification to `services/integrations`' core sync logic

### Requirement: Blackbaud feasibility is undetermined
GrantFlow SHALL NOT offer or advertise Blackbaud Grantmaking sync as a supported capability until a discovery spike confirms the SKY API exposes report/line-item-level data sufficient to implement the same requirements as the Salesforce adapter.

#### Scenario: Blackbaud connection option is hidden until validated
- **WHEN** a donor-org admin views available CRM connection options
- **THEN** Blackbaud SHALL NOT appear as a selectable option unless and until a follow-up change confirms feasibility and implements the adapter
