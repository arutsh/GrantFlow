One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Privacy Policy content update

- [x] 1.1 Rewrite the `id="privacy"` section of `frontend-typescript/src/pages/Legal.tsx`: add a data-retention section (qualitative wording, no invented numbers), a third-party-processors section summarizing `docs/security/subprocessors.md`, a rewritten Contact section listing `privacy@opengrantflow.com` alongside the existing contact form, and a legal-status section stating the project is not yet a registered legal entity. Bump `LAST_UPDATED`.
- [x] 1.2 Update `frontend-typescript/src/pages/Legal.test.tsx` if it asserts on specific section text that changed. (Verified: existing test only checks the two h1 headings, unaffected — no change needed.)
- [x] 1.3 Confirm the `privacy@opengrantflow.com` mailbox/alias exists and forwards somewhere you monitor — do this before merging, since the policy will otherwise cite a dead address.
- [x] 1.4 Run the frontend test suite and lint clean for the changed files; PR merged. (Tests + lint verified clean; PR not yet opened.)

## 2. Transactional email privacy link — depends on 1

- [x] 2.1 Add `"privacy_url": f"{settings.FRONTEND_BASE_URL}/legal#privacy"` to the `personalization` dict in `services/worker/tasks/users/send_verification_email.py`.
- [x] 2.2 Add the same `privacy_url` key to the `personalization` dict in `services/worker/tasks/users/send_invite_email.py`.
- [x] 2.3 Update the settings comment block in `services/worker/config.py` to document `privacy_url` as a personalization var for both the verification and invite templates.
- [x] 2.4 Add unit tests asserting `privacy_url` is present in the personalization dict passed to `send_template_email` for both tasks (new coverage — no existing tests assert on these dicts today).
- [ ] 2.5 In the Mailjet dashboard, edit both the verification-email and invite-email templates to render `{{var:privacy_url:""}}` as a Privacy Policy link in the footer.
- [ ] 2.6 In the MailerSend dashboard (the alternate `EMAIL_PROVIDER`), make the same footer edit to both templates so the link works regardless of which provider is active.
- [ ] 2.7 Trigger a real verification email and a real invite email in dev for each provider and manually confirm the Privacy Policy link renders and points at `/legal#privacy`.
- [ ] 2.8 Run the worker test suite and lint clean; PR merged. (Tests + lint verified clean; PR not yet opened.)
