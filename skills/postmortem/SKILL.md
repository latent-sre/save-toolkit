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

Start from the [postmortem template](./assets/postmortem-template.md). Fill every slot or mark it
`n/a — why`; preserve evidence sources rather than reconstructing the timeline from memory.

Use the causal-analysis method that fits the evidence. Five Whys is one option, not a required
five-line quota; a branching incident may need a fault tree, causal graph, or another method that
preserves multiple contributing paths. Name the method and do not force uncertain facts into a
single linear story.

The goal is **learning, not blame**: explain how a competent team still hit this and reduce its
recurrence or impact. Describe systems and decisions, never people; do not promise zero recurrence.

## Blameless stance

- Assume everyone acted reasonably with the information they had. Ask "what made this action make sense?"
  not "who messed up?".
- Treat human error as a **symptom** of a system that allowed it (missing guardrail, gate, alert, or
  unclear runbook) — fix the system.
- Separate the **trigger** (what set it off) from the **cause** (why our defenses didn't prevent/catch it).

Two claims that need evidence, not silence:

- **"No data loss" is a claim that needs evidence, not an assumption of silence** — state explicitly
  what was checked (row counts, checksums, replay of the write path) or mark it `[unverified]`.
- **Assess detection, not who detected it.** Name the source, delay, available signals, and noise.
  Human detection is not automatically a gap. Propose `observability-engineer` follow-up when
  evidence supports an actionable, earlier signal worth its paging cost.

## Action items that reduce risk

- Prefer **systemic** fixes (a gate, an alert, a guardrail, an automated check) over "be more careful."
- **Tag every item mitigative vs preventative** — *mitigative* reduces impact or recovery time;
  *preventative* reduces recurrence likelihood. Name the risk reduced and remaining limits; an
  action need not eliminate the whole failure class. Track justified items, not a category quota.
- Every action names the **artifact** it becomes — a runbook line, an alert, a drill, a validator
  rule — plus a **proof-of-done** check. An action with no artifact will not happen.
- Every action names its **instrumentation prerequisite**: the signal, exporter, instrumented code,
  or pipeline/config change its proof depends on. Use `none` only when the proof is independent of
  missing telemetry; otherwise the dependent action remains blocked until this prerequisite lands.
- Each item is **owned, dated, tracked** — an un-owned action item is a wish. Use typed handoffs:
  resilience/code → typed `software-engineer` agent; detection/SLO → typed `observability-engineer` agent; investigation follow-up →
  the responder with `incident-investigation`; deploy/rollback safety → human release owner; operating documentation → typed `scribe`
  agent.
- Resolved impact does not require a known cause. Mark unconfirmed causes `[unverified]` and give
  unresolved causal questions an owner and next check; do not block the write-up on certainty.

## Operational learning closeout

After the primary write-up, apply `operational-learning` to every new operational fact. Disposition
affected runbook, card, index, observability, automation, code, and accepted-risk work with evidence
and one owner; group justified `not_applicable` categories instead of inventing work. The typed
`scribe` agent prepares documentation only; other lanes receive tracked handoffs, not chat-only advice.

## Lessons — include "where we got lucky"

Capture three things, not just what broke: **what went well** (keep doing it), **what went wrong** (the
gaps), and **where we got lucky** — latent risks this incident *revealed* that didn't bite us this time
(an untested backup that happened to work, an alert that fired by coincidence, a key person who happened
to be online). Luck is a preventative action item waiting to be written.

## Near-misses

A near-miss earns the same write-up at half the length: the incident that almost happened is the
cheapest one to learn from. Same structure, same owned action items, less prose.

## Tip

Seed this from the supplied incident timeline and the incident record's root-cause evidence (the advisor's
closeout packet and any `sre-assistant` slices) so it is accurate
while memory is fresh. Preserve every `[verified]`, `[sourced]`, and `[unverified]` label; never upgrade one.
