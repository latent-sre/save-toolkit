# Roster altitude — design the agent system, not one artifact

## Contents

- First question: should this be multi-agent at all?
- Agent vs. skill (this fleet's decision rule)
- The loop inside each lane (loop engineering)
- Orchestration shapes (graph engineering)
- Design principles
- Failure modes to diagnose
- Deliverable
- When it pays — and when it doesn't
- Right-sizing
- Multi-agent pattern catalog (design vocabulary)
- Learning as repository state (learning engineering)
- Wrapper-layer failure taxonomy

## First question: should this be multi-agent at all?

A single agent with good tools beats a committee for most tasks. Reach for multiple agents when: the
work exceeds one context window; stages need isolation (research vs execution, finder vs verifier);
independent perspectives reduce error (review panels, adversarial verification); or parallelism buys
real wall-clock time. If none of those hold, recommend the single-agent design and say why.

Multi-agent is an architecture decision with real costs — tokens, latency, and information loss at
every handoff. Fan-out runs **~15× the tokens of a normal chat** (single agents already run ~4×), so
weigh that cost when splitting work across agents versus deepening skills on an existing role.
*[sourced: Anthropic "Building effective agents", "How we built our multi-agent research system"]*

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

- **Name the verifier before the work.** A failing test or fixture for `sde`; the two-lens packet
  for `reviewer`; golden-signal recovery evidence for `sre` and `observability-engineer`; Gate A
  plus `mutation_guard.py` for changes to the fleet itself. An agent whose loop has no verifier
  can only emit `[unverified]` claims, however good the prose.
- **Gather minimally.** Pull the slice (grep, tail, a pinned file:line), not the corpus —
  oversized gathering is the loop-level cause of context rot, and it is why workers return short
  summaries instead of transcripts.
- **The loop beats the model.** A weaker model in a tight loop with a real verifier outperforms a
  stronger model asserting once — which is why this fleet invests in verifiers and carries no
  `model:` pins.

*[sourced: Anthropic "Building agents with the Claude Agent SDK", "Building effective agents"]*

## Orchestration shapes (graph engineering)

- **Orchestrator–workers** — the main session owns plan + synthesis; workers get bounded mandates
  and isolated context. This is the fleet default.
- **Pipeline** — items flow through stages independently, no barrier; wall-clock = slowest
  single-item chain. Default for multi-stage work.
- **Fan-out with barrier** — only when a stage needs ALL prior results at once (dedupe,
  cross-compare, early-exit on zero). Barriers idle the fast workers; justify each one.
- **Judge panel / adversarial verification** — independent attempts scored, or findings that
  survive only if skeptics prompted to *refute* them fail. Kills plausible-but-wrong output;
  worth the cost on high-stakes review.
- **Loop-until-dry** — for unknown-size discovery, iterate until K consecutive rounds surface
  nothing new; fixed counts miss the tail.

## Design principles

- **Workers are stateless and context-blind.** Construct exactly the context each needs: intent, current state, success criteria, exact inputs, source trust, open unknowns, and a return schema.
  Never assume workers inherit the caller's context. Underspecified handoffs are the #1 multi-agent bug.
- **The final message is the interface.** Specify each agent's return contract; free-text handoffs
  drop constraints at every hop. Preserve [verified], [sourced], [unverified], and [UNTRUSTED] labels.
- **Tools are authority.** The agent's `tools:` list encodes the mandate. Enforce roles at the tool
  layer, not with prose.
- **Descriptions route; keep them trigger-only** (see [artifact guidance](./artifact.md)).
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
cheaply tiering routine agents separately from judgment-heavy agents. Accept the shared tier by
default. A per-agent `model:` pin is a reviewed roster decision, justified only
when the cost of a wrong call exceeds that maintenance overhead. Hand single-artifact wording to
[artifact guidance](./artifact.md), approved implementation to the typed `sde` agent, independent
findings to the typed `reviewer` agent, and authorization to the human release owner with existing
approval evidence naming the exact target, action, and rollback.

## When it pays — and when it doesn't

- **Parallelize** genuinely *independent* strands: research across sources, a multi-lens review,
  sweeping many files/foundations, surfacing a differential of hypotheses. Anthropic's multi-agent
  research system beat single-agent by a wide margin on parallelizable breadth — *"token usage
  explains ~80% of the variance"*. *[sourced: Anthropic multi-agent research system]*
- **Keep sequential** tightly-coupled work — especially **coding**, where each step depends on the
  last. Fan-out there causes conflicting edits and rework. *[sourced: Anthropic — multi-agent is weak
  for coding]*
- **Mind the cost.** Multi-agent fan-out can run **~15× the tokens of a normal chat** (single agents already run ~4×). Spend it only when the outcome clears that bar; **most tasks capture the reliability gains inside one agent** (sectioned tool calls, a couple of review lenses) without the multi-agent premium. *[sourced: Anthropic multi-agent research system]*

## Right-sizing

- 1 agent for a simple lookup; 2–4 for a comparison or multi-lens review; more only for genuinely complex, decomposable work. Extra agents cost coordination and tokens.
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
- **Loop-until-dry** — for unknown-size discovery, iterate until K consecutive rounds surface nothing
  new; fixed counts miss the tail.
- **Completeness critic** — a final pass that asks "what's missing?"; its answers become the next
  round of work. Guards against a roster that stops at the first plausible-looking result.

## Learning as repository state (learning engineering)

The fleet's durable memory is files. Skills with progressive disclosure hold the how-to; new
operational knowledge lands as reviewable repository state under the learning-disposition and
fleet-improvement lifecycles — consolidation is deliberate, bounded, and human-promoted, never a
background memory write. This is the conservative end of the current platform direction (Agent
Skills as files; the managed-agent memory-consolidation preview gates every learned change behind
human approve/reject), so the stance is a choice, not a gap. The failure mode it prevents is
below: memory poisoning by admission.

*[sourced: Anthropic Agent Skills; 2026-05 "dreaming" research preview, third-party coverage]*

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
