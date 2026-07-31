---
name: eng-ladder
description: >-
  Set your altitude before the task — engineering (builder: a scoped change in one component;
  principal: cross-cutting design, contract/schema change, migration, real blast radius;
  distinguished: high-ambiguity architecture, build-vs-buy, a standard others follow) or SRE
  (responder → investigator → elite for alerts and incidents). Triggers: 'how rigorous should this
  be', 'review this at the principal level', 'what tier is this incident work'. A scoped change with
  an obvious owner and an existing pattern routes straight to its builder or craft skill without
  this. Read exactly one tier file.
argument-hint: "[task, diff, file, or design doc]"
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

## The ladder

| | Builder | Principal | Distinguished |
|---|---|---|---|
| **Scope** | a tool, feature, or service | a system across services/teams | platform or org, across years |
| **Horizon** | this release | 6–18 months | 3–5 years |
| **Core question** | does it work, and can it be operated? | is this the right design, and what's the blast radius? | is this the right problem, and will the solution survive the org? |
| **Artifacts** | working, verified code + tests | design docs, decision records, phased plans | ADRs, north-star architecture, build/buy analyses |
| **Failure lens** | handles errors, timeouts, retries | failure modes, rollout/rollback | failure domains, blast-radius containment |

## The SRE track — altitude for an alert or incident

Same idea, detection-side. Match response depth to the situation and read exactly one tier file:

- **Responder** — safe first response: golden signals, read-only checks, work the runbook,
  decide severity, escalate → [responder](./references/responder.md) (signals primer:
  [golden signals](./references/golden-signals.md))
- **Investigator** — hypothesis-driven RCA: timeline, "what changed", test hypotheses against
  evidence → [investigator](./references/investigator.md)
- **Elite** — systemic/distributed failure analysis and prevention → [elite](./references/elite.md)

## Mode 1 — Route a task

Match the task to the lowest rung whose core question it raises. Signals it needs principal: multiple services or teams, a migration, a hard-to-reverse choice, "design" or "how should we" phrasing. Signals it needs distinguished: build-vs-buy, platform consolidation, anything measured in years. When in doubt, route DOWN — a lower rung that recognizes its limit and escalates is cheaper than ceremony, and the agents are prompted to escalate.

Routing includes routing to yourself. Work stays in the current context when it fits the conversation you're already in; hand work to the `sde` agent when it needs fresh context or runs alongside other work. For in-context work, load the matching altitude reference and work its method: [builder](./references/builder.md), [principal](./references/principal.md), or [distinguished](./references/distinguished.md). Load **only** the tier that matches, and move up the moment it isn't enough — moving up means loading the next reference; a delegated agent reports a material fork to its caller instead of silently changing altitude. Each rung's reference file is its full bar.

Ownership map only—not a load: the `ops-tooling` skill applies this altitude routing inside its build pipeline. This table is the source of truth for routing — on any conflict over which rung a task belongs to, the table wins; fix the paraphrase, not the table.

Application-operations work routes to the `sre` agent; platform internals route to the platform team; code that runs on the platform still uses this ladder.

## Mode 2 — Assess work at a bar

The table above routes; it is not the bar. Each rung's reference file is its full bar. Read the relevant one before scoring. Score the artifact against its current-level bar: **meets**, or **gaps** with cited evidence (specific lines or sections — no generic feedback). Then state the next-level delta: the two or three concrete things that would make this artifact next-rung work. Example: "The code works and is tested — the principal version would name the migration rollback plan and cut the config surface in half."

## Mode 3 — Growth feedback

For a body of work (several diffs or docs): identify recurring patterns, strengths at the current level, and the single highest-leverage next-level behavior to practice. One behavior, not a list — growth feedback that names ten things changes nothing.
