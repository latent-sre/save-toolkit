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

## Closed items

One row per closed item. The row is the disposition; the linked document is evidence, never a task
list. An item with no surviving evidence document closed into a live contract instead, named here.

| Item | Closed | Disposition and evidence |
|---|---|---|
| `SAFE-001` | 2026-08-01 | Research trust zones split into local-only and external-only roles, and evidence normalized. Contracts: [`local-external-research-separation`](decisions/2026-07-31-local-external-research-separation.md) and [`schema-compatibility.md`](schema-compatibility.md) |
| `IMPROVE-001` | 2026-08-01 | Bounded improvement lifecycle. Its executables were parked at tag `pre-trim-2026-08-02` and no record advances past `observed`/`rejected` while they are — [closure](reviews/2026-08-01-fleet-improvement-closure.md) |
| `VERIFY-001` | 2026-08-02 | Executable verification isolated. Contract: [`verification-sandbox.md`](verification-sandbox.md) |
| `PROTECT-001` | 2026-08-05 | Repository protection and distinct promotion identity — [closure](reviews/2026-08-05-protect-001-closure.md) |
| `HOST-001` | 2026-08-06 | Host installation proof — [closure](reviews/2026-08-06-host-001-closure.md) |
| `ADAPT-001` | 2026-08-06 | Sibling-repo adaptations; its review history records defects Gate A was green over — [closure](reviews/2026-08-06-adapt-001-closure.md) |
| `SWEEP-001` and `MUTATION-001` | 2026-08-21 | Closed by **explicit owner disposition**, not a closure review: `not_applicable` as live work, owner `latent-sre`. No survivor count established a broken contract; the disposition does not assert every survivor was harmless. Diagnostic: [fleet mutation sweep](reviews/2026-08-15-fleet-mutation-sweep.md) |
| `EVAL-002` | 2026-08-22 | Agent-target discovery is calibration, never a regression gate — [ADR](decisions/2026-08-22-agent-discovery-calibration.md) |
| `REVIEW-001` | 2026-08-22 | Independent exact-SHA review is required for a production deployment of new bytes, not for every merge — [ADR](decisions/2026-08-22-production-review-boundary.md) |
| `NAV-001` | 2026-08-22 | Incident-navigation rejected and archived — [ADR](decisions/2026-08-22-incident-navigation-archive.md) |
| `RELEASE-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. The custom publication workflow, request/workflow contracts, release-specific tests, runbook, and the standalone four-host probe were never activated and had no named consumer; they were retired rather than maintained. The `release-gate` skill, manifest versions, and changelog history remain. Historical design ADR: [`superseded`](decisions/2026-08-11-immutable-release-promotion.md). Reopen only when a named consumer requires an immutable selector and rollback-capable release |
| `STATE-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. It described a future durable-execution control plane with no named workflow, implementation, or active dependency; handoffs and learning derive ownership and completion from Git, pull requests, tests/evals, and evidence. Reopen only when a named workflow must survive process or session loss and replay from version-bound artifacts would be unsafe or materially costly |
| `EVAL-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. Its only named trigger was a release decision, the parked suite no longer matches the current plugin identity or roster, and Codex stopped being a distribution target — no fleet component runs on Sol, so the trigger can no longer fire. Tag `pre-trim-2026-08-02` preserves the historical bytes — [ADR](decisions/2026-08-23-retire-codex-distribution-target.md) |
| `AUDIT-002` (Batch 1) | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. Implementation and review corrections merged in PR [#141](https://github.com/latent-sre/save-toolkit/pull/141) at merge commit `09e775b`, final head `11b8041`. Batch 1 selected no graph runtime, added no unconsumed schema, and activated no SRE capability addition; two positive-route reliability gaps moved to deferred `ROUTE-003` rather than triggering retries against unchanged bytes. Evidence: [`2026-08-22 skill clarity, routing, prompt, loop, and graph audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) |

The local Sol evaluator decision is recorded separately in
[`2026-08-01-local-sol-conformance.md`](decisions/2026-08-01-local-sol-conformance.md).

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

## Active runtime work

### WF-001 — establish a supported exact-dispatch boundary for Claude workflows

**Status:** `blocked`

**Outcome:** The repository carries no executable `ship-review` workflow until Claude provides a
supported way to dispatch one exact trusted workflow without granting caller-supplied workflow code.

**Source:** A version-pinned probe on Claude Code 2.1.221 found two incompatible behaviors. Setting
`CLAUDE_WORKFLOW_NAME_ONLY=1` suppresses inline-plugin workflows, so the trusted workflow cannot be
loaded. Without that flag, a native permission for `Workflow(save-toolkit:ship-review)` also admits
an input containing the same `name` plus caller-supplied `script`; the resolver executes that script
override. A plugin `PreToolUse` hook can deny the override, but the resulting launcher, hook receipt,
Git-object isolation, and upgrade matrix were a bespoke security broker disproportionate to this
fleet. That experiment was removed rather than shipped as a fragile control plane.

**Upstream check (2026-08-18):** Claude Code 2.1.227's built-in `claude ultrareview` removes the
caller-supplied workflow-body surface but exposes no immutable reviewed-subject identity and no
findings-sensitive verdict — it exits 0 either way, bundles a mutable tree, and uploads to a paid
cloud sandbox. Still blocked. Sources and queries: the
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

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `blocked` (2026-08-18) — the current Windows host has VS Code but no installed
extensions, so it has no Copilot tools surface to observe. No profile installation or mutation was
performed to manufacture the prerequisite.

**Outcome:** The guarded roles' VS Code posture rests on observed host behavior rather than
inference, and the fleet knows whether the read-only guard is portable to that host or whether
policy-delivered Copilot managed settings are the only real control there.

**Source:** A 2026-08-12 scan on two evidence bases. `[verified]` from the installed VS Code
1.133.0 bundle (`workbench.desktop.main.js`, build `a5b500951314efd502d07465bd138dfbd714a960`): the
generator's tool-set vocabulary and its Claude→VS Code equivalence table match the host's enums;
`disable-model-invocation` is a recognized key; `runSubagent` delegation is unscoped; the hook
surface (`chat.useClaudeHooks` and friends) exists. `[sourced]` at one remove — upstream
`microsoft/vscode` @ `0157e11` and `vscode-docs` @ `95cc3b3b`, read by the research lane and not
confirmed here: omitting a tool sets an explicit `false`; session selection outranks the agent
file; only extension agents are read-only; the picker writes the user's change back; a prompt
file's `tools:` outranks a referenced agent's. The second base is what makes `tools:` a default
rather than a boundary, and it is the half this item must confirm by observation.

**Current environment:** `[verified]` On 2026-08-18, `code --version` reported VS Code 1.127.0,
commit `4fe60c8b1cdac1c4c174f2fb180d0d758272d713`, x64;
`code --list-extensions --show-versions` returned no extensions. This establishes only that the
probe cannot start here, not any tool-enforcement behavior.

**Prerequisites:** Use an installed VS Code build with the GitHub Copilot tools surface and an
authenticated disposable test profile or other approved non-production session. The probe is
observational: it changes no live system, and it neither authorizes nor implies a Copilot hook
implementation.

**Acceptance:** A dated review packet records, from an observed session, whether the tools picker
offers `execute` to `sre`; whether a session-level override reinstates it; and whether using the
picker mutates `.github/agents/sre.agent.md` on disk. It states the VS Code build tested, keeps
`[verified]`/`[sourced]` labels honest, and either confirms the `AGENTS.md` VS Code limit or replaces
it with the measured behavior. Any hook-portability finding is recorded as evidence only; wiring a
Copilot hook is separate work needing its own review.

**Next action:** Provision the missing Copilot surface in an approved disposable profile, then run
the linked [`HOST-002 VS Code tool-enforcement probe`](probes/host-002-vscode-tool-enforcement.md),
validate its per-criterion evidence envelopes, and record the dated packet. Do not weaken the
`AGENTS.md` limit on inference alone, and do not populate `hooks/copilot-hooks.json` before a probe
shows the payload can scope to an exact agent identity.

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-08-23) — the `incident-command`, `ops-tooling`, and `agent-security`
router slices merged in PRs #142, #143, and #145. `ci-actions` is the only completed fourth-router
candidate pending owner acceptance in PR #146; `pcf-deploy` is the only fifth-router candidate under
implementation on its isolated dependent branch. No sixth candidate is edited.

**Outcome:** No skill spends a caller's context on detail the call did not need. Every entrypoint
that still meets the oversized-unconditional-body criterion becomes a router with a conditional
“if the question involves X, read Y” table while retaining its authority and safety invariants.

**Source:** The initial measurement and reproduction command are in the
[`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md). The later
[`complete skill audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) found that the old
eight-skill list had drifted: at its baseline, the nine candidates were `agent-security`,
`ci-actions`, `database-reliability`, `incident-command`, `ops-tooling`, `pcf-deploy`, `pcf-ops`,
`production-change-gate`, and `stack-profile`; `operational-learning` no longer belonged in the
set. Canonical bodies then totaled 231,622 bytes.

That nine-skill inventory is historical evidence, not the implementation baseline. Batch 0 and
Batch 1 both change relevant entrypoints, so this item must remeasure before editing. Description
metadata follows the current rule—capability or user goal, invocation conditions, and meaningful
exclusions, without procedure—rather than the retired “trigger only” doctrine.

`[verified]` The required 2026-08-23 remeasurement on tree `8ea628d` found 30 entrypoints totaling
232,717 bytes and confirmed the same nine candidates. Exact per-skill bytes and reference totals are
recorded in the audit's
[`Batch 2 remeasurement`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md#batch-2-remeasurement-and-first-router-candidate).
The first candidate reduces `incident-command` from 11,056 unconditional bytes to a 3,903-byte
entrypoint routing 9,977 reference bytes across three conditional lanes while retaining shared
authority and safety controls.

`[verified]` Candidate `cbda2b9` passed its focused static checks. Fixed run
`20260823T134724Z-a1b538a1` was overall inconclusive after two 180-second timeouts, but both raw
traces invoked `save-toolkit:incident-command` before the model became stuck trying to read linked
references in a discovery harness that denies `Read`. Activation is observed 2/2;
reference-dependent response behavior remains `[unverified]`. The audit records the exact evidence
and the disagreement between raw tool-use events and the timeout summary's empty derived invocation
fields.

The owner then authorized one timeout-calibration run on unchanged model-facing bytes. `[verified]`
Run `20260823T140515Z-83460c27`, clean commit `ea4cf74`, `claude-sonnet-5`, two trials, and a
540-second timeout passed 2/2. Trial durations were 263.594 and 40.531 seconds, so the first result
demonstrates that 180 seconds was an insufficient ceiling. The longer run is not rate-comparable to
the shorter run; it closes the after-change activation check under its own recorded condition. The
global runner default remains 300 seconds, and detailed reference-dependent behavior remains outside
the discovery evidence layer.

`[verified]` After PR #142 merged, the exact next-slice base
`17b4ba97aa0b8091a1b3bbff462bfc9bbae0d109` carried 30 entrypoints totaling 225,614 bytes and eight
remaining candidates: `agent-security`, `ci-actions`, `database-reliability`, `ops-tooling`,
`pcf-deploy`, `pcf-ops`, `production-change-gate`, and `stack-profile`. `ops-tooling` was the largest
at 14,427 unconditional entrypoint bytes versus two references totaling 7,202 bytes.

`[verified]` The second bounded implementation commit
`3b9559412ef06c1ae3e8a19e82fe23395a183ac0` converts only `ops-tooling`. Its unchanged description
now opens a 6,502-byte entrypoint that keeps the right-size exit, spawn-degradation behavior,
human-only production authority, evidence boundary, self-contained handoff contract, bounded phase
exits, and conditional `stack-profile` requirement. Six routed references total 17,897 bytes across
requirements/design, CLI, multi-component, build, review, and verification/handoff lanes. The full
canonical entrypoint corpus falls to 217,689 bytes and the mechanical candidate set to seven.

Those sizes are immutable Git-object measurements, not checkout byte lengths: run
`git ls-tree -r --format='%(objectsize)%x09%(path)' <sha> -- skills`, sum only
`skills/<name>/SKILL.md`, and use `git cat-file -s <sha>:skills/ops-tooling/SKILL.md` for the focused
entrypoint. Apply the same `ls-tree` command to `skills/ops-tooling/references` for the reference
total. The earlier values came from a line-ending-sensitive working tree and were not reproducible
from the commits they named.

The owner authorized one fixed five-agent fresh-context artifact exercise before commit. `[verified]`
Three lanes passed on the first candidate: early exit, independent review, and verification/handoff.
The requirements/design lane found the missing conditional `stack-profile` dependency and a stale
host-specific instruction in the environment-card asset; the multi-component build lane found that
the contract template loaded even when a project-owned contract already existed. The pre-commit
correction added the conditional `stack-profile` route, repaired the host-specific asset text, and
added a direct template predicate, but the agents were not rerun under the fixed budget. Independent
review of exact branch revision `270aab16cdc7c2dbd34557d1c395f550058a2634` later showed that the
multi-component procedure still bypassed that predicate and unconditionally instantiated the
template. It also found the non-reproducible byte counts above.

`[verified]` Follow-up commit `80c7c331b06bb5b593d8663475d0bbaa995e3880` makes the existing
project-owned versioned contract authoritative and limits the bundled contract template to the first
HTTP contract when none exists; its own header forbids duplicate contracts and applying its HTTP/RFC
9457 shape to non-HTTP interfaces. The router now separates procedure lanes from five optional asset
lanes: missing environment card, missing plan, new Python CLI without a project starter, first HTTP
contract when no project-owned versioned contract exists, and a drafted/replaced/relaunched builder
packet. A bounded fresh-context static regression passed the existing-contract, established-CLI,
existing-packet-validation, and existing-environment/plan cases without loading those assets. This
retest did not test host activation, final-response quality, or runtime behavior; those remain
`[unverified]` for the exact commit.

At `80c7c33`, the `ops-tooling` entrypoint is 6,922 immutable bytes, its six references total 18,709
bytes, the 30-entrypoint corpus totals 218,109 bytes, and the mechanical candidate set remains seven.

`[verified]` PR #143 merged exact head `2927a2120da0494195e8d901570963a15bdb877a` into `main` as
`14b7aeae7c22aff3b50800ef262123adb9a48bc3`. A bounded retrospective review of that immutable merge
found no P0/P1 issue and one merge-safe P2: the paragraph above counted four optional asset lanes
while naming only four of the five implemented predicates. The corrected count and omitted HTTP
contract predicate now match the Git object; no skill or projection byte changed in that correction.

`[verified]` The post-merge remeasurement on `14b7aea` keeps 30 entrypoints totaling 218,109 bytes
and seven candidates. `agent-security` is the largest at 13,629 unconditional bytes with no routed
references, so it is selected alone for the third bounded router slice.

`[verified]` The exact implementation and remediation each passed direct link and fleet validation,
strict Claude plugin validation, 112 focused link/adapter/fleet/canary tests (three skips), and
`git diff --check`; each canonical edit was regenerated once, producing 282 adapter files with byte
consistency. No description or eval scenario changed, no existing scenario targets `ops-tooling`,
and no paid routing run was required or performed.

`[verified]` Third bounded implementation commit
`e5838598c4d8f7ee52e788045c68f6b1033385ab` converts only `agent-security`. Its byte-identical
description now opens a 7,971-byte entrypoint that keeps the prompt-injection premise,
lethal-trifecta and Rule-of-Two decision, host-authority verification, cross-agent taint and
delegation limits, evidence labels, action-boundary validation, active-compromise stop, five-question
review, output contract, and human-approval handoff. Two explicit references total 7,188 bytes:
current-fleet/integration/MCP/host controls and the OWASP LLM Top 10 crosswalk. The 30-entrypoint
corpus falls to 212,451 bytes and the mechanical candidate set to six.

A fixed three-case fresh-context artifact exercise was attempted before commit. `[verified]` The
thread limit admitted two cases and rejected the OWASP case before execution. The risky
webhook/secret/MCP/egress case loaded only integration controls and returned the required structural
containment. The nominal core-only case unnecessarily loaded that reference because its first
predicate was too broad and also found an overclaim that a read-only reporter could not leak through
its output. One consolidated correction narrowed the predicate to secrets, external actions, host
enforcement, or tool-result envelopes and constrained the report channel while keeping its output
`[UNTRUSTED]`; the agents were not rerun under the one-candidate bound. Exact-candidate conditional
loading, OWASP response quality, host activation, and runtime behavior therefore remain
`[unverified]`.

`[verified]` One independent static review of exact commit `e583859` approved the complete immutable
nine-file canonical-plus-projection diff with no findings and no P0/P1. The reviewer confirmed the
description identity, always-loaded invariants, explicit reachable predicates, current fleet facts,
and absence of schema, runtime, capability, or authority expansion. It did not run tests, validators,
external source refreshes, or host probes.

`[verified]` The exact candidate passed the skill quick validator, direct link/fleet/roadmap/stale-name
validation, strict Claude plugin validation, 112 focused link/adapter/fleet/canary tests (three
skips), and `git diff --check`. The one required regeneration produced 286 adapter files with byte
consistency. Two direct calibration scenarios target `agent-security`, but its description routing
content is unchanged; no paid routing run was required or performed.

`[verified]` PR #145 merged final head `97008f442f282912e1e682af192811d833a0c8e5` into `main` as
`a10c8820ad569fcf2ef4f07866ef1836c081e3b1`. Its two review findings corrected the OWASP title and
an unreachable crosswalk control before merge; Linux validation, Windows validation, and the Claude
plugin contract passed on that final head. The final entrypoint remains 7,971 immutable bytes and
its two references total 7,231 bytes. These merge facts do not upgrade the earlier independent
review from `e583859` to the final head.

`[verified]` The required current-main remeasurement on
`80cd023b8606f4b94f7a8b508a70e2ed255e44aa` finds 30 entrypoints totaling 212,440 bytes and six
remaining candidates. `ci-actions` is largest at 12,197 unconditional entrypoint bytes with one
reference totaling 1,620 bytes, so it is selected alone for the fourth bounded router slice.

`[verified]` Fourth bounded implementation commit
`a5c425d69eaf5211226db81e42ddc277496dfd62` converts only `ci-actions`. Its byte-identical
description now opens a 7,282-byte entrypoint that keeps the build-once/promote contract,
project-owned-workflow precedence, human-only deployment authority, untrusted-input boundary,
least-privilege permissions, immutable action/image pins, event-injection and fork isolation,
protected-environment credential rule, non-cancellable production concurrency, layered verification,
and evidence-bound handoff. Three explicit references total 10,706 bytes across security/provenance,
execution/runners, and PCF deployment; the starter asset is available only when a new reusable
workflow is required and no project-owned workflow or starter exists. The 30-entrypoint corpus falls
to 207,525 bytes and the mechanical candidate set to five.

A bounded pre-commit static exercise covered invariant retention and an existing-workflow fork-cache
case against canonical blobs that are byte-identical in `a5c425d`. `[verified]` The cache case loaded
only the security/provenance and execution/runner references, kept the bundled starter unloaded,
proposed a narrow project-owned-workflow change, and preserved the fork/secret boundary; runtime
effectiveness remains `[unverified]`. The invariant review found one contradiction: the broad
credential predicate made the entrypoint's reference-free missing-secret diagnosis unreachable. The
correction limits the route to credential/OIDC design or changes, and a focused reread passed. This
was static artifact evidence, not host activation or runtime behavior.

`[verified]` Independent review approved exact commit `a5c425d69eaf5211226db81e42ddc277496dfd62`
with no findings and zero independently found P0/P1s. The candidate passed the skill quick validator,
direct link/fleet/roadmap/stale-name validation, strict Claude plugin validation, 102 focused
link/adapter/fleet/canary tests (three skips), generator byte validation, and `git diff --check`. The
one required regeneration produced 144 supported Copilot adapter files; the retired
`plugins/save-toolkit` root remains absent. No scenario targets `ci-actions`, its description routing
content is unchanged, and no paid routing run was required or performed. Gate A remains the single
push-boundary check.

`[verified]` Remeasurement of exact implementation commit `a5c425d` leaves five candidates.
`pcf-deploy` is largest at 10,351 unconditional entrypoint bytes with no routed references, so it is
the next one-skill candidate after the fourth-slice pull request is green. Its dependent pull request
must target the fourth-slice branch until the stack is accepted.

`[verified]` PR #146 is open against `main` at final head
`a8bcefd8a38064181fdf946573edbf68c70ce226`; Linux validation, Windows validation, and the Claude
plugin contract are green and GitHub reports the branch clean. The owner explicitly authorized one
next isolated dependent branch, so `pcf-deploy` starts from that exact head and its pull request must
target the PR #146 branch.

**Prerequisites:** The Batch 1 routing contract is merged and closed. The `obs-logs` conditional
table is the existing pattern; `incident-command` is converted alone as the first reviewed Batch 2
pattern. Description edits follow the routing-content change playbook.

**Acceptance:** A dated remeasurement names the exact current candidates. Each confirmed candidate
either drops below 8,000 bytes or routes more reference bytes than it retains, and each carries a
conditional table whose targets are reachable through `check_links`; rerunning the recorded command
returns an empty set. Entrypoints retain all authority/safety invariants. Each changed description
passes the 600-byte and `Triggers:` contracts and has an after-change overlapping scenario run; a
previous-revision baseline is required only for an existing scenario that returns red. Gate A green.

**Next action:** Convert and independently review only `pcf-deploy` from exact PR #146 head
`a8bcefd`. After its exact revision is accepted, remeasure that head before selecting one sixth
candidate; do not assume the historical ordering. Do not rerun unchanged `incident-command` or
`ops-tooling` bytes; use an explicit 540-second timeout only if a future comparable
`incident-command` run is authorized. Keep the already-owed `eng-ladder` after-change run bounded to
its overlapping scenarios and separate from this slice.

### ROUTE-003 — remeasure workflow-graph and service-readiness discovery reliability

**Status:** `deferred` (2026-08-23)

**Owner:** `latent-sre`

**Outcome:** The two positive discovery routes left inconclusive by Batch 1 have reproducible,
model-labelled reliability evidence before either is promoted into a stronger routing claim.

**Source:** Batch 1 run `20260823T053852Z-1e677acb` timed out both workflow-graph trials. Closeout
run `20260823T131840Z-9e4c7fca` on merged commit `09e775b`, Claude Code 2.1.241,
`claude-sonnet-5`, two trials, and a 180-second timeout passed read-only service readiness 1/2 and
timed out the second trial. The exact dispositions are in the
[`skill clarity and routing audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md).

**Prerequisites:** A material routing, evaluator, host, or model change that can alter the result,
or explicit owner approval of a fixed no-tuning measurement budget. Use a clean exact plugin
revision and predeclare model, timeout, trials, threshold, and selected scenarios.

**Acceptance:** The workflow-graph and service-readiness cases each meet their declared threshold
on the exact candidate under the predeclared conditions, with no overlapping regression loss. A
failed or inconclusive batch remains evidence; it does not authorize prompt edits or retries without
a separately accepted fleet failure and candidate budget.

**Reopen trigger:** A material change to either route or its evaluator/runtime boundary, a named
model-migration question, or explicit owner approval for one fixed-budget reliability measurement.

**Next action:** None while deferred. Do not rerun unchanged bytes merely to turn timeouts green,
and do not move reference-dependent behavior graders into discovery.

### ROUTE-002 — resolve the `obs-logs` / `obs-alerting` trigger collision

**Status:** `active` (2026-08-20) — kept open: the "no other overlapping scenario moved" half of
acceptance is not yet evidenced.

**Outcome:** One skill owns log-based alert design **in the canonical text**, and the routing suite
contains a scenario that would fail if the other started firing for it. Both halves are required:
the descriptions must state the boundary, and a scenario must be able to detect a regression.

**Source:** [`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md).
`[sourced]` `obs-logs` advertises the trigger `'build a log alert'`
while `obs-alerting` claims Splunk saved-search alerts, and `obs-logs`'s ownership map disclaims
only `obs-metrics` and `obs-dashboards` — not `obs-alerting`. The pre-change 66-scenario suite
contained `discovery-obs-alerting-splunk-saved-search.yaml` expecting `obs-alerting` to fire, and
**no** scenario asserting `obs-logs` defers to it. The collision was therefore unmeasured rather
than known to be harmless.

**Current preparation (2026-08-18):** `discovery-obs-logs-defers-obs-alerting.yaml` now presents the
overlapping user phrase to `obs-logs` as a zero-tolerance near-miss and requires `obs-alerting` as the
alternative. The 67-scenario structural suite and all 345 grader checks pass. This makes the
collision measurable; no live routing result exists, and neither canonical description has changed.

**Prerequisites:** None structural. Verification needs the live runner.

**Acceptance:** Both, and neither alone. (1) The canonical text disambiguates: `obs-logs` no longer
advertises a trigger that `obs-alerting` owns, **or** its ownership map names `obs-alerting`
explicitly. (2) A `discovery-obs-logs-defers-obs-alerting` scenario exists and passes after the edit,
and the other overlapping scenarios remain green. A prior-revision baseline is needed only for a
scenario that is red.

A passing scenario on its own does **not** close this item. If the scenario already passes against
today's descriptions, that is evidence the collision is currently latent — not that it is resolved —
and closing on it would leave `obs-logs` still advertising `'build a log alert'` with the ownership
map still silent about `obs-alerting`.

**Measured evidence (2026-08-20).** The scenario ran for the first time, on branch
`fix/obs-skill-hardening` (PR [#122](https://github.com/latent-sre/save-toolkit/pull/122)); full
detail in [`the obs-skill hardening round packet`](reviews/2026-08-19-obs-skill-hardening-round.md).

- **The collision was real, not latent.** `discovery-obs-logs-defers-obs-alerting` at base
  `e31d04e06d3d` routed **1/2** — one trial kept log-based alert design inside `obs-logs` instead of
  deferring. After the ownership-map edit it routes **2/2** on `claude-opus-5[1m]` and **2/2** on
  `claude-sonnet-5`. This is the outcome this item warned might be ambiguous; it is not.
- **Acceptance half (1) is satisfied in canonical text:** `obs-logs`'s ownership map now names
  `obs-alerting` explicitly. The `'build a log alert'` trigger is retained deliberately — the
  disjunctive acceptance allows either remedy, and the trigger is how a user actually phrases the
  request.
- **Acceptance half (2) is partially evidenced.** The scenario exists and passes *routing*. Its
  former literal-grader failures were a separate contract defect, closed in `19aaa52`; they were not
  routing evidence and no longer block this item.
**Next action:** Establish the missing half of acceptance — run the *other* overlapping
`obs-alerting`/`obs-logs` scenarios against the changed descriptions and show they remain green. If
one is red, run that scenario at the prior revision to attribute it. Then close. Do not close on the
defer scenario alone.

### GRADER-002 — bind direct-skill trials to current slash-command expansion

**Status:** `ready` (2026-08-22).

**Outcome:** A direct-skill trial proves that the named skill contributed without requiring a legacy
`Skill` tool event, while an answer produced without the skill still fails closed.

**Source:** `[verified]` on Claude CLI 2.1.240 in runs `20260822T234553Z-3b860051` and
`20260822T235252Z-a9531e1a`. The runtime listed `save-toolkit:production-change-gate`, the slash
command produced version-specific skill behavior, and every trace still reported `skills=[]`.
Consequently both behaviorally approved candidate trials were marked FAIL only by `skill-fired`.
Reconfirmed on candidate `e51f9ec62cebc1883e1f9a6cfba3b716f5d2ab1b` in run
`20260823T005205Z-27dbcbfe`: both trials returned `APPROVED` and passed every response grader; only
the absent skill-completion event kept the aggregate red. *[verified]*
Review repair on Claude CLI 2.1.241 added the paired missing-authority case. An uncommitted
weakened-rule mutation (`plugin_inputs_dirty=true`) incorrectly returned `APPROVED` 2/2 in
`20260823T011640Z-4e6a6eaa`; restored candidate
`e6f6178d755501bd3aad1ddc40c92e4669ff18c1` returned `BLOCKED` 2/2 for that case in
`20260823T012204Z-1a382e31` and `APPROVED` 2/2 for the complete packet in
`20260823T012314Z-ec65c221`. Every response grader passed on the restored pair; only `skill-fired`
remained red because both traces still reported `skills=[]`. *[verified]*
Post-review hardening on candidate `3a1fe384485911b610326b4cb4ce6a635987bd0d` rejects a negated
specific binding, a BLOCKED verdict whose actual deficit is unrelated while the binding is present,
and each individually omitted required checklist acknowledgement (446/446 offline checks). Fresh
CLI 2.1.241 runs `20260823T021128Z-d180d56d` and `20260823T021249Z-28262e5d` returned
`APPROVED` 2/2 and `BLOCKED` 2/2 respectively; every response grader passed and only `skill-fired`
remained red because all four traces still reported `skills=[]`. *[verified]*
Plugin-input rereview hardening on candidate `3f06dcc05edf8fd69eb9c0556164498387698f07` also rejects
direct `does not establish` authority, double-negated missing evidence, and individually negated
checklist acknowledgements (466/466 offline checks). Run `20260823T023336Z-c0983823` exposed and
stopped on a Windows CP1252 diagnostic failure before completing; a red-first portability check now
keeps grader specs printable. Fresh runs `20260823T024010Z-4eaa212c` and
`20260823T024148Z-cfe1ecb5` returned `APPROVED` 2/2 and `BLOCKED` 2/2 respectively; every response
grader passed and only `skill-fired` remained red because all four traces reported `skills=[]`.
*[verified]*

**Prerequisites:** Identify a stable trace or invocation signal for slash-command expansion. Do not
infer contribution from answer prose alone.

**Acceptance:** Focused red-first fixtures cover the current expansion shape and the legacy tool-event
shape; the paired approved and missing-authority production-gate scenarios each pass 2/2; and the
existing inline-answer control remains red when no skill contributes.

**Next action:** Capture the smallest current trace around one direct slash command, then either grade
its expansion signal or make direct mode invoke the skill explicitly. Keep the response-text fallback
forbidden.

### DOCTOR-001 — make `fleet_doctor` diagnose the guard, not just the checkout

**Status:** `ready` (2026-08-14)

**Outcome:** A user whose Bash suddenly denies session-wide can run one command and learn why.
`scripts/fleet_doctor.py` reports whether the `PreToolUse` hook is registered in the installed
plugin, whether a Python on the hook's candidate list answers with the guard's `42`/`43` exit
codes, and whether the guard file resolves under `CLAUDE_PLUGIN_ROOT` — and it runs from an
installed plugin, not only from a repository checkout.

**Source:** Owner-requested usability review, 2026-08-13. `fleet_doctor` covers git revision,
worktree state, fleet contracts, plan status, host CLIs, and plugin inventory —
none of which is a failure mode users actually hit. The three that are load-bearing are unchecked:
the hook is the only mechanism that arms the guard (`scripts/readonly-guard.py` docstring), and
`scripts/readonly-guard-hook.sh` denies **all** Bash session-wide, main loop included, when no
interpreter answers 42/43. That is the blast radius of a missing Python or an unset
`CLAUDE_PLUGIN_ROOT`, and today it presents as "Bash mysteriously stopped working" with no
diagnostic. `REPO_ROOT = Path(__file__).resolve().parents[1]` plus imports of `validate_fleet` and
`check_plan_status` also make the tool checkout-only, so the marketplace user who most needs it
cannot run it.

**Prerequisites:** Preserve the existing evidence-envelope contract and the rule that a missing CLI
is `skip`, never `pass`. The interpreter probe must assert the exact 42/43 answer rather than exit
0 — accepting exit 0 is the stand-in-interpreter hole the exit codes exist to close, and a
diagnostic that repeats it would certify a disarmed guard as healthy. Repository-dependent checks
must degrade to `skip` outside a checkout instead of failing the run.

**Acceptance:** Red-first tests cover hook registered/absent, interpreter answering 42/43 versus
exit 0 versus absent, and guard file present/missing; the tool returns useful output with no
checkout present; the guard's own suite and Gate A pass; no new dependency (standard library only).

**Next action:** Add the interpreter-answer probe first — it is the single highest-value check and
needs no host inventory work.

### GCPOPS-001 — correct the stale guard sentence in `gcp-ops`

**Status:** `active` (2026-08-22) — the canonical correction and focused guard regression are
complete on the current candidate; the item leaves this file when that revision merges.

**Outcome:** `skills/gcp-ops/SKILL.md` stops telling agents that a quoted `severity>=ERROR` trips the
read-only guard, which stopped being true when PR #112 loosened the guard's proven-safe false
positives.

**Source:** PR #112. The branch originally corrected this sentence, but the edit was deferred because
the now-retired ROUTE-001 canary pinned the exact projected `gcp-ops` body. That evaluator dependency
no longer exists; its historical rationale remains in the accepted
[`retirement decision`](decisions/2026-08-11-codex-terra-routing.md).

**Interim mitigation (in place):** `skills/obs-logs/references/gcp-logging.md` carries the correct
behavior, probe-cited, and `gcp-ops` already routes Logging query-language detail to that reference
rather than owning it. The stale sentence is in the triage-flow skill; the query-construction skill
an agent is told to load is right.

**Verified 2026-08-22** against the current `scripts/readonly-guard.py` and focused corpus:
`gcloud logging read 'severity>=ERROR AND resource.type=cloud_run_revision' --freshness=1h` returns
exit 42 (allow), the same filter unquoted returns exit 43 (deny), and all 20 focused guard tests pass.

**Prerequisites:** Met. The quoted and unquoted cases are explicit focused-corpus fixtures.

**Acceptance:** `gcp-ops` states the guard's real behavior, the focused allow/deny corpus proves it,
generated projections match, and Gate A passes.

**Next action:** Merge the exact candidate; no provider evaluation is attached to this text
correction.

### SURFACE-001 — trim the user-facing surface (banner, retracted examples, shipped maintenance bytes)

**Status:** `ready` (2026-08-13; progress 2026-08-23) — remaining: the two example-footnote
compactions. The maintenance skills remain bundled by owner decision.

**Outcome:** A user who opens any canonical skill reaches actionable content within a few lines: the
shared evidence-default banner is gone, worked examples carry provenance as a single footnote instead
of a paragraph retracting the example, retired learning packet/ledger machinery no longer ships in
every install, and the packaging question for maintenance skills has a recorded decision.

**Source:** Owner-requested usability review, 2026-08-13 (evidence recorded inline here; measured
against this repository at the review session's checkout). Findings, each `[sourced]` to that
review: the identical 4-line evidence-default banner opens 29/29 `SKILL.md` files; first actionable
content starts at line 16–19 (mean 16.7), and `skills/service-onboarding/SKILL.md` stacks two
banners so content starts at line 25 of 72; provenance boilerplate totals ~249 lines (8.2% of the
SKILL.md corpus) with 155 `[unverified]` markers across bundles; two worked examples retract
themselves (`skills/pcf-deploy/SKILL.md` manifest-name interaction; `skills/runbook/SKILL.md`
example footer); `skills/operational-learning/` is 3,714 lines — 27% of toolkit bytes — including
three schema versions, two migration scripts, and a drift watcher, and `skills/agent-authoring/` is
1,678 lines, both shipped to every end user.

**Prerequisites:** None blocking. The banner work is done. By owner decision, the maintenance skills
stay in the shared package: no current measurement shows that their install size or discovery surface
harms a named consumer. Reopen that packaging decision only with measured consumer impact attributable
to those bundles.

**Acceptance:** No shared evidence-default banner remains and adapters regenerate byte-clean; the
two self-retracting examples keep their labels as one-line footnotes; the retired learning packet
and ledger paths remain absent; Gate A passes; operational closeout still produces evidence-bound
documentation dispositions and owners without execution authority.

**Next action:** Compact the provenance paragraphs in the `pcf-deploy` and `runbook` worked examples
to one-line footnotes. Keep the maintenance skills together unless the measured-impact reopen trigger
fires.

## Deferred

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`

**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.

**Source:** Fleet authority reviews that reject prose approval and require an explicit unknown-outcome
state for externally dispatched effects.

**Prerequisites:** A named workflow approved to cross the current prepare/recommend boundary, a
separately controlled execution identity, and live `main` ruleset enforcement as recorded in
[`docs/reviews/2026-08-05-protect-001-closure.md`](reviews/2026-08-05-protect-001-closure.md).

**Acceptance:** Effect-bound approval, dispatch, unknown-outcome reconciliation, replay prevention,
expiry, rollback, and operator-resolution tests pass for the named effect target.

**Reopen trigger:** A named workflow is approved to move beyond the fleet's current prepare/recommend
boundary and has a separately controlled execution identity.

**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority.
