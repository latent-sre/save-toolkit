---
name: postmortem
description: >-
  Apply the standard blameless postmortem structure after the scribe agent selects postmortem mode,
  or when a user explicitly invokes this skill. Covers the resolved incident, systemic causes,
  timeline, detection, response, and owned action items. Direct retrospective writing belongs to
  scribe; active incidents route to sre and incident-command. Triggers:
  "postmortem mode selected", "apply the postmortem structure", "use the postmortem template".
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Blameless postmortem

Start from the [postmortem template](./assets/postmortem-template.md). Fill every slot or mark it
`n/a — why`; preserve evidence sources rather than reconstructing the timeline from memory.

The goal is **learning, not blame**: find the systemic reasons a competent team still hit this, and fix
them so the failure class can't recur. Describe systems and decisions, never people.

## Blameless stance

- Assume everyone acted reasonably with the information they had. Ask "what made this action make sense?"
  not "who messed up?".
- Treat human error as a **symptom** of a system that allowed it (missing guardrail, gate, alert, or
  unclear runbook) — fix the system.
- Separate the **trigger** (what set it off) from the **cause** (why our defenses didn't prevent/catch it).

Two claims that need evidence, not silence:

- **"No data loss" is a claim that needs evidence, not an assumption of silence** — state explicitly
  what was checked (row counts, checksums, replay of the write path) or mark it `[unverified]`.
- **Name the detection source.** A *person* noticing is a detection gap, and the gap is a finding —
  it belongs in Detection and usually seeds a preventative action item. Ask directly: could typed
  `observability-engineer` evidence have paged sooner?

## Action items that actually prevent recurrence

- Prefer **systemic** fixes (a gate, an alert, a guardrail, an automated check) over "be more careful."
- **Tag every item mitigative vs preventative** — *mitigative* fixes this specific gap; *preventative*
  eliminates the whole failure class. A postmortem with no preventative item rarely stops a recurrence.
  Track them in the template's Action items table so none is lost.
- Every action names the **artifact** it becomes — a runbook line, an alert, a drill, a validator
  rule — plus a **proof-of-done** check. An action with no artifact will not happen.
- Each item is **owned, dated, tracked** — an un-owned action item is a wish. Use typed handoffs:
  resilience/code → typed `sde` agent; detection/SLO → typed `observability-engineer` agent; investigation follow-up →
  typed `sre` agent; deploy/rollback safety → human release owner; operating documentation → typed `scribe`
  agent.
- Be honest about what you don't know; mark unconfirmed causes `[unverified]` and state how to confirm them.

## Operational learning closeout

A postmortem is incomplete until every new operational fact has a **learning disposition**. Apply the
`operational-learning` policy after the primary postmortem is written: prepare or propose updates for
runbook, service card, alert card, knowledge index, observability, automation, code, and accepted
risk. Each outcome is `prepared`, `proposed`, `blocked`, `duplicate`, or `not_applicable`, with evidence
and one owner. The typed `scribe` agent may prepare documentation only; other lanes receive handoffs.
No action item may end as chat-only advice.

## Lessons — include "where we got lucky"

Capture three things, not just what broke: **what went well** (keep doing it), **what went wrong** (the
gaps), and **where we got lucky** — latent risks this incident *revealed* that didn't bite us this time
(an untested backup that happened to work, an alert that fired by coincidence, a key person who happened
to be online). Luck is a preventative action item waiting to be written.

## Near-misses

A near-miss earns the same write-up at half the length: the incident that almost happened is the
cheapest one to learn from. Same structure, same owned action items, less prose.

## Tip

Seed this from the supplied incident timeline and typed `sre` agent's root-cause evidence so it is accurate
while memory is fresh. Preserve every `[verified]`, `[sourced]`, and `[unverified]` label; never upgrade one.

## Pairs with

Ownership map only—not a load: the `incident-command` skill owns the live incident; the `sre` agent
supplies investigation evidence.
