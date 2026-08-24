## Why

Mailjet auto-blocked the production account on 2026-08-17 after a pentest
email flood to example.com. To get the account unblocked, we committed to
Mailjet support (their Section 1(g) requirement) to review/update the
Privacy Policy and add a Privacy Policy link to transactional emails. The
live Privacy Policy is thin (no retention, processor, or real contact info)
and no transactional email currently links to it, so both commitments
require real changes, not just a reply email.

## What Changes

- Rewrite the Privacy Policy (`frontend-typescript/src/pages/Legal.tsx`,
  `id="privacy"` section) to add: a data-retention section (qualitative —
  no enforced schedule exists yet), a third-party-processors section
  summarizing `docs/security/subprocessors.md`, a real contact address
  (`privacy@opengrantflow.com`, alongside the existing contact form), and a
  legal/status section stating the project is not yet a registered legal
  entity. Bump `LAST_UPDATED`.
- Add a `privacy_url` personalization variable
  (`{FRONTEND_BASE_URL}/legal#privacy`) to both transactional-email Celery
  tasks (`services/worker/tasks/users/send_verification_email.py`,
  `send_invite_email.py`), and document it in `services/worker/config.py`'s
  settings comment block.
- **Not in scope for code**: creating the `privacy@opengrantflow.com`
  mailbox, and editing the Mailjet/MailerSend dashboard-hosted email
  templates to render the new `privacy_url` link — both are manual actions
  outside this repo, called out as prerequisites in tasks.md.

## Capabilities

### New Capabilities
- `privacy-policy`: the live Privacy Policy page (`Legal.tsx`) and what it
  must state — retention posture, third-party processors, contact, and the
  project's legal status. Not previously spec'd.

### Modified Capabilities
- `transactional-email`: adds a requirement that every transactional email
  includes a link to the Privacy Policy, on top of the existing
  provider-abstraction requirements in `openspec/specs/transactional-email/spec.md`.

## Impact

- Frontend: `frontend-typescript/src/pages/Legal.tsx`,
  `frontend-typescript/src/pages/Legal.test.tsx` (update if it asserts on
  section text).
- Backend (worker): `services/worker/tasks/users/send_verification_email.py`,
  `services/worker/tasks/users/send_invite_email.py`,
  `services/worker/config.py`.
- External/manual: Mailjet + MailerSend dashboard templates; a new
  `privacy@opengrantflow.com` mailbox/alias.
