---
name: postmortem
description: >-
  Apply the standard blameless postmortem structure after the scribe agent selects postmortem mode,
  or when a user explicitly invokes this skill. Covers the resolved incident, systemic causes,
  timeline, detection, response, and owned action items. Direct retrospective writing belongs to
  scribe; active incidents route to incident-investigation and incident-command. Triggers:
  "postmortem mode selected", "apply the postmortem structure", "use the postmortem template".
argument-hint: "[the resolved incident]"
---

# Blameless postmortem

Use the [postmortem template](./assets/postmortem-template.md): full for P1/P2 or an explicit full
review; abbreviated for P3/near-misses unless policy or the owner requires full depth. Keep unknown
severity unknown and confirm required depth before finalizing. A summary/explanation request gets
only that answer, not a completed postmortem by implication.

Fill the selected form's required facts from evidence, marking missing facts `[unverified]` and
genuinely inapplicable requirements `n/a — why`. Omit the unselected form and optional empty sections.

For full causal analysis, fit the evidence: Five Whys, a fault tree, causal graph, or another method.
Name it, preserving branches and uncertainty rather than forcing a line count or linear story.

## Blameless stance

Explain decisions from the information available then. Human error is not the root cause; identify
system conditions. Separate trigger from mechanism and failed defenses; aim to reduce recurrence
or impact, never promise zero recurrence.

Two claims that need evidence, not silence:

- **"No data loss" is a claim that needs evidence, not an assumption of silence** — state explicitly
  what was checked (row counts, checksums, replay of the write path) or mark it `[unverified]`.
- **Assess detection, not who detected it.** Name the source, delay, available signals, and noise.
  Human detection is not automatically a gap. Propose `observability-engineer` follow-up when
  evidence supports an actionable, earlier signal worth its paging cost.

## Action items that reduce risk

- Prefer systemic risk reduction over "be more careful." Tag actions **mitigative** (impact/recovery)
  or **preventative** (recurrence), with the risk reduced and remaining limits; no category quota.
- Every action has an artifact and proof-of-done check, owner, due date, and tracking link.
- When proof depends on missing instrumentation, include that prerequisite with the action and keep
  it blocked until the signal, exporter, code, or pipeline/config change lands. Unrelated actions
  need no instrumentation field.
- Route code/resilience to `software-engineer`, detection/SLO to `observability-engineer`, causal
  follow-up to the responder with `incident-investigation`, deploy/rollback safety to the human
  release owner, and operating documents to `scribe`.
- Resolved impact does not require a known cause. Mark unconfirmed causes `[unverified]` and give
  unresolved causal questions an owner and next check; do not block the write-up on certainty.

## Operational learning closeout

Keep one Follow-ups record with incoming IDs for actions, questions, and artifact dispositions.
Consolidate repeated copies, not distinct targets/owners/status/evidence. After the write-up,
`operational-learning` enriches these rows; group justified `not_applicable` categories, not new work.
`scribe` prepares documentation only; other lanes receive tracked handoffs. Unsupported `prepared`
claims stay proposed/blocked with the missing checkout binding or diff noted.

## Lessons — include "where we got lucky"

Use evidenced successes, gaps, and narrowly avoided failures. A revealed risk warrants a justified
follow-up or explicit accepted risk, not an invented action to fill the template.

## Tip

Seed this from the supplied incident timeline and the incident record's root-cause evidence (the advisor's
closeout packet and any `sre-assistant` slices) so it is accurate
while memory is fresh. Preserve every `[verified]`, `[sourced]`, and `[unverified]` label; never upgrade one.
