Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

Note: per explicit user request, both groups below shipped together as one ticket (#203, `Frontend/Issue-203/mobile-nav-and-donor-mobile-layout`) and one PR instead of two.

## 1. App Shell Mobile Drawer

- [x] 1.1 Create GitHub ticket via `scripts/new-issue.sh` (branch `Frontend/Issue-203/mobile-nav-and-donor-mobile-layout`), move to In Progress
- [x] 1.2 In `DashboardLayout.tsx`, add a new `isMobileDrawerOpen` state (default `false`). (The planned "independent desktop `isOpen`" turned out to be unreachable dead state — its only toggle button was `md:hidden` — so it was removed rather than kept; see design.md.)
- [x] 1.3 Wire the top bar's menu (hamburger) button to `isMobileDrawerOpen`
- [x] 1.4 Rework the `<aside>`'s below-`md` rendering to be `fixed` + `translate-x`-based (off-canvas by default, sliding in over content when `isMobileDrawerOpen`), always showing full nav-item labels; `md:`+ renders static and fully expanded (matching its only-ever-reachable prior state)
- [x] 1.5 Make the scrim conditionally rendered on `isMobileDrawerOpen` only, and close on scrim tap or the drawer's close control, dismissing drawer and scrim together
- [x] 1.6 Add/update tests for `DashboardLayout.tsx` covering: drawer closed and no scrim present by default below `md`, drawer opens on menu press, drawer and scrim both dismiss on backdrop tap and on close control, desktop `md:`+ sidebar behavior unchanged
- [ ] 1.7 Run `npm run lint` and `npm test` (frontend-typescript) clean; PR merged (`Closes #203`)

## 2. Donor Dashboard Mobile Content — independent of group 1

- [x] 2.1 Create GitHub ticket via `scripts/new-issue.sh` — shared with group 1 (#203)
- [x] 2.2 In `DonorDashboard.tsx`, restyle the grantee directory below `sm` (640px) into a horizontally scrolling, snap row of cards (`overflow-x-auto`, scroll-snap), replacing the current wrapping grid at that breakpoint; leave the `sm:`+ grid unchanged
- [x] 2.3 Restyle the existing `sm:hidden` funded-budgets mobile block into compact list rows (budget name, grantee name, amount, status chip) per the approved mockup, replacing the current stacked card block; leave the `sm:`+ table unchanged
- [x] 2.4 Update `DonorDashboard.test.tsx` queries/assertions affected by the new mobile markup (none needed — new markup preserves the same text-node values the existing assertions check)
- [x] 2.5 Manually verify at ~375px and ~414px viewport widths: no clipped text, grantee row scrolls smoothly, budget rows readable (verified by user)
- [ ] 2.6 Run `npm run lint` and `npm test` (frontend-typescript) clean; PR merged (`Closes #203`)
