# Roster altitude — design the agent system, not one artifact

Four disciplines shape this fleet: **Prompt Engineering** (selection, guidance, and output
contracts), **Context Engineering** (the smallest relevant, trusted state), **Loop Engineering**
(work, verification, budgets, and termination), and **Graph Engineering** (ownership and authority
transitions). Handoffs are the context payload on a graph edge; durable learning is accepted loop
output, not a fifth discipline. Each theme names a failure mode this fleet has actually hit; none is
free-standing ceremony.

## Contents

- First question: should this be multi-agent at all?
- Four-theme decision rule
- Agent vs. skill (this fleet's decision rule)
- The loop inside each lane (loop engineering)
- Orchestration shapes (graph engineering)
- Handoffs between contexts (context + graph engineering)
- Design principles
- Failure modes to diagnose
- Deliverable
- When it pays — and when it doesn't
- Right-sizing
- Learning as repository state (loop engineering)
- Wrapper-layer failure taxonomy

## First question: should this be multi-agent at all?

Start with one agent or a deterministic workflow. Add agents when evaluation shows that ownership
transfer, context or authority isolation, independent verification, parallel breadth, or additional
context capacity pays for the added coordination. If none of those hold, recommend the simpler
design and say why.

Multi-agent is an architecture decision with real costs — tokens, latency, and information loss at
handoffs. Budget it per lane from this fleet's own measurements, not from a vendor's multiplier.

## Four-theme decision rule

| Theme | Owns the decision |
|---|---|
| Prompt Engineering | Which owner is selected, its instructions, and the response/tool shape it must produce |
| Context Engineering | What that owner sees, in what order, with which provenance, freshness, trust, compaction, and retention |
| Loop Engineering | Entry and mutable state, action/verification cycle, budgets, stops, terminal evidence, and promotion authority |
| Graph Engineering | Which node owns the work, which ownership transitions exist, and what authority and payload cross each edge |

Apply all four to the same work unit. **Skills deepen a node; agents change ownership.** Keep work in
one agent and load a skill when the owner and authority remain correct. Add or traverse an agent edge
only when ownership, authority isolation, independent verification, parallel breadth, or additional
context capacity justifies the transition. A graph edge never substitutes for a missing verifier,
and a larger prompt never substitutes for a required authority boundary.

## Agent vs. skill

An **agent** is a roster role with its own tool posture and lane. A **skill** is altitude, method,
checklist, or playbook loaded into a lane. Seniority tiers are ladder skills, not cloned agents;
routing and live coordination usually stay in the main session because a coordinator subagent often
adds a round-trip for a low-context decision the main session can make inline. When adding an agent,
record why in the agent's own file (or an ADR if it reshapes the roster). Tool-scope splits are a
common reason — not the only one. That routing choice is a reasoned default, not a measured result:
neither shape has been A/B tested for this fleet.

The local/external research split is the fleet's concrete example. `repository-investigator` receives
only local `Read`/`Grep`/`Glob`; `researcher` receives only external web, Context7, and GitHits
authority. Keeping both jobs in one prompt would preserve the sensitive-data plus untrusted-content
plus egress combination, so this boundary warrants two agents. A mixed question is orchestrated by
the caller with a sanitized public handoff, never by giving either worker both evidence domains.

## The loop inside each lane (loop engineering)

The roster shape is the second design decision. The first is the loop every single lane runs:
**gather context → take action → verify → repeat.** A lane's quality is set by its verify step —
the mechanism that lets the agent check its own work instead of asserting it. Design that step
explicitly:

Every engineered loop names its **entry state**, the state or artifact allowed to change, and its
**verifier**. Before the first iteration it sets maximum iterations and candidates (where candidates
exist), an elapsed-time/cost budget, success termination, no-progress termination, a
safety/authority stop, and who may promote the result. Missing or inconclusive verification never
becomes success. Persist only the accepted result and the evidence needed to reproduce the decision;
scratch attempts are not a second learning system.

- **Name the verifier before the work.** A failing test or fixture for `software-engineer`; the two-lens packet
  for `reviewer`; golden-signal recovery evidence for `sre` and `observability-engineer`; one
  focused red-first test for a changed fleet contract, plus Gate A once before push. An agent whose
  loop has no verifier can only emit `[unverified]` claims, however good the prose.
- **Gather minimally.** Pull the slice (grep, tail, a pinned file:line), not the corpus —
  oversized gathering contributes to context rot, and it is why workers return short
  summaries instead of transcripts.
- **The verifier defines success.** A model upgrade can improve an attempt, but it does not replace
  external outcome evidence. This fleet carries no `model:` pins today, for host portability and
  synchronization policy; it does not claim that a weaker model always beats a stronger one.

## Orchestration shapes (graph engineering)

- **Orchestrator–workers** — the main session owns plan + synthesis; workers get bounded mandates
  and isolated context. This is the fleet default when multi-agent work is justified.
- **Pipeline** — use for fixed, decomposable stages where items can advance independently without a
  global barrier; wall-clock is the slowest single-item chain.
- **Fan-out with barrier** — only when a stage needs ALL prior results at once (dedupe,
  cross-compare, early-exit on zero). Barriers idle the fast workers; justify each one.
- **Judge panel / adversarial verification** — independent attempts scored, or findings that
  survive only if skeptics prompted to *refute* them fail. Kills plausible-but-wrong output;
  worth the cost on high-stakes review.
- **Loop-until-dry** — for unknown-size discovery, choose K and a hard maximum before starting, then
  stop after K consecutive rounds surface nothing new or the hard budget is reached. Fixed counts
  alone miss the tail; an unspecified K creates a runaway loop.

Decompose by **context boundary — what each lane may see — not by job title.** That is why `reviewer`
reads the local checkout but holds no web, shell, or delegation, and `researcher` holds only the
public web and no local read. Fan-out costs real tokens (see *When it pays*), so the single-lane
default stands until breadth, isolation, or adversarial verification pays for the split.

## Handoffs between contexts (context + graph engineering)

The graph's edges carry more risk than its nodes. Some runtimes retain a worker thread; others start
each delegation from a new context. The explicit packet is the only portable handoff contract, and
an underspecified packet can fail silently when the receiver works from the wrong premise.

- **Structured note-taking beats a summary.** The packet convention in each agent body is a fixed
  field set — owner, change, findings with evidence, current state, what was NOT done, success
  criteria — because free-form prose drops whichever field the sender did not think mattered.
- **Labels survive the trip.** `[verified]`, `[sourced]`, `[unverified]`, and `[UNTRUSTED]` are
  copied exactly and never upgraded in transit. A receiver that re-labels has manufactured evidence.
- **Name the change or it is stale on arrival.** The `Change:` line identifies the PR, branch, named
  diff, or working tree the packet describes. The receiver re-derives the current diff before relying
  on it; a prior review does not cover later changes automatically.
- **State what you did not do.** The omission a sender finds obvious is the gap a receiver fills
  with an assumption.
- **Carry execution lineage.** Every packet includes `Run/attempt:` and `Model:` with the requested
  and resolved model identity. Preserve the run identity across a workflow and increment the
  attempt for every dispatch, retry, resume, or replacement. A missing resolved identity cannot
  close a model-dependent decision.
- **Make delegate failure state explicit.** An empty, malformed, partial, timed-out, or killed return
  is a failed attempt rather than success. Record it, dispatch no dependent work, and return control
  to the caller as `BLOCKED` or `INCONCLUSIVE`; a human may choose a replacement or a retry inside
  the declared budget. No background scheduler, lease, stale-worker detector, or heartbeat is implied.

## Design principles

- **Never assume inherited context.** Construct exactly the context each worker needs: intent,
  current state, success criteria, exact inputs, source trust, open unknowns, and a return schema.
  A runtime may preserve a worker thread while still isolating it from the caller's history.
- **The final message is the interface.** Specify each agent's return contract; free-text handoffs
  drop constraints at every hop. Preserve [verified], [sourced], [unverified], and [UNTRUSTED] labels.
- **Tools are authority.** The agent's `tools:` list encodes the mandate. Enforce roles at the tool
  layer, not with prose.
- **Descriptions route.** State the concise **capability or user goal**, **invocation conditions**,
  and **meaningful exclusions**; never put **step-by-step procedure or tool choreography** there
  (see [artifact guidance](./artifact.md)).
- **Budget explicitly.** Tokens, latency, and strand count per task; right-size the fan-out: 1 agent
  for a lookup, 2–4 for a comparison or multi-lens review, more only for genuinely decomposable work.
- **Design the failure path.** Decide up front what happens when a worker returns garbage, nothing,
  or half the contract — and where untrusted content could enter.

## Failure modes to diagnose

Context poisoning (bad early output contaminates downstream) · telephone-game loss (each
summarization hop drops a constraint) · duplicated/overlapping work from vague lane boundaries ·
ambiguity amplification (one underspecified task fanned to N agents → N interpretations) · barrier
waste · runaway loops with no dry-out condition · missing return contracts.

## Deliverable

A roster delta or design: each agent's lane, trigger description, tool authority, handoff edges,
context budget, and failure handling. Agents inherit the session model by default, and none pins
one today. A **generation alias** (`haiku`/`sonnet`/`opus`/`fable`/`inherit`) is permitted where a
lane's cost or latency profile justifies tiering; a full model ID is rejected by
`validate_fleet.py` because that is the form that rots. Tier *down* a lane whose work is
high-volume and mechanical, and leave judgment-heavy lanes — review, root cause, authority
decisions — inheriting. A pin is a claim about a lane's difficulty: state why in the same change,
and drop it when the reason stops holding. Generated host adapters carry no model concept, so a
pin is Claude-only and the projection simply omits it. Hand single-artifact wording to
[artifact guidance](./artifact.md), approved implementation to the typed `software-engineer` agent, independent
findings to the typed `reviewer` agent, and authorization to the human release owner with existing
approval evidence naming the exact target, action, and rollback.

## When it pays — and when it doesn't

- **Parallelize** genuinely *independent* strands: research across sources, a multi-lens review,
  sweeping many files/foundations, or distinct hypotheses.
- **Keep tightly coupled work sequential.** Decide by the task dependency graph and evals, not by
  declaring all coding single- or multi-agent.
- **Mind the cost.** Measure this fleet's token, latency, and outcome delta before generalizing a
  fan-out from one lane to another.

## Right-sizing

- Start with 1 agent for a simple lookup and a small fan-out for an independent comparison or
  multi-lens review; scale only when the task remains genuinely decomposable.
- Give each strand an **isolated context** and a **bounded mandate**, and have it return a **short
  summary**, not its transcript (see [context guidance](./context.md)).
- Combine deliberately: a merge pass reconciling the strands beats naive concatenation.
- **Set the tier per strand.** A spawned agent inherits the session model unless the call names
  one, so on an expensive session tier a fan-out silently prices bulk work at the top rate. Name the
  generation alias for every strand — `sonnet` for mechanical executors, graders, and routing
  trials, `opus` for judgment-heavy review — and reserve the session's top tier for work the human
  has explicitly priced. Before launching more than a handful of strands, state the tier and the
  rough token cost in the plan; a fork inherits the session model and cannot be tiered down.

## Learning as repository state (loop engineering)

The fleet's durable memory is owned files: an accepted behavior becomes a focused test or eval,
operational knowledge becomes a reviewable documentation diff, and unfinished work in this
repository has one owner in `docs/fleet-roadmap.md`. Candidate generation is bounded and scratch
state is discarded; human acceptance of the exact PR revision promotes the exact winning revision,
never a background memory write. The stance is deliberately stricter than session-written memory
stores: it prevents memory poisoning by admission.

## Wrapper-layer failure taxonomy

When an agent runs behind prompt-assembly, memory, retry, and delivery layers, the model is rarely
the first thing to suspect. Diagnose the stack:

- **Wrapper regression** — the model answers correctly on a direct call but fails inside the stack.
  Bisect the layers before blaming the model.
- **Hidden second passes** — a repair, retry, or summarize step mutating output between generation
  and delivery. Make each an explicit contract or remove it; a silent second pass is unaccountable.
- **Memory poisoning by admission** — the agent's own assertions written into durable memory and
  later read back as fact. User corrections outrank the agent's self-reports; never let an agent
  promote its own claim to accepted knowledge (this is the fleet's learning-disposition rule).
- **Context duplication** — one fact arriving via prompt, history, *and* memory reads as three
  independent confirmations. Dedupe the source, or it manufactures false certainty.
- **Transport corruption** — the logs show the right answer but the user sees a wrong one. The defect
  is rendering or delivery, not generation; check the last hop.
- **Prompt-only tool mandates** — a required tool the code never actually gates gets skipped under
  load. If a step must run a tool, enforce it in the harness, not with prose alone.
