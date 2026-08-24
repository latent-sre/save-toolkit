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
| `GCPOPS-001` | 2026-08-22 | Canonical `gcp-ops` now states that a quoted `severity>=ERROR` filter is guard-safe while the unquoted shell-redirection spelling is denied, and the focused guard corpus locks both outcomes. Correction commit `c989103`, final PR head `f5235c1`, merged in PR [#137](https://github.com/latent-sre/save-toolkit/pull/137) at `e96e741` |
| `RELEASE-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. The custom publication workflow, request/workflow contracts, release-specific tests, runbook, and the standalone four-host probe were never activated and had no named consumer; they were retired rather than maintained. The `release-gate` skill, manifest versions, and changelog history remain. Historical design ADR: [`superseded`](decisions/2026-08-11-immutable-release-promotion.md). Reopen only when a named consumer requires an immutable selector and rollback-capable release |
| `STATE-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. It described a future durable-execution control plane with no named workflow, implementation, or active dependency; handoffs and learning derive ownership and completion from Git, pull requests, tests/evals, and evidence. Reopen only when a named workflow must survive process or session loss and replay from version-bound artifacts would be unsafe or materially costly |
| `EVAL-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. Its only named trigger was a release decision, the parked suite no longer matches the current plugin identity or roster, and Codex stopped being a distribution target — no fleet component runs on Sol, so the trigger can no longer fire. Tag `pre-trim-2026-08-02` preserves the historical bytes — [ADR](decisions/2026-08-23-retire-codex-distribution-target.md) |
| `AUDIT-002` (Batch 1) | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. Implementation and review corrections merged in PR [#141](https://github.com/latent-sre/save-toolkit/pull/141) at merge commit `09e775b`, final head `11b8041`. Batch 1 selected no graph runtime, added no unconsumed schema, and activated no SRE capability addition; two positive-route reliability gaps moved to deferred `ROUTE-003` rather than triggering retries against unchanged bytes. Evidence: [`2026-08-22 skill clarity, routing, prompt, loop, and graph audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) |
| `DOCTOR-001` | 2026-08-23 | Installed-layout `fleet_doctor` now separates checkout and plugin evidence, validates each payload's first authenticated guard answer and independently trusted launcher bytes, and degrades repository-only checks outside a checkout. Final head `505f9b5`, merged in PR [#152](https://github.com/latent-sre/save-toolkit/pull/152) at `e76d38b` |
| `GRADER-002` | 2026-08-24 | Direct-skill trials explicitly request the exact `Skill` invocation and still require its completed tool result; availability-only metadata and inline answers fail closed. Implementation commit `ec6e583`, paired approved/missing-authority evidence matched the committed evaluator digest, merged in PR [#155](https://github.com/latent-sre/save-toolkit/pull/155) at `24e62b0` |

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

**Status:** `blocked` (2026-08-24) — the current Windows host has VS Code and extensions, but its
installed set contains neither `github.copilot` nor `github.copilot-chat`; no approved authenticated
GitHub Copilot tools surface is available to observe. No profile installation or mutation was
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

**Current environment:** `[verified]` On 2026-08-24, `code --version` reported VS Code 1.134.0,
commit `110a328ea54b42367b803ec53ee0bf52ef26b419`, x64. The installed extension list contains
development, operations, Claude, and OpenAI tooling, but neither GitHub Copilot extension named
above. This establishes only that the approved probe cannot start here, not any tool-enforcement
behavior.

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

**Status:** `active` (2026-08-24) — all nine Phase 1 router slices are merged: `incident-command` in
PR #142, `ops-tooling` in #143, `agent-security` in #145, `ci-actions` in #146, `pcf-deploy` in #147,
`pcf-ops` in #149, `production-change-gate` in #150, `database-reliability` in #151, and
`stack-profile` in #154. The owner authorized a Phase 2 immutable-byte screen at 5,000 bytes while
excluding those completed nine; Phase 1 is evidence, not a candidate pool to rerun.

**Outcome:** No skill spends a caller's context on detail the call did not need. Each screened
entrypoint receives one evidence/recommendation checkpoint. A confirmed conditional body becomes a
router with an “if the question involves X, read Y” table while retaining its authority and safety
invariants; a cohesive body is retained explicitly rather than split to satisfy a byte target.

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

The [`2026-08-24 host context-budget audit`](reviews/2026-08-24-host-context-budget-audit.md)
separates the host contracts that prompted Phase 2. Claude's default 8,000-character value budgets
the aggregate discovery listing on a 200k context; its 5,000-token-per-skill and 25,000-token-total
values govern post-compaction invoked content. Copilot's 30,000-character value applies to one
generated custom-agent prompt, not to a skill. None is the repository's 5,000-byte screen, and moving
body detail into references does not reduce discovery metadata unless a description changes.

`[verified]` The owner-approved Phase 2 remeasurement on exact current-main base
`b9b274f237caf8ce6068812e151f8543f608c7e7` finds 12 non-Phase-1 entrypoints at or above 5,000
immutable bytes, totaling 95,068 bytes: `frontend-craft` 13,827; `backend-craft` 10,814;
`obs-dashboards` 10,724; `agent-authoring` 9,420; `obs-alerting` 7,656; `runbook` 7,385; `gcp-ops`
7,384; `operational-learning` 6,078; `eng-ladder` 5,873; `obs-pipeline` 5,835; `root-cause` 5,048;
and `obs-traces` 5,024. The audit records reference-byte totals and the initial recommendation for
each. Selection means inspect, not rewrite; size alone is not a finding.

`[verified]` The same base carries 28 model-invocable skills whose names, descriptions, and line
separators total 13,239 characters in the fleet's Claude namespace, 5,239 above the installed
CLI 2.1.241 default fallback. No individual description reaches 1,536 characters and every
entrypoint is below 500 lines. The exact real-session truncation remains `[unverified]` because
bundled skills, usage priority, model context, and user overrides share that budget. This discovery
risk is measured separately and does not authorize a description rewrite inside Phase 2.

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

`[verified]` Remeasurement of exact implementation commit `a5c425d` left five candidates and selected
`pcf-deploy`, then the largest at 10,351 unconditional entrypoint bytes with no routed references,
for the fifth one-skill slice.

`[verified]` PR #147 merged exact head `1034bc9a0807974293c667eb2938e2cbbb63acc7` into the PR #146
branch as `f6eeb59e741a859bbdc9cc42c900fe2e9f297c92` on 2026-08-23. PR #146 then merged that exact final
head into `main` as `829af56032ab921fdde208ae7c57f4ae329c9293`. Linux validation, Windows
validation, and the Claude plugin contract passed on `f6eeb59`; both reviewed implementation commits
are ancestors of the resulting `main`.

`[verified]` Fifth bounded implementation commit
`af9cb4bf7ba2a04a557160b975dd1b22913ae7bc` converts only `pcf-deploy`. Its byte-identical
frontmatter, including the manual-only controls, now opens a 7,854-byte entrypoint that keeps
agent-never-executes authority, release/change gate stop, exact artifact/target/approved-manifest
identity and diff, action-boundary revalidation, secret and human-only `cf env` rules, rollback
non-reversibility, owner maps, common strategy choices, target uncertainty, abort criteria, and the
evidence handoff. Three explicit references total 8,959 bytes across manifest/blue-green,
rolling/canary/revisions, and configuration/scaling; the starter manifest is available only when a
new manifest is required and no project-owned manifest or starter exists. The 30-entrypoint corpus
falls to 205,028 bytes and the mechanical candidate set to four.

A bounded pre-commit static exercise covered invariant retention and a valid-gate blue-green plan
with an existing project manifest. `[verified]` The plan loaded only the manifest/blue-green
reference, kept the starter asset and unrelated procedures unloaded, remained human-run, and named
phase-specific rollback; target behavior remains `[unverified]`. The invariant review found two
production-safety ambiguities: approval did not bind immutable manifest identity, and an instruction
asked for rollback commands even at irreversible boundaries. One correction binds the approved
manifest revision/hash and diff through action-time revalidation and requires rollback, recovery,
compensation, or an explicit irreversible declaration. A focused reread passed both corrections.

`[verified]` Independent review approved exact commit `af9cb4bf7ba2a04a557160b975dd1b22913ae7bc`
with no findings and zero independently found P0/P1s. The candidate passed direct
link/fleet/roadmap/stale-name validation, strict Claude plugin validation, 102 focused
link/adapter/fleet/canary tests (three skips), generator byte validation, and `git diff --check`. The
one required regeneration produced 147 supported Copilot adapter files. The generic Codex
skill-creator quick validator is not applicable to this existing manual Claude skill: after an
introduced incompatible prose character was removed, it still rejected the pre-existing,
repository-required `compatibility` and `disable-model-invocation` keys. The repository validators
and strict Claude plugin validation are the governing contracts.

Two scenarios target `pcf-deploy`: a negative discovery regression and a direct behavioral
calibration. Its description and manual-only routing metadata are byte-identical, so neither is an
affected routing scenario; no paid routing run was required or performed. Host activation,
final-response quality, and deployment runtime behavior remain `[unverified]`. Gate A remains the
single push-boundary check.

`[verified]` Post-merge remeasurement of exact current-main commit `829af56` leaves four candidates.
`pcf-ops` is largest at 10,173 unconditional entrypoint bytes with 1,543 routed reference bytes. It
is not started automatically; current-main inspection and an owner-accepted one-skill scope come
before any edit.

`[verified]` After PRs #149–#153 merged, the required remeasurement of exact current-main commit
`2294832ab0d4edc1199766530f4bea37367db197` found 30 canonical entrypoints totaling 195,009
immutable Git-object bytes. `stack-profile` was the sole remaining skill meeting this item's
criterion: an 8,673-byte entrypoint and zero reference bytes. The three newly merged routers no
longer met it, and no historical candidate ordering was reused.

`[verified]` Exact post-review implementation commit
`1cdecbd2a25b4fa2578e217f48e901169b43025d` converts only `stack-profile`. Its 425-character
description retains every trigger, use condition, and named alternative while replacing the false
single-file maintenance promise with the canonical skill-bundle boundary. It opens a 6,412-byte
entrypoint that keeps the current PCF/GCP runtime truth, pending landing-runtime decision,
no-self-managed-Kubernetes rule, three-state evidence contract, additive/no-retirement observability
decision, incident/change/documentation ownership, stay-in-lane and platform boundaries, and the
default-inherit/generation-alias/full-model-ID rules accepted in PR #153. Three explicit references
total 5,421 bytes across observability inventory and lifecycle, application/CI/runner/data-store
facts, and the current Copilot picker order. The 30-entrypoint corpus falls to 192,748 bytes and the
mechanical candidate set is empty.

A fixed five-agent fresh-context artifact exercise covered the shared runtime boundary, each of the
three conditional lanes, and a two-lane combined request. `[verified]` Every case read exactly the
matching reference set: zero for the runtime-only question, one each for observability,
application/data, and Copilot models, and observability plus application/data for the combined case.
The combined case initially invented an unsupported `[inference]` evidence state; one correction
made the entrypoint explicitly retain the fleet's three-state contract, and the same fifth agent's
focused retest used `[unverified]` for the inference with no routing or conclusion regression. These
are static fresh-context artifact results, not host activation or runtime-behavior evidence.

One independent read-only review of the pre-fix exact candidate found a P1 behavior-preservation
gap: the advertised broad `"what's our stack"` request matched no conditional row and could load
zero references. The current-main conformance pass also found the superseded blanket model-pin rule,
the false single-file promise, and an observability reference that claimed its missing parent owned
the additive-stack rule. `[verified]` The correction adds an explicit broad row, reconciles the
accepted alias-versus-full-ID policy, names the canonical bundle/projection boundary, and returns the
additive/no-retirement decision to the entrypoint. Two clean-context regressions then showed the
literal broad request loading all three and omitting no requested stack category, and the model case
permitting a cost/latency-justified `sonnet` alias while rejecting a full ID and refusing to treat the
Copilot picker order as Claude-agent authorization. No automated review loop was started.

A subsequent PR review of exact published head `8f2b62c` found two remaining context-selection gaps:
a narrow edge/CDN/WAF/RUM request and a general CI-platform/tooling request could omit the reference
that owns the requested inventory, and the setup instructions still pointed only to the entrypoint.
`[verified]` Fix commit `3a056e5d44c7b66d00ec8f0673a4b731d606a301` adds those predicates to
the router and matching reference lead-ins and points setup at the canonical skill bundle. The
description remains byte-identical. Direct link/fleet/roadmap/stale-name validation, 115 focused
link/adapter/fleet/frontmatter/canary tests (three skips), strict Claude plugin validation, and
`git diff --check` passed after the one required regeneration. Model-selected reference loading for
the two new narrow requests remains `[unverified]`; no discovery scenario targets this internal
reference-selection boundary, so no paid routing run was added.

`[verified]` The exact candidate passed direct link/fleet/roadmap/stale-name validation, read-only
adapter verification, 115 focused link/adapter/fleet/frontmatter/canary tests (three skips), strict
Claude plugin validation, and `git diff --check`. The review-fix canonical pass regenerated 158
adapter files with byte consistency. The existing `discovery-runtime-boundary` scenario targets
`stack-profile`, but its description's routing elements are unchanged; only the inaccurate
maintenance sentence changed. No affected routing scenario or paid live run was required or
performed. Gate A remains the single push-boundary check.

**Prerequisites:** The Batch 1 routing contract is merged and closed. The `obs-logs` conditional
table is the existing pattern; `incident-command` is converted alone as the first reviewed Batch 2
pattern. Description edits follow the routing-content change playbook.

**Acceptance:** The exact-base remeasurement names every non-excluded entrypoint at or above 5,000
immutable bytes. Each receives one committed disposition: a confirmed router either drops below the
screen or routes more reference bytes than it retains, with every target reachable through
`check_links`; a retained entrypoint records why no clean conditional boundary exists. Rerunning the
recorded measurement returns no **undispositioned** candidate. Entrypoints retain all authority and
safety invariants. Each changed description passes the 600-byte and `Triggers:` contracts and has an
after-change overlapping scenario run; a previous-revision baseline is required only for an existing
scenario that returns red. Gate A green.

**Next action:** Inspect `frontend-craft` alone on the exact Phase 2 base because it is the largest
selected entrypoint and already owns substantial routable reference depth. Present its retained
invariants, proposed conditional boundaries, expected byte movement, and recommendation before
changing its bytes. Do not start a second skill, requeue a completed Phase 1 skill, rewrite discovery
descriptions, or combine the already-owed `eng-ladder` after-change run with this checkpoint.

### SKILLS-003 — add a portable executable workflow-graph engineering skill

**Status:** `ready` (2026-08-24) — roadmap activation merged in PR
[#157](https://github.com/latent-sre/save-toolkit/pull/157) at `a8f98ce`. Renewed owner direction
activates only the executable workflow/state-graph capability from Batch 3. The proposed SRE
capability additions remain held; this item selects no graph runtime, creates no execution service,
and does not activate `codebase-atlas`.

**Owner:** `prompt-engineer` owns the canonical design method and its routing/evaluation contract.
`sde` owns any later implementation in team-authored code, but this item grants no implementation,
deployment, or live-effect authority. Human acceptance of the exact pull-request revision remains
with `latent-sre`.

**Outcome:** A user asking to design or review an executable workflow/state graph can invoke one
runtime-neutral `workflow-graph-engineering` skill and receive a portable, evidence-labelled design
contract. The result names its data, nodes, edges, concurrency, failure recovery, human-control,
lifecycle, authority, observability, and evaluation semantics without implying that a checkpoint
makes an external effect exactly once or that a graph-shaped design requires a particular runtime.

**Concrete consumer:** The immediate consumer is `prompt-engineer` when a team-approved request
needs an executable workflow/state-graph design or a review of one. Its output is a human-reviewed
engineering artifact that can later become a pinned handoff to `sde`. There is no machine consumer
in this slice, so it adds no JSON Schema or validator. A later proposal may add those only after it
names the exact producer, consumer, compatibility policy, and safety-critical predicate the
validator enforces.

**Source:** The
[`2026-08-22 skill clarity, routing, prompt, loop, and graph audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md)
separated graph engineering into three contracts: the existing roster/delegation graph, the missing
executable workflow/state graph, and a separate code/dependency/knowledge graph capability. Its
Batch 3 hold required renewed owner direction plus a concrete consumer and authority boundary. The
[`2026-08-23 research refresh`](reviews/2026-08-23-prompt-loop-graph-engineering-research.md)
compared current framework contracts and pinned upstream source/tests, found that no inspected
runtime supplied the entire portable contract, and recommended a runtime-neutral reference before
runtime or schema selection. Owner direction on 2026-08-24 supplies the activation decision: use
the repository's agent/skill framework, keep SRE additions deferred, and do not add a universal
runtime.

**Required discipline taxonomy audit:** Before changing a canonical agent, skill, description, or
scenario, derive the working taxonomy from the exact current `agents/` and `skills/` sources rather
than from this roadmap, a dated review, an installed projection, or model memory. Record a compact
table in the pull-request evidence with each discipline's canonical name, owner, authoritative
path, inputs, output/return contract, state and authority boundary, verifier, neighboring owner, and
any overlap or contradiction. At minimum audit these six user-facing terms:

| User-facing discipline | Current canonical owner and boundary to verify |
|---|---|
| Prompt engineering | `prompt-engineer` plus the artifact tier of `agent-authoring`: routing metadata, instructions, human-facing output shape, tool/grader descriptions, and evidence-matched minimal prompt changes; schemas, runtime controls, and evaluator defects remain with their actual owning layer |
| Context engineering | `agent-authoring/references/context.md`: what is selected, ordered, trusted, refreshed, compacted, retained, preloaded, or retrieved just in time; context isolation is not tool, filesystem, credential, or authority isolation |
| Handoff engineering | `agent-authoring/references/roster.md` plus the packet convention in canonical agent bodies: the final message is a stateless receiver's interface, with one owner, exact change/state, evidence labels and taint preserved, success criteria, open unknowns, and explicit non-actions |
| Loop engineering | `agent-authoring`, `references/artifact.md`, and `references/roster.md`: entry and mutable state, one verifier, hard iteration/time/cost/tool budgets, success/no-progress/safety termination, durable evidence, and human promotion authority |
| Graph engineering | `agent-authoring/references/delegation-graph.md` owns the roster/delegation capability graph; `SKILLS-003` adds the distinct portable executable workflow/state-graph method; neither is a source-code/knowledge graph or proof of runtime enforcement |
| Self-learning | Treat this requested term as a taxonomy question, not an authorization. Current canonical sources call the durable fleet discipline **learning engineering**, while `operational-learning` owns evidence-bound operational dispositions. Verify that mapping, preserve any disagreement explicitly, and do not introduce autonomous self-modification, background memory promotion, or an unbounded optimizer |

The audit starts with canonical bytes at the implementation base. Generated projections may confirm
host rendering but never establish ownership. Dated research may explain a current contract only
after the canonical source is identified. If two current canonical sources disagree, retain the
disagreement as a finding and repair it only when it is directly necessary for this one-skill
contract; do not silently synthesize a seventh discipline or broaden an owner.

**Cross-discipline implementation rules:**

- **Apply Prompt Engineering.** Make the smallest candidate change. Prefer positive output shapes
  and predicate-keyed instructions. When a new ordering or precedence rule loses to an earlier
  sentence in the same artifact, do not append another lower-priority rule: reword the incumbent
  claim already occupying that semantic position, then measure the residual behavior. Diagnose the
  first failing layer before changing prose, and keep one candidate unless the owner explicitly
  approves a larger fixed budget.
- **Apply Context Engineering.** Keep universal mandate, authority, safety, common decision rules,
  and the minimum usable output contract in the always-loaded body. Put conditional depth behind
  explicit reachable predicates, remove actual duplication instead of merely relocating it, and do
  not force an agent to fetch multiple references before it can safely begin. Account separately
  for canonical authored context, host-preloaded context, generated projection context, and
  host-specific additions or omissions; identical text in two of those surfaces is not automatically
  two independent sources of truth.
- **Apply Handoff Engineering.** Any contract moved behind a reference or across a node/agent edge
  remains sufficient for a receiver with no inherited conversation. Its packet names intent,
  exact inputs/state or revision, allowed scope, source trust and taint, success criteria, return
  shape, open unknowns, one next owner, and what was not done. No sender or receiver upgrades an
  evidence label or treats packet prose as authority.
- **Apply Loop Engineering.** Freeze the success cases and verifier before editing, retain one
  writer and one candidate by default, and predeclare iteration, elapsed-time, call/cost, and tool
  budgets. Stop on success, no progress, inconclusive evidence, budget exhaustion, safety or
  authority regression, or owner interruption. Only human acceptance of the exact revision
  promotes it; a loop never promotes itself.
- **Apply Graph Engineering.** Maintain one writer in the isolated implementation worktree.
  Preserve declared tool authority, approval edges, handoff ownership, terminal lanes, and
  host-specific controls while changing graph-facing text. Compare the capability graph, portable
  workflow contract, generated host render, and actual runtime evidence as separate artifacts; do
  not report capability-graph or workflow-contract output as runtime enforcement.
- **Apply learning engineering to every discovery.** For this implementation audit, disposition
  each discovery as `worked` (necessary and resolved in this one-skill scope), `already owned`
  (the current roadmap or canonical component already owns it), `proposed to roadmap` (material,
  unowned, and intentionally deferred for operator selection), or `dropped with reason`
  (unsupported, duplicate, immaterial, or outside the accepted boundary). These working
  dispositions do not replace `operational-learning`'s canonical `prepared`, `proposed`, `blocked`,
  `duplicate`, and `not_applicable` states when the discovery is operational knowledge. Check the
  live roadmap for an existing owner before proposing anything new, do not implement unrelated
  audit findings in this branch, and return evidence-bound proposals for later operator selection.

**Capability boundaries:**

- The existing **roster/delegation graph** remains in `agent-authoring` and
  `agent-authoring/references/delegation-graph.md`. This item may sharpen the neighboring routing
  boundary but does not duplicate or relocate that method.
- **Executable workflow/state graph design** belongs to the new
  `workflow-graph-engineering` skill. It defines portable contracts and reviews designs; it does
  not execute a graph, select infrastructure, or write application code.
- **Code, import, dependency, knowledge, runtime-topology, and GraphRAG graphs** remain a separate
  possible `codebase-atlas` capability with different inputs, provenance, and success criteria.
  This item does not activate it.
- Prompt Engineering owns LLM-facing instructions and semantic behavior; Context Engineering owns
  selection, ordering, provenance, freshness, trust, compaction, and retention; Loop Engineering
  owns bounded gather/action/verify/repeat control and promotion authority. Workflow Graph
  Engineering composes their contracts but does not collapse those evidence lanes into one score.
- SRE concerns below are design requirements for an operable graph, not authorization for a new
  SRE agent, skill, runtime, deployment, credential, or production-change lane.

**Required portable design contract:**

| Concern | Required output |
|---|---|
| Identity and boundary | Graph ID/version, purpose, owner, caller, trust boundary, start condition, and exact agent, prompt, tool, schema, configuration, grader, model, and runtime identities/revisions when they exist; an unavailable identity stays explicit, while a supplied identity is never omitted |
| Typed data | Input, internal state, context, node input/output, edge payload, reducer state, checkpoint, and final-output contracts; unresolved types remain explicit rather than inferred |
| Nodes | Deterministic compute, model call, tool/effect, approval, reducer/join, verifier, and terminal classes with preconditions, authority, timeout, retry owner, and success/failure results |
| Edges | Deterministic, conditional, model-selected handoff, fan-out, fan-in, interrupt, retry, compensation, and terminal edges; every model-selected edge names its allowed destination set and deterministic guardrails |
| Concurrency and joins | Writer cardinality, reducer identity and algebra, ordering guarantees, conflict handling, join quorum, partial-worker failure, late-result policy, and fan-out budget |
| Scheduling and admission | Queue ownership and capacity, priority and fairness, tenant quota, concurrency cap, backpressure and load-shed behavior, worker lease/heartbeat/liveness, stale-worker handling, poison-work quarantine/manual repair, and the evidence required to admit work |
| Failure and retry | Failure classes, one retry owner, attempt/time budget, backoff, replay-safety classification, authority for an unsafe replay, timeout ownership, and fail-closed handling of missing or inconclusive evidence |
| Replay and compatibility | Recovery model that distinguishes checkpoint resume from deterministic event-history replay, code/build version, history and state-schema compatibility boundary, replay or shadow verification, fork semantics, migration, and repair policy |
| Durability | Run/thread/checkpoint identity, state and checkpoint schema version, durability mode, checkpoint boundary, last known recovery point, resume semantics, retention, restore, and evidence of persisted state |
| External effects | Deterministic caller/operation/target/tenant/payload-bound idempotency-key construction, attempt identity, mismatched-intent rejection, result/tombstone retention, effect journal or receipt, atomic receipt/mutation coupling when the target supports it, read-after-write reconciliation, explicit `UNKNOWN`, safe compensation limits, and a prohibition on automatic replay while outcome is unknown |
| Human control | Approval immediately before the effect path, bound to approver identity, exact action and target, immutable candidate/config identity, expiry, rejection, timeout, and resumed state |
| Lifecycle and cancellation | Pause/resume, cooperative-cancel signal and safe observation point, durable-cancel persistence and new-dispatch prevention, in-flight effect handling, late-worker/result quarantine, supersession, restart behavior, replay/fork relationship, and cleanup deadline |
| Termination | Success, no-progress, maximum turns/iterations/time/tokens/cost, cancellation, safety stop, unreachable-exit detection, and terminal evidence requirements |
| Security and context | Actor and credential scope, least authority per node, untrusted-input treatment, provenance/freshness, taint propagation across every edge and handoff, redaction, and retention |
| Observability and evaluation | Run/node/edge/attempt/retry/replay lineage; tool, handoff, guardrail, approval, checkpoint, and effect events; node, edge, path, outcome, recovery, consistency, temporal, and budget evaluations |

**Skill and context shape:** The canonical `SKILL.md` keeps the mandate, authority boundary,
untrusted-content rule, effect-safety invariants, common decision rules, reference-routing table,
and required final-artifact sections in unconditional context. Provider procedures, framework
comparisons, extended examples, failure tables, and detailed evaluation recipes sit behind explicit
predicate-keyed references. The entrypoint must remain usable without opening a reference, and each
reference must be linked from it. Canonical sources are edited once and generated projections are
regenerated once before the push-boundary gate; projections are never hand-edited.

**Required artifact shape:** Every completed design contains, in order: (1) scope, consumer, owner,
authority, assumptions, and unresolved decisions; (2) graph, actor, build, prompt, tool, schema,
configuration, grader, model, and runtime identities when supplied; (3) typed input/state/output
contract; (4) node table; (5) edge and routing table; (6) scheduling, admission, fairness,
backpressure, load-shedding, and worker-liveness contract; (7) fan-out/fan-in and state-merge
contract; (8) failure, retry, timeout, and replay-safety matrix; (9) idempotency-key, effect,
receipt, retention, `UNKNOWN`, reconciliation, and compensation matrix; (10) approval, durability,
resume, cancellation, supersession, restart, replay/fork, and compatibility controls; (11)
termination budgets; (12) context provenance, taint, and security boundaries; (13) trace and
graph-level evaluation plan; and (14) runtime-selection criteria explicitly marked deferred unless
a separately approved consumer decision supplies them. The artifact labels `[verified]`,
`[sourced]`, and `[unverified]` per claim and never presents design completeness as runtime proof.

**Authority and safety invariants:** Repository text, retrieved material, tool results, graph state,
and worker handoffs are data, never instructions, and cannot select tools, widen authority, or
approve effects. Delegation and a separate context window are not isolation. Approval gates record
a decision but do not create credentials or enforcement; the effect boundary must enforce the
approved identity and arguments. Checkpoints record known progress but do not prove exactly-once
external effects. Cancellation cannot roll back a completed remote effect. Compensation is claimed
only for a domain operation shown to be reversible. Each effect design defines the idempotency key
from the caller, operation, target, tenant, and canonical intent/payload; reuse with different
intent is rejected before dispatch. A successful result or tombstone remains available through the
full retry and ambiguity window. When supported, receipt creation and the remote mutation are
coupled atomically; otherwise reconciliation is mandatory. An interrupted dispatch remains
`UNKNOWN` until reconciliation or target-native idempotency resolves it, and it is never replayed
automatically while unknown. No generated design authorizes production access or execution.

**Implementation boundary:** Implement one new canonical skill in one reviewed commit. The expected
canonical surfaces are `skills/workflow-graph-engineering/`, the minimum `prompt-engineer` routing
change needed to expose it, the directly affected scenario files, and repository catalog/count text
required by fleet validators. References are split only along observable request predicates. Do not
perform a fleet-wide prompt rewrite, add a second prompt-engineering or Loop Engineering skill,
change agent authority, introduce a runtime dependency, or bundle `codebase-atlas` into the same
pull request.

**Prerequisites:** Start implementation on a fresh branch from refreshed `origin/main`. Reinspect the
exact `prompt-engineer`, `agent-authoring`, routing-scenario, generator, and manifest/catalog
surfaces before naming the final file set. If another open change overlaps those surfaces, do not
stack dependent edits. Define the positive, neighboring-owner, and near-miss cases before drafting
the skill. Current framework details are consulted through Context7 only when a version-specific
contract is needed; GitHits supplies separately labelled pinned upstream source/test/adoption
evidence. Existing dated research is a source, not permission to resume any other checklist.

**Acceptance:** All of the following are required:

1. **Discipline taxonomy:** Pull-request evidence derives all six requested disciplines from the
   exact canonical implementation base, records the owner/boundary table and any disagreements, and
   accounts separately for canonical, preloaded, generated, and host-specific context. Every audit
   discovery has one of the four implementation dispositions above and any proposal demonstrates
   that the live roadmap has no existing owner. No unrelated finding is implemented in the branch.
2. **Routing separation:** A positive request for portable executable workflow/state-graph design
   reaches `workflow-graph-engineering`; a roster/delegation-graph request remains with
   `agent-authoring`; a repository dependency/knowledge/GraphRAG request does not route to the new
   skill; a request to implement a concrete runtime remains with `sde`; and runtime selection needs
   a separate owner decision under `stack-profile`. Only scenarios affected by changed routing
   content are run.
3. **Artifact behavior:** One fixed five-agent fresh-context exercise uses exactly one trial for each
   predeclared case: a deterministic graph with queue admission, fairness, backpressure,
   load-shedding, and worker liveness; a model-selected handoff with authority and taint;
   fan-out/fan-in with partial failure; an approval-gated external effect with semantic idempotency,
   mismatched-intent rejection, retention, `UNKNOWN`, and reconciliation; and a durable cyclic graph
   that distinguishes checkpoint resume from deterministic event-history replay and cooperative
   from durable cancellation while covering in-flight/late workers, supersession, explicit budgets,
   tracing, and graph-level evals. Before any call, the exercise records the exact candidate full
   SHA and clean tree, canonical/plugin input digest, host and CLI version, runtime and model
   identity, effective tool permissions, the five immutable prompts, grader identities and
   thresholds, per-call timeout, and maximum call/cost budget. Raw prompts, outputs, grader results,
   timing, errors, and spend evidence are retained. Changing a case, grader, threshold, or candidate
   creates a new candidate that requires owner approval rather than silently extending this pass.
   Each result satisfies the required artifact shape without choosing a runtime or claiming
   execution evidence. This is one bounded candidate/evaluation pass, not an optimizer loop.
4. **Safety controls:** Focused checks reject automatic replay of an unknown effect; acceptance of a
   reused idempotency key with mismatched intent; result/tombstone retention shorter than the retry
   or ambiguity window; approval not bound to the exact action/state; admission without declared
   queue capacity, fairness, backpressure/load-shed, and worker-liveness behavior; cancellation that
   omits cooperative versus durable semantics or in-flight/late-worker disposition; checkpoint
   resume presented as deterministic event-history replay; unbounded cycles; missing terminal
   states; taint dropped at a handoff; and checkpoint-equals-exactly-once claims. If a deterministic
   validator or other machine contract is introduced despite the current boundary, its exact
   consumer must be named and one focused red-to-green regression must prove each new enforced
   predicate.
5. **Evidence separation:** Activation/routing, artifact/output quality, and runtime behavior are
   reported independently. Runtime execution, durability, provider behavior, effect safety, and
   production readiness remain `[unverified]` unless separately exercised on an approved exact
   implementation; a strong static design never upgrades that lane.
6. **Repository integrity:** Every reference is reachable, scenario parsing and affected offline
   graders pass, the exact changed-description scenario set is recorded, projections regenerate
   byte-clean once, strict plugin validation passes, and Gate A passes once at the push boundary.
   The pull request receives one independent exact-revision correctness/security and roadmap-plan
   conformance review; no automated review loop is started.

**Closure:** Merge the accepted exact revision, record its focused structural, routing, artifact,
and review evidence without conflating their claims, then move `SKILLS-003` to the closed table. A
runtime, schema, executable validator, `codebase-atlas`, or SRE capability remains separate future
work and does not keep this skill-capability item open.

**Next action:** From refreshed `origin/main`, inventory the exact owning surfaces, freeze the
routing matrix and five bounded artifact cases, and implement only `workflow-graph-engineering` as
the first reviewed Batch 3 slice.

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
