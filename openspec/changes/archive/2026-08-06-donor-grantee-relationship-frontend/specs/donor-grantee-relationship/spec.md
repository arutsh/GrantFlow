## ADDED Requirements

### Requirement: Donor manages their grantee list from Settings
The system SHALL provide a UI on the Settings page, visible only to donor customers, where a donor can view their currently approved grantees, search for an NGO customer by name to approve as a new grantee, and revoke an existing approval, without leaving Settings.

#### Scenario: Donor views their approved grantees
- **WHEN** a donor customer opens their Settings page
- **THEN** the UI displays their current list of approved grantees, fetched from their own donor-side relationship list

#### Scenario: Donor searches for a grantee to add
- **WHEN** a donor enters an NGO name and submits the search
- **THEN** the UI displays matching NGO customers who are not already an approved grantee of this donor

#### Scenario: Donor approves a new grantee
- **WHEN** a donor selects an "Add" action on a search result
- **THEN** the UI creates the relationship and the grantee appears in the donor's approved list without a page reload

#### Scenario: Donor revokes an approved grantee
- **WHEN** a donor selects a "Revoke" action on an entry in their approved list
- **THEN** the UI removes the relationship and the entry disappears from the approved list without a page reload

#### Scenario: No approved grantees yet
- **WHEN** a donor with zero approved grantees opens Settings
- **THEN** the UI shows an explicit empty state rather than a blank section

### Requirement: Grantee selects a donor when creating a budget
The system SHALL let a grantee, when creating a budget, choose a funding donor from their own list of donors that have approved them, and SHALL submit the selection as the budget's `funding_customer_id`.

#### Scenario: Grantee picks an approved donor
- **WHEN** a grantee opens the add-budget form and selects one of their approved donors
- **THEN** the created budget has `funding_customer_id` set to that donor's id

#### Scenario: Grantee has no approved donors
- **WHEN** a grantee with zero approving donors opens the add-budget form
- **THEN** the UI shows an explicit message explaining no approved donors exist yet, instead of an empty selectable control

#### Scenario: Donor selection and free-text funder are mutually exclusive
- **WHEN** a grantee has selected a donor from the picker and then enters a value in the free-text funder-name field (or vice versa)
- **THEN** the UI clears the other field so only one of `funding_customer_id` or `external_funder_name` is submitted

#### Scenario: Budget creation without any funder is still possible
- **WHEN** a grantee submits the add-budget form with neither a donor selected nor a free-text funder name entered
- **THEN** the budget is created with neither `funding_customer_id` nor `external_funder_name` set, unaffected by this change

### Requirement: Grantee edits an existing budget's funder between an approved donor and a custom name
The system SHALL let a grantee editing an already-created budget choose the funder from their own approved-donor list or enter a custom name, in either direction, with the same mutual-exclusivity rule as budget creation.

#### Scenario: Editing pre-selects the donor for a donor-linked budget
- **WHEN** a grantee opens the edit form for a budget whose funder is one of their approved donors
- **THEN** the donor picker shows that donor selected, and the free-text field is empty and disabled

#### Scenario: Editing pre-fills the custom name for a free-text-funded budget
- **WHEN** a grantee opens the edit form for a budget whose funder is a free-text name (no linked donor)
- **THEN** the free-text field shows that name, and no donor is selected in the picker

#### Scenario: Switching a donor-linked budget to a custom funder clears the donor link
- **WHEN** a grantee clears the donor selection and enters a custom funder name, then saves
- **THEN** the budget's `funding_customer_id` is explicitly cleared and `external_funder_name` is set to the entered name

#### Scenario: Switching a custom-funded budget to an approved donor clears the custom name
- **WHEN** a grantee selects an approved donor on a budget that previously had a free-text funder, then saves
- **THEN** the budget's `funding_customer_id` is set to that donor's id and `external_funder_name` is cleared
