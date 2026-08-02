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
[`IMPROVE-001 closure`](reviews/2026-08-01-fleet-improvement-closure.md). The local Sol evaluator
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

**Outcome:** Claude, Codex, Copilot CLI, and VS Code each report static, discovery, behavioral, and
model evidence independently; an unavailable host reports `skip` or `inconclusive`, never `pass`.

**Source:** Multi-platform packaging ADR and the import review's unverified-runtime limits.

**Prerequisites:** A disposable installation root; authenticated host access only for the lane being
measured. Codex/Sol behavioral runs use only fixed manifests and reviewed, committed local source;
the same-user login copy is an explicit limitation, not hostile-candidate containment.

**Acceptance:** Each supported host proves install, inventory/discovery, one authority boundary, and
uninstall without modifying user-owned components. Results record CLI/version, requested and observed
model where exposed, exact source revision, and limitations. Copilot/VS Code remain incomplete until
their runtime is actually available.

**Current evidence:** `fleet_doctor.py` now emits typed static/availability evidence without starting
a model or modifying host installations. This machine has Claude, Codex, and VS Code CLIs; Copilot
CLI remains unavailable, and the doctor reports that lane as `skip` rather than `pass`. Local live
Codex conformance now runs in a disposable home on reviewed source and reports that same-user
authentication isolation is not proven. It is not authorized for external candidate code.

**Next action:** Add disposable install/uninstall probes only for available hosts; keep Copilot and
VS Code behavioral lanes explicitly incomplete until their drivers can prove them.

### VERIFY-001 — isolate executable verification

**Status:** `active`

**Outcome:** Repository-controlled tests and build hooks can be verified without exposing host
credentials, writable source, host paths, or unrestricted network access.

**Source:** Agent-security's explicit statement that a worktree is not a sandbox and the sister
lab's digest-pinned verification runner.

**Prerequisites:** The merged `schemas/evidence-envelope-v1.schema.json` contract and
`scripts/evidence_envelope.py` validator; a trusted Docker or Podman engine; a locally present image
pinned by digest. A verification-agent roster change remains separate until the boundary is proven.

**Acceptance:** The trusted runner disables pulls and networking, mounts the exact source revision
read-only with separate writable scratch, runs non-root with dropped capabilities and resource/time
limits, confirms automatic cleanup or force-removes only an inspected owned container ID, checks
residue, and emits typed pass/fail/inconclusive evidence. Negative tests cover unpinned images,
source indirection, unsafe engines, bounded scratch/output, timeout, and cleanup failure.

**Current evidence:** The adapted runner passed a harmless digest-pinned Alpine command against an
unchanged committed `.claude-plugin` subtree with network disabled, no pull, read-only source/root
filesystem, non-root user, dropped capabilities, resource limits, automatic cleanup, no residue, and
matching pre/post tree digest. A live infinite-output probe was terminated at the 1 MiB cap, then its
owned container was force-removed with no residue and an `inconclusive` verdict. Negative tests cover
unsafe engines, unpinned images, source
indirection, Git metadata, digest drift, timeouts, output overflow, oversized scratch, missing image, cleanup
failure, foreign name collision, and container residue.

**Review evidence:** The boundary and its hosted-runner portability changes received exact-SHA
independent approval; Gate A exercised its deterministic contracts on Ubuntu, macOS, and Windows.
This is not evidence of a separate workflow consumer and does not reopen the roster decision.

**Next action:** Keep the verification-agent roster decision deferred until a real workflow
demonstrates a separate consumer.

### EVAL-001 — expand risk-weighted Sol coverage

**Status:** `active`

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

**Current evidence:** The static Sol manifests declare 11 skill/reference lanes and thirteen intended
custom-agent lanes covering all eight roles, both trust-separated refusal behaviors, reviewer
detection of a supplied object-authorization regression, and `scribe`'s no-execution plus
knowledge-closeout boundaries. Offline validation confirms their schemas, inventory, and pinned Sol model; it does not
establish model behavior. The 2026-07-31 live results
are retained but revoked: their same-user `auth.json` boundary and parsed-response reports were not
safe release evidence. The local runners now retain only sanitized hashes, verdicts, usage,
timeouts, exact commit/tree identities, and typed evidence. The local runners copy the operator's
Codex login into a disposable home only after plugin bootstrap, delete that home before returning,
reject credential-shaped volatile output, and make dirty development runs non-exact and
inconclusive. Reports always state that source review is unverified by the runner, the evaluator is
not independent, and the result is neither baseline-eligible nor release-granting. Skill lanes
have no collaboration tools, and agent lanes use constrained local prompt/configuration bytes while
bounding V1/V2 concurrency and shared rollout usage.
Sixteen negative routing cases remain in the ordinary eval suite, including `scribe` collisions with
live incident investigation, observability design, automation, independent review, and the
operational-learning method's direct-writing boundary.

**Next action:** Commit this local harness change, independently review that exact commit, then run
both fixed manifests from its clean checkout. Retain each sanitized report beside the matching review
packet; acceptance of the pair is an external human/protected-workflow decision, never a field the
runner grants itself. Keep implicit routing observational rather than making it a release gate.

## Decision needed

### PROTECT-001 — assign repository protection identities

**Status:** `decision-needed`

**Outcome:** `main` and publication controls require reviewed changes and separate the code owner from
the identity that performs exact-SHA promotion.

**Source:** `CONTRIBUTING.md` promotion policy and the live GitHub configuration review.

**Prerequisites:** Owner assignment. At present only `latent-sre` is a repository collaborator;
`agentic-sre-dev` is authenticated locally but is not a collaborator, and no dedicated promotion App
has been established.

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

### STATE-001 — durable orchestration state

**Status:** `deferred`

**Outcome:** If a real multi-agent workflow needs resumable ownership, add append-only run/task/attempt
state with versions, leases, cancellation, supersession, revision binding, and evidence-linked
completion.

**Reopen trigger:** A workflow spans multiple independent workers or sessions and cannot safely derive
ownership and completion from the pull request, Git commits, and evidence artifacts alone.

**Next action:** None. Do not add a coordinator persona or unused state database first.

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`

**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.

**Reopen trigger:** A named workflow is approved to move beyond the fleet's current prepare/recommend
boundary and has a separately controlled execution identity.

**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority.
