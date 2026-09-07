## ADDED Requirements

### Requirement: Desktop Budget Lines table offers a Grouped/Simple display toggle
The system SHALL provide a two-state display toggle — Grouped, Simple — on the desktop Budget Lines table, alongside the existing currency display toggle. Grouped SHALL show lines grouped by category with per-category subtotal rows (current default behavior). Simple SHALL show every line as a flat, ungrouped list with no subtotal rows.

#### Scenario: Default view is grouped by category
- **WHEN** the desktop Budget Lines table is first rendered
- **THEN** lines are grouped by category with subtotal rows, identical to current behavior, and the toggle shows "Grouped" as active

#### Scenario: Switching to Simple shows a flat list
- **WHEN** a user switches the toggle to "Simple"
- **THEN** the table re-renders as a flat list of every budget line with no category grouping and no subtotal rows

#### Scenario: Switching back to Grouped restores subtotals
- **WHEN** a user switches the toggle from "Simple" back to "Grouped"
- **THEN** the table re-renders grouped by category with subtotal rows restored

### Requirement: Mobile Budget Lines view is unaffected by the Grouped/Simple toggle
The mobile card layout of the Budget Lines view SHALL remain always grouped by category, unchanged by this toggle.

#### Scenario: Toggle has no effect on mobile
- **WHEN** the Budget Lines view is rendered on a mobile viewport, regardless of the desktop toggle's last-set state
- **THEN** the mobile card layout shows lines grouped by category with subtotals, as it does today
