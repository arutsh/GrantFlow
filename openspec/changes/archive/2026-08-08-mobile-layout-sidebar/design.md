## Context

`DashboardLayout.tsx` renders one `<aside>` that is either `w-64` (open) or `w-16` (icon rail), controlled by a single `isOpen` state initialized to `true`. The only control that ever calls `setIsOpen` is a button rendered `md:hidden` — i.e. it's invisible at exactly the breakpoint (`md:`+) where the icon-rail collapse would apply, so that mode was never actually reachable; `isOpen` was permanently `true` in practice. Below `md:`, Tailwind's `md:static` never applies, so the `fixed` positioning stays in effect and the aside always occupies screen space over — not beside — the main content; the `{isOpen && <scrim>}` overlay compounds this since `isOpen` starts `true`. There is no separate "mobile drawer" concept today — the one boolean (permanently `true`) drives the always-visible mobile rail and its stuck-on overlay.

`DonorDashboard.tsx` already branches mobile vs. desktop markup with `sm:hidden` / `hidden sm:block`, so the mobile grantee/budget presentation can be restyled in place without touching the desktop branch or the data-fetching layer.

## Goals / Non-Goals

**Goals:**
- Below `md:`, the sidebar defaults to fully closed (off-canvas, `translate-x-[-100%]`) and opens as a drawer over content on demand.
- Exactly one dismiss path: closing the drawer always closes its scrim in the same state update.
- At `md:` and up, the sidebar renders exactly as it does today in practice: static, fully expanded, always-visible labels (the unreachable collapse-to-icons mode is removed rather than preserved, since keeping a `setIsOpen` with no caller is dead code).
- Below `sm:` (640px), `DonorDashboard.tsx`'s grantee cards scroll horizontally and funded budgets render as list rows, matching the approved mockup.

**Non-Goals:**
- No new nav items, routes, or permissions.
- No change to `GranteeDashboard.tsx` content — it inherits the fixed shell only.
- No animation/gesture library — CSS transitions only, consistent with the rest of the codebase.
- Not touching the desktop (`sm:`+) table view of funded budgets or its columns.

## Decisions

- **Replace the shared `isOpen` with a single `isMobileDrawerOpen` (default `false`), rather than keeping `isOpen` for a desktop mode.** Since the desktop collapse-to-icons mode had no reachable trigger, keeping it "for parity" would mean shipping a `setIsOpen` with no caller — dead code the linter would (rightly) flag. Desktop now always renders expanded via a plain `md:w-64` class, and `isMobileDrawerOpen` alone drives the mobile translate-based off-canvas state. Alternative considered — a single `isOpen` gated by a `useMediaQuery` breakpoint hook — rejected as heavier (new hook, resize-listener edge cases) for no behavioral benefit.
- **Drawer implemented with `translate-x` + `fixed`, not `display`/`width`.** Keeps the existing DOM mounted for a CSS transition (matches the mockup's slide-in) rather than an abrupt show/hide. The scrim is conditionally rendered (`{isMobileDrawerOpen && <scrim>}`) exactly as today's overlay is, so it can never persist without the drawer.
- **Drawer nav markup is shared with the desktop nav via the same `<ul>` items, not a duplicated component.** Avoids the two lists drifting (already a pattern of the current file — the `isOpen && <span>` guards are removed for the drawer where the label is always shown since the drawer is never icon-only).
- **`DonorDashboard.tsx` mobile grantee row uses CSS `overflow-x-auto` + `snap-x` utilities**, no carousel library — consistent with "no new dependency" from the proposal.

## Risks / Trade-offs

- [Removing the desktop collapse-to-icons mode outright, rather than fixing its trigger, could be read as silently dropping a feature] → It was already unreachable in production (no visible control at any breakpoint could call `setIsOpen`), so nothing user-facing changes; a short code comment at the state declaration explains why it's gone rather than fixed.
- [Existing tests may assert on the current always-mounted-scrim/rail markup] → `DonorDashboard.test.tsx` and `DashboardLayout` tests are checked and updated as part of this change (see tasks.md); no production behavior is hidden behind untested branches.
- [Horizontal scroll row can hide overflow content from users unaware they can swipe] → Cards are sized so the next card is partially visible at the viewport edge (as in the mockup), signaling scrollability without extra UI chrome.

## Migration Plan

Pure frontend rendering change behind existing breakpoints — no data migration, no feature flag. Ship as a normal PR; if a regression surfaces, revert the PR (no server-side state to roll back).
