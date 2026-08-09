## ADDED Requirements

### Requirement: Responsive Navigation Shell
The system SHALL wrap every authenticated page in a navigation shell that, at viewport widths of `md` (768px) and above, renders a static, always-expanded sidebar occupying its own column of the layout, and at viewport widths below `md`, renders no persistent sidebar column — navigation SHALL instead be reachable via a menu button in the top bar.

#### Scenario: Desktop viewport shows the static sidebar
- **WHEN** an authenticated user views any dashboard page at a viewport width of 768px or wider
- **THEN** the sidebar SHALL render as a static, fully expanded column beside the main content

#### Scenario: Mobile viewport shows no persistent sidebar
- **WHEN** an authenticated user views any dashboard page at a viewport width below 768px, without having opened the menu
- **THEN** no sidebar column or overlay SHALL occupy or dim any part of the main content

### Requirement: Off-Canvas Mobile Drawer
Below the `md` breakpoint, the system SHALL provide the same navigation items as the desktop sidebar inside a drawer that is closed by default, opens by sliding in from the left edge over the page content when the top bar's menu button is pressed, and is dismissed by pressing a close control or the area outside the drawer.

#### Scenario: Opening the drawer
- **WHEN** a user on a viewport below 768px presses the top bar's menu button
- **THEN** the navigation drawer SHALL slide in from the left over the current page content, showing the same navigation entries as the desktop sidebar (Dashboard, Budgets, Reports, and, for donors, the expandable Grantees submenu, plus Settings and AI Mode)

#### Scenario: Dismissing via the close control
- **WHEN** the navigation drawer is open and the user presses its close control
- **THEN** the drawer SHALL slide out of view

#### Scenario: Dismissing via outside tap
- **WHEN** the navigation drawer is open and the user taps outside the drawer
- **THEN** the drawer SHALL slide out of view

### Requirement: Scrim Lifecycle Tied To Drawer State
The system SHALL render a dimming scrim behind the mobile drawer if and only if the drawer is open, so that the scrim and drawer always appear and disappear together.

#### Scenario: Scrim absent while drawer is closed
- **WHEN** the mobile navigation drawer is closed
- **THEN** no dimming scrim SHALL be present over the page content

#### Scenario: Scrim present while drawer is open
- **WHEN** the mobile navigation drawer is open
- **THEN** a dimming scrim SHALL cover the page content behind the drawer until the drawer is dismissed
