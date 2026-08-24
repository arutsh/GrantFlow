## ADDED Requirements

### Requirement: Excel upload produces a draft budget
The chat service SHALL expose `POST /chat/import-excel` accepting a single `.xlsx` file upload, orchestrate extraction across the budget and AI services, and create a budget in `ai_draft` status via a `create_budget_with_lines` tool call against budget service's budget-with-lines creation path, without requiring the user to map columns before upload. The budget service SHALL expose `POST /budgets/excel/prepare-import`, accepting the same upload, to clean the sheet and attempt a template fingerprint match on chat service's behalf.

#### Scenario: Successful import creates an ai_draft budget
- **WHEN** an authenticated user uploads a `.xlsx` file with at least one identifiable budget line
- **THEN** chat service creates a budget with `status: ai_draft` and returns its id, with lines populated from the extracted data

#### Scenario: File is not a valid Excel workbook
- **WHEN** the uploaded file cannot be parsed as an `.xlsx` workbook
- **THEN** budget service's `prepare-import` step rejects the request with an error and chat service creates no budget

### Requirement: AI-based line extraction is BYOK-preferred with a platform-funded fallback
The AI service SHALL extract category, description, amount, and currency per budget line from a cleaned representation of the sheet — provided by chat service, sourced from budget service's `prepare-import` step — using a structured-output AI call. The AI service SHALL use the organization's configured AI provider key when one exists, and SHALL fall back to a GrantFlow-funded low-cost model when no key is configured, so extraction quality does not depend on the organization having set up AI. This behavior is unchanged by which service calls it — only the caller (chat service, not budget service) changed.

#### Scenario: Organization with a configured provider key
- **WHEN** an organization with a configured AI provider key uploads a file requiring AI extraction (no matching template fingerprint)
- **THEN** the AI service performs the extraction using that organization's provider key

#### Scenario: Organization with no configured provider key
- **WHEN** an organization with no AI provider key configured uploads a file requiring AI extraction
- **THEN** the AI service performs the extraction using a GrantFlow-funded low-cost model rather than skipping AI or blocking the import

### Requirement: AI extraction calls are audit-logged and rate-limited
The AI service SHALL record an audit log entry for every AI extraction call, including which funding source was used (organization's own key or GrantFlow-funded), token counts, and cost. The AI service SHALL apply a per-organization rate limit to GrantFlow-funded extraction calls.

#### Scenario: Audit log records funding source
- **WHEN** an AI extraction call completes, successfully or not
- **THEN** an audit log entry is written recording whether it was BYOK or GrantFlow-funded, along with token usage and cost

#### Scenario: Platform-funded rate limit exceeded
- **WHEN** an organization with no provider key configured exceeds its rate limit for GrantFlow-funded extraction calls
- **THEN** the AI service rejects the request with an explanatory error, and chat service surfaces this as a failed import rather than performing the call

### Requirement: Unresolved or low-confidence data is preserved, never dropped
When the AI extraction cannot confidently resolve part of a row to a canonical budget field, the service SHALL still include it in the created budget by placing the raw source data into the corresponding budget line's `extra_fields`, rather than omitting it from the import.

#### Scenario: Low-confidence line still produces line data
- **WHEN** a row's extraction confidence is below the threshold for a clean match
- **THEN** the resulting budget line is still created, with the raw row data included in `extra_fields`

### Requirement: Total and summary rows are excluded from line extraction
Budget service's `prepare-import` step SHALL exclude rows that represent category totals or a grand total from becoming individual budget lines.

#### Scenario: Grand total row excluded
- **WHEN** a sheet contains a row whose first cell reads "Total Project" (or an equivalent total-row pattern)
- **THEN** that row does not appear as a budget line in the created budget

### Requirement: Donor templates are shared, named, and reused by structural fingerprint
Budget service SHALL persist a recognized template layout as a named, donor-scoped `DonorTemplateModel` record keyed by a fingerprint of the sheet's normalized structure. Fingerprint lookup SHALL be global across organizations: any organization uploading a file matching an existing template's fingerprint SHALL reuse its stored structure and skip AI extraction, regardless of which organization created that template record.

#### Scenario: First recognized upload can be saved as a template
- **WHEN** an organization completes an AI-extracted import and confirms the resulting budget without editing its lines
- **THEN** chat service offers an optional prompt to save the extraction's structure as a named, reusable `DonorTemplateModel`

#### Scenario: A different organization reuses an existing template
- **WHEN** an organization uploads a file whose structure fingerprint matches an existing `DonorTemplateModel`, regardless of which organization created that template
- **THEN** budget service's `prepare-import` step returns lines extracted directly from the stored structure, and chat service does not call the AI extraction endpoint

#### Scenario: Changed layout does not match a stored template
- **WHEN** an uploaded file's structure fingerprint does not match any stored `DonorTemplateModel`
- **THEN** budget service's `prepare-import` step reports no match, and chat service performs AI extraction rather than reusing an unrelated stored structure

### Requirement: A budget created via Excel import records its source template
When chat service calls `create_budget_with_lines` to create a budget from an Excel import, it SHALL pass the matched or newly created `DonorTemplateModel`'s id as `donor_template_id`, and budget service SHALL set the created budget's existing `donor_template_id` field from it, when one exists.

#### Scenario: Provenance recorded on template match
- **WHEN** an import matches an existing `DonorTemplateModel` by fingerprint
- **THEN** the created budget's `donor_template_id` references that template

#### Scenario: No provenance when no template is saved
- **WHEN** an import uses AI extraction and the user does not save the result as a template
- **THEN** the created budget's `donor_template_id` remains unset

### Requirement: Uploaded files are stored through existing cloud-agnostic storage
Budget service's `prepare-import` step SHALL persist the uploaded Excel file using the existing cloud-agnostic storage capability rather than local disk.

#### Scenario: Uploaded file is retrievable via configured storage backend
- **WHEN** a file is uploaded for import
- **THEN** budget service stores it through the cloud-agnostic storage service and records a reference to it, not a local filesystem path
