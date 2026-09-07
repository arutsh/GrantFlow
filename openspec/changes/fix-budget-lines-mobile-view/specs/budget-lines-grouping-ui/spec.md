## MODIFIED Requirements

### Requirement: Desktop Budget Lines table offers a Grouped/List display toggle
The system SHALL provide a two-state display toggle — Grouped, List — on the desktop Budget Lines table, alongside the existing currency display toggle. Grouped SHALL show lines grouped by category with per-category subtotal rows (current default behavior). List SHALL show every line as a flat, ungrouped list with no subtotal rows. This is a label change only — the toggle's underlying state has two values, previously surfaced as "Grouped"/"Simple", now surfaced as "Grouped"/"List"; the flat-list behavior itself is unchanged.

#### Scenario: Default view is grouped by category
- **WHEN** the desktop Budget Lines table is first rendered
- **THEN** lines are grouped by category with subtotal rows, identical to current behavior, and the toggle shows "Grouped" as active

#### Scenario: Switching to List shows a flat list
- **WHEN** a user switches the toggle to "List"
- **THEN** the table re-renders as a flat list of every budget line with no category grouping and no subtotal rows

#### Scenario: Switching back to Grouped restores subtotals
- **WHEN** a user switches the toggle from "List" back to "Grouped"
- **THEN** the table re-renders grouped by category with subtotal rows restored

## ADDED Requirements

### Requirement: Mobile line-item card places Edit/Delete inline with the amount
The mobile Budget Lines card list SHALL place a line item's Edit and Delete controls in the same row as its amount, rather than in a separate row beneath the usage indicator.

#### Scenario: Short description
- **WHEN** a mobile line-item card renders a description short enough to fit on one line
- **THEN** the description, amount, Edit control, and Delete control all appear in that line's row, and no separate row exists containing only the Edit/Delete controls

#### Scenario: Long description wraps
- **WHEN** a mobile line-item card renders a description long enough to wrap to two lines
- **THEN** the amount, Edit control, and Delete control remain fully visible and are not pushed off-card or clipped
