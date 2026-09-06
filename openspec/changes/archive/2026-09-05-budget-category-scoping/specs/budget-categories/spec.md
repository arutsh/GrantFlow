## ADDED Requirements

### Requirement: Categories are owned by exactly one budget
Every `BudgetCategoryModel` row SHALL belong to exactly one budget via a required `budget_id` foreign key. No category row SHALL ever be referenced by budget lines belonging to more than one budget.

#### Scenario: Two budgets create categories with the same name
- **WHEN** Budget A and Budget B (regardless of whether they belong to the same or different customers) each get a line created with `category_name="Travel"` and neither already has a category named "Travel"
- **THEN** two distinct `BudgetCategoryModel` rows are created, one scoped to Budget A's `budget_id` and one scoped to Budget B's `budget_id`

#### Scenario: Deleting a budget deletes its categories
- **WHEN** a budget is deleted
- **THEN** every `BudgetCategoryModel` row scoped to that budget's `budget_id` is deleted along with it

### Requirement: Category name resolution is deduped within one budget, never across budgets
When a line is created by category name rather than category id, the backend SHALL look up an existing category by `(budget_id, name)`. A match within the same budget SHALL be reused; no match outside that budget SHALL ever be considered.

#### Scenario: Repeated category name within one import
- **WHEN** an Excel import creates multiple lines in the same new budget, several of which resolve to `category_name="Personnel"`
- **THEN** all of those lines reference the same single `BudgetCategoryModel` row, scoped to that budget

#### Scenario: Same category name in a different budget is not reused
- **WHEN** Budget A already has a category named "Personnel" and a line is created in Budget B with `category_name="Personnel"`
- **THEN** a new `BudgetCategoryModel` row scoped to Budget B is created rather than reusing Budget A's row

### Requirement: Category name and code can be edited, scoped to the owning budget
The backend SHALL provide `PATCH /budget-categories/{id}`, callable only by the owning budget's customer, which updates a category's `name` and/or `code`. The request SHALL be rejected if the category's budget does not belong to the requesting customer, or if the owning budget is locked (confirmed).

#### Scenario: Owner renames a category
- **WHEN** a user belonging to the customer that owns the category's budget calls `PATCH /budget-categories/{id}` with a new `name`
- **THEN** the category's `name` is updated, `updated_by` is set to the requesting user, and no other budget's data is affected

#### Scenario: Rename rejected for a category owned by another customer's budget
- **WHEN** a user calls `PATCH /budget-categories/{id}` for a category whose owning budget belongs to a different customer
- **THEN** the backend rejects the request and the category is unchanged

#### Scenario: Rename rejected once the owning budget is confirmed
- **WHEN** a user calls `PATCH /budget-categories/{id}` for a category whose owning budget's status is `confirmed`
- **THEN** the backend rejects the request, matching the existing rule that budget lines cannot be changed once a budget is confirmed

### Requirement: Categories can be deleted, scoped to the owning budget
The backend SHALL provide `DELETE /budget-categories/{id}`, subject to the same ownership and confirmed-budget-lock checks as edit.

#### Scenario: Owner deletes an unused category
- **WHEN** a user belonging to the customer that owns the category's budget calls `DELETE /budget-categories/{id}`
- **THEN** the category row is deleted and any budget lines that referenced it have `category_id` set to null

### Requirement: Categories can be listed per budget
The backend SHALL provide `GET /budget-categories/by-budget/{budget_id}`, returning only categories scoped to that budget, subject to the requesting user belonging to the budget's owning customer.

#### Scenario: Listing a budget's categories
- **WHEN** a user belonging to the owning customer calls `GET /budget-categories/by-budget/{budget_id}`
- **THEN** the backend returns exactly the categories whose `budget_id` matches, and none from any other budget
