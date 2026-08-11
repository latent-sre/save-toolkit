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

An item leaves this file after its acceptance evidence is committed and the change is merged. Git
history and archived source documents retain the implementation detail.

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

**Upstream refresh (2026-08-11):** Claude Code 2.1.227 now exposes the documented built-in
[`claude ultrareview`](https://code.claude.com/docs/en/ultrareview) subcommand. It removes the old
caller-supplied workflow-body surface, but does not yet satisfy this item: the research-preview
contract bundles the current working tree or clones a mutable PR target, documents no immutable
candidate SHA/digest in `bugs.json`, and exits 0 whether findings are present or absent. It also
uploads code to Anthropic's cloud sandbox and may consume paid usage credits. `--help` was inspected
without launching, uploading, posting, or spending; an undocumented live observation would not turn
these missing guarantees into a supported boundary.

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

**Status:** `active` (2026-08-11) — repository implementation is in progress; publication remains
blocked and no release effect is authorized.

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

**Current implementation:** The accepted
[`exact-SHA promotion ADR`](decisions/2026-08-11-immutable-release-promotion.md) chooses one protected
annotated `save-toolkit--v<version>` tag plus an immutable GitHub Release, never a moving branch.
The prepared workflow, release-contract/mutation tests, changelog, strict remote-tag host-probe mode,
and [`release runbook`](release-runbook.md) are repository-local evidence only. The workflow separates
the configured human requester, distinct environment reviewer, Actions-read/no-write publisher App,
and environment-only HMAC proof. A non-replacing queue, permanent protected per-run version
reservation, prior-run/job scan, stable workflow-created issuance time, exact artifact IDs, and
prior-smoke guard make reruns reconciliation-only. The strict host evidence binds the checkout's
observed commit to an exact `ls-tree` ordinary-file/Git-blob map, then independently requires both
marketplace and installed Claude/Codex trees to match; identical non-HEAD source/install bytes and a
moving `HEAD` both fail closed. Claude Code 2.1.227 and Codex CLI 0.147.0 accepted a tag-pinned public
marketplace source in credential-isolated disposable probes. The release contracts, workflow mutation
suite, host-probe suite, Gate A, and Claude strict validation pass on the current locally committed
candidate.
Hash-bound independent review found no P0/P1 in the release state machine; the follow-up host edge-case
fixtures received no P0-P2 finding. Exact counts, byte identities, review boundaries, and
authorization limits are bound in the dated
[`release/routing preparation evidence`](reviews/2026-08-11-release-routing-backlog-evidence.md). The
clean exact-commit tag dry-run derives `save-toolkit--v0.1.0`; no force flag was used and no tag or
Release was created.

**Live blockers:** The local commit has not been pushed or merged; exact-SHA review is required before
merge. Immutable releases are currently disabled, and no protected release environments,
release-tag ruleset, or separately controlled release App exists. Creating those controls and
dispatching the workflow are external effects requiring an explicit owner-approved plan and rollback;
repository implementation does not grant that authority.

**Next action:** Retain exact-SHA review evidence, then the owner decides whether to authorize branch
publication and merge. After merge, the owner separately decides whether to authorize the ADR's exact
live GitHub configuration. If approved, record its API evidence, dispatch the exact merged `main` SHA,
preserve the strict host/immutability reports, and add RELEASE-001 closure evidence. Do not create or
move a release ref manually.

### ROUTE-001 — routing evals for the 2026-08 description changes

**Status:** `blocked` (2026-08-11) — the local runner/scenario repair is complete, but no comparable
before/after pair exists and the live external data/cost boundary lacks explicit owner approval.

**Outcome:** The clean-room runner measures routing before/after for every description edited or
added in the SRE/GCP/Akamai expansion, and any regression (a component that stops firing, or a
near-miss that starts) is fixed or explicitly accepted.

**Source:** The 2026-08 expansion changed the descriptions of `obs-logs`, `obs-metrics`,
`obs-traces`, `obs-alerting`, and `runbook`, and added two new routed components (`gcp-ops`,
`akamai-edge`). The change playbook requires overlapping scenarios through the clean-room runner
for every description edit; the run was deferred with a stated reason — the authoring session had
no live-API eval capability — never eyeballed as a substitute.

**Prerequisites:** Explicit owner approval to transmit the fixed eval prompts and isolated plugin
context to the live Claude service and incur model usage; a live Claude API session with the
clean-room runner from `evals/`; the merged description set checked out clean.

**Acceptance:** Before/after runs over the overlapping scenarios in `evals/scenarios/` (log, metric,
trace, alerting, and runbook routing), plus new-component scenarios proving `gcp-ops` and
`akamai-edge` fire on their trigger phrasings and do not steal `pcf-ops`, `obs-*`, or `sre`-lane
traffic. Results recorded beside the scenarios with model/runtime evidence.

**Current evidence:** Nineteen regression scenarios cover the five edited descriptions plus
`gcp-ops`/`akamai-edge` positives and cross-lane negatives. The repaired parser accepts only coherent
same-session continuation epochs, rejects ambiguous/error/unfinished streams, and keeps persisted
diagnostics identity-only. Root-scoped incident negatives require the expected SRE owner at root and
prove every nested target descends from that owner; inline, orphan, non-agent, wrong-root, cyclic, and
duplicate-identity ancestry fails closed. The runner, clean-room, response-grader, and scenario
validation checks pass in the dated evidence packet. Its prompt-echo regression records the exact
red/green counts without changing prompts, targets, or routing expectations. Independent review found
no remaining P0/P1 in the routing/parser slice; exact commands and limits are recorded in the dated
[`release/routing preparation evidence`](reviews/2026-08-11-release-routing-backlog-evidence.md). The
campaign is prepared with one five-case harness shared by clean baseline
`a39a81f33f7ad7325c52d883822bbbdd80c7ed28` and current
`65fe5c8c28da0052e3204adfac2af152e9a02475`, plus a fourteen-case current-only harness; all 25 copied
files match the reviewed source, both plugin-input sets are clean, and the two harness manifest
digests are recorded in that packet. The first paid live canary was rejected before execution because
the owner has not explicitly approved that external data/cost boundary, so no new model call occurred.
Earlier current-only results remain partial historical evidence, the retained July run remains an
invalid before run, private raw traces stay outside the repository, and no sanitized closure report
has been recorded.

**Next action:** The owner decides whether to authorize the stated live Claude data/cost boundary. If
approved, run the prepared five paired cases against baseline/current and the fourteen current-only
cases sequentially at two trials, Sonnet, and 300 seconds; stop on instrument exit 2/3 and record only
sanitized digest/count/verdict/runtime evidence. Without that approval, retain the prepared campaign
and blocker. Do not tune descriptions from the earlier confounded or inconclusive evidence.

## Deferred

### EVAL-001 — expand risk-weighted Sol coverage

**Status:** `deferred` (2026-08-02) — the Codex/Sol conformance runners, contract tests, and fixed
manifests are recoverable at tag `pre-trim-2026-08-02`. Gate A plus the local Claude eval runner is
the active verification surface for the beta. Reopen when a Codex/Sol behavioral baseline is
actually needed for a release decision; the prerequisites and acceptance below are unchanged and
still apply at that point.

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

**Current evidence:** Tag `pre-trim-2026-08-02` retains the fixed manifests, sanitized local runners,
contract tests, and their documented same-user credential limitation. The 2026-07-31 live results
remain retained but revoked and there is no current Sol behavioral baseline. The active ordinary
suite retains negative routing coverage for trust separation, `scribe` collisions, and the
operational-learning method's direct-writing boundary.

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
