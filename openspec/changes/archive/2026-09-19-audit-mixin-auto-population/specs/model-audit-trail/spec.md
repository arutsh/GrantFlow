## ADDED Requirements

### Requirement: Automatic created_by population on insert
When a new row is inserted for any model using `AuditMixin` or `AuditColumnsMixin`, the system SHALL set `created_by` to the id of the currently authenticated user, without requiring the inserting CRUD code to pass it explicitly.

#### Scenario: Authenticated request creates an audited row
- **WHEN** an authenticated user makes a request that inserts a new row for a model using `AuditMixin`/`AuditColumnsMixin`
- **THEN** the persisted row's `created_by` equals that user's id

#### Scenario: Insert with no authenticated request context
- **WHEN** a row is inserted for a model using `AuditMixin`/`AuditColumnsMixin` from a context with no authenticated user (e.g. a Celery worker task or a seed script)
- **THEN** the persisted row's `created_by` is `NULL` and no exception is raised

### Requirement: Automatic updated_by population on insert and update
When a row for a model using `AuditMixin`/`AuditColumnsMixin` is inserted or updated, the system SHALL set `updated_by` to the id of the currently authenticated user, without requiring the CRUD code to pass it explicitly.

#### Scenario: Authenticated request updates an audited row
- **WHEN** an authenticated user (different from the original creator) makes a request that updates an existing row for a model using `AuditMixin`/`AuditColumnsMixin`
- **THEN** the persisted row's `updated_by` equals the updating user's id, distinct from `created_by`

#### Scenario: Authenticated request creates an audited row
- **WHEN** an authenticated user creates a new row for a model using `AuditMixin`/`AuditColumnsMixin`
- **THEN** the persisted row's `updated_by` equals that user's id, matching `created_by`

### Requirement: Non-id primary keys can use audit columns
A model whose primary key is not named `id` SHALL be able to gain `created_at`/`updated_at`/`created_by`/`updated_by` behavior via a mixin that does not declare a primary key column.

#### Scenario: Model with a custom primary key adopts the audit columns
- **WHEN** a model declares its own primary key column and mixes in the PK-less audit columns mixin
- **THEN** the model gains `created_at`, `updated_at`, `created_by`, and `updated_by` columns with the same automatic population behavior as `AuditMixin`, without a conflicting second primary key definition

### Requirement: No cross-service foreign key on audit columns
The `created_by`/`updated_by` columns SHALL remain plain UUID columns with no foreign-key constraint to any users table, since user records live in a separate service/database.

#### Scenario: Referenced user no longer exists
- **WHEN** a row's `created_by` or `updated_by` references a user id that has since been deleted from the users service
- **THEN** no database constraint violation occurs, since no foreign key exists between services
