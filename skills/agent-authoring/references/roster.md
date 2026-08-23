# Roster altitude — design the agent system, not one artifact

Four disciplines shape this fleet, and the sections below are grouped by them: **loop engineering**
(the verify step inside each lane), **graph engineering** (which lanes exist and what each may see),
**handoff engineering** (what survives between contexts), and **learning engineering** (where durable
knowledge lands). Each names a failure mode this fleet has actually hit; none is free-standing
ceremony. Vendor and community evidence was refreshed and reconciled in the repository record
`docs/reviews/2026-08-23-prompt-loop-graph-engineering-research.md`. External claims remain
`[sourced]`, and workload-specific measurements stay scoped to the workload that produced them.

## Contents

- First question: should this be multi-agent at all?
- Agent vs. skill (this fleet's decision rule)
- The loop inside each lane (loop engineering)
- Orchestration shapes (graph engineering)
- Handoffs between contexts (handoff engineering)
- Design principles
- Failure modes to diagnose
- Deliverable
- When it pays — and when it doesn't
- Right-sizing
- Multi-agent pattern catalog (design vocabulary)
- Learning as repository state (learning engineering)
- Wrapper-layer failure taxonomy

## First question: should this be multi-agent at all?

Start with one agent or a deterministic workflow. Add agents when evaluation shows that ownership
transfer, context or authority isolation, independent verification, parallel breadth, or additional
context capacity pays for the added coordination. If none of those hold, recommend the simpler
design and say why.

Multi-agent is an architecture decision with real costs — tokens, latency, and information loss at
handoffs. Anthropic measured agents at roughly 4× and its multi-agent **research system** at roughly
15× the tokens of a chat; those figures are a budgeting signal from that workload, not a universal
multiplier. *[sourced: Anthropic,
["How we built our multi-agent research system"](https://www.anthropic.com/engineering/multi-agent-research-system)]*

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

- **Name the verifier before the work.** A failing test or fixture for `sde`; the two-lens packet
  for `reviewer`; golden-signal recovery evidence for `sre` and `observability-engineer`; one
  focused red-first test for a changed fleet contract, plus Gate A once before push. An agent whose
  loop has no verifier can only emit `[unverified]` claims, however good the prose.
- **Gather minimally.** Pull the slice (grep, tail, a pinned file:line), not the corpus —
  oversized gathering contributes to context rot, and it is why workers return short
  summaries instead of transcripts.
- **The verifier defines success.** A model upgrade can improve an attempt, but it does not replace
  external outcome evidence. This fleet carries no `model:` pins for host portability and
  synchronization policy; it does not claim that a weaker model always beats a stronger one.

*[sourced: Anthropic,
["Building effective agents"](https://www.anthropic.com/engineering/building-effective-agents) and
["Define outcomes"](https://platform.claude.com/docs/en/managed-agents/define-outcomes)]*

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

*[sourced: Anthropic,
["How we built our multi-agent research system"](https://www.anthropic.com/engineering/multi-agent-research-system),
["Building effective agents"](https://www.anthropic.com/engineering/building-effective-agents), and
[Managed Agents multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multi-agent)]*

## Handoffs between contexts (handoff engineering)

The graph's edges carry more risk than its nodes. Some runtimes retain a worker thread; others start
each delegation from a new context. The explicit packet is the only portable handoff contract, and
an underspecified packet can fail silently when the receiver works from the wrong premise.

- **Structured note-taking beats a summary.** The packet convention in each agent body is a fixed
  field set — owner, change, findings with evidence, current state, what was NOT done, success
  criteria — because free-form prose drops whichever field the sender did not think mattered.
- **Labels survive the trip.** `[verified]`, `[sourced]`, `[unverified]`, and `[UNTRUSTED]` are
  copied exactly and never upgraded in transit. A receiver that re-labels has manufactured evidence.
- **Name the change or it is stale on arrival.** The `Change:` line pins the commit or range the
  packet describes, and the receiver's first act is to compare it against the current head. That one
  field carries byte identity for review and merge work — which is why the full-SHA pin on *other*
  references is scoped to release evidence rather than demanded of every link.
- **State what you did not do.** The omission a sender finds obvious is the gap a receiver fills
  with an assumption.

*[sourced: Anthropic,
["Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
and [Managed Agents multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multi-agent)]*

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
context budget, and failure handling. Agents carry no `model:` pins — the whole fleet inherits the
session model. That removes per-agent synchronization and lineup maintenance, but it also prevents
cheaply tiering routine agents separately from judgment-heavy agents. Under the current hard rule a
per-agent pin is forbidden, not a roster-level exception; changing that policy would require an
explicit fleet decision and validator change. Hand single-artifact wording to
[artifact guidance](./artifact.md), approved implementation to the typed `sde` agent, independent
findings to the typed `reviewer` agent, and authorization to the human release owner with existing
approval evidence naming the exact target, action, and rollback.

## When it pays — and when it doesn't

- **Parallelize** genuinely *independent* strands: research across sources, a multi-lens review,
  sweeping many files/foundations, or distinct hypotheses. In Anthropic's BrowseComp analysis,
  token usage explained about 80% of performance variance; that is evidence about breadth-first
  research, not a general law of agent quality. *[sourced: Anthropic multi-agent research system]*
- **Keep tightly coupled work sequential.** Anthropic reports that most coding tasks expose less
  useful parallelism than research, while its earlier pattern catalog also identifies complex,
  multi-file coding as a possible orchestrator–workers fit. Resolve that by the task dependency
  graph and evals, not by declaring all coding single- or multi-agent.
- **Mind the cost.** Anthropic's roughly 4×/15× figures came from its research system. Measure this
  fleet's token, latency, and outcome delta before generalizing them to another lane.

## Right-sizing

- Start with 1 agent for a simple lookup and a small fan-out for an independent comparison or
  multi-lens review; scale only when the task remains genuinely decomposable. Anthropic's research
  system used 2–4 workers as one workload-specific allocation rule, not a portable constant.
- Give each strand an **isolated context** and a **bounded mandate**, and have it return a **short
  summary**, not its transcript (see [context guidance](./context.md)).
- Combine deliberately: a merge pass reconciling the strands beats naive concatenation.

## Multi-agent pattern catalog (design vocabulary)

Names for the shapes a `save-toolkit:<name>` roster can take — use them so a design says *which*
pattern it picked and why. The fleet-specific when-to-use guidance lives in **Orchestration shapes**
above; this is the compact naming reference, including the two shapes that section does not name.

- **Orchestrator–workers** — one agent owns plan + synthesis; workers own bounded subtasks with
  explicit inputs and return schemas. The fleet default.
- **Pipeline vs fan-out-with-barrier** — pipeline flows items through stages with no barrier
  (wall-clock = slowest single-item chain); a barrier is warranted only when a stage genuinely needs
  ALL prior results at once (dedupe, cross-compare, early-exit on zero), and it idles the fast
  workers, so justify each one.
- **Judge panel** — N independent attempts from different angles, scored by parallel judges,
  synthesized from the winner. For wide solution spaces.
- **Adversarial verification / finder→verifier** — a finding survives only if independent skeptics
  prompted to *refute* it fail to; pair a finder with a verifier and make evidence (file:line, query)
  a required field so an unrefutable claim cannot survive by default. Kills plausible-but-wrong output.
- **Loop-until-dry** — for unknown-size discovery, choose K and a hard maximum before starting, then
  stop at K consecutive empty rounds or the hard budget. The earlier orchestration-shape definition
  is the governing contract.
- **Completeness critic** — a final pass that asks "what's missing?"; its answers become the next
  round of work. Guards against a roster that stops at the first plausible-looking result.

## Learning as repository state (learning engineering)

The fleet's durable memory is owned files: an accepted behavior becomes a focused test or eval,
operational knowledge becomes a reviewable documentation diff, and unfinished work in this
repository has one owner in `docs/fleet-roadmap.md`. Candidate generation is bounded and scratch
state is discarded; human acceptance of the exact PR revision promotes the exact winning revision,
never a background memory write. This is deliberately stricter than Anthropic Managed Agents:
attached memory stores can be written during sessions, while the research-preview Dreams pipeline
leaves its input unchanged and produces a separate output store that an operator may review, use, or
discard. Dreams do not gate each ordinary memory write. The stricter fleet stance prevents memory
poisoning by admission.

*[sourced: Anthropic, [Managed Agents memory](https://platform.claude.com/docs/en/managed-agents/memory)
and [Dreams](https://platform.claude.com/docs/en/managed-agents/dreams)]*

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
