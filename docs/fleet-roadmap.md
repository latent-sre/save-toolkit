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

Every live item carries six fields: **ID** (stable identifier), **Status** (`active`, `ready`,
`blocked`, `decision-needed`, or `deferred`, dated), **Owner**, **Outcome** (what done looks like, in
one or two sentences), **Next action** (the next concrete step and who takes it), and **Evidence**
(one link to the record that proves current state, or `none yet`). An item leaves this file only
when its Outcome is met and merged, or an owner disposition is committed — both move to
[`roadmap-closed.md`](roadmap-closed.md), which is evidence and never re-queues work.

## Active runtime work

### WF-001 — establish a supported exact-dispatch boundary for Claude workflows

**Status:** `blocked` (2026-08-30)
**Owner:** Save Toolkit maintainers
**Outcome:** The repository carries no executable `ship-review` workflow until Claude provides a
supported way to dispatch one exact trusted workflow without granting caller-supplied workflow code.
**Next action:** Monitor the documented Workflow and `ultrareview` result contracts for immutable
implementation binding and a machine-enforceable finding verdict; re-probe only after one materially
changes. Do not restore `ship-review` or treat an exit-0 result as approval.
**Evidence:** [`2026-08-30 live backlog refresh`](reviews/2026-08-30-live-backlog-refresh.md)

## Repository work

### ROUTE-006 — the `defers-live-incident` routing grader misses the particle form `hand off to sre`

**Status:** `decision-needed` (2026-09-01)
**Owner:** Save Toolkit maintainers
**Outcome:** The observability-engineer `…-defers-live-incident` discovery scenario accepts the
particle phrasing `hand off to sre` as a valid deferral, or an owner records that the phrasing is
out of contract. This is the routing-grader half of the closed GRADER-009; the retry-grader half
was superseded by the rubric judge.
**Next action:** Owner decides whether to widen the routing grader's alternative match; if yes,
edit the scenario and run it in the clean room on Sonnet at its declared trial count.
**Evidence:** [`GRADER-009` closed row](roadmap-closed.md)

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
**Evidence:** [`2026-08-30 live backlog refresh`](reviews/2026-08-30-live-backlog-refresh.md)

### GRAPH-004 — `fleet-atlas`: a revision-bound knowledge graph over fleet artifacts

**Status:** `blocked` (2026-08-31). Successive exact-head reviews keep finding contract defects;
the current implementation is not a merge candidate.
**Owner:** `software-engineer` owns the generator, schema, and tests; `agent-engineer` owns the
`fleet-atlas` skill; Save Toolkit maintainers accept the exact candidate revision.
**Outcome:** A deterministic static atlas answers fleet-artifact provenance and ownership questions
with `path:line` citations and an exact source revision, returning `UNKNOWN` rather than guessing.
**Next action:** Stop one-finding-at-a-time expansion on the open PR. `GRAPH-006` defines and proves
a typed, evidence-bound replacement from current main; do not merge, close, or rewrite the donor PR
before the replacement reaches semantic parity and the owner makes an exact-candidate decision.
**Evidence:** [PR #205](https://github.com/latent-sre/save-toolkit/pull/205)

### GRAPH-005 — AutoGen GraphFlow + A2A canary-evidence sandbox

**Status:** `active` (2026-08-31)
**Owner:** `software-engineer` owns the runtime, cases, and tests; Save Toolkit maintainers accept
the exact final revision.
**Outcome:** A hardened, offline, two-container sandbox proves a Microsoft Agent Framework workflow
can discover and consume a real streamed A2A v1 task from an AutoGen GraphFlow worker, gated by
exactly one human accept/reject decision that writes only a local record.
**Next action:** Resolve independent correctness/security findings and rerun affected checks, then
rerun the exact candidate's pinned-image and six-case lifecycle with cleanup evidence before any
pull request or acceptance decision.
**Evidence:** [`ede57417 verification`](reviews/2026-08-30-autogen-a2a-exact-revision-verification.md)

### GRAPH-006 — refactor `fleet-atlas` around a typed, evidence-bound pipeline

**Status:** `ready` (2026-08-31). Approved direction only; no replacement branch or candidate exists
yet.
**Owner:** `software-engineer` owns the replacement design and implementation; `agent-engineer` owns
consumer-skill and scenario compatibility; Save Toolkit maintainers accept the exact candidate.
**Outcome:** One explicit pipeline extracts every node with source-span-backed attributes and edges,
and `build`/`check`/`query` share one projection/provenance verifier; the public v1 schema and CLI
stay compatible until a measured cutover says otherwise.
**Next action:** Write the compact v2 design and compatibility matrix. After owner review, create the
replacement branch from current main and implement in small builder-owned commits, keeping PR #205
open until the replacement proves parity or is rejected.
**Evidence:** [PR #205](https://github.com/latent-sre/save-toolkit/pull/205)

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `active` (2026-08-30). The installed-Claude-CLI visibility gap is closed; the VS Code
boundary remains open.
**Owner:** Save Toolkit maintainers
**Outcome:** The guarded roles' VS Code posture rests on observed host behavior, establishing whether
the read-only guard is portable to that host or whether policy-delivered Copilot managed settings are
the only real control there.
**Next action:** On the first installed build proven to contain upstream `d679b159`, rerun all six
criteria in the [agent-delegation probe](probes/host-002-vscode-agent-delegation.md), including the
real plugin `software-engineer` -> `reviewer` edge and the paired allowed/forbidden canary, then run
the agent-scoped hook canary. Do not infer runtime enforcement from source alone or populate
`hooks/copilot-hooks.json` before that.
**Evidence:** [`2026-08-30 VS Code subagent and handoff enforcement`](reviews/2026-08-30-vscode-subagent-handoff-enforcement.md)

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-08-30). Phase 1 is closed as evidence; Phase 2 is the live work, one
skill per slice, probe-before-routing.
**Owner:** Save Toolkit maintainers approve each slice; `agent-engineer` executes.
**Outcome:** No skill spends a caller's context on detail the call did not need, or on what the
fleet's models already produce unprompted. Each screened entrypoint gets one probe-then-checkpoint
disposition; a committed component contract outranks both the byte screen and the probe.
**Next action:** At the next evidence/recommendation checkpoint, select the next slice among the six
undispositioned entrypoints at or above the 7,800-byte screen: `obs-dashboards`, `backend-craft`,
`runbook`, `workflow-graph-engineering`, `incident-drill`, `obs-alerting`. The prose-pinning test
suites were removed on 2026-09-01; after a cut, run `python scripts/check_links.py` (link
containment and explicit-only frontmatter) and the skill's eval scenarios.
**Evidence:** [`7,800-byte screen evidence`](reviews/2026-08-30-skill-001-7800-screen.md)

### ROUTE-003 — remeasure workflow-graph and service-readiness discovery reliability

**Status:** `decision-needed` (2026-08-31). Both the original and one approved replacement batch
ended INCONCLUSIVE (provider `server_error`, then expired OAuth) without resolving a model.
**Owner:** Save Toolkit maintainers
**Outcome:** The two positive discovery routes left inconclusive by Batch 1 get reproducible,
model-labelled reliability evidence before either is promoted into a stronger routing claim.
**Next action:** After authentication is restored, the owner decides whether the two consumed
inconclusive attempts are sufficient to dispose the measurement or whether a newly designed,
separately approved v2 campaign is warranted. Do not reuse either consumed profile.
**Evidence:** [`2026-09-01 decision-backlog reconciliation`](reviews/2026-09-01-decision-backlog-reconciliation.md)

### ROUTE-004 — the three `frontend-craft` discovery scenarios route unreliably on Sonnet

**Status:** `decision-needed` (2026-09-01). A later exact-revision native batch is merged and
disposition-ready; the three scenarios no longer support one shared routing conclusion.
**Owner:** Save Toolkit maintainers
**Outcome:** The `frontend-craft` regression scenarios either fire reliably enough to sit in the
regression split at threshold 1.0, or move to calibration with the reason recorded, so a red there
means a skill regression rather than a routing coin-flip.
**Next action:** Owner dispositions the three scenarios. Recommended: retain the 3/3 Mantine case as
the regression, move the Preact review to calibration, and split the merge-readiness case so routing
belongs to `merge-gate`.
**Evidence:** [`GRADER-005 closure`](reviews/2026-08-31-grader-005-closure.md)

### EVAL-005 — give the Grafana build probe a datasource worth writing a panel against

**Status:** `active` (2026-08-31). The Prometheus fixture and its outcome relation are committed and
independently reviewed with no P0/P1; Docker runtime measurement remains pending.
**Owner:** `observability-engineer` implements; Save Toolkit maintainers accept.
**Outcome:** `build-obs-dashboard-write-honours-the-carve-out` can measure whether the dashboard write
lands, not only whether the Tier 2 boundary holds, because the seeded datasource returns real data
for a real query.
**Next action:** Run the fixed packet once on the Windows Docker host — exact historical and current
plugin revisions, three Sonnet trials per side, no tuning or retries — and record Docker/image
identities before deciding closure.
**Evidence:** [`fixed Windows execution packet`](reviews/2026-08-31-eval-005-prometheus-probe-gate.md)

### EVAL-004 — measure the incident guidance added on 2026-08-26

**Status:** `decision-needed` (2026-09-01). Eight scenario files exist, but no current profile
selects all eight and both retained profiles are v1 evidence that cannot authorize a new live run.
**Owner:** Save Toolkit maintainers
**Outcome:** Every behavior claim added to `incident-command`/`investigation-depth` on 2026-08-26 has
a discriminating scenario, so a later edit that removes the behavior turns a scenario red instead of
passing silently.
**Next action:** Resolve the shared EVAL-004/EVAL-007 closure architecture first — one structured or
named-relation grader plus a committed guidance-removal control. The owner then decides whether that
offline packet closes the work or an eight-scenario native comparison is still warranted.
**Evidence:** [`2026-09-01 decision-backlog reconciliation`](reviews/2026-09-01-decision-backlog-reconciliation.md)

### EVAL-006 — calibrate `discovery-gcp-ops-cloud-run-startup` against measured model behavior

**Status:** `decision-needed` (2026-09-01). Option (a) is applied and confirmed at nine trials; the
remaining decision is the instrumented path.
**Owner:** Save Toolkit maintainers
**Outcome:** The scenario states which path it grades, and its prompt, fixture, and graders agree on
that path, so a red is attributable to the change under test rather than to instrument noise or a
task the fixture forbids.
**Next action:** Owner selects the instrumented path. Recommended: keep the scenario in calibration as
the degraded advisory path, and rewrite the prompt/`success_criteria` to say the lane cannot inspect
live in this fixture, requiring human-run read-only checks and the rollback packet.
**Evidence:** [`2026-09-01 decision-backlog reconciliation`](reviews/2026-09-01-decision-backlog-reconciliation.md)

### LIFECYCLE-001 — a service record stays true for the whole service life

**Status:** `active` (2026-08-26)
**Owner:** Save Toolkit maintainers
**Outcome:** The four unowned service-lifecycle transitions — change, remediation, refresh, and
retirement — have owners, so a record in the operational memory is either current or visibly not.
**Next action:** Design the retirement checklist as `service-lifecycle`'s effect-shaped sibling, then
carry the two schema enhancements (`last_verified`/`maxAge`, and a `forbidden` path list) to
CONTEXT-001 as amendments rather than a skill-local schema.
**Evidence:** none yet

### EVAL-007 — grade incident behaviour without phrase adjacency

**Status:** `decision-needed` (2026-09-01). The structured pilot and offline repair remain valid
partial evidence.
**Owner:** Save Toolkit maintainers
**Outcome:** A behavioural incident scenario returns a verdict that reflects the response rather than
its phrasing, so a red result is worth investigating instead of routinely being a missed synonym.
**Next action:** Do not start a standalone campaign until the owner resolves the shared
EVAL-004/EVAL-007 closure contract. Recommended: one structured or named-relation grader plus one
clean committed guidance-removal candidate for the counterfactual.
**Evidence:** [`2026-09-01 decision-backlog reconciliation`](reviews/2026-09-01-decision-backlog-reconciliation.md)

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
**Evidence:** [`paired result`](reviews/2026-08-30-route-005-paired-result.md)

## Deferred

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`
**Owner:** Save Toolkit maintainers
**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.
**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority. Reopens only when a named workflow is approved
to cross the current prepare/recommend boundary with a separately controlled execution identity.
**Evidence:** none yet
