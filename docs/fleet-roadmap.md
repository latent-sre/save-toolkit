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

**Prerequisites:** A documented direct-dispatch API, or documented permission semantics that bind
the registered workflow implementation as well as its name. Any alternative architecture needs an
accepted decision record before implementation.

**Acceptance:** Pin the supported CLI/API version and prove before merge that (1) only the intended
trusted workflow implementation can execute; (2) same-name `script`, `scriptPath`, resume, remote,
and extra-field variants are denied before task creation; (3) candidate bytes never reach an outer
tool-bearing model; (4) reviewer lanes have structurally bounded authority; and (5) incomplete or
failed review evidence cannot become approval. Gate A and mocked JavaScript are supporting evidence,
not substitutes for the live boundary proof.

**Next action:** Monitor the upstream workflow dispatch contract. Do not restore the removed
`ship-review` implementation or add another workflow until the prerequisite exists and the boundary
is accepted explicitly.

### RELEASE-001 — publish and roll back one immutable release

**Status:** `ready`

**Outcome:** One reviewed commit is versioned, tagged, published, installed, verified, and recoverable
without rebuilding or moving an unprotected ref.

**Source:** The historical distribution plan, rewritten for the accepted multi-platform plugin
architecture. Main-branch protection closed under
[`PROTECT-001 closure`](reviews/2026-08-05-protect-001-closure.md); host installation proof closed
under [`HOST-001 closure`](reviews/2026-08-06-host-001-closure.md).

**Prerequisites:** None. The host closure's accepted limitations (Copilot
CLI out of scope, UI-bound VS Code discovery, headless Codex discovery, no model evidence) carry
forward into this item's host distribution work.

**Acceptance:** Version parity and changelog pass; `claude plugin tag --dry-run` validates the Claude
manifest/marketplace pair; every host's publication mechanism is verified before choosing an
immutable tag or protected moving ref; promotion consumes the reviewed SHA and recorded validation;
install and uninstall smoke tests pass from the published artifact; rollback or yank is rehearsed and
documented.

**Next action:** Write the exact-SHA promotion design owned by the named
promotion operator `agentic-sre-dev` (or a later least-privileged App) and verify each host's remote
distribution contract. Do not create a long-lived `release` branch merely because the superseded
plan named one.

### ROUTE-001 — routing evals for the 2026-08 description changes

**Status:** `ready`

**Outcome:** The clean-room runner measures routing before/after for every description edited or
added in the SRE/GCP/Akamai expansion, and any regression (a component that stops firing, or a
near-miss that starts) is fixed or explicitly accepted.

**Source:** The 2026-08 expansion changed the descriptions of `obs-logs`, `obs-metrics`,
`obs-traces`, `obs-alerting`, and `runbook`, and added two new routed components (`gcp-ops`,
`akamai-edge`). The change playbook requires overlapping scenarios through the clean-room runner
for every description edit; the run was deferred with a stated reason — the authoring session had
no live-API eval capability — never eyeballed as a substitute.

**Prerequisites:** A live Claude API session with the clean-room runner from `evals/`; the merged
description set checked out clean.

**Acceptance:** Before/after runs over the overlapping scenarios in `evals/scenarios/` (log, metric,
trace, alerting, and runbook routing), plus new-component scenarios proving `gcp-ops` and
`akamai-edge` fire on their trigger phrasings and do not steal `pcf-ops`, `obs-*`, or `sre`-lane
traffic. Results recorded beside the scenarios with model/runtime evidence.

**Next action:** Run the overlapping scenarios through the clean-room runner on a live-API session
and record the deltas; add scenarios for the two new skills where coverage is missing.

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
