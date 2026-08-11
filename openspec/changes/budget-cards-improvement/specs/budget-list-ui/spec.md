## ADDED Requirements

### Requirement: Archived status is visually distinct from active statuses
The budget status badge SHALL render the `archived` status with a structurally different treatment (outline, not a solid fill) from `draft`, `ai_draft`, and `confirmed`, so it does not rely on hue alone to be distinguishable from `draft`.

#### Scenario: Draft and archived badges shown side by side
- **WHEN** a budgets list contains both a `draft` and an `archived` budget
- **THEN** the `draft` badge renders as a filled pill and the `archived` badge renders as a dashed-outline pill with an archive icon, so the two are distinguishable without reading the label text

#### Scenario: Active statuses keep their existing fill treatment
- **WHEN** a budget has status `draft`, `ai_draft`, or `confirmed`
- **THEN** its badge renders as a solid-fill pill using that status's existing color from `STATUS_STYLES`, unchanged by this requirement

### Requirement: Budget card delete requires confirmation
A budget card's delete action SHALL require an explicit confirmation step before the delete request is issued.

#### Scenario: User taps Delete on a budget card
- **WHEN** a user taps the Delete action on a budget card
- **THEN** the card shows an inline Yes/No confirmation in place of the action buttons, and no delete request is sent until the user taps Yes

#### Scenario: User cancels the delete confirmation
- **WHEN** a user taps No (or otherwise dismisses) the inline delete confirmation
- **THEN** the card returns to its normal action buttons and no delete request is sent

### Requirement: Budget card actions meet minimum touch target size
Each action button in a budget card's footer SHALL have a minimum tap target height of 44px.

#### Scenario: Card actions rendered on any viewport
- **WHEN** a budget card is rendered
- **THEN** both the Edit and Delete controls in the card footer have a minimum height of 44px

### Requirement: Mobile filter controls collapse into a single trigger
On viewports narrower than the `lg` breakpoint, the Status, Currency, and Duration filter dropdowns SHALL be presented behind a single "Filters" trigger button rather than as three separate full-width controls.

#### Scenario: Budgets page opened on a mobile viewport
- **WHEN** the budgets page is viewed at a width below the `lg` breakpoint
- **THEN** the search input and a single "Filters" button are shown, and the Status/Currency/Duration controls are not rendered as separate full-width elements

#### Scenario: Filters trigger shows an active filter count
- **WHEN** one or more of Status, Currency, or Duration filters are active and the viewport is below the `lg` breakpoint
- **THEN** the "Filters" trigger button displays a badge with the count of active filter selections

#### Scenario: Opening the filters trigger
- **WHEN** a user taps the "Filters" trigger button on a mobile viewport
- **THEN** a sheet opens containing the Status, Currency, and Duration filter groups plus Clear and Apply controls, and closes when the user applies, taps outside it, or dismisses it

#### Scenario: Desktop filter layout is unchanged
- **WHEN** the budgets page is viewed at or above the `lg` breakpoint
- **THEN** the Status, Currency, and Duration controls render as separate controls in the existing single-row layout, not behind a "Filters" trigger

### Requirement: Filter chips use the shared status color palette
The removable status filter chips SHALL derive their colors from the same `STATUS_STYLES`/`STATUS_ACCENT` constants used by the status badge, rather than an independently defined color set.

#### Scenario: A status filter is applied
- **WHEN** a user filters the budgets list by a status (e.g. `draft`)
- **THEN** the removable filter chip for that status uses the same color as that status's badge elsewhere on the page
