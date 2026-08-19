---
name: postmortem
description: >-
  Apply the blameless postmortem structure after scribe selects retrospective mode or on explicit
  invocation. Direct repository writing belongs to scribe; active incidents route to sre and
  incident-command. Triggers: "postmortem mode selected", "apply the postmortem structure", "use
  the postmortem template".
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Blameless postmortem

Start from the [postmortem template](./assets/postmortem-template.md). Fill every slot or mark it
`n/a — why`. Use the authoritative timeline and source evidence; do not reconstruct facts from memory
or turn a plausible hypothesis into the root cause.

## Analysis rules

- Describe system conditions and decisions, not personal fault. Ask what information, incentives,
  interfaces, and safeguards made each action reasonable at the time.
- Separate **trigger**, **root cause**, and **contributing conditions**. Keep unresolved alternatives
  visible and `[unverified]`.
- Support impact, duration, and recovery with evidence. “No data loss” needs a named integrity check;
  silence is not proof.
- Name the detection source and delay. Human discovery can be a detection gap; ask whether a service
  signal could have detected the symptom earlier without unacceptable noise.
- Distinguish the action that restored service from proof of causality. A rollback or restart can
  mitigate impact without proving why the failure began.
- Include what worked, what failed, and where the response was lucky. Treat each material latent risk
  as a candidate action, not narrative decoration.

Near misses use the same evidence and action contract; shorten only sections that genuinely have no
material content.

## Action-item contract

Prefer controls that change the system—tests, gates, alerts, validation, safer defaults, recovery
paths—over “be more careful.” Each action item must contain:

| Field | Requirement |
|---|---|
| Gap | Specific failure or missing defense evidenced by the incident |
| Class | `mitigative` for the observed gap or `preventative` for the wider failure class |
| Artifact | Code, test, alert, runbook, drill, policy, or accepted-risk record that will change |
| Owner and due date | One accountable owner and an explicit date |
| Proof of done | Observable check that demonstrates the artifact and intended control work |
| Tracker | Stable issue, change, or repository locator |

Route code/resilience work to typed `sde`, detection/SLO work to typed
`observability-engineer`, investigation follow-up to typed `sre`, deploy/rollback work to the human
release owner, and operating documentation → typed `scribe`.

## Learning closeout

After the primary retrospective is complete, ensure every new operational fact has a **learning disposition**.
Apply `operational-learning` to every durable consequence:
runbook, service card, alert card, knowledge index, observability, automation, code, and accepted risk.
Each receives `prepared`, `proposed`, `blocked`, `duplicate`, or `not_applicable`, evidence, and one
owner. No action item ends as chat-only advice, and typed `scribe` prepares documentation only within
its authority.

## Output contract

Return:

1. impact and evidence-backed timeline;
2. detection and response analysis;
3. trigger, root cause, contributing conditions, and unresolved hypotheses;
4. what worked, what failed, and where the response was lucky;
5. action-item table satisfying every field above;
6. operational-learning dispositions and handoffs;
7. explicit limitations, conflicts, and claims still `[unverified]`.

## Pairs with

Ownership map only—not a load: `incident-command` owns the live response, and typed `sre` supplies
investigation evidence.
