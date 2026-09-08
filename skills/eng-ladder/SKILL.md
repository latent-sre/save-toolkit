---
name: eng-ladder
description: >-
  Select the engineering altitude for implementation, design, review, or growth feedback when work
  may span components, teams, migrations, or hard-to-reverse choices. Triggers: 'how rigorous
  should this be', 'review this at the principal level', 'is this a design doc or just a PR'. A
  scoped change with an obvious owner and existing pattern routes straight to its builder or craft
  skill. Active-alert troubleshooting belongs to incident-investigation.
argument-hint: "[task, diff, file, or design doc]"
---

## The engineering ladder

Pick the rung the work actually sits at, then read only that tier file. Do not preload neighboring
tiers as a checklist. Load a different tier only when observed scope changes the altitude or the
selected tier's escalation rule requires it.

| | Builder | Principal | Distinguished |
|---|---|---|---|
| **Scope** | a tool, feature, or service | a system across services/teams | platform or org, across years |
| **Horizon** | this release | 6–18 months | 3–5 years |
| **Core question** | does it work, and can it be operated? | is this the right design, and what's the blast radius? | is this the right problem, and will the solution survive the org? |
| **Artifacts** | working, verified code + tests | design docs, decision records, phased plans | ADRs, north-star architecture, build/buy analyses |
| **Failure lens** | handles errors, timeouts, retries | failure modes, rollout/rollback | failure domains, blast-radius containment |

## Mode 1 — Route a task

Match the lowest rung whose core question fits. Cross-service/team work, migrations and hard-to-reverse
design choices need principal reasoning; build-vs-buy, platform consolidation or multi-year choices
need distinguished. Implementing an accepted design stays builder-owned within its agreed scope
and compatibility criteria; return unresolved consequential choices or required constraint changes
for decision. When unsure, start lower and escalate when its bar is insufficient.

Keep implementation ownership separate from consultation. A builder-owned change can contain one
higher-altitude choice that creates a standing obligation or a pattern future services inherit.
Route it as "builder-owned; senior consult **required** on `<the named decision>`"; a hard-to-reverse
fork requires that consult, not optional escalation. The builder returns the undecided fork to its
caller or a human senior engineer at the matching altitude. The consult returns one decision record
without taking implementation ownership; this roster has no principal or architect agent.

Use `reviewer` only to assess an actual proposed decision artifact/change, with caller-supplied
trusted-base altitude context, base/candidate identities and diff. It reviews the proposal, not an
undecided design choice; it neither loads candidate skills nor gains shell or Skill authority.
The caller arranges any invocation the current lane cannot make.

Keep work in the current context when it fits; use `software-engineer` for implementation needing
fresh context or parallel work. Read only the matching bar: [builder](./references/builder.md),
[principal](./references/principal.md), or [distinguished](./references/distinguished.md). If it is
insufficient, the main context loads the next tier; a delegated agent returns the fork to its caller
instead of changing altitude.

This table is the source of truth for routing — on any conflict over which rung a task belongs to, the table wins; fix the paraphrase, not the table.

Application-operations work routes to the responder with `incident-investigation` (`sre-assistant` only for a dispatched read); platform internals route to the platform team; code that runs on the platform still uses this ladder.

## Mode 2 — Assess work at a bar

The table above routes; it is not the bar. Each rung's reference file is its full bar. Read the relevant one before scoring. Score the artifact against its current-level bar: **meets**, or **gaps** with cited evidence (specific lines or sections — no generic feedback). Score against the artifact's own remit: absence of work nobody asked for is not a gap, and a simple artifact done cleanly meets the bar — never invent gaps to make the assessment look rigorous. Then state the next-level delta: the two or three concrete things that would make this artifact next-rung work. Example: "The code works and is tested — the principal version would name the migration rollback plan and cut the config surface in half."

## Mode 3 — Growth feedback

For a body of work (several diffs or docs): identify recurring patterns, strengths at the current level, and the single highest-leverage next-level behavior to practice. One behavior, not a list — growth feedback that names ten things changes nothing.
