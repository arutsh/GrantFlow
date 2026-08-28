## Context

`frontend-typescript/src/pages/Legal.tsx` is the only live Privacy Policy;
`docs/legal/privacy-policy-stub.md` is a draft that already outlines most
of what's needed but is explicitly not wired up as the live page. Two
transactional emails exist (verification, admin-invite), both sent via
Mailjet/MailerSend **dashboard-hosted templates** — there is no local HTML
template in this repo, only a `personalization` dict passed from
`services/worker/tasks/users/*.py`.

Three items here are legal/business judgment calls, not implementation
details, and were resolved with the user before this change was proposed:

- **Retention**: `privacy-policy-stub.md` says retention limits are "not
  yet defined" (real enforcement deferred to an unstarted
  `gdpr-iso27001-priority-2` change). Decision: use qualitative wording now
  rather than inventing numbers we can't operationally back up.
- **Contact**: no `privacy@` mailbox exists today. Decision: reference
  `privacy@opengrantflow.com` in the policy, with mailbox creation as an
  explicit manual prerequisite before this is considered "live" (the policy
  would otherwise cite a dead address).
- **Legal status**: no registered company/nonprofit exists. Decision: state
  this plainly but forward-looking ("not yet a registered legal entity"),
  matching existing README/PRODUCT.md framing rather than inventing
  jurisdiction/incorporation details.

## Goals / Non-Goals

**Goals:**
- Make the live Privacy Policy accurately describe retention posture,
  third-party processors, a real contact, and the project's legal status.
- Get a working Privacy Policy link into both transactional emails end to
  end (code passes the URL; dashboard templates render it).

**Non-Goals:**
- Implementing actual data-retention enforcement (that's
  `gdpr-iso27001-priority-2`, not started, out of scope here).
- Rewriting the Terms of Service section of `Legal.tsx`.
- Incorporating a legal entity, or drafting the exact incorporation
  language for if/when that happens.
- Reviewing Mailjet's Acceptable Use Policy — that's a manual read on the
  user's side, not a repo change.

## Decisions

- **Reuse `docs/security/subprocessors.md` as the source of truth** for the
  processors section rather than re-deriving or duplicating the table —
  summarize it in prose, don't fork a second list that can drift out of
  sync.
- **Build `privacy_url` the same way `verify_url`/`invite_url` are already
  built** (`f"{settings.FRONTEND_BASE_URL}/legal#privacy"`), for
  consistency with the existing pattern in both task files rather than
  introducing a new config var.
- **No new `FRONTEND_BASE_URL`-style config var for the privacy link** —
  it's a fixed path off the existing frontend base URL, not something that
  varies by environment beyond what `FRONTEND_BASE_URL` already captures.
- **Dashboard template edits are out-of-repo, flagged as manual steps**,
  since there's no local template file to change — this is a real gap in
  what "done" means for this change (see Risks below).

## Risks / Trade-offs

- [The policy could go live referencing `privacy@opengrantflow.com` before
  that mailbox exists] → Treat mailbox creation as a hard prerequisite in
  tasks.md; don't merge/deploy the Legal.tsx change until confirmed.
- [Adding `privacy_url` to the personalization dict does nothing visible
  unless the Mailjet/MailerSend dashboard templates are also edited to
  render it] → Call this out explicitly as a required manual step, and
  verify by triggering a real test send in dev before calling Part B done.
- [Qualitative retention wording may not fully satisfy Mailjet's Section
  1(g) requirement if they expect concrete numbers] → Acceptable trade-off
  given no enforcement exists yet; revisit with concrete numbers once
  `gdpr-iso27001-priority-2` lands.

## Migration Plan

No data migration. Rollout is: merge the Legal.tsx + worker code changes,
then complete the two manual steps (mailbox, dashboard templates) before
telling Mailjet support the commitment is fulfilled. Rollback is a normal
revert — no state to unwind.

## Open Questions

- Does MailerSend's dashboard template (the alternate `EMAIL_PROVIDER`)
  need the same footer edit as Mailjet's, or is MailerSend not in scope for
  this specific Mailjet commitment? (Recommend doing both, since both
  templates share the same personalization contract and `EMAIL_PROVIDER`
  can switch between them.)
