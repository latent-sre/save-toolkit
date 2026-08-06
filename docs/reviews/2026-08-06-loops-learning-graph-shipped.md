# Review: self-learning schema, retracted workflow experiment, and graph engineering

- Date: 2026-08-06
- Status: evidence/history (live follow-ups are tracked in `docs/fleet-roadmap.md` only)
- Scope: the round that evaluated self-learning loops, multi-agent workflows ("loops"), and graph
  engineering. Schema-shape enforcement and graph validation remain; the workflow experiment was
  retracted after live runtime probing exposed an unsupported authority boundary.

## The reframe that unblocked the work

The prior default was to ask of each requested feature: **"is the rule against it stale?"** — does
the failure the rule was written to catch still happen? Finding the rule un-stale, the answer was
"no, keep the rule," and the feature was refused. That is the wrong question. The right one is
**"is the rule *right*, given what we now want to build?"** A rule can be simultaneously un-stale
(its failure is still real) and wrong (it forbids more than that failure justifies).

Applying the right question, feature by feature:

| Feature | Was the blocking rule right? | Outcome |
|---|---|---|
| Loops / workflows | **The directory rule was self-imposed; the runtime boundary was not.** Claude Code 2.1.221 cannot both load an inline-plugin workflow under name-only mode and bind native permission to the registered implementation. | Retracted the implementation; `WF-001` is blocked on a supported exact-dispatch contract. |
| Self-learning loops | **Right, and only structurally enforced so far.** The rule ("no agent promotes its own change; learning is reviewable state") is correct. Gate A checks the record schema, while lifecycle semantics remain parked. | Added schema-shape enforcement; kept promotion blocked on the parked semantic validators. |
| Graph engineering | **Right, and honored by making it first-class.** The fleet already was a delegation graph; the rule (edges are real only in frontmatter, main-thread only) is correct. Honoring it meant naming the concept and guarding its unvalidated render. | Named it; validated the render. |

The through-line remains "which narrower rule is actually right, and what enforces it?" That
question supported the schema and graph changes. For workflows, it also supplied the stop condition:
when enforcement required a bespoke security broker around undocumented host behavior, removal was
safer and simpler than calling the experiment shipped.

## What remained after review

**1. Self-learning record shape — enforced.** `validate_improvements.py` (stdlib JSON-Schema subset)
checks every `evals/improvements/*/record.json` against the fleet-improvement v1 schema in Gate A.
The catalog remains `contract-only` because the transition, authority, history, and repository-
binding validators are still parked. The schema layer is executable; it is not the lifecycle
semantic layer. The one
invariant is stated prominently and unchanged: **no agent promotes, merges, or rolls back its own
improvement** — a human or protected workflow does. The loop records and evidences; it is not a
background self-modifying process.

**2. Workflow experiment — removed.** Live probing on Claude Code 2.1.221 showed that
`CLAUDE_WORKFLOW_NAME_ONLY=1` suppresses inline-plugin workflows. Removing that flag loads the
workflow, but native `Workflow(name)` permission also accepts a same-name caller-supplied `script`
override. An exec-form `PreToolUse` guard successfully denied that exact attack before task creation,
but a safe end-to-end design then required a sterile launcher, one-shot hook receipt, immutable Git
scope producer, object-store isolation, loader-size budgeting, and version-pinned upgrade probes.
That was a security broker, not a small fleet workflow. The workflow, launcher, internal reviewer,
scope helper, guard, and focused tests were removed. `WF-001` now records the upstream prerequisite
for reconsideration.

**3. Graph engineering — made first-class.** The fleet already was a directed delegation graph
(`Agent(target)` grants are its edges) and `validate_fleet.py` already enforced each agent's grants
against `EXPECTED_DELEGATION`. What was missing was ownership of the concept and a guard on the
graph's third copy: the roster "Delegates to" column in `AGENTS.md` was a hand-kept render nothing
checked. `validate_roster_graph` now binds that column back to the enforced graph (mutation tests
show dropped edges, phantom edges, duplicate agent rows, and a missing table all fail; the shipped
roster passes). `skills/agent-authoring/references/delegation-graph.md` names the concept — one
enforced source, one pinned expectation, one validated render, the honest main-thread-only
enforcement limit, and the three places an edge change must land together.

## Status and honest limits

- The original closure recorded Gate A **23/23**, but those pre-rebase SHAs do not identify the
  repaired candidate and are not reused as current evidence. Run Gate A on the final revision.
- No executable workflow or internal workflow reviewer remains in the repository. `WF-001` is a
  blocked architecture item, not an implementation checklist.
- The fleet-improvement record's enforced layer is schema shape only. Semantic checks (transition
  legality, cumulative budget across attempts, exact-subject binding, append-only history) remain
  parked; records cannot promote until those executable validators are recovered from tag
  `pre-trim-2026-08-02`.
