## Context

`LandingPage.tsx` is a single-file page with each section (`Nav`, `Hero`, `ProblemSection`, etc.) defined as an inline component and rendered by `LandingPage()`. Brand tokens (colors) live in `src/lib/brand.ts` and are applied via inline `style` props, not Tailwind theme classes. There is no CMS or content-data layer — all copy is literal JSX text. This change is a straightforward, low-risk edit to existing JSX/inline-style markup; no new architecture, dependency, or data model is introduced.

A visual mockup validating the layout and copy was produced and approved before this proposal (published as a design Artifact) — this design doc translates that into the existing component structure rather than re-deriving layout decisions from scratch.

## Goals / Non-Goals

**Goals:**
- Remove the "in development" framing from the Hero section.
- Add a `Request Demo` CTA to the Nav, reachable without scrolling.
- Add a sector-validation content block to `ProblemSection`, reusing existing card/typography patterns (`card-shadow-lg`, `Kicker`-style labels, `TONE_COLORS` conventions).
- Keep all copy and attribution honest: quotes are anonymized by role (no fabricated names), and the one first-hand anecdote is visually distinguished from the verbatim quotes since it's a paraphrase.

**Non-Goals:**
- No CMS, no externalized/config-driven copy — the new content is literal JSX, consistent with the rest of the file.
- No new nav destination/page for "Request Demo" — the button links to the existing `#contact` anchor (`ContactSection`), same target the mockup used. Wiring a dedicated demo-request form/flow is out of scope for this change.
- No changes to `DemoSection`, `AudienceSection`, `SolutionSection`, `VisionSection`, `OpenSourceSection`, `FounderSection`, `PartnerSection`, `Footer`.
- No backend/API changes.

## Decisions

- **Request Demo target**: point at `#contact` (existing `ContactSection`) rather than building a new modal/form. Rationale: the section already exists and captures inbound interest; a dedicated flow can be a future, separately-scoped change if conversion data justifies it.
- **Anecdote styling**: render the paraphrased anecdote in a visually distinct card (tinted background, no quotation marks) rather than as a fourth pull-quote. Rationale: the other three are close to verbatim from sector conversations; presenting the paraphrase identically would misrepresent it as a direct quote.
- **Attribution**: role-only (e.g. "Former UK fund CEO"), no names/orgs. Rationale: none were captured, and fabricating attribution would be misleading on a public page.
- **Placement of validation block**: inside `ProblemSection`, after the existing "Current workflow" diagram, rather than a new top-level section. Rationale: this content supports the *problem* framing (market need), not the product pitch — grouping it with the Problem section keeps the page's argument structure coherent (Problem → Solution) instead of implying these are customer testimonials of the product itself.

## Risks / Trade-offs

- [Risk] A reader skims the new block and mistakes the anonymized quotes for product testimonials → Mitigation: keep the block visually and contextually part of `ProblemSection` (not styled as a "Customers say" section), and keep language framed as "what we're hearing from the sector," not endorsements.
- [Risk] Anonymized, unsourced quotes read as less credible than named testimonials → Mitigation: accepted trade-off for this change; named attribution can replace these once real customer/partner quotes are available (separate future change).
- [Risk] Adding a Nav CTA on small screens could crowd the header → Mitigation: verify at mobile width during implementation; the existing nav links are already `hidden sm:flex` (mobile-hidden), so the Request Demo button needs its own mobile-visible treatment — confirm it doesn't overlap the logo at narrow widths.
