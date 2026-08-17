## ADDED Requirements

### Requirement: Excel upload produces a draft budget
The budget service SHALL expose `POST /budgets/import-excel` accepting a single `.xlsx` file upload, extract budget lines from it via AI-first extraction, and create a budget in `ai_draft` status via the existing budget-with-lines creation path, without requiring the user to map columns before upload.

#### Scenario: Successful import creates an ai_draft budget
- **WHEN** an authenticated user uploads a `.xlsx` file with at least one identifiable budget line
- **THEN** the service creates a budget with `status: ai_draft` and returns its id, with lines populated from the extracted data

#### Scenario: File is not a valid Excel workbook
- **WHEN** the uploaded file cannot be parsed as an `.xlsx` workbook
- **THEN** the service rejects the request with an error and creates no budget

### Requirement: AI-based line extraction is BYOK-preferred with a platform-funded fallback
The service SHALL extract category, description, amount, and currency per budget line from a cleaned representation of the sheet using a structured-output AI call. The service SHALL use the organization's configured AI provider key when one exists, and SHALL fall back to a GrantFlow-funded low-cost model when no key is configured, so extraction quality does not depend on the organization having set up AI.

#### Scenario: Organization with a configured provider key
- **WHEN** an organization with a configured AI provider key uploads a file requiring AI extraction (no matching template fingerprint)
- **THEN** the service performs the extraction using that organization's provider key

#### Scenario: Organization with no configured provider key
- **WHEN** an organization with no AI provider key configured uploads a file requiring AI extraction
- **THEN** the service performs the extraction using a GrantFlow-funded low-cost model rather than skipping AI or blocking the import

### Requirement: AI extraction calls are audit-logged and rate-limited
The service SHALL record an audit log entry for every AI extraction call, including which funding source was used (organization's own key or GrantFlow-funded), token counts, and cost. The service SHALL apply a per-organization rate limit to GrantFlow-funded extraction calls.

#### Scenario: Audit log records funding source
- **WHEN** an AI extraction call completes, successfully or not
- **THEN** an audit log entry is written recording whether it was BYOK or GrantFlow-funded, along with token usage and cost

#### Scenario: Platform-funded rate limit exceeded
- **WHEN** an organization with no provider key configured exceeds its rate limit for GrantFlow-funded extraction calls
- **THEN** the service rejects the import request with an explanatory error rather than performing the call

### Requirement: Unresolved or low-confidence data is preserved, never dropped
When the AI extraction cannot confidently resolve part of a row to a canonical budget field, the service SHALL still include it in the created budget by placing the raw source data into the corresponding budget line's `extra_fields`, rather than omitting it from the import.

#### Scenario: Low-confidence line still produces line data
- **WHEN** a row's extraction confidence is below the threshold for a clean match
- **THEN** the resulting budget line is still created, with the raw row data included in `extra_fields`

### Requirement: Total and summary rows are excluded from line extraction
The service SHALL exclude rows that represent category totals or a grand total from becoming individual budget lines.

#### Scenario: Grand total row excluded
- **WHEN** a sheet contains a row whose first cell reads "Total Project" (or an equivalent total-row pattern)
- **THEN** that row does not appear as a budget line in the created budget

### Requirement: Donor templates are shared, named, and reused by structural fingerprint
The service SHALL persist a recognized template layout as a named, donor-scoped `DonorTemplateModel` record keyed by a fingerprint of the sheet's normalized structure. Fingerprint lookup SHALL be global across organizations: any organization uploading a file matching an existing template's fingerprint SHALL reuse its stored structure and skip AI extraction, regardless of which organization created that template record.

#### Scenario: First recognized upload can be saved as a template
- **WHEN** an organization completes an AI-extracted import and confirms the resulting budget without editing its lines
- **THEN** the service offers an optional prompt to save the extraction's structure as a named, reusable `DonorTemplateModel`

#### Scenario: A different organization reuses an existing template
- **WHEN** an organization uploads a file whose structure fingerprint matches an existing `DonorTemplateModel`, regardless of which organization created that template
- **THEN** the service extracts lines directly from the stored structure and does not perform an AI extraction call

#### Scenario: Changed layout does not match a stored template
- **WHEN** an uploaded file's structure fingerprint does not match any stored `DonorTemplateModel`
- **THEN** the service performs AI extraction rather than reusing an unrelated stored structure

### Requirement: A budget created via Excel import records its source template
When a budget is created via `POST /budgets/import-excel`, the service SHALL set the budget's existing `donor_template_id` field to the matched or newly created `DonorTemplateModel`, when one exists.

#### Scenario: Provenance recorded on template match
- **WHEN** an import matches an existing `DonorTemplateModel` by fingerprint
- **THEN** the created budget's `donor_template_id` references that template

#### Scenario: No provenance when no template is saved
- **WHEN** an import uses AI extraction and the user does not save the result as a template
- **THEN** the created budget's `donor_template_id` remains unset

### Requirement: Uploaded files are stored through existing cloud-agnostic storage
The service SHALL persist the uploaded Excel file using the existing cloud-agnostic storage capability rather than local disk.

#### Scenario: Uploaded file is retrievable via configured storage backend
- **WHEN** a file is uploaded for import
- **THEN** the service stores it through the cloud-agnostic storage service and records a reference to it, not a local filesystem path
