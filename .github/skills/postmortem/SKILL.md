---
name: postmortem
description: >-
  Write a blameless postmortem for a resolved incident: systemic causes, timeline, detection,
  response, and owned action items in the standard structure. Triggers: 'write a postmortem for
  INC-1234', 'draft the retro for the order-router outage', 'apply the postmortem structure'. Direct
  retrospective writing belongs to scribe, which selects postmortem mode and applies this skill;
  active incidents route to incident-investigation; ITO runs coordination in the TLC.
argument-hint: "[the resolved incident]"
---

# Blameless postmortem

Whoever applies this skill, scribe's postmortem mode or the main thread, first gathers the
timeline, closeout packet, and severity; given only an incident ID, ask for them rather than
drafting placeholders.

Use the [postmortem template](./assets/postmortem-template.md): full for P1/P2 or an explicit full
review; abbreviated for P3/P4 and near-misses unless policy or the owner requires full depth. Keep unknown
severity as YAML `null`; draft the full form when the evidenced impact was customer-visible or
multi-service, otherwise abbreviated, state the choice and its reason, and confirm it with the owner
before finalizing. A summary/explanation request gets only that answer, not a completed postmortem
by implication.

Fill the selected form's required facts from evidence, marking missing facts `[unverified]` and
genuinely inapplicable requirements `n/a — why`. Omit the unselected form and optional empty sections.
Use the template's nullable times; preserve impact end separately from human resolution confirmation.

For full causal analysis, fit the evidence: Five Whys, a fault tree, causal graph, or another method.
Name it, preserving branches and uncertainty rather than forcing a line count or linear story.

## Blameless stance

Explain decisions from the information available then. Human error is not the root cause; identify
system conditions. Separate trigger from mechanism and failed defenses; aim to reduce recurrence
or impact, never promise zero recurrence.

- **"No data loss" needs evidence** — state explicitly
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
- Route resilience and toil/automation design and economics to `reliability-engineer`, accepted
  implementation to `software-engineer`, detection/SLO to `observability-engineer`, open causal
  questions to `sre-assistant` (operational evidence) or `software-engineer` with `root-cause`
  (code), deploy/rollback safety to the human release owner, and operating documents to `scribe`.
- Resolved impact does not require a known cause. Mark unconfirmed causes `[unverified]` and give
  unresolved causal questions an owner and next check; do not block the write-up on certainty.

## Operational learning closeout

Keep one Follow-ups record with incoming IDs; after the write-up, knowledge closeout
(`operational-learning`) enriches those rows with artifact dispositions.

## Lessons — include "where we got lucky"

Use evidenced successes, gaps, and narrowly avoided failures. A revealed risk warrants a justified
follow-up or explicit accepted risk, not an invented action to fill the template.

## Tip

Seed this from the supplied incident timeline and the incident record's root-cause evidence (the advisor's
closeout packet and any `sre-assistant` slices) so it is accurate
while memory is fresh. Preserve every `[verified]`, `[sourced]`, and `[unverified]` label; never upgrade one.
