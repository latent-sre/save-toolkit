# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred work for the
> current fleet. Historical plans, reviews, audits, and decision records provide evidence and
> rationale; they do not independently add work to this queue.

The accepted architecture is
[`2026-07-31-multi-platform-plugin-packaging.md`](decisions/2026-07-31-multi-platform-plugin-packaging.md):
one canonical Claude plugin under `agents/`, `skills/`, and `commands/`, with generated host-native
adapters for Copilot/VS Code and Codex.

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

## Active

### MERGE-001 — land the multi-platform migration through review

**Status:** `active`

**Outcome:** The canonical plugin, generated adapters, Sol conformance lanes, and protected-main
canary reach `main` through one reviewable pull request without reviving the conflicting historical
layout.

**Source:** The accepted multi-platform packaging decision and the three-pass sister-lab import
review.

**Prerequisites:** A clean candidate branch with generated output current and local structural
validation passing.

**Acceptance:** A draft PR binds the full candidate SHA; Ubuntu, macOS, Windows, and strict Claude
plugin checks pass; packaging/authority, eval/conformance, and canary/release changes receive
independent review; conflicting PR #70 is closed as superseded with a link to the replacement.

**Next action:** Open the draft PR from `codex/sister-plugin-migration` and let trusted CI evaluate
the current branch.

### SAFE-001 — separate research trust zones and normalize evidence

**Status:** `active`

**Outcome:** The fleet offers mutually exclusive local-only and external-only evidence roles, mixed
questions use a sanitized caller-owned handoff, and new runtime controls emit one validated evidence
envelope instead of incompatible ad-hoc verdicts.

**Source:** The 2026-07-31 fleet-control review and the sister lab's merged P0/P1 safety controls.

**Prerequisites:** Preserve the current researcher evidence contract, generated-adapter authority
translation, and explicit agent selection where autonomous routing is unreliable.

**Acceptance:** A local-only repository investigator has no web, MCP, shell, write, or delegation
tools; the external researcher has no local read/search tools; negative routing cases protect review,
debugging, security-audit, and implementation lanes; a versioned evidence schema rejects unknown or
secret-bearing fields; deterministic tests and generated drift checks pass.

**Current evidence:** Seven canonical roles now pass authority and generated-adapter checks; the
evidence-envelope validator, JSON Schema, fleet doctor, and Codex/Sol result wrappers have mutation
tests. A later independent review found the live runner's `auth.json` boundary unsafe and the
generated reviewer self-disabling on inherited Codex capabilities. The candidate now requires the
pinned trusted-main Responses API broker, removes raw/parsed response fields, detects credential-like
output, avoids token-bearing checkout post callbacks in the model job, and fetches candidate objects
without checkout before a credential-free trusted extractor materializes only bounded raw
plugin/agent blobs. Skill lanes disable delegation; agent lanes permit only trusted-main prompt bytes
plus one live child under a shared rollout budget. The fleet also uses host-portable reviewer
integrity language and adds a real reviewer authorization lane. The earlier Sol runtime results are
revoked; these remediations currently have offline evidence only.

**Next action:** Bind the focused three-pass re-review and draft PR to the committed candidate. After
the broker workflow reaches trusted `main`, wait for PROTECT-001 and distinct promotion authority;
only then run it against an immutable reviewed canary SHA.

## Active runtime work

### HOST-001 — prove host installation and runtime conformance

**Status:** `active`

**Outcome:** Claude, Codex, Copilot CLI, and VS Code each report static, discovery, behavioral, and
model evidence independently; an unavailable host reports `skip` or `inconclusive`, never `pass`.

**Source:** Multi-platform packaging ADR and the import review's unverified-runtime limits.

**Prerequisites:** MERGE-001; a disposable installation root; authenticated host access only for
the lane being measured. Codex model credentials must remain in the trusted broker, never in the
candidate runner's files, environment, or OS identity.

**Acceptance:** Each supported host proves install, inventory/discovery, one authority boundary, and
uninstall without modifying user-owned components. Results record CLI/version, requested and observed
model where exposed, exact source revision, and limitations. Copilot/VS Code remain incomplete until
their runtime is actually available.

**Current evidence:** `fleet_doctor.py` now emits typed static/availability evidence without starting
a model or modifying host installations. This machine has Claude, Codex, and VS Code CLIs; Copilot
CLI remains unavailable, and the doctor reports that lane as `skip` rather than `pass`. Local live
Codex conformance is now rejected because the Windows/same-user credential boundary is insufficient.

**Next action:** Add disposable install/uninstall probes only for available hosts; keep Copilot and
VS Code behavioral lanes explicitly incomplete until their drivers can prove them.

### VERIFY-001 — isolate executable verification

**Status:** `active`

**Outcome:** Repository-controlled tests and build hooks can be verified without exposing host
credentials, writable source, host paths, or unrestricted network access.

**Source:** Agent-security's explicit statement that a worktree is not a sandbox and the sister
lab's digest-pinned verification runner.

**Prerequisites:** SAFE-001 evidence envelopes; a trusted Docker or Podman engine; a locally present
image pinned by digest. A verification-agent roster change remains separate until the boundary is
proven.

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

**Next action:** Independently review the boundary and keep the verification-agent roster decision
deferred until a real workflow demonstrates a separate consumer.

### EVAL-001 — expand risk-weighted Sol coverage

**Status:** `active`

**Outcome:** The highest-risk skills and every explicitly installed Codex custom agent have direct
behavioral evidence on `gpt-5.6-sol`, while implicit routing remains an observational metric rather
than a release gate.

**Source:** Existing Sol reference and six-agent conformance baselines plus the measured headless
agent-discovery limitation.

**Prerequisites:** SAFE-001 if the roster changes; clean plugin, generated-agent, and harness inputs.

**Acceptance:** Direct lanes cover the trust-separated research roles and risk-weighted release,
production-change, PCF, agent-security, and observability contracts. Every result distinguishes
`pass`, `fail`, and `inconclusive`, preserves exact model/runtime evidence, and never relabels the
historical Claude/Opus baselines.

**Current evidence:** The static Sol manifests validate 11 skill/reference lanes and ten custom-agent
lanes covering all seven roles, both trust-separated refusal behaviors, and reviewer detection of a
supplied object-authorization regression without executing or delegating. The 2026-07-31 live results
are retained but revoked: their same-user `auth.json` boundary and parsed-response reports were not
safe release evidence. The new brokered workflow and negative credential tests pass offline; a fresh
live result cannot exist until that workflow is trusted on `main`. The model job has no checkout post
callback or candidate checkout/filter path: candidate acquisition is object-only, then a trusted
credential-free extractor writes raw allowlisted blobs. Skill lanes have no collaboration tools, and
agent lanes require trusted prompt bytes while bounding V1/V2 concurrency and shared rollout usage.
Five static routing collision cases remain in the ordinary eval suite.

**Next action:** Complete the exact-SHA three-pass review and merge the trusted evaluator workflow if
approved. Do **not** create a canary or dispatch the live run until PROTECT-001 and the distinct
promotion-authority control are complete, as required by `CONTRIBUTING.md`. Only then evaluate the
reviewed immutable canary and retain both reduced reports with the fresh-runner attestation. Keep
implicit routing observational rather than turning it into a release gate.

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

**Prerequisites:** MERGE-001, PROTECT-001, HOST-001, and the exact-SHA canary on trusted `main`.

**Acceptance:** Version parity and changelog pass; `claude plugin tag --dry-run` validates the Claude
manifest/marketplace pair; every host's publication mechanism is verified before choosing an
immutable tag or protected moving ref; promotion consumes the reviewed SHA and canary evidence;
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
