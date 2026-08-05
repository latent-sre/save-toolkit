# Roster altitude — design the agent system, not one artifact

## First question: should this be multi-agent at all?

A single agent with good tools beats a committee for most tasks. Reach for multiple agents when: the
work exceeds one context window; stages need isolation (research vs execution, finder vs verifier);
independent perspectives reduce error (review panels, adversarial verification); or parallelism buys
real wall-clock time. If none of those hold, recommend the single-agent design and say why.

Multi-agent is an architecture decision with real costs — tokens, latency, and information loss at
every handoff — justified only when one context genuinely can't hold the work, stages need isolation,
independent perspectives reduce error, or parallelism pays. Fan-out runs **~15× the tokens of a normal
chat** (single agents already run ~4×), so default to fewer agents with better skills.
*[sourced: Anthropic "Building effective agents", "How we built our multi-agent research system"]*

## Agent vs. skill (this fleet's decision rule)

An **agent** exists when it needs a **distinct tool-scope**. A distinct guard posture or recurring domain lane justifies a new agent only when it produces genuinely distinct tool authority. Everything else — altitude, method, checklist, playbook — is a **skill**. Seniority tiers are ladder skills, not cloned agents;
routing and live coordination stay in the main session because a coordinator subagent only adds a
round-trip for a low-context decision the main session can make inline. Apply this test before adding
any agent, and record the justification in the agent's own file (or an ADR if it reshapes the roster).
That routing choice is a reasoned default, not a measured result: neither shape has been A/B tested for
this fleet. Apply the bar symmetrically and change the architecture if a controlled A/B shows that a
coordinator agent outperforms the in-session skill after token, latency, and routing quality are counted.

The local/external research split is the fleet's concrete example. `save-toolkit-repository-investigator` receives
only local `Read`/`Grep`/`Glob`; `save-toolkit-researcher` receives only external web, Context7, and GitHits
authority. Keeping both jobs in one prompt would preserve the sensitive-data plus untrusted-content
plus egress combination, so this boundary warrants two agents. A mixed question is orchestrated by
the caller with a sanitized public handoff, never by giving either worker both evidence domains.

## Orchestration shapes

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
[artifact guidance](./artifact.md), approved implementation to the typed `save-toolkit-sde` agent, independent
findings to the typed `save-toolkit-reviewer` agent, and authorization to the human release owner with existing
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
