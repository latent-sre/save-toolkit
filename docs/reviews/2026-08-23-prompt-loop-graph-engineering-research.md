# Prompt, Loop, and workflow-graph engineering research refresh

> **Status: dated research evidence, not a second backlog.** Current work and sequencing live only
> in [`fleet-roadmap.md`](../fleet-roadmap.md). This record does not select a graph runtime, add a
> schema without a consumer, or activate a deferred capability batch.

**Research baseline:** `598f32921c06e31ce88d5ec6fdcbbcb35eccfa3c`
**Research date:** 2026-08-23
**Scope:** `prompt-engineer`, `agent-authoring`, Loop Engineering, agent roster/delegation graphs,
and the missing portable contract for executable workflow/state graphs.

## Conclusion

Keep one `prompt-engineer` lane and one `agent-authoring` skill. A second prompt skill would create
routing ambiguity. The existing lane is well aimed, but its correct mental model is broader than
prompt prose: it engineers the LLM-facing part of a system contract and diagnoses the first failing
boundary across routing metadata, instructions, context assembly, tools and schemas, orchestration,
model/runtime behavior, wrappers, and evaluation.

Loop Engineering remains a separate discipline. It defines a bounded gather/action/verify/repeat
control loop with explicit state, budgets, termination, verifier, and promotion authority. It can
improve a prompt, but it also applies to system-control loops and is not synonymous with prompt
engineering or with a cycle in a graph.

Graph engineering still has three different meanings:

1. The fleet's roster/delegation graph already belongs to `agent-authoring`.
2. An executable workflow/state graph needs a portable contract before any runtime choice.
3. Code, dependency, knowledge, runtime-topology, and GraphRAG graphs remain a separate capability.

The immediate corrections are accuracy and control-boundary fixes. This follow-up does **not** add a
new agent, skill, runtime, or schema.

## Evidence method

The research kept five provenance lanes separate:

- **Local workspace:** canonical agent/skill sources, the routing/eval harness, hard rules, and the
  prior audit. Generated host projections were treated as consequences, not independent sources.
- **OpenAI primary documentation:** fetched through the official OpenAI documentation service.
- **Anthropic primary documentation and engineering posts:** fetched directly from Anthropic.
- **Context7:** current documented contracts for LangGraph, OpenAI Agents SDK, AutoGen, and Pydantic
  AI. The resolved IDs were `/langchain-ai/langgraph/1.0.8`,
  `/openai/openai-agents-python/v0.7.0`, `/microsoft/autogen/python_v0_7_4`, and
  `/pydantic/pydantic-ai/v2.0.0`.
- **GitHits:** exact upstream documentation, source, and tests at named commits for the same graph
  runtimes plus DSPy, Promptfoo, and Obra Superpowers.

Context7 established documented framework contracts; GitHits checked implementation and test
evidence. Context7 sometimes returned a `main` source window while answering a versioned query, and
GitHits reported lagging LangGraph and AutoGen snapshots. Version-sensitive claims below are
therefore bound to an explicit version or commit instead of being asserted as current HEAD.

## 1. Prompt engineering is system-contract engineering

OpenAI and Anthropic now give the same high-level direction: prompt text matters, but reliable
systems also depend on context, tool contracts, schemas, runtime controls, and evals. OpenAI says to
use Structured Outputs for schema adherence; Anthropic says to use Structured Outputs or strict tool
schemas when valid JSON or tool arguments must conform. Both reject prompt-only formatting as the
strongest production control. See [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs),
and [Anthropic strict tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use).

Use this ownership map before editing a prompt:

| Observed failure | First owner | First control |
|---|---|---|
| Skill or agent does not activate, over-activates, or chooses the wrong lane | Routing metadata | Capability, invocation conditions, exclusions, and positive/near-miss discovery cases |
| Human-facing answer has the wrong meaning, tone, or shape | Instructions and examples | Minimal prompt change plus representative cases |
| Machine-consumed response has invalid structure | Output contract/runtime | Strict structured-output schema plus validation |
| Tool is wrong or arguments are malformed | Tool surface | Distinct name/description, typed schema, strict mode where available, and tool-selection/argument evals |
| Fixed branch, approval, or side effect occurs at the wrong place | Orchestration/runtime | Deterministic edge, tool/effect boundary, or approval interrupt |
| Direct call works but wrapped call fails | Wrapper/context/runtime | Boundary bisection; do not compensate in prompt text |
| Valid behavior receives a bad score | Evaluator | Repair task, grader, or harness before optimizing the artifact |

OpenAI's current prompt guide also says production API prompts should be stored in code with typed
inputs, fixtures, tests, and staged deployment; reusable API prompt objects are scheduled for
retirement. This repository's canonical Markdown sources already satisfy the durable principle:
they are version-controlled, reviewed, projected deterministically, and tested. It should not adopt
the retiring prompt-object surface. See
[Version prompts in code](https://developers.openai.com/api/docs/guides/prompt-engineering#version-prompts-in-code).

OpenAI recommends pinning model snapshots for a production API application. That does not override
this fleet's no-`model:` rule: the recommendation applies to an application runtime that owns model
selection; these host-native agent files deliberately inherit the host session model. Comparable
eval evidence must still record the exact host, model, runtime, wrapper, and artifact revision.

## 2. Evaluate the boundary that changed

OpenAI separates instruction/output behavior, workflow stages, tool selection and arguments, and
multi-agent handoffs. Anthropic separates task, trial, transcript/trajectory, outcome, agent harness,
and evaluation harness, and recommends multiple trials because behavior is variable. Both favor
deterministic outcome checks where possible and require model graders to be calibrated against human
judgment. See [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices),
[OpenAI agent workflow evaluation](https://developers.openai.com/api/docs/guides/agent-evals), and
[Anthropic's agent-eval guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

The portable eval stack is:

1. **Activation:** did selection invoke the intended component and avoid sibling near misses?
2. **Artifact behavior:** after explicit selection and with its required references available, did
   the prompt/agent/skill satisfy its output contract?
3. **Tool behavior:** were the correct tool and arguments selected, and was the result interpreted
   correctly?
4. **Graph behavior:** were the correct handoff/edge/path, approval, retry, and termination taken?
5. **Outcome:** did the environment reach the required state without violating cost, latency,
   safety, or authority constraints?

This distinction explains the Batch 1 discovery result: a target invocation can establish
activation, while a `Skill,Task`-only harness that cannot read the linked reference cannot grade the
reference-dependent body. Making the description longer would hide an evaluator defect rather than
improve the skill.

Repository-visible cases remain calibration or regression cases. A true held-out promotion result
requires cases withheld outside the authoring checkout. Use balanced positive and negative cases,
typical/edge/adversarial inputs, stable environments, multiple trials where variability matters,
and separately maintained capability and regression suites. OpenAI's current hosted Evals platform
is scheduled for retirement; its portable methods remain useful, but this repository should keep its
own harness rather than migrate to a retiring service surface.

## 3. Loop Engineering contract

The Batch 1 loop contract is sound and should remain bounded:

- name entry state and exactly what one iteration may change;
- separate gather, action/candidate generation, verification, and promotion;
- name maximum iterations, candidates, elapsed time, cost, and tool calls as applicable;
- stop on success, no progress, safety/authority violation, external interruption, or exhaustion;
- treat missing or inconclusive evidence as non-success;
- use deterministic outcome evidence first, then narrow model graders calibrated with human labels;
- retain the incumbent on a tie and reject any safety, authority, or regression loss; and
- persist only the accepted revision and evidence needed to reproduce the decision.

Anthropic Managed Agents' outcome loop supplies a separate grader context and a hard iteration
limit, which corroborates the separation of action and verification. It is one product-specific
implementation, not proof that self-critique is independent or correct. See
[Define outcomes](https://platform.claude.com/docs/en/managed-agents/define-outcomes).

Community source agrees with the bounded method. DSPy implements budgeted candidate/evaluator
search and documents train/validation/test separation, held-out promotion evidence, reproducible
seeds, trace-aware metrics, and small-set overfitting risk. Promptfoo separates skill activation
from output quality and supports tool/schema/trajectory/outcome assertions. Obra Superpowers gives
useful red-baseline and pressure-case evidence, but its strict “description says when, not what” rule
came from one harness-specific failure and is not a universal vendor contract.

The local description rule remains the correct reconciliation:

> Description = concise capability or user goal + invocation conditions + meaningful exclusions.
> Never put step-by-step procedure or tool choreography in it.

## 4. Portable executable workflow-graph contract

No inspected runtime supplies the whole portable contract. Before implementation, an executable
graph design must name:

| Concern | Required contract |
|---|---|
| Identity and version | Graph ID/version; exact agent, prompt, tool, schema, grader, model/runtime, and configuration revisions |
| Typed data | Input, internal state, node input/output, edge payload, context, and final output schemas |
| Node class | Deterministic compute, model call, tool/effect, approval, reducer/join, verifier, or terminal node |
| Edge class | Deterministic, conditional, model-selected handoff, fan-out, fan-in, interrupt, retry, compensate, or terminal |
| Concurrent state | Reducer semantics, ordering guarantees, conflicting writes, join quorum, partial worker failure, and late results |
| Termination | Success, no progress, maximum turns/iterations/time/cost, cancellation, safety stop, and unreachable-exit detection |
| Durability | Run/thread/checkpoint IDs, schema version, checkpoint boundary, resume point, replay/fork semantics, and migration |
| External effects | Idempotency key, attempt ID, effect journal, read-after-write reconciliation, explicit `UNKNOWN`, and safe compensation |
| Human control | Approval immediately before the effect path; approver identity, expiry, rejection, timeout, and resumed-state binding |
| Lifecycle | Pause, resume, cancel, supersede, late-worker quarantine, restart, replay, and retention |
| Security and taint | Actor, tool authority, credential scope, untrusted-data lineage, and edge-by-edge label preservation |
| Observability and eval | Node/edge spans; tool, handoff, guardrail, and approval events; node, edge, path, outcome, recovery, and temporal evals |

Checkpointing proves known graph progress, not exactly-once external effects. A remote write can
commit before its result or the next checkpoint becomes durable. Retrying, resuming, replaying, or
canceling may therefore execute a handler again or leave the outcome unknown. The graph contract
must make `UNKNOWN` a real state and reconcile before retrying. Compensation is valid only when the
domain operation is actually reversible.

### What the inspected runtimes establish

| Runtime/source evidence | Established behavior | Boundary |
|---|---|---|
| [OpenAI Agents SDK at `2334679`](https://github.com/openai/openai-agents-python/tree/233467994fac7e7dbd868931573cc9a4302c0a16) | Manager/agents-as-tools versus ownership-transfer handoffs; model- versus code-selected flow; runtime `max_turns`; boundary-scoped guardrails; approval interruption with serialized resume state; parented tracing spans | Useful orchestration primitives, not a general durable graph runtime; input guardrails cover the first agent and output guardrails the final agent |
| [LangGraph at `f09cfe8`](https://github.com/langchain-ai/langgraph/tree/f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f) | Typed state/input/output/context, reducer-defined concurrent merges, dynamic `Send` fan-out, task/interrupt snapshots, checkpoints, thread IDs, replay, resume, and bounded retry | Checkpoints do not make external effects exactly once; evidence is bound to the named indexed snapshot |
| [AutoGen GraphFlow at `027ecf0`](https://github.com/microsoft/autogen/tree/027ecf0a379bcc1d09956d46d12d44a3ad9cee14) | Sequential/conditional edges, parallel fan-out, `all`/`any` joins, cycles, exits, saved manager state, and resume | Explicitly experimental; callable edge conditions are not serializable; a conditional cycle edge does not prove the exit is reachable |
| [Pydantic AI v2.33.0 at `1d7eb69`](https://github.com/pydantic/pydantic-ai/tree/1d7eb695cc17c5bed46d32749ed02092819fc3a1) | Typed node return edges, explicit `End`, parent-fork cycle analysis, Pydantic-validated tool/output surfaces, and durable-engine guidance for determinism/idempotency | Pydantic Graph v2 deliberately has no graph snapshot persistence; cancellation cannot roll back synchronous effects and recovery can repeat handlers |
| [Anthropic Managed Agents multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multi-agent) | Versioned agent definitions and snapshotted rosters, persistent context-isolated worker threads, one-level delegation, shared session budgets, interrupts, and event streams | Beta, product-specific, and not authority isolation: agents share a sandbox, filesystem, and session vault credentials even though tools and histories are agent-scoped |

Among the inspected OSS runtimes, LangGraph exposes the most complete checkpoint/retry surface;
AutoGen exposes useful graph-flow semantics but is experimental; Pydantic Graph emphasizes typing
and join analysis while separating persistence. That disagreement is evidence for a portable
contract first, not for choosing one framework by default.

## 5. Corrections made by this refresh

The local research found and corrected these concrete problems:

- `prompt-engineer` no longer treats every failure as an ambiguous prompt; it diagnoses the owning
  system boundary first.
- Machine-consumed output and tool arguments now route to schemas/runtime validation before prose
  recipes; human-facing shape still uses positive instructions and examples.
- Activation, artifact behavior, tool behavior, graph path, and final outcome are separate eval
  results.
- The roster no longer permits a “reviewed” per-agent model pin that contradicts the fleet's hard
  no-pin rule.
- Anthropic's 4×/15× token measurements and 80% BrowseComp variance are scoped to its research
  workload rather than presented as universal constants.
- Roster and spawn guidance no longer claim that a weaker model with a verifier always beats a
  stronger model, that underspecified handoffs are the universal number-one defect, or that workers
  are always stateless or always inherit no context.
- Managed Agents Dreams are described accurately: the preview creates a separate output memory
  store; it does not approval-gate each ordinary memory write.
- Tool guidance no longer invents a roughly-dozen-tool failure threshold or recommends hiding
  unrelated actions behind one enum merely to reduce tool count.
- Context guidance no longer calls tool-result clearing lossless or recommends replay without
  defined checkpoint and effect semantics.

## 6. Disagreements and resolutions

| Evidence disagreement | Local resolution |
|---|---|
| OpenAI recommends model-snapshot pins for production API apps; the fleet bans agent `model:` pins | Keep the fleet portable and host-inherited; record exact runtime/model in eval evidence. An application that owns model selection may pin outside these canonical agent files |
| OpenAI is retiring reusable prompt objects; Anthropic Managed Agents version agent configurations | Keep canonical prompts/agents/skills in Git and generate host projections. Do not move them into a retiring provider object or infer cross-provider equivalence |
| Obra's measured rule says description is invocation-only; OpenAI and Anthropic say what it does and when to use it | Preserve Obra's warning against executable mini-workflows, while retaining concise capability, invocation conditions, and exclusions |
| Anthropic's 2024 “Building effective agents” now says its tooling section is dated, while current Managed Agents supplies a beta harness | Keep the still-valid simplicity/eval principles; use current product docs for runtime facts and do not make the beta harness the fleet default |
| Frameworks disagree on bundled persistence and validation | Require the portable contract; select a runtime only against a concrete consumer, failure model, and SRE boundary |

## 7. What an SRE needs from an executable graph

If the team builds or operates an executable workflow graph, SRE needs these capabilities even if
they do not become a separate skill:

- **Run identity:** graph/config/prompt/tool/schema versions and actor attached to every run.
- **Traces:** node and edge timing, model calls, tool calls and arguments, handoffs, approvals,
  guardrails, retries, checkpoints, and final outcome in one lineage.
- **Service indicators:** success and consistency rate, invalid tool arguments, path divergence,
  retry and timeout rate, stuck loops, cancellation latency, approval wait, checkpoint age/recovery,
  token/cost, and `UNKNOWN` effects awaiting reconciliation.
- **Effect safety:** idempotency keys, effect journal, read-after-write reconciliation, least-
  privilege credentials at the effect boundary, and an operator-visible partial-effect state.
- **Run control:** pause, resume, cancel, supersede, quarantine late results, and safely decide
  whether replay is permitted.
- **Durability operations:** checkpoint-store retention, backup/restore, schema migration, corrupt or
  orphaned-run recovery, and disaster-recovery testing.
- **Runbooks and alerts:** distinguish model failure, tool failure, join starvation, approval
  timeout, checkpoint failure, effect uncertainty, and budget exhaustion; each needs a different
  response.

Do not claim a graph is production-ready from prompt quality or happy-path completion alone. It
needs effect reconciliation, recovery evidence, and graph-level observability.

## Disposition

- **Now:** retain one prompt lane, apply the accuracy/control-boundary corrections above, and keep
  the Batch 1 evaluator limitation explicit.
- **Batch 1 closeout:** resolve or disposition the discovery evaluator boundary and remaining graph
  and service routing evidence without another unbounded paid tuning loop.
- **Batch 2:** remeasure context-heavy entrypoints after Batch 1 merges, then use the reviewed
  router pattern as already planned.
- **Executable graph capability:** keep deferred until a concrete consumer, owner, authority model,
  and SRE contract are approved. Start with a runtime-neutral reference; add a JSON Schema and
  validator only when a machine consumer exists.
- **Do not add:** a second prompt skill, a universal graph runtime, per-agent model pins, or a schema
  merely for packaging symmetry.

## Primary and upstream source register

### OpenAI

- [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- [Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)
- [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [Agent workflow evaluation](https://developers.openai.com/api/docs/guides/agent-evals)

### Anthropic

- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview)
- [Managed Agents multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multi-agent)

### Community and upstream source/test evidence

- [OpenAI Agents SDK `2334679`](https://github.com/openai/openai-agents-python/tree/233467994fac7e7dbd868931573cc9a4302c0a16)
- [LangGraph `f09cfe8`](https://github.com/langchain-ai/langgraph/tree/f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f)
- [AutoGen `027ecf0`](https://github.com/microsoft/autogen/tree/027ecf0a379bcc1d09956d46d12d44a3ad9cee14)
- [Pydantic AI `1d7eb69`](https://github.com/pydantic/pydantic-ai/tree/1d7eb695cc17c5bed46d32749ed02092819fc3a1)
- [DSPy `4ed377e`](https://github.com/stanfordnlp/dspy/tree/4ed377ee9110e912d4f5e1be43b317b87455053c)
- [Promptfoo `127d905`](https://github.com/promptfoo/promptfoo/tree/127d90534b9c1b1ba4554f007dd4b5fd2c8bf1b4)
- [Obra Superpowers `b36e082`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797)
