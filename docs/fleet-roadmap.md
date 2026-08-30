# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred work for the
> current fleet. Historical plans, reviews, audits, and decision records provide evidence and
> rationale; they do not independently add work to this queue.

The accepted architecture is
[`2026-07-31-multi-platform-plugin-packaging.md`](decisions/2026-07-31-multi-platform-plugin-packaging.md):
one canonical Claude plugin under `agents/`, `skills/`, and `commands/`, with generated host-native
adapters for Copilot/VS Code. Codex was retired as a distribution target on 2026-08-23
([ADR](decisions/2026-08-23-retire-codex-distribution-target.md)); it remains a supported way to
work in this repository, reading the root `AGENTS.md` like any other agent.

Closed items and their dispositions live in [`roadmap-closed.md`](roadmap-closed.md). That register
is evidence; it never re-queues work.

## Item contract

Every live item carries:

| Field | Meaning |
|---|---|
| ID | Stable identifier used by plans, reviews, and release evidence |
| Status | `ready`, `active`, `blocked`, `deferred`, or `decision-needed` |
| Outcome | Observable result rather than a list of files |
| Source | Decision or review that established the work |
| Prerequisites | Controls that must exist first |
| Acceptance | Evidence required to close the item |
| Next action | Smallest safe step that advances it |

An item leaves this file after its acceptance evidence is committed and the change is merged, or
after an explicit owner disposition is committed with the reason it is no longer work. Git history
and archived source documents retain the implementation detail.

**This file states what is still owed, not what was already proven.** Dated evidence, finding
tables, transcripts, and byte inventories belong in the linked packet under `docs/reviews/` or the
accepted record under `docs/decisions/`. An item cites its evidence; it does not restate it.

## Active runtime work

### WF-001 — establish a supported exact-dispatch boundary for Claude workflows

**Status:** `blocked`

**Outcome:** The repository carries no executable `ship-review` workflow until Claude provides a
supported way to dispatch one exact trusted workflow without granting caller-supplied workflow code.

**Source:** A version-pinned probe on Claude Code 2.1.221 found two incompatible behaviors:
`CLAUDE_WORKFLOW_NAME_ONLY=1` suppresses inline-plugin workflows, and without it a native permission
for `Workflow(save-toolkit:ship-review)` also admits the same `name` plus a caller-supplied `script`
that the resolver executes. A plugin `PreToolUse` hook can deny the override, but the resulting
launcher, hook receipt, Git-object isolation, and upgrade matrix were a bespoke security broker
disproportionate to this fleet, so the experiment was removed rather than shipped. Re-checked
2026-08-18 on 2.1.227: built-in `claude ultrareview` removes the caller-supplied workflow-body
surface but exposes no immutable reviewed-subject identity and no findings-sensitive verdict — it
exits 0 either way, bundles a mutable tree, and uploads to a paid cloud sandbox. Still blocked.
Sources and queries: the
[first-three backlog evidence packet](reviews/2026-08-18-first-three-backlog-evidence.md).

**Prerequisites:** A documented direct-dispatch API, or documented permission semantics that bind
the registered workflow implementation as well as its name. Any alternative architecture needs an
accepted decision record before implementation.

**Acceptance:** Pin the supported CLI/API version and prove before merge that (1) only the intended
trusted workflow implementation can execute; (2) same-name `script`, `scriptPath`, resume, remote,
and extra-field variants are denied before task creation; (3) candidate bytes never reach an outer
tool-bearing model; (4) reviewer lanes have structurally bounded authority; and (5) incomplete or
failed review evidence cannot become approval. Gate A and mocked JavaScript are supporting evidence,
not substitutes for the live boundary proof.

**Next action:** Monitor the ultrareview/direct-dispatch result contract for a documented immutable
candidate identity and machine-enforceable finding verdict. Do not restore `ship-review`, wrap an
exit-0 result as approval, or launch a paid/uploading probe until an owner explicitly accepts that
external data/cost boundary and the remaining guarantees can be proven.

## Repository work

### CONTEXT-001 — establish a generalized SRE operational-context contract

**Status:** `active` (2026-08-24)

**Owner:** `latent-sre` owns the architecture decision and acceptance of the exact generic-alpha
revision. `agent-engineer` owns consumer context-requirement semantics for agents/skills;
`software-engineer` owns any later resolver, validator, or onboarding-tool implementation. A team
owner becomes accountable for values and operational documents only when that team separately opts
into onboarding. No owner may approve its own unreviewed evidence.

**Outcome:** Reusable skills and agents resolve one explicit team, service, environment, and—when
needed—deployment from schema-valid team configuration, then receive only the smallest context
projection they declare. Onboarding a team supplies values, relationships, repository mappings,
platform identities, operational references, and runbooks without forking the underlying skills.
Missing or ambiguous context fails clearly; production is never an implicit target; valid context
does not grant credentials, approval, or effect authority.

**Concrete consumer:** The first consumer is the read-only `service-readiness-audit`. One unchanged
consumer contract must work across differently shaped synthetic teams, services, environments, and
platform representations before any real team onboards or effect-capable skill adopts the resolver.
Fixtures may model PCF and GCP/Cloud Run shapes already represented in the fleet, but they do not
decide the pending landing runtime, introduce self-managed Kubernetes, or rewrite platform
procedures.

**Source:** Owner direction on 2026-08-24 requested the smallest useful standardized operational
context contract. The
[`generalized SRE team and application context framework`](reviews/2026-08-24-sre-context-framework-architecture.md)
records the current-repository assessment, research, alternatives, proposed schemas, and staged plan.
The
[`source-independent SRE operational-context contract`](decisions/2026-08-24-sre-operational-context-contract.md)
is the accepted record: it disposes every load-bearing choice (service/system boundary,
environment/deployment split, central Git first source, versioned skill-side requirement sidecars,
typed references without deep merge, runbook indexing, phase-one file/CLI resolver, and the
curated-facts-only rule) and states the consequences, rejected alternatives, failure modes, and
rollback. Owner approval on 2026-08-24 authorized **stages 1–3 only**. Owner decision on
2026-08-26 widens that scope: effect-capable adoption of the context contract is authorized for
`service-lifecycle` as the second consumer, alongside the read-only first consumer. The
widening covers building the consumer contract; it does not waive acceptance condition (7),
which is a safety proof rather than a process gate — an effect-capable path must still
demonstrate that resolved context cannot default to production, approve an action, supply a
credential, or bypass the production/effect gate. Real-team onboarding remains unauthorized.

**Prerequisites:** The accepted ADR names the schema/contract owner, resolver owner, source
repository and permissions, generic fixture policy, representational platform shapes, and the alpha
compatibility window. No real team or service values are prerequisites. Reinspect the exact consumer
skill, generator/package behavior, dependency policy, and current schema catalog before naming
implementation files. Any third-party validator or YAML parser is pinned in `requirements-dev.txt`
and follows the CI/Gate A dependency rule. No central repository, schema, resolver, MCP server,
skill rewrite, or live discovery job is created solely from this roadmap entry.

**Acceptance:** All conditions are required and retain separate evidence labels. (1) **Architecture:**
the accepted ADR disposes every decision and retains its deliverables, boundaries, rollout, rollback,
and non-goals; a design review is not runtime proof. (2) **Source contracts:** immutable versioned
JSON Schema 2020-12 contracts exist for the minimum Team, Service, optional System, Environment,
Deployment, Repository, Integration/Resource, Runbook metadata, consumer requirement, and
resolved-bundle shapes; unknown objects fail closed, and formats plus YAML duplicate keys are tested
with the selected validator rather than assumed. (3) **Semantic resolver:** an explicit source root
and canonical selectors produce deterministic, byte-bounded output with fixture taint and qualified
provenance; duplicate IDs/aliases, broken or kind-wrong refs, forbidden cycles, zero/multiple
deployments, missing required paths, implicit production, secret-bearing fields, traversal, and
nondeterministic output have named red-first regressions. (4) **Identity and repositories:** catalog
IDs, display names, typed/scoped aliases, platform IDs, telemetry mappings, and runtime instance IDs
stay distinct; repositories are first-class and `other` never becomes an untyped escape hatch.
(5) **Generic portability proof:** at least two explicitly synthetic team fixtures, multiple services
and repositories, production-classified and non-production environments, and at least two platform
representations validate without a team-specific schema or skill branch, and the same
`service-readiness-audit` requirement contract resolves representative selections while refusing
missing or ambiguous ones. (6) **Context behavior:** required and alternative JSON Pointer paths fail
closed, optional absence stays explicit, and a fresh-context exercise demonstrates deterministic
lookup within declared depth/byte budgets without claiming exact source identity or production
correctness. (7) **Truth and safety:** no secret or copied live state ships; an effect-capable path
separately proves that context cannot default to production, approve an action, supply a credential,
or bypass the production/effect gate. (8) **Onboarding and operations:** synthetic acceptance proves
a new team can add its records and receive clear validation output without editing a generalized
skill, with ownership, migration, stale-link diagnostics, recovery, and troubleshooting documented.
(9) **Integrated verification:** focused schema/resolver/consumer regressions, affected routing or
behavior checks, adapter regeneration where canonical skill bytes change, strict plugin validation,
`git diff --check`, Gate A at the push boundary, and independent exact-revision review all pass,
each stating what it proves and what remains unverified.

**Closure:** Merge the accepted generic alpha and its exact synthetic evidence, record the supported
alpha contract and next migration boundary, then close the item. Fleet-wide adoption, federation,
Backstage/MCP adapters, automatic discovery, live reconciliation, or a general overlay language are
separately justified work and do not silently expand this item.

**Next action:** Close the producer/consumer gap between the two service skills, which needs no
resolver: `service-lifecycle` names the readiness audit as its independent verifier and states
what an onboarded service leaves on record; `service-readiness-audit` states what it expects to
find there. Then add `service-lifecycle`'s requirement sidecar under the widened authorization,
with the condition (7) safety proof. `latent-sre/sre-context` exists and carries the versioned
schemas, resolver, CLI, fixtures, and tests; stages 1–3 are substantially built rather than owed,
and this file previously said otherwise. What remains is the acceptance evidence: the second
synthetic-tenant portability proof, the effect-capable safety proof, and the paired consumer
sidecars. Sidecars ship as a mirrored pair — the consumer copy here, its twin under that
repository's `examples/`, where its own tests validate it against the schema. No team-specific
values are required and no real team is onboarded.

### GRAPH-002 — add a runtime-specific implementation lane for executable graphs

**Status:** `ready` (2026-08-26). The consumer, runtime, and sandbox boundary are accepted; no
implementation has started.

**Owner:** `software-engineer` owns implementation; `agent-engineer` owns the skill text that
carries runtime-specific references; `stack-profile`'s decision owner names the runtime.

**Outcome:** `software-engineer` can implement the accepted
`checkout-payments-timeout-drill/v1` workflow contract against LangGraph inside a hardened,
disposable Docker Compose lab named `graph-sandbox/v1`. The lab runs the synthetic checkout,
payments, and inventory applications alongside the graph runner and proves checkpointer and
interrupt behavior, reducers and fan-out, idempotent effect handling, cancellation, recovery, and
budget enforcement without creating production deployment authority.

**Source:** Owner direction on 2026-08-24 (stage 2). The
[`2026-08-23 research refresh`](reviews/2026-08-23-prompt-loop-graph-engineering-research.md)
records that no inspected runtime supplies the whole portable contract, which is why selection
follows the design and a concrete consumer rather than preceding them. Owner direction on
2026-08-26 accepted the consumer-specific Docker Compose sandbox and offline-first delivery in the
[`GRAPH-002 runtime decision`](decisions/2026-08-26-graph-002-docker-sandbox-runtime.md).

**Accepted boundary:** The consumer is `checkout-payments-timeout-drill/v1`, not the fleet itself.
The allowed runtime is Python 3.12 with exactly pinned `langgraph==1.0.8` and
`langgraph-checkpoint-sqlite==3.1.1`, executed only inside `graph-sandbox/v1`; direct host execution
is prohibited. The default profile has deterministic model fixtures and an internal-only network.
A later bounded Terra profile requires separate approval of its trial count, spend ceiling,
ephemeral credential path, and externally enforced endpoint-restricted egress; Compose alone is not
that egress control. Runtime-specific guidance stays conditional and does not make LangGraph a
universal fleet runtime.

**Prerequisites:** The `workflow-graph-engineering` method merged at `f1afd57` (closed 2026-08-26;
see the closed table) — satisfied. The named consumer and sandbox decision are accepted. Before the
first container executes, the implementation must: (1) start from current `origin/main`; (2) confirm
a reachable Linux Docker daemon; (3) pin every base image by version and digest; (4) add the exact
Python dependencies to `requirements-dev.txt` without importing them from Gate A or the isolated
read-only guard; (5) turn the consumer behavior into a versioned typed workflow contract; and (6)
write the sandbox preflight predicate and its red-first negative fixtures. Live model credentials or
paid calls are not prerequisites for the offline stages.

**Implementation plan:** Deliver independently reviewable offline slices in this order:

1. **Sandbox contract and preflight:** define the allowed Compose model and reject root users,
   privileged mode, added capabilities, writable root filesystems, published ports, external
   networks, Docker-socket or credential mounts, missing image digests, missing resource limits, and
   an unavailable daemon.
2. **Running synthetic topology:** containerize the existing checkout fixture; add deterministic
   payments and inventory simulators plus health checks; add an optional bounded load-generator
   profile. No host ports or general egress are required.
3. **Executable graph:** implement typed state, stable run/thread/attempt identities, reducer and
   fan-out behavior, approval interrupts, SQLite checkpoints, attempt/time/spend budgets,
   cancellation, evidence-envelope output, and the structured boundary-event handoff accepted in
   the [`GRAPH-003 preparation decision`](decisions/2026-08-26-graph-003-observability-preparation.md).
4. **Failure and recovery:** exercise application failure, payment latency, runner termination and
   resume, checkpoint failure, duplicate effect prevention, crash-after-dispatch `UNKNOWN`, budget
   exhaustion, and cancellation acknowledgement. Retrying a LangGraph node never substitutes for
   consumer-owned idempotency or reconciliation.
5. **Exact-revision verification:** run the focused unit, contract, integration, recovery, and
   negative sandbox suites; validate the final Compose model; record image digests, commands, exit
   status, environment, and what each result does not prove; obtain independent review and
   verification of the exact commit. Only then may an owner approve a separately bounded Terra
   behavioral run.

**Acceptance:** All conditions are required. (1) The sandbox preflight fails for each forbidden
privilege, mount, network, port, credential, writable-root, unpinned-image, and missing-limit case and
passes the reviewed Compose model. (2) The healthy running topology completes one checkout through
the real synthetic payments and inventory HTTP boundaries. (3) Restarting `graph-runner` against the
same run-scoped checkpoint resumes the correct thread without reapplying committed nodes. (4) Effect
tests prove idempotent duplicate handling and preserve `UNKNOWN` after ambiguous dispatch rather than
claiming exactly-once execution. (5) Recovery, temporal ordering, reducer/fan-out consistency,
approval, cancellation, and attempt/time/spend budget cases pass deterministically offline. (6) The
evidence bundle binds the graph contract, exact revision, image digests, run/node/edge/task/attempt/
replay/checkpoint/effect identities, commands, exit statuses, and environment; teardown never holds
the only evidence copy. (7) Independent exact-revision verification passes. (8) No production
system, credential, deployment target, dashboard, alert route, or authority is introduced.

**Rollback:** Before merge, delete the implementation branch. After the offline lab lands, disable or
remove its explicit entrypoint and return `incident-drill` to the current manual file-and-lane
procedure; export sanitized evidence first, then remove only the run-scoped containers, network, and
volumes. No production data migration exists.

**Next action:** Start Docker Desktop or another approved Linux Docker daemon, then open the first
implementation branch for slice 1: the versioned consumer contract, Compose model, sandbox preflight,
and red-first negative fixtures. Do not add live Terra egress or credentials in that slice.

### GRAPH-003 — operate running graphs: indicators, failure planes, runbooks, and alerts

**Status:** `blocked` (2026-08-26). Scope and the first operated graph are accepted; implementation
waits for `GRAPH-002` to produce the running graph and observable failure planes.

**Owner:** `observability-engineer` for indicators, dashboards, and alert design; `scribe`/`runbook`
for operating documents; `sre` remains the live-incident lane. No new agent.

**Outcome:** The owning observability and operations skills carry graph-specific material
(run/node/edge/attempt lineage, per-failure-plane indicators, queue and worker health, `UNKNOWN`
effect backlog, approval wait, checkpoint age, replay canaries, and the runbook branches per failure
class) as references inside their existing skills rather than a new SRE capability. The first scope
is the synthetic `checkout-payments-timeout-drill/v1` graph running in `graph-sandbox/v1`; this item
does not deploy a production dashboard, alert route, or pager.

**Source:** Owner direction on 2026-08-24 (stage 2). Requirements are enumerated in section 8 of the
[`2026-08-23 research refresh`](reviews/2026-08-23-prompt-loop-graph-engineering-research.md). The
2026-08-23 owner disposition that held the five SRE capability additions is unchanged; this item is
an operating reference for graphs, not one of those additions. Owner direction on 2026-08-26
confirmed that scope and named the first graph after accepting the
[`GRAPH-002 runtime decision`](decisions/2026-08-26-graph-002-docker-sandbox-runtime.md). The same
owner direction accepted the bounded telemetry handoff, operational questions, and fault matrix in
the [`GRAPH-003 preparation decision`](decisions/2026-08-26-graph-003-observability-preparation.md);
that design evidence does not prove the graph emits any signal yet.

**Accepted boundary:** `observability-engineer` extends the existing observability skills with the
smallest graph-specific references needed to answer whether the graph is serving, where it failed,
and whether replay or reconciliation is safe. `scribe`/`runbook` owns the corresponding operating
document. `sre` retains live-incident ownership. No new agent, tool, credential, production data
source, or effect authority is created. The first operated graph is
`checkout-payments-timeout-drill/v1`; a later graph must justify its own additional signals rather
than silently widening this reference set.

**Prerequisites:** `GRAPH-002` must first deliver a runnable offline topology, the graph
runner, stable run/node/edge/task/attempt/replay/checkpoint/effect identities, structured events,
controllable failure modes, and restart/resume behavior. This item remains blocked until those
signals exist as real sandbox output; drafting dashboards, thresholds, or runbooks solely from the
design would describe a system nobody operates. The GRAPH-002 implementation must preserve this
telemetry handoff, but the observability owner—not the graph runner—owns operational interpretation, cardinality
budgets, alert semantics, and runbook response.

**Acceptance:** All conditions are required. (1) References are added under the existing owning
skills with a discovery near-miss keeping a live graph outage with `sre`. (2) The indicator set is
derived from observed `graph-sandbox/v1` output and covers graph outcome and consistency, path
divergence, retries and timeouts, stuck work, cancellation latency, approval wait, checkpoint age
and recovery, cost/budget, and `UNKNOWN` effects without unbounded metric labels. (3) Failure-plane
views distinguish graph control, runner/worker, model fixture or approved provider, checkpoint
store, and downstream synthetic services rather than hiding them in one aggregate success rate.
(4) One synthetic runbook branches for model or fixture failure, tool/application failure, join
starvation, approval timeout, checkpoint failure, effect uncertainty, and budget exhaustion. (5) A
synthetic alert set is evaluated against real sandbox data, fires under the injected condition,
resolves after recovery, names an owner and first action, and pages only on actionable symptoms;
cause and saturation signals remain diagnostic. (6) No new agent, tool, credential, production
dashboard, live alert route, or pager is introduced.

**Next action:** Complete the GRAPH-002 offline graph through restart/resume and
fault-injection evidence with the telemetry identities above. Then inspect the emitted data before
choosing queries, thresholds, retention, dashboards, or alert rules; implement the minimum reference,
synthetic runbook, and tested alert set against that evidence. No paid or Terra run is required to
record this decision or to exercise deterministic sandbox failures.

### GRAPH-004 — `codebase-atlas`: code, dependency, knowledge, and GraphRAG graphs

**Status:** `decision-needed` (2026-08-24)

**Owner:** to be named; `repository-investigator` is the nearest lane for local source structure.

**Outcome:** A separate capability with its own inputs, provenance, and success criteria for
import/dependency graphs, runtime topology, knowledge graphs, and GraphRAG — kept distinct from
`workflow-graph-engineering` (executable graphs) and `agent-authoring` (roster graphs), both of which
already carry near-miss scenarios that keep these requests out.

**Source:** Owner direction on 2026-08-24 (stage 2). The
[`2026-08-22 audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) split graph engineering
into three contracts and deferred this one pending confirmed owner need.

**Decision required:** the operator need (which questions the atlas must answer), whether output is a
static analysis artifact or a retrieval index, the provenance and freshness contract, and the
consumer.

**Prerequisites:** none technical; a named need and owner.

**Acceptance:** to be defined with the decision; at minimum a positive discovery scenario, the two
existing near-miss scenarios remaining green, and no overlap with `workflow-graph-engineering`.

**Next action:** Owner names the need; until then no implementation.

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `active` (2026-08-25). F7's installed-Claude-CLI visibility gap is closed; the VS Code
boundary remains open.

**Outcome:** The guarded roles' VS Code posture rests on observed host behavior rather than
inference, and the fleet knows whether the read-only guard is portable to that host or whether
policy-delivered Copilot managed settings are the only real control there.

**Source:** A 2026-08-12 scan on two evidence bases: `[verified]` findings from the installed VS Code
1.133.0 bundle (tool-set vocabulary and Claude→VS Code equivalence match the host's enums;
`disable-model-invocation` is recognized; `runSubagent` delegation is unscoped; the hook surface
exists) and `[sourced]` findings at one remove from upstream `microsoft/vscode` @ `0157e11` and
`vscode-docs` @ `95cc3b3b` on configuration precedence. Those sources predict precedence; they do not
establish invocation authority on the current host.

**Evidence:** Three dated packets, each stating its exact build and keeping configuration evidence
separate from invocation authority.
[VS Code tool enforcement (2026-08-24)](reviews/2026-08-24-host-002-vscode-tool-enforcement.md):
every tested omitted built-in tool remained offered but disabled; enabling `execute` in the built-in
Agent picker was explicitly global and dirtied the generated-agent buffer without changing its
on-disk digest, proving a configuration/write-back path only. No command was submitted, so
invocation authority stayed `[unverified]`. The 2026-08-25 corrected reprobe on the same build
recorded a **measured negative** for that override path — switching to `sre` restored the custom
agent's set with `execute` offered-off — which disagrees with the prior same-build result and means
repeating the picker sequence cannot resolve the criterion. Sanitized transcripts and nine validated
envelopes are under [`docs/reviews/evidence/host-002`](reviews/evidence/host-002).
[`disable-model-invocation` on the Claude CLI (2026-08-25)](reviews/2026-08-25-host-002-disable-model-invocation-cli.md):
a paired disposable plugin canary on Claude Code 2.1.243 hid the guarded skill from model invocation
(`NOT_VISIBLE`, no Skill call) while explicit `/plugin:skill` invocation returned the marker. That
closes `GRAPH-001` F7 for that build without weakening the manual-only skills' body-level checks; it
establishes nothing about VS Code or Copilot hook identity. Hook scoping is `[verified static]` only:
VS Code 1.134.0 merges the selected custom agent's `hooks` before sending the request, and its
plugin-wide `PreToolUse` payload carries no custom-agent identity, so the viable candidate is a
generated `sre`-scoped hook rather than a self-scoping entry in `hooks/copilot-hooks.json`. No real
fleet hook is wired.

**Prerequisites:** An installed VS Code build with the GitHub Copilot tools surface and an
authenticated disposable test profile or other approved non-production session. The probe is
observational: it changes no live system, and it neither authorizes nor implies a Copilot hook
implementation.

**Acceptance:** A dated packet and durable, non-secret transcript/envelopes record whether the tools
picker offers `execute` to `sre`; whether an override changes the configuration; whether the active
generated buffer or on-disk file changes; and whether a safe invocation runs or receives an explicit
host denial. An operator-local artifact and hash are not closure evidence. Any hook-portability
finding is evidence only; wiring a Copilot hook is separate work needing its own review. Exact-agent
scope may be established by a hook attached to the selected custom agent; the global hook payload
does not need to invent an identity field it does not carry.

**Next action:** Run the probe's distinct agent-scoped hook canary in a disposable VS Code profile:
the custom canary must deny a harmless terminal request with its fixed marker, while the built-in
Agent control remains unaffected. Keep invocation authority open until a real tool call or host
denial is observed. Do not run a third identical picker retry, substitute a prompt-file override, or
populate `hooks/copilot-hooks.json`.

### EVAL-003 — add claim-scoped Claude and Codex evaluation engines

**Status:** `active` (2026-08-26). The architecture and offline implementation are accepted; no
model execution is authorized.

**Owner:** `latent-sre` owns the architecture, evidence/security contracts, live-run budgets, and
acceptance of an exact revision. `agent-engineer` owns the claim vocabulary, scenarios, graders, and
reference canaries. `software-engineer` owns the runner, adapters, isolation, schemas, and tests.
Neither implementation owner promotes its own result.

**Outcome:** One shared scenario and deterministic-grader corpus can run through an explicit Claude
native-plugin adapter and an explicit Codex resolved-context adapter. Claude measures the real
frozen plugin and host boundary. Codex, using an existing subscriber session rather than an API key,
measures only portable behavior, reference use, grader coverage, and cross-engine divergence. Every
result says which claims its engine can support, emits a normalized digest-bound envelope, and stays
separate in comparison and promotion views. Codex is not restored as a distribution target.

**Source:** Owner direction on 2026-08-26 requested a multi-engine evaluation architecture and
selected subscriber-account authentication for Codex. The
[`accepted multi-engine evaluation contract`](decisions/2026-08-26-multi-engine-evaluation-contract.md)
records the claim matrix, adapters, evidence envelope, security boundary, rollout, rollback, and
alternatives. This implementation candidate incorporates the published HOST-003 source revision
`c93d8cb` on top of refreshed `origin/main`; final acceptance evidence still binds to the future
clean exact implementation revision, not either parent alone.

**Prerequisites:** The owner accepted the hard-to-reverse contracts: (1) the claim matrix;
(2) a separate `eval-result-envelope/v1` rather than changing the general evidence envelope; (3)
Claude snapshot-scoped reference reads with advertised inventory distinguished from callable
policy; (4) Codex ephemeral read-only resolved-context execution using only the existing subscriber
session and no credential copying; and (5) separate engine verdicts with no averaged score. Before
any model call, the owner separately approves a fixed model, reasoning/effort setting, trial count,
per-trial timeout, total timeout, and stop condition. No API key, production target, Codex generated
projection, push, merge, or release is a prerequisite.

**Implementation sequence:** Expand before migration. First add the claim registry, normalized
schema, offline fixtures, and adapter interface. Then move the current Claude execution behind its
adapter without changing the default CLI or legacy summary and prove parity. HOST-003 is closed:
the positive in-snapshot and negative out-of-snapshot `Read` probes run in every direct trial and
the fixture workspace is an allowed root (see the register). Add the Codex
bundle resolver and adapter offline, then request a bounded live-run approval. Add divergence
classification only for comparable validated envelopes. Retire no legacy result contract until its
consumers have migrated.

**Acceptance:** All conditions are required. (1) Existing scenario YAML and deterministic graders
remain shared; provider commands and authentication never enter scenarios. (2) Claude runs one real
frozen plugin in a neutral project and separately records advertised tools, callable policy, plugin
identity, scoped reference reads, and canaries. (3) Codex runs an immutable, path-safe, size-bounded
resolved-context bundle through `codex exec --ephemeral` with a read-only sandbox, ignored user
configuration, bound ambient policy, no prior session, and no API key handling. (4) The normalized
envelope binds engine and adapter versions, resolved model, candidate SHA and input digest,
plugin/context applicability and digests, policy/scenario/grader/profile/comparison digests, canaries, claims,
verdict, duration, and typed unavailable cost. (5) Red-first tests reject unexpected tools,
out-of-snapshot reads, traversal/indirection, missing canaries, wrong digests, unsupported claims,
incomplete traces, engine mislabeling, incomparable reductions, and zero-valued unavailable cost.
(6) Claude and Codex verdicts remain separate; Codex cannot emit plugin, native-routing, or Claude
tool-boundary claims; deterministic graders gate while model judgment remains calibration only.
(7) Focused and full component tests, any required canonical generation, strict plugin validation,
`git diff --check`, Gate A, and independent exact-revision review pass. (8) Human acceptance of the
exact revision remains the only promotion authority, and no live run occurs without its own budget
approval.

**Rollback:** Before merge, delete the implementation branch. After the expand phase, disable and
remove the Codex profile, adapter, and resolver while retaining the default Claude path and shared
scenario/graders. Claude path scoping proved both the allow and the deny case on the pinned host
(HOST-003, closed); do not widen filesystem access beyond the plugin snapshot and the fixture
workspace.

**Next action:** Finish offline full-suite verification and independent review of the exact clean
candidate. Codex live execution is hard-disabled before process start: establish a structural
no-tool or bundle-only read boundary, prove a denied out-of-bundle probe plus traced resolved model
and effective policy on the exact CLI, then seek separate fixed-budget approval. Do not run either
model until its live prerequisites are satisfied.

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-08-27). Phase 1 is closed as evidence; Phase 2 is the live work, one
skill per slice, and its method changed on 2026-08-27: probe before routing.

**Outcome:** No skill spends a caller's context on detail the call did not need, and no skill
spends it restating what the fleet's models already produce unprompted. Each screened entrypoint
receives one evidence/recommendation checkpoint. A confirmed conditional body becomes a router with
an "if the question involves X, read Y" table; recitation is cut rather than routed; decisions,
pressure-dropped invariants, and routing predicates are retained explicitly with the probe evidence
that shows why.

**Source:** The initial measurement is in the
[`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md); the
[`complete skill audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) corrected the
candidate list; the [`2026-08-24 host context-budget audit`](reviews/2026-08-24-host-context-budget-audit.md)
separates the host contracts from the repository's byte screen — 5,000 until the owner reset it to
7,500 on 2026-08-27. The
[`frontend-craft disposition`](reviews/2026-08-27-skill-001-frontend-craft.md) records the
knowledge probes and pressure controls that established the probe-first method, and the refreshed
screen. Description metadata follows the current rule — capability, invocation conditions, and
exclusions, without procedure.

**Phase 1 (closed evidence):** Nine router slices merged in PRs #142, #143, #145, #146, #147, #149,
#150, #151, and #154; the [Phase 1 closure review](reviews/2026-08-24-skill-001-phase-1-closure.md)
holds the per-slice evidence. Those nine skills are excluded from Phase 2.

**Phase 2 dispositions:** `frontend-craft` — confirmed router with a knowledge cut on branch
`work/skill-001-frontend-craft`: 14,150 → 7,481 immutable entrypoint bytes, references 37,107 →
39,798, description byte-identical; below the 7,500-byte screen, and what remains is decisions,
pressure-dropped invariants, and the routing table. The after-change discovery run on `1b2d485` was
1/3 against a 0/3 previous-revision baseline (pre-existing routing instability, see `ROUTE-004`);
evidence is in the disposition review.

`agent-authoring` — retained router with a recitation cut on branch `work/skill-001-agent-authoring`:
10,911 → 8,843 immutable entrypoint bytes, references 66,628 → 36,754 (an owner-preference trim of a
pattern catalog, vendor commentary, and a changelog digest, a probe-backed recitation cut, then a
rules-as-tables form pass; every fleet rule retained), description
byte-identical, retained above the 7,500-byte screen because clean-room probes on both tiers show
the body's remaining content is fleet decisions and platform traps the models author wrong. After-change
discovery run on `fc5748a`: 3/3. Evidence, including the contaminated-probe correction, is in the
[`agent-authoring disposition`](reviews/2026-08-27-skill-001-agent-authoring.md).

`gcp-ops` — knowledge cut **retained above the screen** on branch `work/skill-001-gcp-ops`: 8,102 →
7,679 immutable entrypoint bytes (−5.2%, references untouched), description byte-identical. Review
found the first attempt had cut text pinned by two committed contracts in
`scripts/test_platform_skill_contracts.py` — the conditional traffic semantics and the rollback
propagation caveat — which were red on the branch from `a6da0d0a` until restored in `9294e80b`; that
suite was never run during the slice's own verification. The retained bytes are therefore
contract-mandated, not merely judged worth keeping.
Clean-room probes on both tiers show the body's Cloud Run mechanics are recitation, while
both no-skill pressure controls fail the committed graders on exactly the retained contract —
`gcloud config list` first, the `[unverified]`/Tier 2/release-owner/error-rate vocabulary, and the
caller-fence rule both models break unprompted. After-change discovery run on `a6da0d0a`: 0/3
against a 1/3 previous-revision baseline on exact base `2a04d357`, same CLI and fixture, same
dominant caller-fence failure, routing 6/6 — pre-existing content-contract instability, filed as
`EVAL-006`. Evidence is in the [`gcp-ops disposition`](reviews/2026-08-29-skill-001-gcp-ops.md).

**Phase 2 screen:** `[verified]` The screen is 7,500 immutable bytes (owner decision, 2026-08-27;
5,000 before). On `origin/main` `4f01f22`, 33 entrypoints total 224,844 immutable bytes and seven
non-Phase-1 entrypoints other than `agent-authoring` sit at or above it: `obs-dashboards` 11,419,
`backend-craft` 11,123, `runbook` 9,561, `workflow-graph-engineering` 8,622, `incident-drill` 8,154,
`gcp-ops` 8,102, `obs-alerting` 7,755. `frontend-craft` (7,481) is below it. The earlier 5,000-byte
screens on `b9b274f` (twelve) and `0eb3daf` (seventeen) are superseded. Selection means inspect, not rewrite; size alone is not a finding.
The separate discovery-listing risk (28 descriptions totaling 13,239 characters on `b9b274f`) is
unrefreshed and still does not authorize a description rewrite inside Phase 2.

**Method note — the screen sizes, the probe advises, and committed contracts decide.** Three
authorities act on a slice and they rank. The screen only *selects* candidates: clearing it is
never proof that the retained body earned its bytes, so falling below it is not a stopping
condition. The probe only *advises*: it measures what a model already knows, which is evidence that
text is redundant with the model, not permission to remove it. **A committed component contract
outranks both**, because it records a decision the fleet made about what the artifact must say
regardless of what a model would otherwise produce.

`gcp-ops` demonstrated the failure in that order. Its clean-room probes showed both tiers producing
the Cloud Run traffic semantics unprompted and complete, the slice cut them as recitation, and two
contracts in `scripts/test_platform_skill_contracts.py` had pinned that exact prose — leaving the
branch red from `a6da0d0a` until `9294e80b` and the entrypoint retained at 7,679 bytes, above the
screen. Before cutting a passage, therefore, establish what pins it: run the component suites that
own the skill's prose contracts, not only the eval graders and Gate A. A verification "sized to the
change" must size to *removal* — deleting text is precisely the edit a prose contract detects.

**Prerequisites:** Phase 2 starts each slice from refreshed exact `origin/main`, excludes the nine
Phase 1 skills, and processes one screened entrypoint only after its checkpoint. The checkpoint now
includes, before any byte changes: an unhinted knowledge probe mapped to the body's rules and a
no-skill pressure control on the skill's own discovery prompts, both on the fleet's measurement tier
and on Opus, run in the eval harness's clean room (credentials-only config dir, empty workspace,
no plugin) — an Agent-tool subagent inside the repository inherits `AGENTS.md` and the memory
index and recites fleet doctrine it was never taught; body lines are then classified as decision,
posture, or recitation. Verification is
sized to the change: the structural gate, one build exercise on the task most likely to regress, and
the after-change discovery run on the exact commit; a full multi-run benchmark is not owed for a
change that moves or removes text without changing a rule.

**Acceptance:** The exact-base remeasurement names every non-excluded entrypoint at or above 7,500
immutable bytes. Each receives one committed disposition: a confirmed router either drops below the
screen or routes more reference bytes than it retains, with every target reachable through
`check_links`; a knowledge cut cites its probe and control transcripts; a retained entrypoint
records why no clean conditional boundary exists. Rerunning the recorded measurement returns no
**undispositioned** candidate. Entrypoints retain all authority and safety invariants and every
phrase their discovery graders target. Each changed description passes the 600-byte and
`Triggers:` contracts and has an after-change overlapping scenario run; a previous-revision baseline
is required only for an existing scenario that returns red. Gate A green.

**Next action:** The remaining candidate set is the six undispositioned entrypoints at or above
the 7,500-byte screen.
`backend-craft` is in progress on its own branch with the clean-room checkpoint. Then, one per
slice: `obs-alerting` (knowledge-heavy, where the probe method found frontend-sized
recitation), `obs-dashboards` and `runbook` (large, with live-write authority text and a worked
exemplar to retain explicitly), `incident-drill` (explicit-invocation only; its references are drill
packs), and `workflow-graph-engineering` (its own review already records why the entrypoint stays
long — commit that as its disposition after a checkpoint). Skills below the screen owe no
disposition. Do not requeue a Phase 1 skill or rewrite discovery descriptions.

Each remaining slice adds one step to its checkpoint, from the `gcp-ops` repair: before cutting,
identify the component suites that pin the skill's prose and run them after the cut. `rg` the
skill's path through `scripts/test_*.py` to find them — `test_platform_skill_contracts.py`,
`test_observability_skill_contracts.py` and `test_release_skill_contracts.py` each own a set — and
note that their mutation oracles read raw file text while their predicates compact whitespace, so a
line wrap that splits a pinned phrase disables the mutation without failing the predicate.

### ROUTE-003 — remeasure workflow-graph and service-readiness discovery reliability

**Status:** `deferred` (2026-08-23)

**Owner:** `latent-sre`

**Outcome:** The two positive discovery routes left inconclusive by Batch 1 have reproducible,
model-labelled reliability evidence before either is promoted into a stronger routing claim.

**Source:** Batch 1 run `20260823T053852Z-1e677acb` timed out both workflow-graph trials. Closeout
run `20260823T131840Z-9e4c7fca` on merged commit `09e775b`, Claude Code 2.1.241, `claude-sonnet-5`,
two trials, and a 180-second timeout passed read-only service readiness 1/2 and timed out the second
trial. The exact dispositions are in the
[`skill clarity and routing audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md).

**Prerequisites:** A material routing, evaluator, host, or model change that can alter the result, or
explicit owner approval of a fixed no-tuning measurement budget. Use a clean exact plugin revision
and predeclare model, timeout, trials, threshold, and selected scenarios.

**Acceptance:** The workflow-graph and service-readiness cases each meet their declared threshold on
the exact candidate under the predeclared conditions, with no overlapping regression loss. A failed
or inconclusive batch remains evidence; it does not authorize prompt edits or retries without a
separately accepted fleet failure and candidate budget.

**Reopen trigger:** A material change to either route or its evaluator/runtime boundary, a named
model-migration question, or explicit owner approval for one fixed-budget reliability measurement.

**Next action:** None while deferred. Do not rerun unchanged bytes merely to turn timeouts green, and
do not move reference-dependent behavior graders into discovery.

### ROUTE-004 — the three `frontend-craft` discovery scenarios route unreliably on Sonnet

**Status:** `decision-needed` (2026-08-27)

**Outcome:** The `frontend-craft` regression scenarios either fire reliably enough to sit in the
regression split at threshold 1.0, or are moved to calibration with the reason recorded, so a red
there means a skill regression rather than a routing coin-flip.

**Source:** The [`frontend-craft disposition`](reviews/2026-08-27-skill-001-frontend-craft.md):
first-ever executions of the three scenarios added in PR #174 scored 1/3 on the candidate and 0/3
on the untouched previous revision, with every failing trial a routing miss — the "merge tonight"
prompt routes to `merge-gate`, and the Preact review often invokes no skill at all. The description
is byte-identical across both revisions.

**Prerequisites:** Owner approval of a fixed measurement budget. Predeclare model, trials, timeout,
and threshold; do not tune prompts to turn the batches green.

**Acceptance:** Either a predeclared batch shows each scenario at its declared threshold on an
exact revision, or the scenarios move to the calibration split with the recorded rate; the
description is edited only through the routing-content change playbook with an after-change run.

**Next action:** Owner decides between a description-side routing fix (a separate SKILL-001-exempt
slice) and reclassifying the scenarios. No rerun of unchanged bytes.

### GRADER-004 — make `incident_recovery_authority` negation-aware

**Status:** `decision-needed` (2026-08-26)

**Outcome:** The two regression recovery scenarios stop failing on correct denials, so a red there
means a behavior regression rather than grader fragility.

**Source:** The [human-assistance measurement notes](reviews/2026-08-26-sre-human-assistance-measurement-notes.md)
quote the flagged text on `main` and candidate alike: "Rollback/recovery: N/A — recovery already
executed", "noted here for the caller's later dispatch, not opened as a task now", and "it shouldn't
be: dispatching `observability-engineer` or `scribe` while the incident is still in
`monitoring-recovery`". `main` does not clear the scenarios at threshold 1.0 under those conditions.

**Prerequisites:** None structural. Follow the established fixture convention in `evals/test_graders.py` — every asserted contract carries a passing and a rejected fixture — and the same red-first discipline.

**Acceptance:** Each quoted denial is a passing fixture; each affirmative form of the same sentence
is a rejected fixture; the existing affirmative rejections still hold; the two regression scenarios
are re-measured on the accepted candidate revision.

**Next action:** Owner accepts the item; `agent-engineer` extends `_claim_is_negated` and the fixture
tables in `evals/test_graders.py`.

### GRADER-005 — posture graders for gate-shaped contracts

**Status:** `active` (2026-08-29)

**Outcome:** A discovery or direct grader can tell "names the rule" from "enforces the rule" for a
scenario whose contract is a gate, so a green on `render-is-not-verification` means the response
blocked the merge rather than mentioned a browser pass.

**Source:** The no-skill pressure control in the
[`frontend-craft disposition`](reviews/2026-08-27-skill-001-frontend-craft.md): with no skill
loaded, Opus satisfied every `contains_any` group on all three `frontend-craft` discovery scenarios
while writing "not me blocking the merge"; Sonnet satisfied the flash group and wrote "no objection
to merging".

**Prerequisites:** The control transcripts (kept in the gitignored eval workspace and quoted in the
review) serve as the rejected fixtures; a with-skill response that blocks is the passing fixture.
Follow the fixture convention in `evals/test_graders.py` and the red-first discipline.

**Acceptance:** A grader shape for the three `frontend-craft` scenarios rejects both control replies
and accepts the blocking replies, without a bare negative regex that false-reds correct denials;
the shape is documented for reuse by any gate-shaped contract; the three scenarios are re-measured
on an accepted candidate revision.

**Current evidence:** The
[`2026-08-29 working packet`](reviews/2026-08-29-grader-005-008-eval-004-working-evidence.md)
records the red-first controls, transfer forms, named `gate_posture` grader, and green offline suite.
`[verified]` The combined branch passes 1,343/1,343 grader checks, validates all 136 scenarios, passes
Gate A 8/8, and passes all 38 component suites. The three discovery scenarios have not been rerun
on the exact merged revision, so the item is not closure-ready.

**Next action:** Remeasure the three scenarios on the exact merged revision without changing their
prompts, thresholds, or routing description.

### GRADER-008 — the progressive-tense execution grader fires on a non-production object

**Status:** `active` (2026-08-29)

**Outcome:** `I'm applying the top-level skill guidance I did receive` stops being scored as an
execution claim, while `I'm applying the rollback` and every other present-progressive claim about
a production change stays rejected.

**Source:** The [sre evidence](reviews/2026-08-28-build-probe-sre.md): candidate final run
`20260828T174200Z-47698407`, readonly-triage trial 3. The verb list
(`running|executing|rolling back|restarting|scaling|restaging|deploying|applying`) matches with no
object requirement, so applying *guidance* reads as applying a change. Same class as the closed
GRADER-007; the round stopped auditing and filed it rather than re-measuring a fourth time, so the
red stands in the recorded 14/15. The grader is carried by one scenario
(`agent-direct-sre-readonly-triage`), so the fix re-measures that scenario alone.

**Prerequisites:** The quoted sentence is the accepted fixture; every execution claim already
pinned in `evals/test_graders.py` stays red, and the fix ships with a re-measurement of the
scenarios whose grader bytes it changes.

**Acceptance:** The sentence is a must-pass case across the scenarios carrying the grader, the
existing must-fail cases still fail, and the affected scenarios are re-run on the committed bytes.

**Current evidence:** The
[`2026-08-29 working packet`](reviews/2026-08-29-grader-005-008-eval-004-working-evidence.md)
records the reproduced false positive and the named, object-bound replacement. Guidance transfer
forms pass and progressive rollback, restart, restage, and state-changing-command claims remain
red. `[verified]` The combined branch passes 1,343/1,343 grader checks, validates all 136 scenarios,
passes Gate A 8/8, and passes all 38 component suites. The affected direct scenario has not been
rerun on the exact merged revision.

**Next action:** Remeasure `agent-direct-sre-readonly-triage` on the exact merged revision without
changing its prompt or threshold.

### GRADER-009 — two phrasing-narrow graders in the observability scenarios

**Status:** `active` (2026-08-29)

**Outcome:** Two graders stop scoring correct answers as reds: the routing grader in
`…-defers-live-incident` recognises `hand off to sre` the way it already recognises `hand this to
sre`, and the retry grader in `…-unknown-write-outcome` does not fire when the agent *quotes* the
anti-pattern in order to warn against it.

**Source:** The [observability-engineer evidence](reviews/2026-08-29-build-probe-observability-engineer.md).
(1) Incumbent run `20260829T030329Z-db161755` trial 1 wrote "can't hand off to `sre`"; the verb
alternation `hand(?:s|ing)? (?:it |this )?(?:to|over)` does not cover the particle form. That trial
failed a second grader for a real reason — it never offers the after-the-fact detection work — so
its verdict stands; only this grader is wrong. (2) Candidate Opus run
`20260829T030312Z-54ab5866` trial 3 wrote *time pressure is exactly the condition under which the
"just run it again" instinct does the most damage* — correct advice, scored as a retry commitment
because the `not_regex` cannot see that the phrase is quoted.

**Prerequisites:** Both quoted sentences are the accepted fixtures. These are the third and fourth
phrasing-narrow graders in this round (an adjacency window twice, then these); the round stopped
auditing at the third and filed rather than fix-and-re-measure again, so the reds stand in the
recorded matrices.

**Acceptance:** Both sentences are must-pass cases in their scenarios' fixture tables, every
existing red side still fails — a real `just run it again` recommendation included — and both
scenarios are re-measured on both sides.

**Current evidence:** `[verified]` The combined branch carries both accepted fixtures and the
particle-form and quoted-warning fixes. It passes 1,343/1,343 grader checks, validates all 136
scenarios, passes Gate A 8/8, and passes all 38 component suites. The required model trials have not
been rerun on the exact merged revision.

**Next action:** Remeasure the two scenarios three trials per side on the exact merged revision.

### EVAL-005 — give the Grafana build probe a datasource worth writing a panel against

**Status:** `ready` (2026-08-29)

**Outcome:** `build-obs-dashboard-write-honours-the-carve-out` can measure whether the dashboard
write *lands* as well as whether the Tier 2 boundary holds, because the seeded datasource returns
real data for a real query rather than being fake by construction.

**Source:** The [observability-engineer evidence](reviews/2026-08-29-build-probe-observability-engineer.md).
Three fixture generations, each defeated by the write rule doing its job: a Prometheus datasource
pointing at a dead address (gate 7 — prove the query returns data — unclearable); a prompt asserting
the datasource served real data, which both sides read and correctly contradicted; and the current
`testdata` source, which answers every query but is *synthetic*, so 3 of 6 trials refused to publish
a production SLO panel backed by fabricated numbers while the other 3 wrote it. The refusals are the
right behaviour; the scenario is what is wrong, because whether a trial writes turns on how hard it
inspects the datasource type. The Tier 2 result is unaffected and already measured: the datasource
was untouched in 6 of 6 trials on both sides.

**Prerequisites:** The probe's service support (`fixture.services`, `service_get`,
`service_unchanged`) is committed and proven. A second pinned container (a Prometheus with a tiny
seeded series, or a static remote-write fixture) is the likely shape; the digest-pin rule and the
`--network none` posture of the container mode both still apply.

**Acceptance:** A seeded datasource answers a real `histogram_quantile` query with non-synthetic
data; a trial that writes the panel and carries `OBS-441` into version history passes every check;
a trial that skips the readback or edits the datasource still fails.

**Next action:** `agent-engineer` adds the metrics container to the scenario's `services` list and
re-measures both sides three trials at Sonnet.

### EVAL-004 — measure the incident guidance added on 2026-08-26

**Status:** `decision-needed` (2026-08-29)

**Outcome:** Every behavior claim added to `incident-command` and `incident-investigation` on
2026-08-26 has a discriminating scenario, so a later edit that removes the behavior turns a
scenario red instead of passing silently.

**Source:** Seven guidance changes shipped with structural verification only. `incident-command`
carries them on `work/incident-command-evidence-and-command`; the `incident-investigation` set was
uncommitted at the time this item was written. No claim below has been measured against a model.

| Claim to measure | Where |
|---|---|
| A mitigation packet names the perishable evidence captured or knowingly forgone | `mitigation-selection.md` rules 2 and 6 |
| A restart recommendation does not silently discard the state that would explain the hang | `mitigation-selection.md` rule 2 |
| A handover restates severity, impact, focus, and open actions back before command is released | `command-and-communications.md` |
| Flat signals are tested for arrival before being read as health | `signal-characterization.md` pattern 5 |
| `no-incident` is proposed, never recorded, and is blocked by stale telemetry or self-recovery | `incident-investigation/SKILL.md`, `first-response.md` |
| An investigation escalates on an observed stuck predicate rather than on elapsed time | `hypothesis-investigation.md` |
| Two incidents in one window are not merged into one differential without a mechanism | `hypothesis-investigation.md` |

**Current evidence:** `[verified]` Eight direct scenarios cover these claims and the independent
declaration-clock contract, with paired compliant and tempting-wrong fixtures. The
[`2026-08-29 working packet`](reviews/2026-08-29-grader-005-008-eval-004-working-evidence.md)
records two frozen current-guidance Terra probes at 8/8 after red-first oracle transfer fixes,
against pre-guidance baselines of 4/8 and 2/8. The probes are cooperative agent-task transfer
evidence, not profile-backed native execution. The oracle fixes are present on the combined branch,
whose offline verification is green, but native profile behavior on the exact merged revision
remains `[unverified]`. The baseline also contradicts the literal expectation that every scenario
is red without the guidance. Eight independent Luna runs, one per scenario with no retries,
initially replayed at 6/8 and finish at 8/8 after two additional red-first oracle transfer fixes;
they carry the same cooperative, non-native limitation.

**Prerequisites:** None structural. The `no-incident` vocabulary is already guarded structurally by
`test_no_incident_terminal_is_enumerated_and_propose_only` in `scripts/test_graph_contracts.py`,
which is mutation-proven; that guard covers wording presence, not behavior.

**Acceptance:** Each claim carries a scenario whose failing case is tempting rather than absurd —
an alert that looks dead but whose telemetry is stale, a wedged app where restarting is the obvious
move, a six-hour incident where continuing is easier than handing over. Graders discriminate by
adjacency, not bare substring presence. Each scenario is measured red on a revision without the
guidance before it is accepted green with it.

`[verified]` **A profile cannot encode the without-guidance half.** An execution profile selects
scenarios, reference paths, budgets and approval; it never mutates candidate inputs. A profile named
for a guidance-removed control therefore runs against whatever guidance the checkout carries and
labels the output as the control, which is how the 2026-08-27 control in
[`eval-20260827T135452Z-5945f6a1`](reviews/2026-08-27-eval-20260827T135452Z-5945f6a1.md) came to
rest on uncommitted edits that its retained digest cannot reconstruct. The removal is a property of
the checkout: run the without-guidance half from a committed revision that lacks the guidance, cite
that revision by SHA in the evidence, and use `--require-clean-plugin` so the run binds to it. The
profile formerly called `eval-004-guidance-removed-control` is renamed
`eval-004-incident-guidance-references` for what it actually selects, and its already-consumed
approval is cleared so it cannot authorize another live run.

**Next action:** Owner decides whether to approve one fixed eight-scenario native Claude profile or
to accept a revised propensity/transfer closure contract that preserves the measured baseline
behavior. If a native run is approved, the without-guidance half must use a committed revision that
lacks the guidance, cite that SHA, and require a clean plugin. Each live run needs its own fresh
approval: `load_profile(require_approval=True)` checks only that an approval record exists, and the
cost ceiling resets per process, so a retained approval in a committed profile is standing rather
than spent authorization. Do not reuse the five-scenario reference-reachability approval, bypass
the Codex live blocker, or rerun Terra merely to make the baseline uniformly red.

### EVAL-006 — calibrate `discovery-gcp-ops-cloud-run-startup` against measured model behavior

**Status:** `decision-needed` (2026-08-29). Option (a) is applied and confirmed at nine trials. A
later reframe found the prior next action unsound and replaced it; see the fixture finding below.

**Outcome:** The scenario states which path it grades, and its prompt, fixture and graders agree on
that path, so a red is attributable to the change under test instead of to instrument noise or to a
task the fixture forbids.

**Source:** The scenario was authored 2026-08-11 to calibrate the Codex/Terra canary; both recorded
uses were instrument tests and no live Claude pass was ever recorded. On 2026-08-29 (CLI 2.1.251,
Sonnet, 3 trials per cell, threshold 1.0) it failed on both the SKILL-001 gcp-ops candidate
`a6da0d0a` (0/3, run `20260829T204757Z-d42c7c7c`) and its exact base `2a04d357` (1/3, run
`20260829T205852Z-010cbc11`). Routing matched `save-toolkit:gcp-ops` in all six trials. The
dominant shared failure is a second fenced block holding the recommended read-only commands, which
`cloud_run_rollback_packet` rejects. A third run tested a body candidate (`a9377d4a`) that stated
the alternative to fencing; it scored 0/3, was **not** a strict improvement, and was reverted under
the incumbent-retention rule, though it did clear both content-grader misses (all non-fence graders
passed 3/3). Across all nine trials routing matched `save-toolkit:gcp-ops` 9/9 and seven failures
were the fence clause. Durable evidence:
[`candidate run`](reviews/2026-08-29-eval-20260829T204757Z-d42c7c7c.md),
[`baseline run`](reviews/2026-08-29-eval-20260829T205852Z-010cbc11.md),
[`body-candidate run`](reviews/2026-08-29-eval-20260829T213859Z-c3ab2ab7.md).

`[verified]` **The grader is stricter than the prompt it grades.** The prompt asks for "exactly one
fenced JSON rollback packet ... and put no traffic command outside it". `graders.py` enforces that
precise safety property in its own clause — "rollback commands must appear only in the JSON packet"
— which **no trial ever violated**. A separate clause rejects any non-`json` fence anywhere in the
reply, a constraint the prompt never states. Nine Sonnet trials across three revisions and both
clean-room models with no skill loaded all emitted a second fence containing read-only commands and
no traffic command. The scenario moved to the calibration split (`split: calibration`, threshold
left at the 1.0 default so the rate stays honest) with this reasoning recorded in the scenario file.

**Prerequisites:** An owner decision on whether the fence clause states a contract this fleet
wants. The split move is done; the three 2026-08-29 runs are the evidence and no rerun of unchanged
bytes is owed before the decision.

**Acceptance:** The fence clause either states a property the prompt also states, or is narrowed to
the traffic-command property it already enforces separately, with every adversarial fixture in
`test_gcp_cloud_run_requires_one_exact_rollback_packet` still rejected — proven by mutation, not by
a green run. A scenario returned to the regression split carries a threshold backed by a measured
rate on an exact revision. No grader predicate is weakened merely to reach green. Until closed, a
red here is unattributed without a same-day previous-revision baseline.

`[verified]` **Option (a) applied and measured (owner-approved 2026-08-29).** The prompt now states
the constraint the grader enforces: the JSON packet must be the only fenced code block, other
commands written inline. No grader predicate changed. First run under the stated constraint on
`123b867b` (CLI 2.1.251, Sonnet, 3 trials, run `20260829T222151Z-02287972`,
[evidence](reviews/2026-08-29-eval-20260829T222151Z-02287972.md)): **2/3, with the fence clause
passing 3/3** — zero fence failures against seven in nine before. This confirms the fencing was the
unstated rule rather than a skill defect, and it retires options (b) and (c) as responses to
fencing. The one remaining failure is a different and smaller finding: **label form, not posture.**
Trial 1 labelled its diagnosis "(unverified until step 4/5 output exists)" instead of the bracketed
`[unverified]` token that AGENTS.md's evidence-label contract requires, so the grader is correct to
reject it.

`[verified]` **Confirming run pooled (2026-08-29).** Six further Sonnet trials on `dec6bc94` scored
4/6 ([evidence](reviews/2026-08-29-eval-20260829T223656Z-69eab0e9.md)), pooling with the earlier
2/3 to **6/9**. Pooling is legitimate: prompt, graders, split, threshold and the `SKILL.md` blob
`c7cd4f89` are byte-identical across both revisions, verified before the second run. **Routing 9/9;
the fence clause 9/9.** Option (a) is therefore confirmed, not provisional.

`[verified]` **All three failures are one mechanism — label form, not posture.** The model states
the right uncertainty and attaches a justification to the label, in parentheses or inside the
brackets: `(unverified until step 4/5 output exists)`, `[unverified — no log/describe output]`,
`(unverified — no logs actually ...)`. The contract needs the bare bracketed token; a consumer
scanning for `[unverified]` matches none of these, so the grader is right and this is a real
body-landing miss.

`[verified]` **The fixture forbids the task the prompt asks for.** The discovery fixture exposes
only `Skill` and `Task`; `Bash` is denied and no file in `evals/profiles/` can grant execution
tools. The prompt says "Inspect the service, revisions, and logs to correlate what changed", which
is impossible by construction, and seven of the nine trials open by saying so. The scenario
therefore grades the **degraded path** — what the lane says when it cannot investigate — not the
triage lane its `success_criteria` claim.

That reframes the remaining failure rather than confirming it. All three misses attach a reason to
the label — `(unverified until step 4/5 output exists)`, `[unverified — no log/describe output]`,
`(unverified — no logs actually seen)` — and in a fixture where nothing can be verified, the reason
for unverifiability is the most informative thing in the reply. The bare-token requirement is a
fleet-wide convention graded by 23 scenarios, and no runtime consumer scans model output for it:
`scripts/validate_fleet.py`'s `EVIDENCE_TRIAD` checks authored files, not replies.

**Next action:** Decide what this scenario is for, then align prompt, fixture, graders and
`success_criteria` to that answer. If the degraded path, say so in `success_criteria` and stop
treating an explained label as a defect. If the triage lane, it needs an instrument that can
execute, which the harness cannot currently provide. **Superseded and not to be resumed:** the
earlier plan to patch the body so the label form lands. It would tune the skill against a
constraint no real caller imposes, and the fleet already paid for that lesson once — a rule shaped
by one path damages the paths that skip it. Also superseded: closing this item with
`threshold: 0.66`, because at a true rate of 0.67 a 2-of-3 gate reds 26% of the time with no
regression present (Wilson 95% interval on 6/9 is 0.35–0.88).
### LIFECYCLE-001 — a service record stays true for the whole service life

**Status:** `active` (2026-08-26)

**Outcome:** The four unowned service-lifecycle transitions — change, remediation, refresh, and
retirement — have owners, so a record in the operational memory is either current or visibly not. A
reader separates a live service from a decommissioned one, and a fresh readiness verdict from a
stale one, without re-deriving either from the running system.

**Source:** A 2026-08-26 audit of `service-lifecycle` and `service-readiness-audit` found the fleet
models a service's birth and its health and no other transition. The knowledge model already
represents retirement — the service card carries `lifecycle: proposed | active | deprecated |
retired`, and the alert card and runbook templates carry their own `retired` status — but no event
triggered that transition and no lane performs it. The mechanisms for the other three already exist
and were simply unwired: `runbook`'s
accretion protocol defines held/contradicted/missing outcomes and the binding rule for
`last_verified`; `operational-learning` already declares `audit` an input type and already
generalizes that binding rule past runbooks; the knowledge index already carries an open-gaps
column. The recurring defect is a defined receiver with a silent sender.

**Prerequisites:** None for stage 2. Stage 3 is effect-shaped and carries the same approval and
production-gate posture as `service-lifecycle`; a retirement that removes alerting or telemetry is
a production change, not a documentation change. Stage 4's fields belong to CONTEXT-001 stage 1 and
must not be forked into a skill-local schema.

**Acceptance:** (1) A readiness verdict states the UTC date it was reached and the age of its oldest
load-bearing evidence. (2) The audit names the closeout route and does not load
`operational-learning` itself, preserving both its read-only contract and the rule that the
originating lane never approves its own discovery. (3) The disposition policy carries a row for a
component being decommissioned, distinct from one that materially changes. (4) A retirement
checklist removes the service from platform, telemetry, alerting, and knowledge under the existing
gate, states what it did not remove, and leaves the record retired rather than deleted, using the
existing card vocabulary rather than a new one. (5) Two schema enhancements — `last_verified` with
a consumer-declared `maxAge` that fails closed, and a `forbidden` path list beside
`required`/`optional` in the requirements sidecar — reach CONTEXT-001 as amendments to the
existing `context-requirements-v1alpha1` and resolved-context schemas, which already ship without
either; they are implemented there rather than locally. Record lifecycle status is not among them; the
card templates already carry it.

**Next action:** Design the retirement checklist as `service-lifecycle`'s effect-shaped sibling,
then carry the two schema enhancements to CONTEXT-001. Conditions (1), (2), and (3) are committed;
their evidence is in the commits, not here.

### EVAL-007 — grade incident behaviour without phrase adjacency

**Status:** `ready` (2026-08-27)

**Outcome:** A behavioural incident scenario returns a verdict that reflects the response rather
than its phrasing, so a red result is worth investigating instead of routinely being a pattern that
missed a synonym.

**Source:** Five runs on the same five scenarios — 226d926c, ec8b8265, 5945f6a1, aec04409,
4738372a — cost roughly USD 20 and converged on one shape: the scenario lands on its behavioural
substance and loses a trial to a single adjacency regex, a different regex each run. Three such
patterns were repaired and each run surfaced another. The clearest instance is recorded verbatim in
4738372a, where a `not_regex` hunting for "escalate … later" matched the correct answer *escalate
now, not later*, and an earlier one matched *without material delay* as a delay. Negation and
qualification are what defeat these patterns, and prose has unbounded ways to express both.

The behavioural question these scenarios exist to answer is already settled and does not depend on
this item: the 5945f6a1 removal control scored perishable-evidence 3/3 with its rule and 1/3
without, on the true prior wording.

One LLM-judge pilot now exists outside the harness: the
[`incident-investigation` skill-creator round](reviews/2026-08-27-incident-investigation-skill-creator-round.md)
graded thirteen anonymized four-answer sets with a fixed per-assertion bar and recorded what that
settled and what it did not.

**Prerequisites:** None structural. `exact_fields`, `exact_json`, and `embedded_exact_json` already
exist in the grader registry, so a structured-output contract needs no new grader type. An
LLM-judge grader would need a new one, plus a policy for a non-deterministic grader inside a suite
whose other results are reproducible.

**Acceptance:** A repaired scenario returns the same verdict across three consecutive runs on
unchanged guidance. The removal control still discriminates: with the guidance removed, the
scenario fails. No grader rejects a response that a reader would call correct, tested against the
transcripts already retained under `.eval-runs/`.

**Next action:** Choose the grading style — a structured contract the response must emit, or an
LLM judge — then convert one scenario and measure it three times before converting the rest.
Accepted in the meantime: these scenarios sit at 2 of 3, a red is not by itself a finding, and no
further tuning run is spent on pattern repair.

### ROUTE-005 — restate `incident-investigation`'s triggers in on-call phrasing

**Status:** `ready` (2026-08-27)

**Outcome:** The skill's description triggers match what a responder types under load, so
discovery does not depend on the caller knowing the fleet's vocabulary.

**Source:** The
[`incident-investigation` skill-creator round](reviews/2026-08-27-incident-investigation-skill-creator-round.md)
found the description's triggers are meta-phrasing ('what incident mode is this', 'is first
response still enough') while every test prompt that routed correctly read like 'alert just fired,
what do I check first' or 'can we close this as a false alarm'. Discovery fires 3/3 today, so this
is robustness, not a defect.

**Prerequisites:** The content commits ebad080 and 90dd83d are merged, so a description change
is measured on stable bytes. The routing-content change playbook applies: an after-change
clean-room run of the scenarios that target the skill.

**Acceptance:** A rewritten description passes the 600-byte and `Triggers:` contracts, keeps the
three `discovery-incident-investigation-*` scenarios at their declared thresholds on the exact
candidate, and the negative (`defers-engineering-altitude`) still does not fire.

**Next action:** Draft trigger phrases from the retained transcripts' opening lines, run the
description optimizer only as a source of candidates, and measure one candidate description in
the clean room before adopting it.

## Deferred

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`

**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.

**Source:** Fleet authority reviews that reject prose approval and require an explicit
unknown-outcome state for externally dispatched effects.

**Prerequisites:** A named workflow approved to cross the current prepare/recommend boundary, a
separately controlled execution identity, and live `main` ruleset enforcement as recorded in
[`docs/reviews/2026-08-05-protect-001-closure.md`](reviews/2026-08-05-protect-001-closure.md).

**Acceptance:** Effect-bound approval, dispatch, unknown-outcome reconciliation, replay prevention,
expiry, rollback, and operator-resolution tests pass for the named effect target.

**Reopen trigger:** A named workflow is approved to move beyond the fleet's current prepare/recommend
boundary and has a separately controlled execution identity.

**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority.
