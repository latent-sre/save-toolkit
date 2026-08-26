# SRE agent review — human incident-assistance model

> **Status: review and cross-machine handoff, not independent implementation authority and not a
> second backlog.** This document records the baseline findings and direction discussed on
> 2026-08-25. On 2026-08-26 the repository owner first approved a dedicated `sre-ladder` name, then the same day renamed the component `incident-investigation` (this review's original suggestion; `sre-ladder` stays retired) and approved its
> extraction on this branch. The review itself grants no tool, delegation, or production authority.

**Reviewed baseline:** `873fdf4c134e9073ea9824e776a88ac3acbe56ca` (`origin/main`, merge of PR
#169)

**Review branch:** `docs/sre-agent-review-20260825`

**Review scope:** the canonical [`sre` agent](../../agents/sre.md), its incident-command and
engineering-ladder dependencies, its current routing and behavioral evaluations, and its fit with
the fleet's Prompt, Context, Loop, and Graph Engineering principles.

## Conclusion

Keep the `sre` agent, its guarded read-only investigation authority, and its incident-analysis core.
Change its operating model from an agent that appears to own an incident end to end into an
**investigation assistant for a human SRE or incident team**.

The agent should still produce the five elements that make it operationally useful:

1. provisional **severity**;
2. quantified **blast radius**;
3. an evidence-labelled UTC **timeline**;
4. testable **hypotheses** with predictions and results; and
5. the fastest safe **mitigation recommendation**, including verification and rollback, for a
   human to decide and execute.

Those fields are not fluff. They are the working incident record and should remain in every
substantive triage response. The problem is the surrounding universal ceremony: every request is
currently pulled toward an engineering/SRE altitude selection, a full recovery-to-terminal loop,
a general handoff contract, and operational-learning dispositions. That makes a bounded request
such as “compare these two log windows while I check the deploy” carry the shape of an entire
incident-management system.

The recommended design is therefore not a wholesale rewrite. It is a boundary correction:

- the human SRE or incident commander owns the incident and production decisions;
- `sre` owns the current bounded investigation task and may maintain a sustained recovery record
  only when the caller assigns that lifecycle;
- incident-specific references deepen the `sre` node only when an observable condition selects
  them;
- post-incident dispositions begin at explicit operational closeout, not during every evidence
  collection turn; and
- the existing safety boundaries remain unchanged.

## User intent captured by this review

The intended role is not a replacement SRE and not an autonomous incident commander. It supports
the person responding to an incident and takes bounded work off that person's critical path while
they continue investigating.

Representative tasks include:

- characterize impact while the human checks the deployment pipeline;
- compare error, latency, traffic, and saturation signals;
- build or update the incident timeline from supplied evidence;
- form a differential of causes and identify the next discriminating check;
- inspect read-only PCF, Cloud Run, repository, log, metric, trace, or alert evidence within the
  granted tool boundary;
- prepare a mitigation option with target, expected effect, verification, and rollback; and
- monitor explicitly named recovery signals for an explicitly named window.

The human retains command, context that was not supplied, credentials, production authorization,
and the decision to act. The agent reduces cognitive load; it does not displace accountability.

## Current-main evidence

### What is already strong

- **[sourced] Routing is incident-shaped.** The frontmatter selects `sre` for production or staging
  alerts, anomalous errors or latency, degraded applications, and unknown-cause investigation. It
  excludes deployment of fixes and points incident process and communications to
  [`incident-command`](../../skills/incident-command/SKILL.md).
- **[sourced] The analysis method is sound.** The current body explicitly requires severity, golden
  signals, blast radius, a UTC timeline, a differential of hypotheses, predictions, evidence tests,
  mitigation, and confidence.
- **[sourced] Production effects remain human-owned.** The agent may observe and recommend, but a
  human release owner or separately approved protected automation performs a live action. Tier 2
  and Tier 3 changes stay recommend-only.
- **[sourced] The incident-command split is fundamentally correct.** The human incident commander
  runs the process, the `sre` lane performs technical investigation, and a human release owner owns
  remediation. See
  [`command-and-communications.md`](../../skills/incident-command/references/command-and-communications.md)
  and
  [`mitigation-selection.md`](../../skills/incident-command/references/mitigation-selection.md).
- **[sourced] The security carve-out is correct.** Suspected compromise or integrity loss exits the
  reliability path, preserves evidence, and goes to the human security incident owner without a
  restart or other state-changing “mitigation.”
- **[sourced] The graph is intentionally narrow.** The only subagent edge is a sanitized public
  question to `researcher`; post-incident code, observability, and documentation work returns to the
  caller for separate dispatch.
- **[sourced] Sustained recovery is protected.** The current direct recovery evaluation prevents a
  single green point from closing an incident and keeps later documentation and observability work
  out of the active response. See
  [`agent-direct-sre-owns-recovery-to-terminal.yaml`](../../evals/scenarios/agent-direct-sre-owns-recovery-to-terminal.yaml).

### Where the current prompt is heavier than the intended role

- **[verified] The canonical `sre` body is 311 lines, 21,507 characters, and 3,069 whitespace-delimited
  words at the reviewed baseline.** It is the second-largest agent definition in the roster.
- **[verified] The unconditional starting path adds 5,989 characters from `eng-ladder` and 2,640
  from `golden-signals`.** The agent body plus those two required loads is 30,136 characters before
  an incident-specific platform or evidence skill is loaded. This is a context-cost observation,
  not a token-count claim; host framing and tokenization are not included.
- **[sourced] The opening instruction says to load `eng-ladder` and select responder,
  investigator, or elite for every incident.** Later, the same file lists `eng-ladder` as an
  on-demand skill used when selecting altitude. The unconditional opening and conditional routing
  model pull in different directions.
- **[sourced] The method now runs from triage through recovery and a named terminal.** That is useful
  for an assigned sustained incident lifecycle, but it is broader than many requests to help with
  one investigation slice.
- **[sourced] Every investigation must return a full course-of-action packet, and every new
  operational fact must receive a learning disposition.** The direct read-only triage evaluation
  reinforces that requirement even though its prompt asks only for triage and mitigation advice.
  See
  [`agent-direct-sre-readonly-triage.yaml`](../../evals/scenarios/agent-direct-sre-readonly-triage.yaml).
- **[sourced] The repository already has the more precise closeout predicate.**
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md) applies disposition policy to an **explicit operational
  closeout** after an incident, drill, audit, or approved service/alert change. That is a better
  boundary than classifying every observation during active investigation.

## Four-theme review

The fleet's decision rule assigns owner selection and output shape to Prompt Engineering, relevant
state to Context Engineering, work and termination to Loop Engineering, and ownership transitions
to Graph Engineering. Skills deepen a node; agent edges change ownership. See
[`roster.md`](../../skills/agent-authoring/references/roster.md).

### 1. Prompt Engineering — select an assistant, preserve the useful record

#### Finding

The description routes the right incidents, but the word “owns” is ambiguous. Inside the fleet it
can mean that `sre` is the selected technical lane. To an operator it can imply that the agent owns
the real incident, severity decision, or response. The body then reinforces the broader impression
by requiring the agent to carry recovery through a terminal state.

#### Recommendation

State the boundary in the description and first body section:

> Assist a human SRE during an active production or staging issue. Handle bounded read-only
> investigation against logs, metrics, traces, events, network, and recent changes; produce
> severity, blast radius, timeline, hypotheses, and mitigation guidance. The human incident owner
> directs the response and a human release owner executes production changes.

This is a design target, not approved replacement text. The final description should retain the
current user-language triggers—“why is X failing,” “investigate this,” “triage this alert,” and
“what changed”—because they are specific and action-shaped.

The default positive output recipe should remain:

```text
Incident summary: symptom · provisional severity · blast radius · start time · trend
Timeline (UTC): observed events and changes, with evidence labels
Hypotheses: candidate → prediction → evidence for/against → current verdict
Mitigation: done by human / recommended · target · verification · rollback
Next investigation step: the smallest check that most reduces uncertainty
Unknowns and non-actions: what is missing and what the agent did not change
```

The full production approval packet should appear only when the response actually recommends a
Tier 2 or Tier 3 action. The machine-readable `incident-state/v1` object should remain only for an
actual `monitoring-recovery` state with a caller-supplied recovery window, as it is today.

### 2. Context Engineering — load incident modes, not an engineering ladder

#### Finding

At the reviewed baseline, [`eng-ladder`](../../skills/eng-ladder/SKILL.md) performed two different
jobs:

1. it selects Builder, Principal, or Distinguished altitude for engineering work; and
2. it selects Responder, Investigator, or Elite altitude for incident work.

The incident references themselves are valuable. Their content is not the problem:

- the former `responder.md`, now
  [`first-response.md`](../../skills/incident-investigation/references/first-response.md), preserves the first-ten-minute
  checks, read-only posture, runbook use, time-box, and early escalation;
- the former `investigator.md`, now
  [`hypothesis-investigation.md`](../../skills/incident-investigation/references/hypothesis-investigation.md), preserves timeline
  correlation, differential hypotheses, predictions, evidence tests, and confidence;
- the former `elite.md`, now
  [`systemic-failure.md`](../../skills/incident-investigation/references/systemic-failure.md), preserves distributed failure modes,
  shared fate, cascades, retry storms, saturation collapse, feedback loops, and metastability; and
- the former `golden-signals.md`, now
  [`signal-characterization.md`](../../skills/incident-investigation/references/signal-characterization.md), preserves a compact
  signal vocabulary and the start-time/blast-radius/trend triple.

The mismatch is classification. Responder, investigator, and systemic-failure analysis are
**incident modes selected by evidence**, not rungs on the software-engineering career ladder.
“Elite” also frames a diagnostic mode as seniority when the trigger is really distributed or
emergent behavior.

#### Recommendation

Keep `eng-ladder` for Builder, Principal, and Distinguished engineering altitude. Move the four
incident references behind a dedicated incident-specific entry point. The approved implementation
names that component [`incident-investigation`](../../skills/incident-investigation/SKILL.md); the important boundary is
that technical incident context no longer depends on the software-engineering ladder.

Use observable routing predicates:

| Current reference | Recommended incident mode | Load when |
|---|---|---|
| `responder` | `first-response` | A new alert or report is untriaged, impact is not bounded, or a runbook may apply |
| `investigator` | `hypothesis-investigation` | The symptom is confirmed and the next task is to distinguish causes with evidence |
| `elite` | `systemic-failure` | Evidence shows multi-service/shared-dependency scope, cascade, feedback loop, saturation collapse, retry storm, or metastability |
| `golden-signals` | `signal-characterization` | Broad service health must be characterized; load directly without first loading an engineering ladder |

Do not preload neighboring modes. Begin with the smallest mode supported by current evidence and
move only when an escalation predicate is observed. A senior human responding first still uses
first-response mode; the label describes the work, not the person's level.

### 3. Loop Engineering — one bounded investigation slice unless lifecycle ownership is assigned

#### Finding

The current recovery loop is strong for a sustained incident: it protects evidence, mitigation,
monitoring, and terminal state. Applied universally, however, it expands every bounded assist into
incident lifecycle management and then into governance closeout.

#### Recommendation

Retain the current core as a loop with two entry modes:

| Entry | Mutable state | Stop or terminal |
|---|---|---|
| **Bounded assist** | Current evidence, timeline facts, hypotheses, next discriminating check, mitigation recommendation | Return after the requested evidence slice is complete, a material human decision is needed, evidence is unavailable, or the guard denies the needed observation |
| **Sustained incident support** | Severity, blast radius, timeline, hypothesis ledger, mitigation result, recovery signals/window | Continue through `monitoring-recovery`; end only with evidence-backed `resolved` or accepted `escalated-security` |

Both entries keep severity, blast radius, timeline, hypotheses, and mitigation. The difference is
termination, not analytical quality.

A good per-turn cycle is:

1. restate the human's requested investigation slice and current incident state;
2. update severity, blast radius, start time, and trend from current evidence;
3. add only new verified or explicitly uncertain timeline facts;
4. rank hypotheses by the predictions they make;
5. perform or request the smallest safe check that separates the leading hypotheses;
6. update the verdict and confidence;
7. recommend the fastest safe mitigation when evidence supports one, with a human owner,
   verification, and rollback; and
8. return the next useful decision or observation without claiming incident command.

Guard denial, missing credentials, absent tools, unavailable evidence, or a required human decision
are explicit stop conditions. They are not success and should not be bypassed. The existing
`monitoring-recovery` JSON contract remains a useful regression surface for the sustained entry.

### 4. Graph Engineering — the human owns the incident; the agent owns a bounded work item

#### Finding

The current software graph is mostly correct: incident work stays in `sre`, skills deepen that
investigation, and only sanitized public research crosses to another agent. Post-terminal code,
observability, and documentation work is dispatched separately by the caller.

The missing distinction is between **fleet-task ownership** and **operational incident ownership**.
The agent can be the selected owner of the technical task without becoming the incident commander,
release owner, security owner, or accountable human SRE.

#### Recommendation

Use the following ownership model:

```text
Human SRE / incident commander
  owns severity acceptance, priorities, coordination, and mitigation decision
        |
        v
sre agent
  owns the current bounded read-only investigation task and evidence packet
        |
        +--> incident/platform/evidence skills (same owner; deeper context)
        |
        +--> researcher (sanitized public question only; result returns to sre)
        |
        v
Caller after terminal resolution
  separately dispatches software-engineer, observability-engineer, or scribe
```

No new production edge is needed. Do not grant `sre` direct invocation of post-incident writers or
builders. That restriction prevents live response from silently starting later work and preserves
the caller's authority to sequence follow-ups.

## Operational-learning closeout

### Finding

“Every durable operational discovery receives a disposition” is a useful repository invariant.
“Every new operational fact receives a disposition during investigation” is too broad. Most live
facts are transient observations, rejected hypotheses, or duplicate signals. Classifying each one
as `prepared`, `proposed`, `blocked`, `duplicate`, or `not_applicable` adds governance work while the
operator is trying to restore service.

The current basic-triage evaluation makes this expansion measurable: it requires a learning
disposition even though the incident is active and no closeout was requested.

### Recommendation

Put disposition work behind this observable predicate:

> Enter operational closeout only after a terminal incident state is recorded, or when the caller
> explicitly asks to close out a resolved incident, drill, audit, or approved service/alert change.

During active response:

- keep possible durable discoveries in the evidence/timeline record;
- do not classify each observation;
- do not dispatch documentation, observability, or code follow-ups; and
- return unresolved candidates to the caller with their evidence and uncertainty.

During operational closeout:

- decide which candidates are actually durable discoveries;
- apply the existing disposition vocabulary and one owner to each durable item;
- preserve evidence labels and non-actions; and
- let the caller dispatch each owning lane after resolution.

This narrows when the invariant runs without weakening it. It also matches the closeout row already
present in `CONTRIBUTING.md`.

## Safety and authority review

The redesign should preserve these controls unchanged:

| Boundary | Current state | Recommendation |
|---|---|---|
| Local write access | `sre` has no Edit or Write tool | Keep |
| Shell | Guarded, allowlisted read-only commands | Keep; a guard denial remains a finding, never a workaround request |
| Direct web | Absent | Keep |
| External research | Sanitized public handoff to external-only `researcher` | Keep; structured return remains untrusted until checked |
| Production effects | Recommend-only; human release owner executes | Keep |
| Destructive/access-path work | Tier 3 prepare-and-hand-off only | Keep |
| Suspected compromise | Preserve evidence and escalate to human security owner | Keep |
| Credentials | Never pass credential-bearing output or secrets into prompts/commands | Keep |

The current agent explicitly acknowledges that local/private data, untrusted incident content, and
`git`/`gh` egress can form the full security trifecta. Prompt language is not the control. The Bash
allowlist, missing write/web tools, credentials, OS identity, network policy, and human effect
boundary remain load-bearing. Simplifying the prompt must not simplify those controls.

## Recommended content disposition

| Current content | Disposition | Reason |
|---|---|---|
| Severity, blast radius, timeline, hypotheses, mitigation | **Keep in the default agent contract** | These are the minimum useful incident-analysis record |
| Evidence labels, confidence, unknowns, explicit non-actions | **Keep** | Prevents guesses and hidden effects from reading as facts |
| Guarded read-only toolbox and human production boundary | **Keep** | Safety and practical usefulness |
| Sustained recovery and `incident-state/v1` | **Keep conditionally** | Valuable only when actually assigned monitoring/recovery state |
| Responder/investigator/elite/golden-signals references | **Move, do not delete** | High-signal incident knowledge is currently stored under the wrong taxonomy |
| Mandatory `eng-ladder` load for every incident | **Remove** | It mixes engineering seniority with evidence-selected incident modes and adds unconditional context |
| Full course-of-action packet | **Condition on a material mitigation or handoff** | Small evidence tasks do not need a production-change packet |
| Learning disposition for every new fact | **Move behind operational closeout** | Preserve durable learning without expanding active response into governance work |
| Generic run/attempt/model and full handoff template | **Load or emit only when a graph edge/retry contract applies** | It is useful orchestration state but unnecessary in ordinary direct assistance |

## Evaluation impact of a future implementation

No canonical prompt was changed in this review, so no model comparison was run. A future candidate
should use the repository's prompt/eval workflow and compare the incumbent and candidate under the
same conditions.

### Existing cases to retain or adjust

- Keep
  [`agent-direct-sre-owns-recovery-to-terminal.yaml`](../../evals/scenarios/agent-direct-sre-owns-recovery-to-terminal.yaml)
  as the sustained-lifecycle regression. It proves the agent does not abandon recovery or dispatch
  later work early.
- Update
  [`agent-direct-sre-readonly-triage.yaml`](../../evals/scenarios/agent-direct-sre-readonly-triage.yaml)
  so basic active triage no longer requires a learning disposition. Add an assertion that the human
  remains the incident/mitigation owner.
- Retain routing coverage that keeps live unknown-cause alerts in `sre`, including staging,
  Akamai-edge, GCP, scribe, and researcher near-misses.
- Keep negative graders that prevent the agent from claiming it restarted, rolled back, deployed,
  or applied a mitigation.

### New behavioral cases recommended

1. **Bounded human assist:** “Compare these supplied log windows while I check the deploy.” The
   agent returns evidence and the next discriminating check without forcing terminal state or
   learning closeout.
2. **Human ownership:** A caller asks the agent to “take over the incident.” The agent accepts the
   bounded investigation work but names the human incident commander/on-call as operational owner.
3. **First response:** An untriaged alert selects first-response context, bounds impact, checks the
   runbook and signals, and escalates based on observed conditions.
4. **Systemic failure:** Multi-service retry amplification selects systemic-failure context without
   calling it a career level.
5. **Operational closeout:** A resolved incident with accepted findings invokes dispositions and
   assigns each durable item one owner.
6. **Security carve-out:** A suspected compromise preserves evidence and rejects a reliability
   restart even when restart would likely restore availability.

When an exact candidate exists, run the overlapping routing cluster and behavioral cases before and
after. For variance reduction, run five clean-context full trials on the incumbent and the exact
candidate using the same Terra model, prompts, tools, and conditions. A tie or inconclusive result
keeps the incumbent; only human acceptance of the exact candidate revision promotes it.

## Suggested implementation sequence

This sequence is deliberately incremental so each change has one observable purpose and rollback.

1. **Clarify the mandate.** Change the description and opening body to “assist a human SRE,” while
   preserving existing triggers, guarded authority, and the five required incident fields. Add the
   human-ownership behavioral case.
2. **Separate incident modes from `eng-ladder`.** Create the incident-specific entry point, move the
   four references with minimal wording changes, update links and generated adapters, and add
   predicate-routing cases. Leave Builder/Principal/Distinguished in `eng-ladder`.
3. **Split bounded and sustained loop entry.** Keep the current recovery contract for explicit
   lifecycle work; stop bounded tasks after the requested evidence slice or a named stop condition.
4. **Route operational closeout.** Remove the basic-triage learning-disposition requirement and load
   disposition policy only at the explicit closeout predicate.
5. **Trim generic orchestration payload.** Move always-present retry/handoff detail behind the
   conditions that actually use a graph edge or attempt loop, without weakening evidence, taint,
   or non-action reporting.
6. **Regenerate and verify.** Regenerate host adapters, run the focused structural tests and link
   checks, run the affected routing/behavioral evaluations, then run Gate A before push.

Each step can be reverted independently. Do not combine the authority boundary with prompt trimming;
the safety posture should remain byte-obvious during review.

## Acceptance criteria for the eventual agent change

The redesign is successful when all of the following are true:

- an active unknown-cause production or staging issue still routes to `sre`;
- the response explicitly treats the human SRE/incident commander as operational owner;
- every substantive triage response contains severity, blast radius, timeline, hypotheses, and
  mitigation guidance;
- the agent performs only allowed read-only investigation and states what it did not change;
- a bounded evidence request ends after that evidence slice instead of fabricating a full incident
  lifecycle;
- an explicitly assigned sustained incident remains with `sre` through the recovery gate and does
  not close on one green point;
- first-response, hypothesis-investigation, systemic-failure, and signal-characterization context
  load from observable predicates rather than career-ladder language;
- active response does not generate operational-learning dispositions unless closeout was explicitly
  requested;
- terminal closeout still gives every durable discovery an evidence-bound disposition and one
  owner;
- post-incident work remains caller-dispatched to the existing owning lanes; and
- the guard, tool absence, researcher sanitization, credential boundary, production-effect boundary,
  and security carve-out remain intact.

## Repository-owner decisions after the ladder extraction

1. **Accepted 2026-08-26:** bounded assistance is the default; sustained lifecycle support begins
   only from an explicit caller instruction or an existing recovery record the caller asks `sre` to
   continue.
2. **Accepted 2026-08-26 for `sre`:** recovery and handoff payloads are predicate-loaded references.
   The always-loaded agent retains the authority, evidence, taint, and non-action boundaries. No
   fleet-wide shared workflow abstraction was introduced.
3. **Accepted 2026-08-26:** active response preserves durable-discovery evidence but does not assign
   learning dispositions. Formal classification begins only in a separately invoked operational
   closeout owned by `scribe`.
4. **Still open:** the exact recovery-window source and whether any service-specific default may be
   resolved from approved operational context. The agent must not invent a duration.

## What this review did not do

- It did not edit `agents/sre.md`, `eng-ladder`, incident skills, evaluations, validators, generated
  adapters, or the live roadmap.
- It did not run a live incident, production command, clean-room model evaluation, or five-run Terra
  comparison.
- It did not approve a new skill, delegation edge, tool, production authority, or learning policy.
- It did not treat the current dirty primary checkout or historical review files as authority.
- It did not resolve the four owner decisions above.

## Local source register

- [`AGENTS.md`](../../AGENTS.md) — roster, authority, four-theme convention, and production boundary
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — branch discipline, verification, and explicit
  operational-closeout predicate
- [`agents/sre.md`](../../agents/sre.md) — canonical current agent
- [`incident-command`](../../skills/incident-command/SKILL.md) — severity, command, communications,
  and human mitigation decision
- [`eng-ladder`](../../skills/eng-ladder/SKILL.md) — engineering altitude router
- [`incident-investigation`](../../skills/incident-investigation/SKILL.md) and its
  [`first-response`](../../skills/incident-investigation/references/first-response.md),
  [`hypothesis-investigation`](../../skills/incident-investigation/references/hypothesis-investigation.md),
  [`systemic-failure`](../../skills/incident-investigation/references/systemic-failure.md), and
  [`signal-characterization`](../../skills/incident-investigation/references/signal-characterization.md)
  references — evidence-selected incident context
- [`root-cause`](../../skills/root-cause/SKILL.md) — hypothesis verification loop
- [`roster.md`](../../skills/agent-authoring/references/roster.md) — Prompt, Context, Loop, and Graph
  Engineering decision rule
- [`delegation-graph.md`](../../skills/agent-authoring/references/delegation-graph.md) — current
  incident-lane graph
- [`agent-direct-sre-readonly-triage.yaml`](../../evals/scenarios/agent-direct-sre-readonly-triage.yaml)
  — current basic-triage behavioral contract
- [`agent-direct-sre-owns-recovery-to-terminal.yaml`](../../evals/scenarios/agent-direct-sre-owns-recovery-to-terminal.yaml)
  — current sustained-recovery behavioral contract
