# budget-category-rename-ui Specification

## Purpose
TBD - created by change budget-lines-view-controls. Update Purpose after archive.

## Requirements
### Requirement: Budget category name is inline-editable from the Budget Lines view
The system SHALL let a user with edit access rename a budget category's name from its group header in the Budget Lines table, without navigating away from the view, by calling `PATCH /budget-categories/{id}`.

#### Scenario: User renames a category
- **WHEN** an editable budget's Budget Lines table is grouped by category and the user activates the rename control on a category group header, changes the name, and confirms (Enter or blur)
- **THEN** the system sends a `PATCH /budget-categories/{id}` request with the new name, and on success the new name is shown immediately on every line in that group without a full page reload

#### Scenario: User cancels a rename in progress
- **WHEN** a user has opened the inline rename input and presses Escape (or otherwise cancels) before confirming
- **THEN** the category name reverts to its original value and no request is sent

#### Scenario: Rename affordance hidden on a read-only budget
- **WHEN** the Budget Lines table is rendered in read-only mode
- **THEN** no rename affordance is shown on any category group header

#### Scenario: Rename affordance hidden for the uncategorized group
- **WHEN** the Budget Lines table is grouped and includes an "uncategorized" group (lines with no category)
- **THEN** that group's header shows no rename affordance, since there is no category to rename

#### Scenario: Rename affordance unavailable in List (ungrouped) view
- **WHEN** the desktop Budget Lines table's Grouped/List toggle is set to List
- **THEN** no rename affordance is shown anywhere in the table, since there is no category group header to attach it to; switching back to Grouped restores it

### Requirement: Mobile category header does not overflow when the rename control is active
The system SHALL keep the mobile Budget Lines category header (name, count, subtotal, used-%) fully visible and non-overlapping regardless of category-name length or whether the inline rename control is open, by truncating the category name and allowing the header row to wrap rather than clip its contents.

#### Scenario: Long category name on mobile
- **WHEN** the mobile Budget Lines card list renders a category whose name is long enough to otherwise overflow the header row
- **THEN** the name is truncated and the subtotal and used-% pill on the same row remain fully visible

#### Scenario: Rename control opened on mobile
- **WHEN** a user activates the inline rename control on a category header in the mobile card list
- **THEN** the rename input and its confirm/cancel controls are fully visible, and the subtotal/used-% pill on that row is not pushed off-screen or clipped

### Requirement: Duplicate category name on rename is surfaced inline
When a rename would collide with another category already existing in the same budget, the system SHALL show the rejection inline near the rename input rather than failing silently.

#### Scenario: Rename collides with an existing category name in the same budget
- **WHEN** a user renames a category to a name that already exists in the same budget and the `PATCH` request is rejected with a duplicate-name error
- **THEN** the input stays open, showing the attempted name and an inline error message, and the category's name is not changed
