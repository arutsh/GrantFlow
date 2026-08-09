## Why

On mobile viewports the app's left sidebar (`DashboardLayout.tsx`) never has a true closed state: it defaults to `isOpen = true`, so below the `md` breakpoint it renders as either a full-width or icon-width rail permanently overlapping page content, with its dim overlay stuck on. Users on phones see clipped headers, a squeezed hero stat card, and no clean way to dismiss the rail. A reviewed mockup ([artifact](https://claude.ai/code/artifact/537d23c7-4682-4bd7-99b0-7680d30e1eb7)) proposes an off-canvas drawer pattern (functionally modeled on Jack & Jill's job-board nav) plus a mobile-appropriate content layout for the donor dashboard, and the user has approved it for implementation.

## What Changes

- `DashboardLayout.tsx`'s sidebar becomes closed-by-default below `md`, rendered as a full off-canvas drawer (~78% width, max 270px) that slides in over content rather than sharing width with it.
- A scrim/backdrop is only mounted while the drawer is open; tapping it or the close (✕) button dismisses drawer and scrim together.
- The mobile top bar gains a menu (hamburger) button that opens the drawer; the existing desktop static sidebar behavior (`md:` and up) is unchanged.
- Drawer content mirrors the existing desktop nav one-for-one (Dashboard, Budgets, Reports, expandable Grantees submenu, Settings, AI Mode) — no new nav items, no new routes.
- `DonorDashboard.tsx` mobile presentation (`<sm`, i.e. below 640px): the grantee grid becomes a horizontal, snap-scrolling row of cards instead of a stacked/wrapped grid; the funded-budgets mobile card list is restyled as compact list rows (name, grantee, amount, status chip) — the existing `sm:hidden` mobile branch is restyled, not newly introduced. Desktop table view (`sm:` and up) is unchanged.
- **BREAKING**: none — this only changes rendering below the `md`/`sm` breakpoints; no API, route, or prop-contract changes.

## Capabilities

### New Capabilities
- `app-shell`: The responsive navigation shell wrapping all authenticated pages — static sidebar at `md:`+ (unchanged), off-canvas drawer + scrim + menu button below `md:` (new). Owns `DashboardLayout.tsx`.

### Modified Capabilities
- `donor-dashboard`: The "Donor Dashboard Page" requirement's mobile scenario is updated — below `sm:`, grantees render as a horizontal-scrolling card row (not a stacked grid) and funded budgets render as list rows (not the current mobile card block), while the `sm:`+ table/grid behavior is unchanged.

## Impact

- **Frontend**: `frontend-typescript/src/pages/Dashboard/DashboardLayout.tsx` (drawer/scrim/menu-button behavior), `frontend-typescript/src/pages/DonorDashboard/DonorDashboard.tsx` (mobile grantee/budget markup), `frontend-typescript/src/pages/DonorDashboard/DonorDashboard.test.tsx` (update/add coverage for new mobile markup).
- **No backend, API, or database changes.**
- **No new dependencies** — implemented with existing Tailwind utility classes and `lucide-react` icons already in use.
- Visual-only change; no effect on other dashboards (`GranteeDashboard.tsx`) beyond inheriting the fixed drawer shell from `DashboardLayout.tsx`.
