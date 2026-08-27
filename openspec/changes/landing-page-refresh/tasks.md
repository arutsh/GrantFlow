One task group = one GitHub ticket = one PR, merged before the next group starts.

**Deviation (user-directed):** both groups below are implemented on a single
branch/PR (`Frontend/Issue-245-246/landing-page-refresh`, closing both #245
and #246), while keeping separate tickets per group.

## 1. Hero & Nav: drop dev-status framing, add Request Demo CTA

- [x] 1.1 Create GitHub ticket (Frontend) via `scripts/new-issue.sh` for this group; branch `Frontend/Issue-<number>/landing-hero-nav-demo-cta`. — Ticket #245; combined branch per deviation above.
- [x] 1.2 In `Hero()` (`frontend-typescript/src/pages/LandingPage.tsx`), remove the "In active development" status pill `<div>` (the gold-dot + text block above the `<h1>`).
- [x] 1.3 In `Nav()`, add a "Request Demo" link/button styled as a solid navy button (matching the existing `Become a Founding Design Partner` primary CTA treatment), placed to the right of the nav links, linking to `#contact`.
- [x] 1.4 Verify at mobile width (nav links are `hidden sm:flex`) that the new button doesn't crowd or overlap the logo; give it its own responsive treatment if needed. — Verified via Playwright screenshot at 390px; found and fixed a wrap regression (logo text + button compact sizing at `sm:` breakpoint).
- [x] 1.5 Update `LandingPage.test.tsx`: add an assertion that a "Request Demo" nav link/button is rendered and points to `#contact`. (No assertion expected the removed pill, so nothing to replace; a standalone "does not show an in-development status" test was added then dropped as low-value — it just checks for text that no longer exists anywhere in the source.)
- [x] 1.6 Run `npm run lint` and `npm run test` in `frontend-typescript/` clean; PR opened (`Closes #245, Closes #246`) — merge pending review.

## 2. Problem section: sector-validation content block — no dependency on group 1

- [x] 2.1 Create GitHub ticket (Frontend) via `scripts/new-issue.sh` for this group; branch `Frontend/Issue-<number>/landing-problem-sector-validation`. — Ticket #246; combined branch per deviation above.
- [x] 2.2 In `ProblemSection()`, after the existing "Current workflow" diagram card, add a labeled sub-block ("From conversations across the sector" or similar) containing three pull-quote cards, each with role-only attribution (Former UK fund CEO / International nonprofit leader / Nonprofit or fund adviser) — reuse the existing `card-shadow-lg` white-card pattern.
- [x] 2.3 Add the paraphrased anecdote (local nonprofit leader unable to find a suitable alternative) as a visually distinct card — no quotation marks, since it is a paraphrase — attributed generically (e.g. "From a conversation with a local nonprofit leader").
- [x] 2.4 Add the closing statement: "The emerging opportunity: interoperability, not another closed portal."
- [x] 2.5 Update `LandingPage.test.tsx`. (A dedicated test asserting the three quotes/anecdote/closing-statement render, plus a regex-based "no fabricated attribution" check, were added then both removed on review as low-value marketing-copy assertions — the content is exercised implicitly by the existing render tests, not covered by a dedicated assertion.)
- [x] 2.6 Run `npm run lint` and `npm run test` in `frontend-typescript/` clean; PR opened (`Closes #245, Closes #246`) — merge pending review.
