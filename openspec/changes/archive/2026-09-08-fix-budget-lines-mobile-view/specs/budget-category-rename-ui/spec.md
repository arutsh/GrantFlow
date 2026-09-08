## ADDED Requirements

### Requirement: Mobile category header does not overflow when the rename control is active
The system SHALL keep the mobile Budget Lines category header (name, count, subtotal, used-%) fully visible and non-overlapping regardless of category-name length or whether the inline rename control is open, by truncating the category name and allowing the header row to wrap rather than clip its contents.

#### Scenario: Long category name on mobile
- **WHEN** the mobile Budget Lines card list renders a category whose name is long enough to otherwise overflow the header row
- **THEN** the name is truncated and the subtotal and used-% pill on the same row remain fully visible

#### Scenario: Rename control opened on mobile
- **WHEN** a user activates the inline rename control on a category header in the mobile card list
- **THEN** the rename input and its confirm/cancel controls are fully visible, and the subtotal/used-% pill on that row is not pushed off-screen or clipped
