# Security Policy

This document describes how GrandFlow (Open Grant Flow) handles a suspected
security incident or data breach, and how to report a vulnerability. It
covers the platform's own operations; if you self-host GrandFlow, you are
responsible for incident response on your own deployment.

## Reporting a vulnerability

If you believe you've found a security vulnerability, please report it
privately rather than opening a public GitHub issue. Use GitHub's private
[vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
feature on this repository, or open a draft security advisory. Please
include:

- A description of the vulnerability and its potential impact
- Steps to reproduce it
- Any relevant logs, screenshots, or proof-of-concept code

We aim to acknowledge reports within 5 business days.

## Incident response process

### 1. Detection

A suspected incident can surface through several channels: an alert from
the production observability stack (see `docs/observability/`), a report
from a user or subprocessor, an unusual pattern noticed during routine
review, or a vulnerability report as above. Anyone on the team who
suspects a breach should treat it as a live incident immediately rather
than waiting for confirmation — see step 2.

### 2. Triage and containment

- Establish, at a high level, what data or systems may be affected
  (e.g., which service, which database, whether personal data such as
  names/emails/financial records is in scope).
- Contain the exposure as the immediate priority. Depending on the
  situation this may mean: revoking the credential or API key involved,
  forcing re-authentication (session revocation — see the
  `session-security` capability, which makes this possible for the first
  time as of this change), rotating the shared JWT signing secret,
  disabling the affected endpoint, or blocking network access to the
  affected host.
- Preserve evidence (logs, database snapshots) before remediating where
  feasible, so root cause can still be established afterward.

### 3. Investigation

- Determine the root cause, the timeline (when the exposure started and
  when it was contained), and the scope (which records/accounts were
  actually accessed or could have been accessed, not just theoretically
  reachable).
- Production logs and traces are exported to Grafana Cloud (see
  `docs/observability/GRAFANA_CLOUD_PRODUCTION.md`) and are the primary
  source for reconstructing a timeline.

### 4. Notification

- If the investigation confirms personal data was affected, GDPR's
  72-hour notification clock (Article 33) starts from when the breach
  was first confirmed, not from when it began. Assess without delay
  whether the incident is reportable to the relevant supervisory
  authority.
- If the breach is likely to result in a high risk to affected
  individuals, they must also be notified directly (Article 34), in
  clear language describing what happened and what they should do.
- Track who is responsible for each notification (regulator vs. affected
  users vs. any affected subprocessor) as a checklist, not left implicit.

### 5. Remediation and follow-up

- Fix the underlying cause, not just the immediate symptom.
- Write a short post-incident summary: what happened, root cause, what
  changed to prevent recurrence. Keep this internal unless disclosure is
  otherwise required.

## Scope

This process covers GrandFlow's own hosted platform and its
subprocessors (see `docs/security/subprocessors.md`). It does not cover
self-hosted deployments, which are operated independently.
