## Why

The public landing page still signals "In active development," but the budget/AI MVP is functional and the project is ready to be shown to prospective nonprofit and donor partners. Field conversations (informal sector interviews plus a direct anecdote from a local nonprofit leader who couldn't find a suitable alternative) validate real demand, but that evidence currently lives only in a pitch deck, not on the site. The page should stop signaling "still building" and start inviting a live demo, while surfacing the market-validation evidence that supports the pitch.

## What Changes

- Remove the "In active development" status pill from the Hero section.
- Add a "Request Demo" CTA button to the top Nav, next to the existing nav links, styled as a solid navy button matching the existing primary hero CTA.
- Extend the existing Problem section with a sector-validation block placed after the "Current workflow" diagram card:
  - Three anonymized pull-quotes from sector conversations, attributed by role only (Former UK fund CEO, International nonprofit leader, Nonprofit/fund adviser) — no names or organizations, since none were captured.
  - One paraphrased first-hand anecdote from a local nonprofit leader who could not find a suitable existing tool, styled distinctly from the direct quotes (not presented in quotation marks, since it is a paraphrase, not a verbatim quote).
  - A closing line: "The emerging opportunity: interoperability, not another closed portal."
- No backend changes. Frontend-only copy and layout changes in `LandingPage.tsx`.

## Capabilities

### New Capabilities
- `landing-page`: The public marketing landing page — hero messaging/status framing, nav CTAs, and the sector-validation content block in the Problem section.

### Modified Capabilities
_None — no existing spec currently covers the landing page._

## Impact

- `frontend-typescript/src/pages/LandingPage.tsx` (Hero, Nav, ProblemSection components) — copy and layout only.
- `frontend-typescript/src/pages/LandingPage.test.tsx` — update/add assertions for the removed pill, new nav CTA, and new Problem-section content.
- No API, database, or other service changes.
