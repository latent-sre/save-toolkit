# Prompt, Context, Loop, and workflow-graph engineering research refresh

> **Status: dated research evidence, not a second backlog.** Current work and sequencing live only
> in [`fleet-roadmap.md`](../fleet-roadmap.md). This record does not select a graph runtime, add a
> schema without a consumer, or activate a deferred capability batch.

**Research baseline:** `598f32921c06e31ce88d5ec6fdcbbcb35eccfa3c`
**Research date:** 2026-08-23
**Scope:** `prompt-engineer`, `agent-authoring`, Context Engineering, Loop Engineering, agent
roster/delegation graphs, and the missing portable contract for executable workflow/state graphs.

## Conclusion

Keep one `prompt-engineer` lane and one `agent-authoring` skill. A second prompt skill would create
routing ambiguity. LLM application reliability is system-contract engineering; prompt engineering
owns the instruction and semantic-behavior layer, not runtime durability or effect authority. The
existing lane correctly diagnoses the first failing boundary across routing metadata, instructions,
context assembly, tools and schemas, orchestration, model/runtime behavior, wrappers, and
evaluation, then hands implementation to the owning layer.

Context Engineering is a separate responsibility over what enters the model's attention: selection,
ordering, provenance, freshness, trust, compaction, and retention. A large window or isolated thread
does not prove that relevant facts survive, and attention isolation is not filesystem, credential,
or authority isolation.

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

The research kept six provenance lanes separate:

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
- **Independent research and production reports:** peer-reviewed papers and named preprints were
  kept separate from vendor guidance; team-authored engineering reports were treated as adoption and
  failure evidence, not independent validation of their performance claims.

Context7 established documented framework contracts; GitHits checked implementation and test
evidence. Context7 sometimes returned a `main` source window while answering a versioned query, and
GitHits reported lagging LangGraph and AutoGen snapshots. Version-sensitive claims below are
therefore bound to an explicit version or commit instead of being asserted as current HEAD.

## 1. Prompt engineering owns the LLM-facing behavior contract

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

## 2. Context engineering owns selection, provenance, and retention

Anthropic distinguishes prompt engineering—the instruction layer—from context engineering, which
manages the complete token set available to an agent. Its practical methods include just-in-time
retrieval, progressive disclosure, compaction, structured notes, and context-isolated subagents.
Those are useful methods, not evidence that context selection is correct. See
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

Independent long-context research shows why selection remains load-bearing. [Lost in the
Middle](https://aclanthology.org/2024.tacl-1.9/) found strong position sensitivity;
[RULER v3](https://arxiv.org/abs/2404.06654v3) found that simple needle retrieval overstates usable
context; and [NoLiMa v3](https://arxiv.org/abs/2502.05167v3) found substantial degradation when
retrieval cannot rely on literal lexical overlap. Window size is therefore a capacity limit, not a
context-quality guarantee.

A portable context-selection record should name:

- source identity and revision or content hash;
- freshness, trust/taint label, inclusion reason, and owning selector;
- ordering and token budget, including what was deliberately excluded;
- model/runtime and context-builder revisions; and
- evidence-recall, stale-source, retrieval-miss, duplication/noise, and untrusted-instruction
  propagation results appropriate to the task.

Compaction is a lossy state transition, not ordinary summarization. OpenAI's compacted item is an
opaque provider object that must be passed back unchanged; it is runtime state, not a human-auditable
decision or effect record. See [OpenAI compaction](https://developers.openai.com/api/docs/guides/compaction).
Before and after compaction, the application must check preservation of authority and safety rules,
user decisions, unresolved work, evidence provenance, and external-effect state. Record the
compactor/provider version, cutoff, input/output identity, concurrency rule, rollback behavior, and
tool-call/result pairing. Re-inject load-bearing constraints from their authoritative source rather
than trusting a generic summary to preserve them.

Context isolation narrows attention; it does not grant security isolation. Anthropic Managed Agents
uses separate worker histories while sharing a sandbox, filesystem, and session-vault credentials.
See [Managed Agents multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration).
Keep this as a prose contract until a concrete context builder or compactor consumes a machine shape.

## 3. Evaluate the boundary that changed

OpenAI separates instruction/output behavior, workflow stages, tool selection and arguments, and
multi-agent handoffs. Anthropic separates task, trial, transcript/trajectory, outcome, agent harness,
and evaluation harness, and recommends multiple trials because behavior is variable. Both favor
deterministic outcome checks where possible and require model graders to be calibrated against human
judgment. See [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices),
[OpenAI agent workflow evaluation](https://developers.openai.com/api/docs/guides/agent-evals), and
[Anthropic's agent-eval guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

The portable eval stack is:

0. **Evaluation validity:** do the task, fixture, environment, harness, and grader measure the named
   production behavior, and can the grader observe every surface it claims to score?
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

Repository-visible cases remain calibration or regression cases. Withholding promotion cases
outside the authoring checkout is necessary but not sufficient: evaluator access and result reuse
must also be protected, because repeated adaptive queries to aggregate holdout results can overfit.
See [Generalization in Adaptive Data Analysis and Holdout Reuse](https://arxiv.org/abs/1506.02629).
Freeze split provenance, contamination checks, evaluator/model/runtime versions, cache namespace,
retry settings, seeds where applicable, and a query/reuse budget before tuning. Use balanced positive
and negative cases, typical/edge/adversarial inputs, stable environments, and multiple trials where
variability matters. Report pass@k when occasional capability matters and pass^k when every required
run must succeed; [tau-bench](https://arxiv.org/abs/2406.12045) demonstrates why those reliability
questions differ. OpenAI's current Evals API and guides remain active. This repository should keep
its own harness so routing, host, and evidence contracts remain reviewable and portable; only the
reusable prompt-object retirement identified above is documented.

## 4. Loop Engineering contract

“Loop Engineering” is an emerging practitioner term rather than a settled standard. The fleet uses a
specific dialect: a bounded control loop with explicit state, evidence, verifier, budgets,
termination, and promotion authority. Usage outside this fleet now exists, including Atlan's
self-reported production investigation system, but implementations differ on triggers, memory,
validation, and human control. See [Loop Engineering in Production](https://blog.atlan.com/engineering/loop-engineering-in-production-putting-ai-agents-on-call/).

The Batch 1 loop contract is sound and should remain bounded:

- name entry state and exactly what one iteration may change;
- separate gather, action/candidate generation, verification, and promotion;
- freeze the task, rubric, evaluator, model/runtime envelope, data splits, and allowed mutation
  surface before comparing candidates;
- name maximum iterations, candidates, elapsed time, cost, and tool calls as applicable;
- record candidate lineage, split provenance, cache/retry settings, seeds where meaningful, and
  paired-trial conditions;
- stop on success, no progress, safety/authority violation, external interruption, or exhaustion;
- stop on grader drift, protected-case leakage, reward gaming, or invalid harness evidence;
- treat missing or inconclusive evidence as non-success;
- use deterministic outcome evidence first, then narrow model graders calibrated with human labels;
- retain the incumbent on a tie and reject any safety, authority, or regression loss; and
- persist only the accepted revision and evidence needed to reproduce the decision.

Anthropic Managed Agents' outcome loop supplies a separate grader context and a hard iteration
limit, which corroborates the separation of action and verification. A separate context reduces
coupling; it does not make the grader an independent source of truth. This is one product-specific
implementation, not proof that self-critique is correct. See
[Define outcomes](https://platform.claude.com/docs/en/managed-agents/define-outcomes).

Independent research gives competing results. Intrinsic self-correction without external feedback
can degrade reasoning ([ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html));
key-condition verification improves selected tasks ([ProCo v3](https://arxiv.org/abs/2405.14092v3));
and structured search or language feedback can optimize compound systems in the studied settings
([GEPA v2](https://arxiv.org/abs/2507.19457v2),
[TextGrad](https://www.nature.com/articles/s41586-025-08661-4)). The resolution is conditional:
require an informative external or orthogonal signal and protected final evaluation; do not treat
the same model's ungrounded reconsideration as verification.

Community source agrees with the bounded method. DSPy implements budgeted candidate/evaluator
search and documents train/validation/test separation, held-out promotion evidence, reproducible
seeds, trace-aware metrics, and small-set overfitting risk. Promptfoo separates skill activation
from output quality and supports tool/schema/trajectory/outcome assertions. Obra Superpowers gives
useful red-baseline and pressure-case guidance, but its strict “description says when, not what” rule
rests on an upstream-reported observation whose named triggering-test fixture and result artifact are
absent at the inspected pin. It is not a reproducible evaluation or universal vendor contract.

The fleet's one-candidate default is a governance and cost boundary for repository improvement. It
is not a universal optimizer method: DSPy and GEPA intentionally explore multiple candidates inside
explicit trial budgets. Any automated optimizer remains deferred until a stable metric, protected
data split, budget, consumer, and human promotion owner exist.

The local description rule remains the correct reconciliation:

> Description = concise capability or user goal + invocation conditions + meaningful exclusions.
> Never put step-by-step procedure or tool choreography in it.

## 5. Portable executable workflow-graph contract

No inspected runtime supplies the whole portable contract. Before implementation, an executable
graph design must name:

| Concern | Required contract |
|---|---|
| Identity and version | Graph ID/version; exact agent, prompt, tool, schema, grader, model/runtime, and configuration revisions |
| Typed data | Input, internal state, node input/output, edge payload, context, and final output schemas |
| Node class | Deterministic compute, model call, tool/effect, approval, reducer/join, verifier, or terminal node |
| Edge class | Deterministic, conditional, model-selected handoff, fan-out, fan-in, interrupt, retry, compensate, or terminal |
| Concurrent state | Writer cardinality, reducer identity and algebra, ordering guarantees, conflicting writes, join quorum, partial worker failure, and late results |
| Termination | Success, no progress, maximum turns/iterations/time/cost, cancellation, safety stop, and unreachable-exit detection |
| Retry ownership | One retry owner, retryable failure classes, attempts/time budget, backoff, replay-safety state, and unsafe-replay authority |
| Scheduling and admission | Task queue, priority/fairness, tenant quota, backpressure, load shedding, heartbeat, poison-work handling, and manual repair |
| Replay and compatibility | Deterministic workflow boundary, event-history compatibility, code/build version, replay/shadow test, and in-flight migration policy |
| Durability | Run/thread/checkpoint IDs, schema version, durability mode, checkpoint boundary, recovery point, resume/fork semantics, retention, and restore |
| External effects | Caller/operation/target/tenant/payload-bound idempotency key, attempt ID, effect journal or receipt, read-after-write reconciliation, explicit `UNKNOWN`, retention, and safe compensation |
| Human control | Approval immediately before the effect path; approver identity, expiry, rejection, timeout, and resumed-state binding |
| Lifecycle | Pause, resume, cooperative versus durable cancel, supersede, late-worker quarantine, restart, replay, cleanup deadline, and retention |
| Security and taint | Actor, tool authority, credential scope, untrusted-data lineage, and edge-by-edge label preservation |
| Observability and eval | Node/edge spans with attempt/replay identity; tool, handoff, guardrail, approval, and effect events; node, edge, path, outcome, recovery, consistency, and temporal evals |

Checkpointing proves known graph progress, not exactly-once external effects. A remote write can
commit before its result or the next checkpoint becomes durable. Retrying, resuming, replaying, or
canceling may therefore execute a handler again or leave the outcome unknown. The graph contract
must make `UNKNOWN` a real state and reconcile before retrying. Compensation is valid only when the
domain operation is actually reversible.

At-least-once effect safety also requires semantic idempotency: bind the key to the caller,
operation, target, tenant, and payload intent; reject reuse for a different intent; retain the
result or tombstone long enough for late arrivals; and atomically couple the durable receipt to the
mutation where possible. A checkpoint, cache hit, or successful model turn does not supply that
contract. See [Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).

### What the inspected runtimes establish

| Runtime/source evidence | Established behavior | Boundary |
|---|---|---|
| [OpenAI Agents SDK at `2334679`](https://github.com/openai/openai-agents-python/tree/233467994fac7e7dbd868931573cc9a4302c0a16) | Manager/agents-as-tools versus ownership-transfer handoffs; model- versus code-selected flow; runtime `max_turns`; boundary-scoped guardrails; approval interruption with serialized resume state; parented tracing spans | Useful orchestration primitives, not a general durable graph runtime; input guardrails cover the first agent and output guardrails the final agent |
| [LangGraph at `f09cfe8`](https://github.com/langchain-ai/langgraph/tree/f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f) | Typed state/input/output/context, reducer-defined concurrent merges, dynamic `Send` fan-out, task/interrupt snapshots, checkpoints, thread IDs, replay, resume, and bounded retry | Checkpoints do not make external effects exactly once; evidence is bound to the named indexed snapshot |
| [AutoGen GraphFlow at `027ecf0`](https://github.com/microsoft/autogen/tree/027ecf0a379bcc1d09956d46d12d44a3ad9cee14) | Sequential/conditional edges, parallel fan-out, `all`/`any` joins, cycles, exits, saved manager state, and resume | Explicitly experimental; callable edge conditions are not serializable; a conditional cycle edge does not prove the exit is reachable |
| [Pydantic AI v2.33.0 at `1d7eb69`](https://github.com/pydantic/pydantic-ai/tree/1d7eb695cc17c5bed46d32749ed02092819fc3a1) | Typed node return edges, explicit `End`, parent-fork cycle analysis, Pydantic-validated tool/output surfaces, and durable-engine guidance for determinism/idempotency | Pydantic Graph v2 deliberately has no graph snapshot persistence; cancellation cannot roll back synchronous effects and recovery can repeat handlers |
| [Temporal Python SDK at `3a464f9`](https://github.com/temporalio/sdk-python/tree/3a464f9b56bad49926f03aa7b421209dbaa784f8) | Deterministic workflow replay, event histories, durable timers/signals, activity retry, and workflow-version compatibility checks | A durable workflow engine rather than a universal graph authoring model; nondeterministic model/API/database calls belong outside replay, and activities still require idempotent effect handling |
| [Anthropic Managed Agents multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration) | Versioned agent definitions and snapshotted rosters, persistent context-isolated worker threads, one-level delegation, shared session budgets, interrupts, and event streams | Beta, product-specific, and not authority isolation: agents share a sandbox, filesystem, and session vault credentials even though tools and histories are agent-scoped |

Among the inspected OSS runtimes, LangGraph exposes the most complete checkpoint/retry surface;
AutoGen exposes useful graph-flow semantics but is experimental; Pydantic Graph emphasizes typing
and join analysis while separating persistence; Temporal supplies deterministic history replay but
uses a different programming and effect model. That disagreement is evidence for a portable
contract and concrete failure model first, not for choosing one framework by default. Checkpoints,
manual `save_state`, and progress ledgers are recovery aids; they are not interchangeable with
deterministic replay or exactly-once external effects.

The independent MAST taxonomy groups observed multi-agent failures into system design,
inter-agent misalignment, and task-verification failures. That supports explicit state, handoff,
join, verification, and termination contracts rather than assuming that adding agents improves the
outcome. See [Why Do Multi-Agent LLM Systems Fail? v3](https://arxiv.org/abs/2503.13657v3).

## 6. Corrections made by this refresh

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
- Context selection and compaction now have explicit provenance, preservation, concurrency, and
  auditability requirements without introducing an unconsumed schema.
- The eval stack now begins with task/harness/environment/grader validity, and held-out evidence
  includes access and reuse controls rather than relying only on an external file location.
- Loop evidence now distinguishes ungrounded intrinsic self-correction from methods with structured
  or external verification and labels the fleet's one-candidate rule as governance, not a universal
  optimizer algorithm.
- Durable workflow guidance now separates graph checkpoints from deterministic event-history replay,
  retry ownership, and at-least-once external-effect safety.

## 7. Disagreements and resolutions

| Evidence disagreement | Local resolution |
|---|---|
| OpenAI recommends model-snapshot pins for production API apps; the fleet bans agent `model:` pins | Keep the fleet portable and host-inherited; record exact runtime/model in eval evidence. An application that owns model selection may pin outside these canonical agent files |
| OpenAI is retiring reusable prompt objects; Anthropic Managed Agents version agent configurations | Keep canonical prompts/agents/skills in Git and generate host projections. Do not move them into a retiring provider object or infer cross-provider equivalence |
| Obra's reported observation says description is invocation-only; OpenAI and Anthropic say what it does and when to use it | Preserve Obra's warning against executable mini-workflows, retain concise capability, invocation conditions, and exclusions, and do not upgrade unretained upstream results into a reproducible evaluation |
| Intrinsic self-correction can degrade reasoning; structured verification and optimizer feedback improve selected tasks | Require an informative external or orthogonal signal, protected final evidence, and a stop rule; do not treat reconsideration alone as verification |
| Anthropic's 2024 “Building effective agents” now says its tooling section is dated, while current Managed Agents supplies a beta harness | Keep the still-valid simplicity/eval principles; use current product docs for runtime facts and do not make the beta harness the fleet default |
| Graph frameworks checkpoint application state; durable workflow engines replay deterministic event histories | Treat these as different recovery models; select a runtime only against a concrete consumer, effect model, migration need, and SRE boundary |

## 8. What an SRE needs from an executable graph

If the team builds or operates an executable workflow graph, SRE needs these capabilities even if
they do not become a separate skill. These are future consumer requirements, not authorization to
add an SRE lane or begin a capability batch:

- **Run identity:** graph/config/prompt/tool/schema versions and actor attached to every run.
- **Traces:** node and edge timing, model calls, tool calls and arguments, handoffs, approvals,
  guardrails, retries, checkpoints, and final outcome in one lineage.
- **Service indicators:** success and consistency rate, invalid tool arguments, path divergence,
  retry and timeout rate, stuck loops, cancellation latency, approval wait, checkpoint age/recovery,
  token/cost, and `UNKNOWN` effects awaiting reconciliation.
- **Scheduler and worker health:** schedule-to-start latency, queue depth and oldest age, poller and
  worker saturation, heartbeat age, poison-work/manual-repair backlog, hot shards, tenant fairness,
  admission decisions, and load shedding.
- **Failure-plane SLOs:** distinguish the control plane, workers, model provider, checkpoint or
  history store, and downstream effect systems so one aggregate success rate cannot hide the owner.
- **Effect safety:** idempotency keys, effect journal, read-after-write reconciliation, least-
  privilege credentials at the effect boundary, and an operator-visible partial-effect state.
- **Run control:** pause, resume, cancel, supersede, quarantine late results, and safely decide
  whether replay is permitted.
- **Durability operations:** checkpoint-store retention, backup/restore, schema migration, corrupt or
  orphaned-run recovery, workflow/build-version drift, replay canaries, and disaster-recovery
  testing.
- **Attempt-aware telemetry:** run, node/task, attempt, retry/replay, and authoritative-final-result
  identity. OpenTelemetry's GenAI agent/workflow conventions are Development at the inspected
  [`56d6b11`](https://github.com/open-telemetry/semantic-conventions-genai/tree/56d6b11a02129319bf371083fa134b7ce989c976)
  snapshot and do not provide a workflow attempt field, so runtime-specific identity remains
  necessary. Prompt, input, and output content stays opt-in, redacted, retention-bound, and
  cardinality-controlled.
- **Runbooks and alerts:** distinguish model failure, tool failure, join starvation, approval
  timeout, checkpoint failure, effect uncertainty, and budget exhaustion; each needs a different
  response.

Do not claim a graph is production-ready from prompt quality or happy-path completion alone. It
needs effect reconciliation, recovery evidence, and graph-level observability. Uber's Cadence
production report illustrates the operational relevance of replay compatibility, worker health,
backlogs, hot shards, noisy neighbors, persistence pressure, and rate limits; it is durable-workflow
evidence, not a recommendation to adopt Cadence or Temporal. See
[Announcing Cadence 1.0](https://www.uber.com/us/en/blog/announcing-cadence/).

## Disposition

- **Now:** retain one prompt lane, apply the accuracy/control-boundary corrections above, and keep
  the Batch 1 evaluator limitation explicit.
- **Batch 1 closeout:** closed by the explicit evaluator and owner disposition in the
  [`skill clarity and routing audit`](2026-08-22-skill-clarity-routing-graph-audit.md). The two
  unchanged-byte positive-route reliability gaps are deferred to `ROUTE-003`; they do not authorize
  a paid tuning loop.
- **Batch 2:** remeasure context-heavy entrypoints after Batch 1 merges, then use the reviewed
  router pattern as already planned.
- **SRE capability additions:** held by owner decision. Do not add service DR, capacity/performance,
  network/DNS/TLS, vulnerability/upgrade, GCP cost/quota, or security-incident-response skills or
  lanes without a renewed request and a named ownership/authority boundary.
- **Executable graph capability:** keep deferred until a concrete consumer, owner, authority model,
  and SRE contract are approved. Start with a runtime-neutral reference; add a JSON Schema and
  validator only when a machine consumer exists.
- **Do not add:** a second prompt skill, a universal graph runtime, per-agent model pins, or a schema
  merely for packaging symmetry.

## Primary and upstream source register

### OpenAI

- [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Compaction](https://developers.openai.com/api/docs/guides/compaction)
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
- [Managed Agents multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration)

### Community and upstream source/test evidence

- [OpenAI Agents SDK `2334679`](https://github.com/openai/openai-agents-python/tree/233467994fac7e7dbd868931573cc9a4302c0a16)
- [LangGraph `f09cfe8`](https://github.com/langchain-ai/langgraph/tree/f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f)
- [AutoGen `027ecf0`](https://github.com/microsoft/autogen/tree/027ecf0a379bcc1d09956d46d12d44a3ad9cee14)
- [Pydantic AI `1d7eb69`](https://github.com/pydantic/pydantic-ai/tree/1d7eb695cc17c5bed46d32749ed02092819fc3a1)
- [DSPy `4ed377e`](https://github.com/stanfordnlp/dspy/tree/4ed377ee9110e912d4f5e1be43b317b87455053c)
- [Promptfoo `127d905`](https://github.com/promptfoo/promptfoo/tree/127d90534b9c1b1ba4554f007dd4b5fd2c8bf1b4)
- [Obra Superpowers `b36e082`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797)
- [Temporal Python SDK `3a464f9`](https://github.com/temporalio/sdk-python/tree/3a464f9b56bad49926f03aa7b421209dbaa784f8)
- [OpenTelemetry GenAI semantic conventions `56d6b11`](https://github.com/open-telemetry/semantic-conventions-genai/tree/56d6b11a02129319bf371083fa134b7ce989c976)

### Independent research

- [Lost in the Middle (TACL 2024)](https://aclanthology.org/2024.tacl-1.9/)
- [RULER v3 (COLM 2024)](https://arxiv.org/abs/2404.06654v3)
- [NoLiMa v3 (ICML 2025)](https://arxiv.org/abs/2502.05167v3)
- [Generalization in Adaptive Data Analysis and Holdout Reuse](https://arxiv.org/abs/1506.02629)
- [Large Language Models Cannot Self-Correct Reasoning Yet (ICLR 2024)](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html)
- [ProCo v3 (EMNLP 2024)](https://arxiv.org/abs/2405.14092v3)
- [GEPA v2 (ICLR 2026 Oral)](https://arxiv.org/abs/2507.19457v2)
- [TextGrad (Nature 2025)](https://www.nature.com/articles/s41586-025-08661-4)
- [tau-bench](https://arxiv.org/abs/2406.12045)
- [Why Do Multi-Agent LLM Systems Fail? v3](https://arxiv.org/abs/2503.13657v3)

### Production engineering reports

- [Atlan: Loop Engineering in Production](https://blog.atlan.com/engineering/loop-engineering-in-production-putting-ai-agents-on-call/)
- [Uber: Announcing Cadence 1.0](https://www.uber.com/us/en/blog/announcing-cadence/)

These production reports are team-authored accounts. They establish real adoption, operational
failure modes, and design responses; their performance and cost figures are not independently
audited evidence for this fleet.
