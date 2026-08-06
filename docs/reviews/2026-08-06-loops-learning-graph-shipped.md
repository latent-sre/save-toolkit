# Shipped: self-learning loops, workflows, and first-class graph engineering

- Date: 2026-08-06
- Status: evidence/history (live follow-ups are tracked in `docs/fleet-roadmap.md` only)
- Scope: the round that stopped treating three requested capabilities — self-learning loops,
  multi-agent workflows ("loops"), and graph engineering — as things to refuse, and shipped all
  three. Records the reframe that unblocked them so the reasoning is repository state, not memory.

## The reframe that unblocked the work

The prior default was to ask of each requested feature: **"is the rule against it stale?"** — does
the failure the rule was written to catch still happen? Finding the rule un-stale, the answer was
"no, keep the rule," and the feature was refused. That is the wrong question. The right one is
**"is the rule *right*, given what we now want to build?"** A rule can be simultaneously un-stale
(its failure is still real) and wrong (it forbids more than that failure justifies).

Applying the right question, feature by feature:

| Feature | Was the blocking rule right? | Outcome |
|---|---|---|
| Loops / workflows | **No — self-imposed.** Nothing in the repo forbade a `workflows/` tree; the "no workflows" stance was the model's, not the fleet's. The *real* rule is narrower: workflows are Claude-only and never projected. | Built the feature; encoded the narrow rule. |
| Self-learning loops | **Right, and honored by enforcing — not refusing.** The rule ("no agent promotes its own change; learning is reviewable state") is correct. The way to honor it was to make the loop's contract *enforced*, not to keep it parked. | Made the loop live behind schema enforcement. |
| Graph engineering | **Right, and honored by making it first-class.** The fleet already was a delegation graph; the rule (edges are real only in frontmatter, main-thread only) is correct. Honoring it meant naming the concept and guarding its unvalidated render. | Named it; validated the render. |

The through-line: every feature shipped by *satisfying* the repo's doctrine — convert silent
failures into loud ones — never by engineering around it. "No" was the wrong default; "which
narrower rule is actually right, and what enforces it?" was the work.

## What shipped

**1. Self-learning loop — made live.** `validate_improvements.py` (stdlib JSON-Schema subset)
enforces every `evals/improvements/*/record.json` against the fleet-improvement v1 schema, wired
into Gate A; the schema catalog flipped `fleet-improvement-v1` from `contract-only` to `supported`.
`skills/agent-authoring/references/improvement-lifecycle.md` was reframed from "parked" to "live,"
with the schema layer enforced and the deeper semantic checks named as the next layer. The one
invariant is stated prominently and unchanged: **no agent promotes, merges, or rolls back its own
improvement** — a human or protected workflow does. The loop records and evidences; it is not a
background self-modifying process.

**2. Workflows / loops — built.** `workflows/ship-review.js` is the fleet's first Claude workflow:
a `save-toolkit:sde` scope pass enumerates the working-tree diff (read-only git), two
`save-toolkit:reviewer` lanes judge that diff *as data* in parallel (correctness + security), and a
merge-readiness synthesis applies the merge-gate rule. The shape is forced by the fleet's own tool
postures — `reviewer` holds no Bash, so it cannot self-scope; the workflow is the caller that
supplies the diff, exactly as `agents/reviewer.md` requires. Claude-only and never projected (no
other host has a workflow runtime); the AGENTS.md Map records this and the generator stays blind to
the tree. It is **unverified until run against a live session** — roadmap item `WF-001` tracks that.

**3. Graph engineering — made first-class.** The fleet already was a directed delegation graph
(`Agent(target)` grants are its edges) and `validate_fleet.py` already enforced each agent's grants
against `EXPECTED_DELEGATION`. What was missing was ownership of the concept and a guard on the
graph's third copy: the roster "Delegates to" column in `AGENTS.md` was a hand-kept render nothing
checked. `validate_roster_graph` now binds that column back to the enforced graph (four mutation
tests: dropped edge, phantom edge out of a terminal agent, and missing table all fail; the shipped
roster passes). `skills/agent-authoring/references/delegation-graph.md` names the concept — one
enforced source, one pinned expectation, one validated render, the honest main-thread-only
enforcement limit, and the three places an edge change must land together.

## Status and honest limits

- Gate A: **23/23** across all three commits (`576ea4b`, `d3a1346`, `f13d396` on
  `claude/sde-agents-repo-alignment-x5ayt9`).
- Gate A is structural. It proves the workflow file parses and the schema/graph checks have teeth;
  it cannot prove the workflow *runs*. `WF-001` in `docs/fleet-roadmap.md` is the one open item: run
  `ship-review` in a live session and record the result. One proven pipeline is worth more than
  several unrun ones — do not add a second workflow before this one is verified.
- The self-learning loop's enforced layer is the schema. The semantic checks (transition legality,
  cumulative budget across attempts, exact-subject binding, append-only history) remain the
  documented next layer, held by review until the ledger carries enough real records to justify
  recovering the parked executable validators from tag `pre-trim-2026-08-02`.
