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
[`VERIFY-001 closure`](reviews/2026-08-02-verify-001-closure.md). The local Sol evaluator
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

### HOST-001 — prove host installation and runtime conformance

**Status:** `active`

**Outcome:** Claude, Codex, Copilot CLI, and VS Code each report disposable installation, inventory,
discovery, one authority boundary, and uninstall evidence independently; an unavailable host reports
`skip` or `inconclusive`, never `pass`. Model-behavior baselines remain a separate `EVAL-001` concern.

**Source:** Multi-platform packaging ADR and the import review's unverified-runtime limits.

**Prerequisites:** A disposable installation root and authenticated host access only when a bounded
behavioral smoke is explicitly authorized. Host installation evidence must not depend on the parked
Codex/Sol runners or require writes to user-owned plugin and custom-agent directories.

**Acceptance:** Each supported host proves install, inventory/discovery, one authority boundary, and
uninstall without modifying user-owned components. Results record CLI/version, requested and observed
model where exposed, exact source revision, and limitations. Copilot/VS Code remain incomplete until
their runtime is actually available.

**Current evidence:** `fleet_doctor.py` emits typed static/availability evidence without starting a
model or modifying host installations. This machine has Claude, Codex, and VS Code CLIs; Copilot CLI
remains unavailable and reports `skip`. The fleet is absent from the Claude and Codex plugin
inventories. Codex custom agents share one flat, unnamespaced global directory, so the projection
emits `save-toolkit-<role>.toml` mirroring the Claude `save-toolkit:<name>` namespace; `build_sync_plan`
against the real `CODEX_HOME` now reports zero conflicts and eight pending writes, where it
previously reported three collisions with a separate agent fleet installed under the same role names.
Host proof must still use an explicit disposable target — but because this item's prerequisites
forbid writing to user-owned plugin and custom-agent directories at all, not because a name
collision would otherwise occur.

The absent-but-installable status question is settled: `fail` now means exactly one thing across the
doctor's installation checks — an *installed* fleet is unhealthy. `host.codex.custom-agents` reports
`skip` when an available Codex host carries no marker-managed fleet file at all, matching the
plugin-inventory check's standing precedent that absence is not a runtime failure; partial, stale,
or drifted installs and unmanaged conflicts remain `fail`.

`scripts/host_install_probe.py` is the disposable proof surface. Given an explicit, initially empty
target outside user-owned configuration and the repository, it installs the fleet per host, checks
inventory, censuses the user-owned config location before and after to prove the write boundary,
uninstalls, and reports residue — one validated evidence envelope per criterion, recording CLI
identity/version and the exact source revision. Codex installs through the conflict-safe installer,
which now owns `--uninstall` (removing only marker-managed files); VS Code installs as workspace
file placement matching its folder-scan discovery; Claude installs through the CLI's plugin
marketplace/install/list/uninstall verbs against a credential-free disposable `CLAUDE_CONFIG_DIR`;
Copilot mirrors the Claude flow against a disposable HOME (its local-path marketplace,
install/list/uninstall verbs are exercised the same way). A missing CLI is `skip`, a failing CLI
verb is `inconclusive`, and only a proven boundary violation or uninstall residue is `fail`. No
model session is started and no credentials are provisioned, so requested/observed model fields
are absent by design. On a CLI-less machine every host criterion reports `skip`; the probe's
contract tests run in Gate A.

A full four-host run is recorded [verified on a Cursor cloud VM, Linux x64, CLIs installed from
public npm/tarball sources, no credentials provisioned]: Claude Code 2.1.221, codex-cli 0.146.0,
VS Code 1.131.0, and GitHub Copilot CLI 1.0.78 each reported `pass` for install, inventory,
authority, and uninstall at source revision `ed75c9eb38a0b3273a2ab9b70bb29ad7fad2268b`, with every
watched user-owned location unchanged and the disposable target removed. The same run settled two
format questions only real CLIs could answer — Claude's inventory row marker is `❯` and Copilot's
is a bullet row with a version annotation — and both inventory parsers now require an exact
fullmatch. Standing limitations: VS Code runtime discovery is UI-bound (inventory is file-level),
headless Codex agent discovery is unproven, and no model session was started, so model evidence
remains an EVAL-001 concern.

**Next action:** The owner decides whether the verified cloud-VM run and its recorded limitations
satisfy this item's acceptance — VS Code UI discovery and headless Codex discovery are documented
gaps, and model evidence stays with EVAL-001 — or whether a run on the owner workstation topology
is also required. No repository change is blocking either path.

## Blocked on an owner decision

### PROTECT-001 — assign repository protection identities

**Status:** `decision-needed`

**Outcome:** `main` and publication controls require reviewed changes and separate the code owner from
the identity that performs exact-SHA promotion.

**Source:** `CONTRIBUTING.md` promotion policy and the live GitHub configuration review.

**Prerequisites:** Owner assignment. At present only `latent-sre` is a repository collaborator;
`agentic-sre-dev` is authenticated locally but is not a collaborator, and no dedicated promotion App
has been established.

`main` is currently unprotected — `GET branches/main/protection` returns 404 — and no check is
required to merge, so the `Validate fleet` workflow can be disabled without blocking anything. That
happened on 2026-08-02 and went unnoticed until 2026-08-03, during which six pull requests merged
with no structural verification. Until a named required check exists, a switched-off gate is
indistinguishable from a passing one: it does not fail, it stops running.

**Acceptance:** A default CODEOWNERS rule covers canonical sources, generated adapters, hooks,
workflows, manifests, executable skill assets, and the ownership file itself; active rules require PR,
code-owner review, and named checks with no administrative bypass; a distinct least-privileged
operator or repository-scoped GitHub App owns promotion.

**Next action:** The repository owner assigns maintainer and promotion-operator identities. Do not add
a CODEOWNERS rule that the current single-collaborator topology cannot satisfy.

### RELEASE-001 — publish and roll back one immutable release

**Status:** `blocked`

**Outcome:** One reviewed commit is versioned, tagged, published, installed, verified, and recoverable
without rebuilding or moving an unprotected ref.

**Source:** The historical distribution plan, rewritten for the accepted multi-platform plugin
architecture.

**Prerequisites:** PROTECT-001 and HOST-001.

**Acceptance:** Version parity and changelog pass; `claude plugin tag --dry-run` validates the Claude
manifest/marketplace pair; every host's publication mechanism is verified before choosing an
immutable tag or protected moving ref; promotion consumes the reviewed SHA and required checks;
install and uninstall smoke tests pass from the published artifact; rollback or yank is rehearsed and
documented.

**Next action:** After protection identities are assigned, write the exact-SHA promotion design and
verify each host's remote distribution contract. Do not create a long-lived `release` branch merely
because the superseded plan named one.

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
separately controlled execution identity, and `PROTECT-001` enforcement.

**Acceptance:** Effect-bound approval, dispatch, unknown-outcome reconciliation, replay prevention,
expiry, rollback, and operator-resolution tests pass for the named effect target.

**Reopen trigger:** A named workflow is approved to move beyond the fleet's current prepare/recommend
boundary and has a separately controlled execution identity.

**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority.
