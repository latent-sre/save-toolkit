# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred work for the
> current fleet. Historical plans, reviews, audits, and decision records provide evidence and
> rationale; they do not independently add work to this queue.

The accepted architecture is `docs/decisions/2026-07-31-multi-platform-plugin-packaging.md`:
one canonical Claude plugin under `agents/`, `skills/`, and `commands/`, with generated host-native
adapters for Copilot/VS Code. Codex was retired as a distribution target on 2026-08-23
([ADR](decisions/2026-08-23-retire-codex-distribution-target.md)); it remains a supported way to
work in this repository, reading the root `AGENTS.md` like any other agent.

The 2026-09-02 retention pass removed the closed-item register and most evidence packets this file
cited. **Every record named below as a bare path rather than a link is in git history**: read it
with `git show e77fc672^:<path>`. Restoring one is a deliberate act, not a link repair — an item
whose evidence is worth re-reading often enough should carry the packet back into the tree.

## Item contract

Every live item carries seven fields: **ID** (stable identifier), **Status** (`active`, `ready`,
`blocked`, `decision-needed`, or `deferred`, dated), **Owner**, **Outcome** (what done looks like, in
one or two sentences), **Next action** (the next concrete step and who takes it), **Evidence**
(one link to the record that proves current state, or `none yet`), and **SRE task** (the task a
human SRE does differently when this lands; an item that cannot name one is `deferred`). An item
leaves this file only when its Outcome is met and merged, or an owner disposition is committed — and
once it leaves, the commit that removed it and its CHANGELOG entry are its record. Neither re-queues
work.

## Active runtime work

### WF-001 — establish a supported exact-dispatch boundary for Claude workflows

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** Save Toolkit maintainers
**Outcome:** The repository carries no executable `ship-review` workflow until Claude provides a
supported way to dispatch one exact trusted workflow without granting caller-supplied workflow code.
**Next action:** Monitor the documented Workflow and `ultrareview` result contracts for immutable
implementation binding and a machine-enforceable finding verdict; re-probe only after one materially
changes. Do not restore `ship-review` or treat an exit-0 result as approval.
**Evidence:** `docs/reviews/2026-08-30-live-backlog-refresh.md` (removed 2026-09-02)
**SRE task:** none named — this item only withholds an unsafe capability; landing it changes no task
an SRE performs.

## Repository work

### ROUTE-006 — the `defers-live-incident` routing grader misses the particle form `hand off to sre-assistant`

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** Save Toolkit maintainers
**Outcome:** The observability-engineer `…-defers-live-incident` discovery scenario accepts the
particle phrasing `hand off to sre-assistant` as a valid deferral, or an owner records that the phrasing is
out of contract. This is the routing-grader half of the closed GRADER-009; the retry-grader half
was superseded by the rubric judge.
**Next action:** The observability-engineer `…-defers-live-incident` scenario this item told the
owner to edit was retired in the 2026-09-02 corpus cut. Re-decide under EVAL-009 whether the
particle phrasing needs a scenario at all before authoring a new one.
**Evidence:** `GRADER-009` closed row in `docs/roadmap-closed.md` (removed 2026-09-02)
**SRE task:** none named — this decides only whether a grader accepts a phrasing; it does not change
observability-engineer's own prompt or behavior.

### CONTEXT-001 — establish a generalized SRE operational-context contract

**Status:** `active` (2026-08-30)
**Owner:** Save Toolkit maintainers own the architecture and acceptance of the generic-alpha
revision; `agent-engineer` owns consumer context-requirement semantics; `software-engineer` owns any
later resolver, validator, or onboarding-tool implementation.
**Outcome:** Reusable skills and agents resolve one explicit team, service, environment, and
deployment from schema-valid configuration and receive only the smallest context projection they
declare. Missing or ambiguous context fails closed; valid context never grants credentials or
approval.
**Next action:** Review and merge the two published follow-up branches, producer-first:
`sre-context:work/context-001-lifecycle-contract` at `458f39c`, then
`save-toolkit:work/context-001-close-contract-gap` at `96e1784`. Verify the mirrors and the
condition-7 safety boundary together, complete independent review of the remaining acceptance
evidence, then ask the owner to accept or reject the generic alpha.
**Evidence:** `docs/reviews/2026-08-30-live-backlog-refresh.md` (removed 2026-09-02)
**SRE task:** An SRE (or a skill/agent acting for them) states their team, service, environment, and
deployment once in schema-valid config, instead of restating it in every session.

### GRAPH-004 — `fleet-atlas`: a revision-bound knowledge graph over fleet artifacts

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** `software-engineer` owns the generator, schema, and tests; `agent-engineer` owns the
`fleet-atlas` skill; Save Toolkit maintainers accept the exact candidate revision.
**Outcome:** A deterministic static atlas answers fleet-artifact provenance and ownership questions
with `path:line` citations and an exact source revision, returning `UNKNOWN` rather than guessing.
**Next action:** Stop one-finding-at-a-time expansion on the open PR. `GRAPH-006` defines and proves
a typed, evidence-bound replacement from current main; do not merge, close, or rewrite the donor PR
before the replacement reaches semantic parity and the owner makes an exact-candidate decision.
**Evidence:** [PR #205](https://github.com/latent-sre/save-toolkit/pull/205)
**SRE task:** none named — this answers fleet-artifact provenance questions for the people building
the fleet, not an incident-response or operational task.

### GRAPH-005 — AutoGen GraphFlow + A2A canary-evidence sandbox

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** `software-engineer` owns the runtime, cases, and tests; Save Toolkit maintainers accept
the exact final revision.
**Outcome:** A hardened, offline, two-container sandbox proves a Microsoft Agent Framework workflow
can discover and consume a real streamed A2A v1 task from an AutoGen GraphFlow worker, gated by
exactly one human accept/reject decision that writes only a local record.
**Next action:** Resolve independent correctness/security findings and rerun affected checks, then
rerun the exact candidate's pinned-image and six-case lifecycle with cleanup evidence before any
pull request or acceptance decision.
**Evidence:** `docs/reviews/2026-08-30-autogen-a2a-exact-revision-verification.md` (removed 2026-09-02)
**SRE task:** none named — this is a runtime-canary sandbox for fleet engineering, not a capability an
SRE uses.

### GRAPH-006 — refactor `fleet-atlas` around a typed, evidence-bound pipeline

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** `software-engineer` owns the replacement design and implementation; `agent-engineer` owns
consumer-skill and scenario compatibility; Save Toolkit maintainers accept the exact candidate.
**Outcome:** One explicit pipeline extracts every node with source-span-backed attributes and edges,
and `build`/`check`/`query` share one projection/provenance verifier; the public v1 schema and CLI
stay compatible until a measured cutover says otherwise.
**Next action:** Write the compact v2 design and compatibility matrix. After owner review, create the
replacement branch from current main and implement in small builder-owned commits, keeping PR #205
open until the replacement proves parity or is rejected.
**Evidence:** [PR #205](https://github.com/latent-sre/save-toolkit/pull/205)
**SRE task:** none named — same fleet-artifact provenance tool as GRAPH-004, still not an operational
task.

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** Save Toolkit maintainers
**Outcome:** The guarded roles' VS Code posture rests on observed host behavior, establishing whether
the read-only guard is portable to that host or whether policy-delivered Copilot managed settings are
the only real control there.
**Next action:** On the first installed build proven to contain upstream `d679b159`, rerun all six
criteria in the agent-delegation probe (`docs/probes/host-002-vscode-agent-delegation.md`, removed
2026-09-02 — restore it from git before rerunning), including the
real plugin `software-engineer` -> `reviewer` edge and the paired allowed/forbidden canary, then run
the agent-scoped hook canary. Do not infer runtime enforcement from source alone or populate
`hooks/copilot-hooks.json` before that.
**Evidence:** `docs/reviews/2026-08-30-vscode-subagent-handoff-enforcement.md` (removed 2026-09-02)
**SRE task:** none named — this measures host enforcement for the fleet's own guard; it changes no
task an SRE performs.

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-08-30). Phase 1 is closed as evidence; Phase 2 is the live work, one
skill per slice, probe-before-routing.
**Owner:** Save Toolkit maintainers approve each slice; `agent-engineer` executes.
**Outcome:** No skill spends a caller's context on detail the call did not need, or on what the
fleet's models already produce unprompted. Each screened entrypoint gets one probe-then-checkpoint
disposition; a committed component contract outranks both the byte screen and the probe.
**Next action:** At the next evidence/recommendation checkpoint, select the next slice among the four
undispositioned entrypoints at or above the 7,800-byte screen: `obs-dashboards`, `backend-craft`,
`runbook`, `obs-alerting`. The prose-pinning test suites were removed
on 2026-09-01; after a cut, run `python scripts/check_links.py` (link containment and explicit-only
frontmatter) and the skill's eval scenarios.
**Evidence:** `docs/reviews/2026-08-30-skill-001-7800-screen.md` (removed 2026-09-02)
**SRE task:** An SRE gets a faster, cheaper answer, because a skill only loads the routing detail the
call actually needed instead of every branch's reference material.

### ROUTE-003 — remeasure workflow-graph discovery reliability (the service-readiness scenario was retired 2026-09-02)

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** Save Toolkit maintainers
**Outcome:** The two positive discovery routes left inconclusive by Batch 1 get reproducible,
model-labelled reliability evidence before either is promoted into a stronger routing claim.
**Next action:** After authentication is restored, the owner decides whether the two consumed
inconclusive attempts are sufficient to dispose the measurement or whether a newly designed,
separately approved v2 campaign is warranted. Do not reuse either consumed profile.
**Evidence:** `docs/reviews/2026-09-01-decision-backlog-reconciliation.md` (removed 2026-09-02)
**SRE task:** none named — landing this produces reliability evidence for a future promotion
decision; it does not itself change routing behavior.

### ROUTE-004 — the three `frontend-craft` discovery scenarios route unreliably on Sonnet

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** Save Toolkit maintainers
**Outcome:** The `frontend-craft` regression scenarios either fire reliably enough to sit in the
regression split at threshold 1.0, or move to calibration with the reason recorded, so a red there
means a skill regression rather than a routing coin-flip.
**Next action:** The 2026-09-02 corpus cut retired the Preact review and the merge-readiness split,
leaving only the Mantine case, already in the regression split at threshold 1.0; that surviving
positive is now the routing-reliability instrument for `frontend-craft`. Owner still decides whether
it alone is sufficient evidence or a replacement calibration case is warranted.
**Evidence:** `docs/reviews/2026-08-31-grader-005-closure.md` (removed 2026-09-02)
**SRE task:** none named — `frontend-craft` is a software-engineer-lane skill, and this item only
disposes an eval-reliability question about it.

### EVAL-005 — give the Grafana build probe a datasource worth writing a panel against

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** `observability-engineer` implements; Save Toolkit maintainers accept.
**Outcome:** `build-obs-dashboard-write-honours-the-carve-out` can measure whether the dashboard write
lands, not only whether the Tier 2 boundary holds, because the seeded datasource returns real data
for a real query.
**Next action:** Run the fixed packet once on the Windows Docker host — exact historical and current
plugin revisions, three Sonnet trials per side, no tuning or retries — and record Docker/image
identities before deciding closure.
**Evidence:** `docs/reviews/2026-08-31-eval-005-prometheus-probe-gate.md` (removed 2026-09-02)
**SRE task:** none named — this strengthens what one build probe measures; it changes no dashboard an
SRE reads.

### EVAL-006 — calibrate `discovery-gcp-ops-cloud-run-startup` against measured model behavior

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** Save Toolkit maintainers
**Outcome:** The scenario states which path it grades, and its prompt, fixture, and graders agree on
that path, so a red is attributable to the change under test rather than to instrument noise or a
task the fixture forbids.
**Next action:** Owner selects the instrumented path. Recommended: keep the scenario in calibration as
the degraded advisory path, and rewrite the prompt/`success_criteria` to say the lane cannot inspect
live in this fixture, requiring human-run read-only checks and the rollback packet.
**Evidence:** `docs/reviews/2026-09-01-decision-backlog-reconciliation.md` (removed 2026-09-02)
**SRE task:** none named — this rewrites an eval fixture's prompt to match what `gcp-ops` already
does; it does not change `gcp-ops`'s own guidance to the SRE.

### LIFECYCLE-001 — a service record stays true for the whole service life

**Status:** `active` (2026-08-26)
**Owner:** Save Toolkit maintainers
**Outcome:** The four unowned service-lifecycle transitions — change, remediation, refresh, and
retirement — have owners, so a record in the operational memory is either current or visibly not.
**Next action:** Retirement is now the retire mode of `service-lifecycle` itself (`service-retirement`
and `service-readiness-audit` folded in 2026-09-02), not a separate effect-shaped sibling skill.
Carry the two schema enhancements (`last_verified`/`maxAge`, and a `forbidden` path list) to
CONTEXT-001 as amendments rather than a skill-local schema.
**Evidence:** none yet
**SRE task:** An SRE reading a service record trusts it is current, because every lifecycle
transition (change, remediation, refresh, retirement) has a real owner writing to it.

### EVAL-007 — grade incident behaviour without phrase adjacency

**Status:** `deferred` (2026-09-03) — no SRE task names it; see SRE task below
**Owner:** Save Toolkit maintainers
**Outcome:** A behavioural incident scenario returns a verdict that reflects the response rather than
its phrasing, so a red result is worth investigating instead of routinely being a missed synonym.
**Next action:** Do not start a standalone campaign until the owner resolves the shared
EVAL-007 closure contract (EVAL-004 is superseded by EVAL-009). Recommended: one structured or named-relation grader plus one
clean committed guidance-removal candidate for the counterfactual.
**Evidence:** `docs/reviews/2026-09-01-decision-backlog-reconciliation.md` (removed 2026-09-02)
**SRE task:** none named — this is a grading-fidelity fix for one eval scenario; it changes no
incident-response behavior.

### ROUTE-005 — restate `incident-investigation`'s triggers in on-call phrasing

**Status:** `decision-needed` (2026-09-01). The original exact approved pair completed with no
retries; both arms routed correctly 9/9, but the candidate failed the full acceptance contract.
**Owner:** Save Toolkit maintainers
**Outcome:** The original fixed pair determines whether replacing the router's meta-triggers with
on-call phrasing strictly improves its full discovery contract, rather than tuning against a partial
routing win.
**Next action:** Human owner decides whether to close ROUTE-005 with the exact candidate rejected and
the incumbent (now named `investigation-depth`) retained. On acceptance, move this item to
`roadmap-closed.md` with the paired evidence.
**Evidence:** `docs/reviews/2026-08-30-route-005-paired-result.md` (removed 2026-09-02)
**SRE task:** An on-call SRE using plain on-call phrasing, not meta "use the skill" language, is
routed into `incident-investigation` reliably — if the candidate is accepted.

## Deferred

### EVAL-009 — reset the eval baseline after the fleet reshape

**Status:** `deferred` (2026-09-02) until A3–A5, S1, and S4 of the fleet weight review have merged.
**Owner:** Save Toolkit maintainers
**Outcome:** One fresh baseline of the whole corpus (46 scenarios plus the nine build probes) on one
model and one runner build, a fresh judge calibration, and a decision on the 15 "ownership map"
sentences still in skill descriptions. Every measurement taken during the reshape (the
`docs/reviews/2026-09-02-eval-*` packets, the gate-merge batches, the corpus-cut evidence) is a
transitional checkpoint, not a baseline, and is retired once this one exists.
**Next action:** After the last reshape PR merges, run the full corpus at three trials, run
`python evals/judge.py --calibrate`, record both, and retire the transitional packets. Injection-
refusal coverage (the two retired `agent-security` scenarios) is re-added as a rubric-graded
scenario when the baseline is reset.
**Evidence:** [`PR #212`](https://github.com/latent-sre/save-toolkit/pull/212)
**SRE task:** none named — eval-harness baseline maintenance only; no SRE-facing behavior changes.

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`
**Owner:** Save Toolkit maintainers
**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.
**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority. Reopens only when a named workflow is approved
to cross the current prepare/recommend boundary with a separately controlled execution identity.
**Evidence:** none yet
**SRE task:** An SRE approving a live automated action gets one exact, bound, revocable approval —
target, argv/executable digest, expiry, rollback — instead of an open-ended execution grant.
