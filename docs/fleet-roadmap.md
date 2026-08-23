# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred work for the
> current fleet. Historical plans, reviews, audits, and decision records provide evidence and
> rationale; they do not independently add work to this queue.

The accepted architecture is
[`2026-07-31-multi-platform-plugin-packaging.md`](decisions/2026-07-31-multi-platform-plugin-packaging.md):
one canonical Claude plugin under `agents/`, `skills/`, and `commands/`, with generated host-native
adapters for Copilot/VS Code and Codex.

Closed work is retained in the
[`SAFE-001 closure`](reviews/2026-08-01-safe-001-closure.md) and
[`IMPROVE-001 closure`](reviews/2026-08-01-fleet-improvement-closure.md), plus the
[`VERIFY-001 closure`](reviews/2026-08-02-verify-001-closure.md),
[`PROTECT-001 closure`](reviews/2026-08-05-protect-001-closure.md),
[`HOST-001 closure`](reviews/2026-08-06-host-001-closure.md), and
[`ADAPT-001 closure`](reviews/2026-08-06-adapt-001-closure.md). The local Sol evaluator
decision is recorded separately in
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

### RELEASE-001 — publish and roll back one immutable release

**Status:** `active` (2026-08-12) — PR
[#103](https://github.com/latent-sre/save-toolkit/pull/103) merged the repository implementation;
publication remains blocked and no release effect is authorized.

**Outcome:** One reviewed commit is versioned, tagged, published, installed, verified, and recoverable
without rebuilding or moving an unprotected ref.

**Source:** The historical distribution plan, rewritten for the accepted multi-platform plugin
architecture. Main-branch protection closed under
[`PROTECT-001 closure`](reviews/2026-08-05-protect-001-closure.md); host installation proof closed
under [`HOST-001 closure`](reviews/2026-08-06-host-001-closure.md).

**Prerequisites:** Repository preparation has no live prerequisite. Closure requires an independently
reviewed merged candidate, explicit owner authorization, immutable releases, the exact protected tag
ruleset, a human requester, exactly one distinct reviewer user or team on each of two release
environments, a protected reconciliation key, and the separately controlled publisher App. The host
closure's accepted limitations (Copilot CLI out of scope, UI-bound VS Code discovery, headless Codex
discovery, no model evidence) carry forward into this item's host distribution work.

**Acceptance:** Version parity and changelog pass; `claude plugin tag --dry-run` yields the exact
derived tag; promotion consumes the reviewed current-main/workflow SHA and merged-PR evidence under
the separated request/review/publish identities; strict install, exact inventory, marketplace and
plugin removal, standalone-agent cleanup, and authority checks pass from the published tag; a prior
immutable release is strictly rebound and reinstalled, or first-release uninstall is rehearsed;
immutability and unknown-outcome/replay behavior are evidenced without moving, deleting, or reusing a
version tag.

**Implementation (merged, PR #103):** the accepted
[exact-SHA promotion ADR](decisions/2026-08-11-immutable-release-promotion.md) — one protected
annotated `save-toolkit--v<version>` tag plus an immutable Release; separated requester,
environment-reviewer, and publisher-App identities; permanent per-run reservation refs; strict host
evidence binding the checkout's commit to an exact blob map. Preparation-only evidence, byte
identities, and review boundaries: the
[release/routing preparation evidence](reviews/2026-08-11-release-routing-backlog-evidence.md). The
clean dry-run derives `save-toolkit--v0.1.0`; no tag or Release exists.

**Live blockers:**

- GitHub configuration is absent (state as of 2026-08-12): immutable releases disabled; no
  release-tag ruleset; no `release-tag` / `release-finalize` environments; no visible publisher App.
  Creating them and dispatching are owner-approved external effects; the merge grants no publication
  authority.
- The host-probe authority claim: a before/after size-and-mtime census cannot prove that no write
  left the disposable target, so the strict no-user-write criterion is unmet (independent review P1,
  unresolved). Evidence and limits: the
  [first-three backlog evidence packet](reviews/2026-08-18-first-three-backlog-evidence.md).

**Next action:** The owner accepts a design that structurally denies the host CLI write access to
the real user configuration — a separately controlled OS identity or an equivalent sandbox —
recorded as a decision with cross-host proof; weakening the criterion to metadata-visible residue is
not a shortcut. Only then, and after the live GitHub controls exist, consider dispatch. Never create
or move a release ref manually.

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

### SKILL-001 — make the oversized skills routers, and their descriptions triggers

**Status:** `active` (2026-08-20)

**Outcome:** No skill spends a caller's context on content that call did not need. **These eight
skills** become routers with a conditional "if the question involves X, read Y" table —
`ops-tooling`, `pcf-ops`, `incident-command`, `operational-learning`, `ci-actions`,
`agent-security`, `pcf-deploy`, `database-reliability` — and every description is a trigger only, no
workflow summary restating a table the body already carries.

**Source:** [`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md), which
records every figure below with the command that produces it. `[verified]` The eight named skills are
exactly those whose `SKILL.md` is at least 8,000 bytes while their `references/` total is smaller
than `SKILL.md` itself — the bulk inline and unconditional rather than routed. `ops-tooling` is the
worst at 14,607 B against 7,202 B of references, and `incident-command`, `agent-security` and
`pcf-deploy` carry no references at all. `[verified]` Description mass resident in every session is
12,682 bytes across 29 skills.

`[unverified — judgment, not measurement]` That roughly a dozen descriptions carry a workflow
summary, which [`rules.md`](rules.md) forbids. Whether a clause helps a model decide *whether to
load* a skill, versus restating what the body already contains, is not mechanically decidable — so
that judgment motivates this item but deliberately does not appear in its acceptance below.

**Prerequisites:** The `obs-logs` conditional table is the pattern to copy. Description edits follow
the change playbook's after-run rule.

**Acceptance:** **All eight named skills** — not a subset — satisfy the criterion in reverse: each
either drops below 8,000 bytes or routes more reference bytes than it retains, and each carries a
conditional table whose targets are reachable through `check_links`. Re-running the sweep's command
must return an empty set. Each reworded description passes the 600-byte cap and the `Triggers:`
contract, and every routing-content description edit shows an after-change scenario run. A
previous-revision baseline is required only for a scenario that comes back red. Gate A green.

**Next action:** Convert one monolith as a pattern — `incident-command` is the highest-traffic and
has zero references — and land it alone so the conversion shape can be reviewed before it is applied
to the rest. Run the overlapping scenarios after each routing-content edit, fetching the prior
baseline only for a red scenario. One such run is still owed: the `eng-ladder` description was
rewritten in #115 (599 → 418 bytes) without an after-change routing run.

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

### DOCTOR-001 — make `fleet_doctor` diagnose the guard, not just the checkout

**Status:** `ready` (2026-08-14)

**Outcome:** A user whose Bash suddenly denies session-wide can run one command and learn why.
`scripts/fleet_doctor.py` reports whether the `PreToolUse` hook is registered in the installed
plugin, whether a Python on the hook's candidate list answers with the guard's `42`/`43` exit
codes, and whether the guard file resolves under `CLAUDE_PLUGIN_ROOT` — and it runs from an
installed plugin, not only from a repository checkout.

**Source:** Owner-requested usability review, 2026-08-13. `fleet_doctor` covers git revision,
worktree state, fleet contracts, plan status, host CLIs, plugin inventory, and Codex agent parity —
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

**Status:** `ready` (2026-08-22)

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

**Verified 2026-08-20** by probing `scripts/readonly-guard.py` on the #112 branch:
`gcloud logging read 'severity>=ERROR AND resource.type=cloud_run_revision' --freshness=1h` returns
exit 42 (allow); the same filter unquoted returns exit 43 (deny). On `origin/main`'s guard the quoted
form returns exit 43, so the sentence is correct on main and becomes stale only once #112 merges.

**Prerequisites:** None. Reconfirm the quoted and unquoted filter cases against the focused guard
corpus before changing the canonical skill.

**Acceptance:** `gcp-ops` states the guard's real behavior, the focused allow/deny corpus proves it,
generated projections match, and Gate A passes.

**Next action:** Correct the stale sentence with the focused guard regression, regenerate once, and
stop; no provider evaluation is attached to this text correction.

### SURFACE-001 — trim the user-facing surface (banner, retracted examples, shipped maintenance bytes)

**Status:** `ready` (2026-08-13; progress 2026-08-22) — remaining: the two example-footnote
compactions. Packaging of the maintenance skills stays separately deferred.

**Outcome:** A user who opens any of the 29 skills reaches actionable content within a few lines: the
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

**Prerequisites:** None blocking. The banner work is done. The
maintenance-skill packaging split stays deferred until after the first release (the accepted
packaging ADR governs the surface).

**Acceptance:** No shared evidence-default banner remains and adapters regenerate byte-clean; the
two self-retracting examples keep their labels as one-line footnotes; the retired learning packet
and ledger paths remain absent; Gate A passes; operational closeout still produces evidence-bound
documentation dispositions and owners without execution authority.

**Next action:** Compact the provenance paragraphs in the `pcf-deploy` and `runbook` worked examples
to one-line footnotes; leave the separately deferred packaging decision alone.

## Deferred

### EVAL-001 — expand risk-weighted Sol coverage

**Status:** `deferred` (2026-08-02) — the Codex/Sol conformance runners, contract tests, and fixed
manifests are recoverable at tag `pre-trim-2026-08-02`. Gate A and the local Claude runner are the
beta's current verification surfaces; no active Codex evaluator supplies this item's broader direct
Sol coverage. Reopen when a Codex/Sol behavioral baseline is actually needed for a release decision;
the prerequisites and acceptance below are unchanged and still apply at that point.

**Outcome:** The highest-risk skills and every explicitly installed Codex custom agent have direct
behavioral evidence on `gpt-5.6-sol`, while implicit routing remains an observational metric rather
than a release gate.

**Source:** Existing Sol reference and six-agent conformance baselines plus the measured headless
agent-discovery limitation.

**Prerequisites:** Clean committed plugin, generated-agent, and harness inputs; independent review of
that exact commit; and an operator-owned Codex login. Changes originating in an external branch or PR
must first be reviewed and committed into this repository before live evaluation.

**Acceptance:** Direct lanes cover the trust-separated research roles and risk-weighted release,
production-change, PCF, agent-security, and observability contracts. Every result distinguishes
`pass`, `fail`, and `inconclusive`, preserves exact model/runtime evidence, and never relabels the
historical Claude/Opus baselines.

**Reopen trigger:** A named release decision requires a current Codex/Sol behavioral baseline that
the active structural and Claude evaluation surfaces cannot provide.

**Next action:** None while deferred. On reopen: recover the runners from tag `pre-trim-2026-08-02`,
independently review the exact recovered commit, then run both fixed manifests from its clean
checkout. Retain each sanitized report beside the matching review packet; acceptance of the pair is
an external human/protected-workflow decision, never a field the runner grants itself. Keep implicit
routing observational rather than making it a release gate.

### STATE-001 — durable orchestration state

**Status:** `deferred`

**Outcome:** If a real multi-agent workflow needs resumable ownership, add append-only run/task/attempt
state with versions, leases, cancellation, supersession, revision binding, and evidence-linked
completion.

**Source:** Fleet authority reviews that distinguish durable coordination state from prompt prose,
worktrees, and host-native session state.

**Prerequisites:** A named multi-session or multi-worker consumer whose ownership and completion
cannot be derived safely from Git, pull requests, and evidence artifacts alone.

**Acceptance:** A versioned append-only state contract, migration and rollback plan, lease and
supersession semantics, evidence-bound completion, and failure tests exist for that named consumer.

**Reopen trigger:** A workflow spans multiple independent workers or sessions and cannot safely derive
ownership and completion from the pull request, Git commits, and evidence artifacts alone.

**Next action:** None. Do not add a coordinator persona or unused state database first.

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

**Current note (2026-08-11):** RELEASE-001 now has a target-specific workflow design, but its live
effect identity/configuration has not been approved or created, so this trigger is not yet satisfied.
If the owner authorizes that configuration, reopen EFFECT-001 before the first dispatch and close it
only with the workflow's effect-binding, expiry, replay, unknown-outcome, and rollback evidence.
