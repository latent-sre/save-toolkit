# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred work for the
> current fleet. Historical plans, reviews, audits, and decision records provide evidence and
> rationale; they do not independently add work to this queue.

The architecture is one canonical Claude plugin under `agents/`, `skills/`, and `commands/`, with
generated host-native adapters for Copilot/VS Code. No accepted ADR establishes it; the records that
assume it are the two rename ADRs and the Codex retirement, indexed in
[`docs/decisions/README.md`](decisions/README.md). Codex was retired as a distribution target on 2026-08-23
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

## Repository work

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

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-08-30). Phase 1 is closed as evidence; Phase 2 is the live work, one
skill per slice, probe-before-routing.
**Owner:** Save Toolkit maintainers approve each slice; `agent-engineer` executes.
**Outcome:** No skill spends a caller's context on detail the call did not need, or on what the
fleet's models already produce unprompted. Each screened entrypoint gets one probe-then-checkpoint
disposition; a committed component contract outranks both the byte screen and the probe.
**Next action:** The four slices this item last named — `obs-dashboards`, `backend-craft`, `runbook`,
`obs-alerting` — have all landed; `CHANGELOG.md` records each. Re-screen before picking the next:
`wc -c skills/*/SKILL.md | sort -n | awk '$1>7800'` on 2026-09-04 leaves five entrypoints at or above
the 7,800-byte screen — `incident-investigation` (13,703 B), `runbook` (9,783 B), `agent-authoring`
(9,335 B), `service-lifecycle` (8,313 B), `pcf-ops` (7,822 B). `runbook` and `incident-investigation`
were both reshaped on 2026-09-03 (the runbook trim and the incident-lane fold) and stayed above the
screen, so the next slices are `agent-authoring`, `service-lifecycle`, and `pcf-ops`, largest first,
unless a fresh measurement says otherwise. The prose-pinning test suites were removed
on 2026-09-01; after a cut, run `python scripts/check_links.py` (link containment and explicit-only
frontmatter) and the skill's eval scenarios.
**Evidence:** `docs/reviews/2026-08-30-skill-001-7800-screen.md` (removed 2026-09-02)
**SRE task:** An SRE gets a faster, cheaper answer, because a skill only loads the routing detail the
call actually needed instead of every branch's reference material.

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
**SRE task:** An SRE approving a live automated action gets one exact, bound, revocable approval —
target, argv/executable digest, expiry, rollback — instead of an open-ended execution grant.

## Parked — no SRE task names these

Each item below is `deferred` (2026-09-03) because no SRE task names it: landing it changes nothing a
human SRE does. They keep their IDs so a later record can cite them, and their evidence pointers so a
reopening starts from what was measured. Bare paths marked `(removed 2026-09-02)` are in git history;
read one with `git show e77fc672^:<path>`. Reopening an item means restoring its seven fields here,
starting with a named SRE task.

| ID | What it would do | Evidence |
|---|---|---|
| WF-001 | Keep any executable `ship-review` workflow out of the repository until Claude supports dispatching one exact trusted workflow without granting caller-supplied workflow code; monitor the Workflow and `ultrareview` result contracts, re-probe only on a material change. | `docs/reviews/2026-08-30-live-backlog-refresh.md` (removed 2026-09-02) |
| ROUTE-006 | Accept `hand off to incident-investigation` as a valid deferral in the observability-engineer `…-defers-live-incident` grader, or record the phrasing out of contract. That scenario was retired in the 2026-09-02 corpus cut, so EVAL-009 decides first whether the phrasing needs a scenario at all. | `GRADER-009` closed row in `docs/roadmap-closed.md` (removed 2026-09-02) |
| GRAPH-004 | Ship `fleet-atlas`, a deterministic static atlas answering fleet-artifact provenance with `path:line` citations and an exact revision. Do not merge, close, or rewrite the donor PR before GRAPH-006 reaches semantic parity. | [PR #205](https://github.com/latent-sre/save-toolkit/pull/205) |
| GRAPH-005 | Prove, in a hardened offline two-container sandbox, that a Microsoft Agent Framework workflow can consume a real streamed A2A v1 task from an AutoGen GraphFlow worker behind exactly one human accept/reject. Resolve findings and rerun the pinned-image six-case lifecycle first. | `docs/reviews/2026-08-30-autogen-a2a-exact-revision-verification.md` (removed 2026-09-02) |
| GRAPH-006 | Rebuild `fleet-atlas` around one typed, evidence-bound pipeline sharing a projection/provenance verifier across `build`/`check`/`query`. Next step is the compact v2 design and compatibility matrix for owner review. | [PR #205](https://github.com/latent-sre/save-toolkit/pull/205) |
| HOST-002 | Rest the guarded roles' VS Code posture on observed host behavior. On the first installed build proven to contain upstream `d679b159`, rerun all six criteria in `docs/probes/host-002-vscode-agent-delegation.md` (removed 2026-09-02) plus the agent-scoped hook canary; do not populate `hooks/copilot-hooks.json` before that. | `docs/reviews/2026-08-30-vscode-subagent-handoff-enforcement.md` (removed 2026-09-02) |
| ROUTE-003 | Give the two positive workflow-graph discovery routes left inconclusive by Batch 1 reproducible, model-labelled reliability evidence, or have the owner dispose the measurement. Neither consumed profile is reusable. | `docs/reviews/2026-09-01-decision-backlog-reconciliation.md` (removed 2026-09-02) |
| ROUTE-004 | Decide whether the surviving Mantine positive — the only `frontend-craft` discovery case left after the 2026-09-02 corpus cut, already in the regression split at threshold 1.0 — is sufficient routing-reliability evidence or needs a replacement calibration case. | `docs/reviews/2026-08-31-grader-005-closure.md` (removed 2026-09-02) |
| EVAL-005 | Seed the Grafana build probe with a datasource that returns real data, so `build-obs-dashboard-write-honours-the-carve-out` measures whether the write lands and not only that the Tier 2 boundary holds. Run the fixed packet once on the Windows Docker host, three Sonnet trials per side, no retries. | `docs/reviews/2026-08-31-eval-005-prometheus-probe-gate.md` (removed 2026-09-02) |
| EVAL-007 | Make a behavioural incident scenario return a verdict about the response rather than its phrasing. Blocked on the owner resolving the shared EVAL-007 closure contract (EVAL-004 is superseded by EVAL-009); recommended shape is one structured or named-relation grader plus one clean guidance-removal counterfactual. | `docs/reviews/2026-09-01-decision-backlog-reconciliation.md` (removed 2026-09-02) |
| EVAL-009 | Take one fresh baseline of the whole corpus on one model and one runner build, run `python evals/judge.py --calibrate`, decide the 15 "ownership map" description sentences, re-add injection-refusal coverage as a rubric-graded scenario, and retire the transitional `docs/reviews/2026-09-02-eval-*` packets. Deferred until A3–A5, S1 and S4 of the fleet weight review and the post-PR-#224 skills trims have merged; the routing after-run for the eleven descriptions #224 changed folds in here. | [`PR #212`](https://github.com/latent-sre/save-toolkit/pull/212) |
