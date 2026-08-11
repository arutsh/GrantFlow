# Privacy Policy (stub — pending legal review)

**Status: draft.** This is a working stub for legal review, not the
published privacy policy. The live, user-facing policy is
`frontend-typescript/src/pages/Legal.tsx` — that page should only be
updated with legally-reviewed language, not this draft directly.

## Purpose

This stub exists so the data-subject-rights endpoints added in
gdpr-iso27001-priority-1 have a concrete piece of user-facing
documentation to point to, and so legal review has a starting draft
rather than a blank page.

## What this policy needs to cover once reviewed

### Data we collect

- Account data: name, email address, hashed password.
- Consent state: whether data-processing consent (mandatory) and
  marketing consent (optional) are currently granted, and when each was
  last granted or withdrawn. See `consent-management` capability.
- Financial records: budgets, reports, and related line items entered
  by the organisation using the platform.
- Telemetry: request logs and traces used for reliability and security
  (see `docs/security/subprocessors.md` for where this is processed).

### Your rights and how to exercise them

As of this change, the following are available directly in the product
(Settings page), not just on request:

- **Access** — export a copy of your personal data:
  `GET /users/me/export`.
- **Rectification** — correct your name via the existing profile update,
  or change your email address (requires re-verification):
  `POST /users/me/email`.
- **Erasure** — delete your account: `DELETE /users/{id}` (self-service,
  scrubs your name/email and blocks further login; financial records you
  created remain for the organisation's institutional record-keeping,
  shown with an anonymized actor reference — see design.md decision 2 in
  `openspec/changes/gdpr-iso27001-priority-1/design.md` for why this is
  soft-delete rather than hard-delete).
- **Consent withdrawal** — marketing consent can be withdrawn at any
  time in Settings; data-processing consent is required for the account
  to function and withdrawing it is equivalent to requesting erasure.

### Subprocessors

See `docs/security/subprocessors.md` for the full list and what each
receives.

### Data retention

Not yet defined here — retention limits on stored chat/audit content are
tracked separately (`gdpr-iso27001-priority-2`, operational hardening).

### Legal basis for processing

Draft position, needs legal confirmation: account/financial data is
processed on the basis of contract performance (providing the service)
and, for financial records tied to a since-deleted user, legitimate
interest / legal obligation for institutional record-keeping. Marketing
email is processed on the basis of consent.

## Open items before this can be published

- Legal review of the above, including the legal-basis framing.
- Confirm Grafana Cloud's hosting region (see subprocessors.md).
- Decide whether this supersedes or merges into the live
  `frontend-typescript/src/pages/Legal.tsx` page, and whether the public
  compliance-claim wording on the landing page should wait for
  `gdpr-iso27001-priority-2` as well (see the Open Questions in
  `openspec/changes/gdpr-iso27001-priority-1/design.md`).
