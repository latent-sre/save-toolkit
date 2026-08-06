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
[`PROTECT-001 closure`](reviews/2026-08-05-protect-001-closure.md), and
[`HOST-001 closure`](reviews/2026-08-06-host-001-closure.md). The local Sol evaluator
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

### ADAPT-001 — finish the bounded sibling-repo adaptations

**Status:** `ready`

**Outcome:** The larger ideas surfaced by the 2026-08-05 `sde-agents` scan that were worth doing but
out of scope for the first pass are each either implemented behind a test or explicitly dropped with
a reason — no idea left in an unrecorded "maybe" state.

**Source:** [`2026-08-05-sde-agents-adaptation.md`](reviews/2026-08-05-sde-agents-adaptation.md),
which committed the guard, validator, gate, eval, and content changes and listed these as follow-on.

**Prerequisites:** None. Each sub-item is independent and stdlib-only; none depends on an owner
identity or on the deferred `STATE-001`/`EFFECT-001` machinery.

**Acceptance:** Each of the following lands with a fixture or mutation test proven to fail without
it, or is dropped in this item with a stated reason. Sub-items (3), (4), and (5) are **done** and
committed with tests; the two learning-system sub-items remain: (1) a drift watch over
`operational-learning` packets whose `proposed`/`blocked` destination has since changed in git
(advisory by default, exit-non-zero only on an unreadable repo, per the sibling's `ledger_drift.py`
design); (2) forward `review_at`/`expires_at` freshness deadlines on the knowledge-update schema,
governed by [`schema-compatibility.md`](schema-compatibility.md). Done: (3) AGENTS.md
path-and-`@import` drift enforcement in `scripts/check_links.py`, in Gate A; (4) a
`RETIRED_GENERATED_ROOTS` check that fails on a stale generated tree left on disk; (5) CRLF-independent
adapter generation for the `.py`/`.sh`/`.ps1` assets we ship, with a `.gitattributes` companion check.

**Next action:** The two remaining sub-items both touch the learning system, which maps onto the
scribe-bundle-validated `operational-learning` skill and the parked improvement-lifecycle. Scope
them together against `skills/operational-learning/scripts/knowledge_update.py` and its schema, and
do not edit the scribe-bundle contract strings the validator pins. `verification_sandbox.py` is
resolved and needs no work: `host_install_probe.py` consumes its `_is_indirection` helper, so it is
a live utility, not an orphan.

### WF-001 — verify the first Claude workflow against a live session

**Status:** `ready`

**Outcome:** `workflows/ship-review.js` is proven to run end-to-end in a live Claude session — the
scope agent enumerates the diff, both reviewer lanes return schema-valid packets from the diff as
data, and the merge-readiness synthesis produces the expected verdict for a known change — or the
workflow is corrected until it does. Until then it ships as reviewable code with its contract
stated, not as a verified capability.

**Source:** The 2026-08-05/06 alignment work, which established that "no `workflows/` directory" was a
self-imposed rule with nothing in the repo behind it. The narrower correct rule — workflows are
Claude-only and never projected to a generated adapter — is now encoded in the AGENTS.md Map and in
the generator's blindness to the `workflows/` tree.

**Prerequisites:** A live Claude session with the plugin loaded (workflow runtime is Claude-only; no
structural gate can exercise a workflow). A small, known working-tree change to review, so the
expected verdict is predictable.

**Acceptance:** One recorded run against a named source revision showing: the `save-toolkit:sde`
scope agent returned a `SCOPE_SCHEMA` packet; both `save-toolkit:reviewer` lanes returned
`REVIEW_PACKET`s built from the supplied diff (each re-reading cited files, never asking for a
shell); and the final verdict matched the merge-gate rule (any P0/P1 → `request-changes`; dirty tree
→ `provisional-commit-and-re-review`). Record the CLI/version and exact revision. A lane that fails
to return a validated packet must surface as `inconclusive`, never a false `approve`.

**Next action:** Run `ship-review` against a scratch change in a live session and capture the result.
Do not project the workflow to any host adapter, and do not add a second workflow before this one is
verified — one proven pipeline is worth more than several unrun ones.

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
immutable tag or protected moving ref; promotion consumes the reviewed SHA and required checks;
install and uninstall smoke tests pass from the published artifact; rollback or yank is rehearsed and
documented.

**Next action:** Write the exact-SHA promotion design owned by the named
promotion operator `agentic-sre-dev` (or a later least-privileged App) and verify each host's remote
distribution contract. Do not create a long-lived `release` branch merely because the superseded
plan named one.

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
