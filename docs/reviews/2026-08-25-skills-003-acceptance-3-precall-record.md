# SKILLS-003 acceptance 3 — frozen pre-call record

**Status:** frozen 2026-08-25 at `9abdf08`; launch decision completed and the exercise run. The model, agent type, and budget rows were filled in at launch, before any call; everything else is unchanged from the freeze commit. `SKILLS-003` acceptance 3 requires every field below to be
recorded *before the first call*, and states that changing a case, grader, threshold, or candidate
creates a new candidate requiring owner approval rather than silently extending this pass. This
document is that freeze. It is committed before the exercise so the record cannot be edited to fit
the outcome.

## Candidate identity

| Field | Value |
|---|---|
| Skill revision under test | `f1afd574e474dde882ca97947f92e9680e416cab` |
| Branch HEAD at freeze | `12cdf3e657c6acc3b918e53a5fe176c720eab195` |
| Working tree | clean `[verified]` |
| Skill input digest | `sha256:f32367b1484dc0823e8bbe50cab23680a8dd27157dcb5ee5211ed459a2b28ba2` (8 files under `skills/workflow-graph-engineering/`) |
| Canonical plugin digest | `sha256:3acad29f02bf71897f0d70d9ec04e3a6f7bef8b832ba2e9ba1650dcac64510a0` (182 files under `agents/`, `skills/`, `commands/`) |
| Skill bytes vs `f1afd57` | `[verified]` identical — this branch changed only `evals/` and `docs/` |

## Environment

| Field | Value |
|---|---|
| Host | Windows 11 Pro `10.0.26200` |
| Claude Code CLI | `2.1.245` |
| Runtime | Claude Code subagents in this session, one fresh context per call |
| Model | `claude-opus-5`, pinned at launch on 2026-08-25. The 2026-08-24 development pass ran on `claude-fable-5`, so **its 47/47 is a different baseline and is never averaged with this one** |
| Agent type | `claude` (the neutral catch-all). See the tool-permission deviation below |
| Effective tool permissions | **Deviation from the intent stated at freeze, recorded before the run.** The freeze called for read-only generation agents. No available agent type combines a read-only tool set with a system prompt suited to design generation — the read-only types are investigation- and search-shaped and would distort the task. `claude` is therefore used, which carries the full tool set even though the task needs nothing beyond reading. The guarantee is preserved by verification instead of by capability: the working tree is `[verified]` clean at launch and is checked again after the pass, and any repository change or executed command invalidates the result |
| Per-call timeout | 1800 s (the development pass observed 602–1021 s per case; this leaves headroom without being unbounded) |
| Maximum budget | 10 calls — 5 generation, 5 grading — and a hard ceiling of **USD 40**, set at launch because the tier was pinned without one being named. Reaching it ends the pass as `INCONCLUSIVE` rather than continuing; it is not raised mid-run |

## The five immutable prompts

Each is issued to one fresh-context agent, exactly one trial, with the path
`skills/workflow-graph-engineering/SKILL.md` supplied. No prompt is edited after this commit.

**Case 1 — deterministic admission.** *Design the executable workflow graph for a batch
reconciliation service that accepts work from many tenants. Be precise about queue ownership and
capacity, priority and fairness between tenants, per-tenant quota, the concurrency cap, what happens
under backpressure and when load is shed, how worker liveness is established and what happens to a
stale worker's in-flight item, and what evidence is required before work is admitted at all. Do not
choose a runtime.*

**Case 2 — model-selected handoff.** *Design the executable workflow graph for a triage pipeline
where a model decides which specialist lane handles each incoming report, and some reports contain
attacker-controlled text. Be precise about the allowed destination set for the model-selected edge
and the deterministic guardrails around it, the authority each lane holds, and how taint travels
across every edge and handoff. Do not choose a runtime.*

**Case 3 — fan-out/fan-in with partial failure.** *Design the executable workflow graph for a job
that fans work out to many parallel workers and merges their results. Be precise about writer
cardinality, the reducer's identity and algebra, ordering guarantees, conflict handling, join
quorum, what happens when some workers fail and others succeed, what happens to a result that
arrives after the join has closed, and the fan-out budget. Do not choose a runtime.*

**Case 4 — approval-gated external effect.** *Design the executable workflow graph for an automation
that, after a human approves in chat, deprovisions a customer's account in a third-party billing
system and records the outcome. A retry once deprovisioned twice, and a crash mid-call left nobody
sure whether the call landed. Be precise about how the idempotency key is constructed, what happens
when a key is reused with a different intent, how long a completed result is remembered, the state
for "we do not know whether it ran" and how the graph resolves it, and exactly what the approval is
bound to. Do not choose a runtime.*

**Case 5 — durable cyclic graph.** *Design the executable workflow graph for a long-running
remediation loop that may run for days, be paused and resumed, and be superseded by a newer request.
Be precise about the difference between resuming from a checkpoint and deterministically replaying
an event history, cooperative versus durable cancellation and where each is safely observed, what
happens to in-flight and late-arriving workers, how supersession works, every budget that bounds the
cycle, what is traced, and how the graph itself is evaluated. Do not choose a runtime.*

## Graders

One fresh-context agent grades each case independently, sees only the case's response and its
predeclared assertions, and returns a per-assertion pass/fail with a one-line reason. Grader agents
never see the generation agent's reasoning and never see each other's verdicts.

Assertions per case: **(A)** the response contains the fourteen ordered sections of the required
artifact shape; **(B)** every concern named in that case's prompt is addressed with a specific
decision rather than a restatement of the question; **(C)** no runtime is selected; **(D)** no claim
of execution, runtime, or production evidence; **(E)** claims carry `[verified]` / `[sourced]` /
`[unverified]` labels; and **(F)** the case's own effect-safety invariants hold where applicable —
for Case 4, that a checkpoint is never offered as exactly-once proof, an `UNKNOWN` outcome is never
replayed automatically, and a reused key with mismatched intent is rejected before dispatch.

**Threshold:** a case passes only if every assertion passes; the exercise passes at 5/5 cases.

**Conjunction risk, stated in advance.** This is a conjunction of roughly six assertions across five
cases — about 30 assertion-cases at one trial each. `GRADER-003` measured exactly this shape failing
for reasons unrelated to the thing under test: at 97% per assertion, a 30-way conjunction passes
only about 40% of the time. A red here is therefore **not** evidence the skill is deficient until
each failing assertion is traced to the response that failed it, the same discipline applied to all
twelve `GRADER-003` reds, none of which turned out to be a real defect. Tracing is part of this
pass, not a follow-up.

## What this exercise does not establish

Runtime behaviour, durability, provider behaviour, effect safety, and production readiness stay
`[unverified]` by construction — nothing is executed. A strong artifact result never upgrades that
lane. This pass measures artifact quality at one revision on one model with one trial per case.
