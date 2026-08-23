# ADR: Exact-SHA immutable release promotion

- Date: 2026-08-11
- Status: Superseded 2026-08-23; repository implementation retired before live activation
- Decision owners: save-toolkit maintainers
- Roadmap item: `RELEASE-001` (retired by [owner disposition](../fleet-roadmap.md))

> **Historical record only.** No release was published under this design. The custom workflow,
> contracts, release-only tests, and runbook were removed because there was no named consumer for
> this control plane. Reopen release work only when a named consumer requires an immutable selector
> and rollback-capable release; do not restore these files solely because this ADR describes them.

## Context

Save Toolkit has one canonical source tree and generated host adapters, but no release artifact or
promotion boundary. The existing host probe installs from the mutable working checkout. A moving
`release` branch would make consumer bytes change without changing their selector, while a separately
built archive would create a second artifact whose parity must be proven.

Current host contracts support a source tag as the common identity:

| Consumer | Immutable source selection |
|---|---|
| Claude Code | `claude plugin marketplace add latent-sre/save-toolkit@<tag>` |
| Codex skills plugin | `codex plugin marketplace add latent-sre/save-toolkit@<tag>` |
| Standalone Codex agents | conflict-safe installer from the tagged checkout |
| VS Code | agents, skills, and settings from the tagged checkout |

Claude Code 2.1.227 and Codex CLI 0.147.0 accepted the tag/ref-shaped marketplace source in
credential-isolated disposable probes on 2026-08-11. VS Code remains a file-level workspace proof;
Codex custom-agent discovery remains file-level; Copilot CLI and model sessions retain the accepted
HOST-001 exclusions.

GitHub environments protect a job/run but do not independently bind a caller-provided candidate SHA.
The workflow must perform that binding itself. A network failure after a tag or release request also
has an unknown outcome: blindly retrying may repeat an effect or take over another request.

## Decision

1. The release artifact is the reviewed repository commit under one annotated tag named
   `save-toolkit--v<stable SemVer>`, plus a matching immutable GitHub Release. There is no release
   branch and no rebuilt ZIP. A separate permanent lightweight bookkeeping ref named
   `save-toolkit--attempt-v<version>--run-<github.run_id>` reserves the version before the release
   tag is written; it is not a consumer selector or release artifact.
2. `.github/workflows/release.yml` was the proposed only promotion path.
   It runs only by `workflow_dispatch` on protected `main` and binds the request to the repository,
   exact candidate/main/workflow SHA, version-derived tag, merged PR evidence, actor and triggering
   actor, whole-second UTC expiry, recovery target, immutable `github.run_id` nonce, and the run's
   immutable `created_at` issuance time. A non-replacing FIFO concurrency queue serializes all
   requests. A configured human requester starts the run; a different protected-environment
   reviewer approves each effect job.
3. Read-only preflight runs the release contract, Gate A, Claude strict validation, and Claude tag
   dry-run. The release contract requires version parity and an exact dated changelog section.
4. Two distinct protected environments, `release-tag` and `release-finalize`, separate the effect
   jobs so approval state cannot be reused across the intervening smoke. They use a full-SHA-pinned
   official GitHub API action and a scoped GitHub App token; neither checks out or executes candidate files.
   The first creates/reconciles the annotated tag. A separate read-only job installs, inventories, and
   uninstalls every supported surface from that remote tag with strict all-pass semantics. The second
   creates/reconciles the GitHub Release. A final read-only job verifies release immutability.
5. Before the release tag object is created, the publisher writes the permanent protected reservation
   ref for the version, original run, and candidate commit. Any other same-version reservation blocks
   a new dispatch. The workflow also scans all attempts of prior same-version runs and treats any
   started tag-effect job as a reservation; this covers an unknown reservation response while the ref
   is not yet readable. An exact existing object with the same candidate and run nonce is idempotent
   success. A conflicting object fails. An API error is followed by bounded read reconciliation; if
   exact state cannot be proven, the workflow reports `UNKNOWN_OUTCOME`. Only attempt 1 may issue a
   new reservation, tag, or release write. Operators rerun only the failed job and its dependents;
   they never rerun all jobs. Before either download, the finalizer rejects empty or nonnumeric
   producer artifact IDs and proves that both unexpired artifacts belong to this run and the same
   completed attempt. GitHub documents selective reruns and `needs` outputs separately, but does not
   explicitly guarantee cross-attempt output rehydration; the activation rehearsal must prove that
   behavior. Missing outputs fail closed rather than widening artifact selection. A smoke job checks
   all earlier attempts and cannot run again once any earlier smoke job started. A new dispatch has a
   new run ID and cannot take over the version, tag, or release.
6. The remote host proof binds `ls-tree` to the checkout's already-observed exact commit, derives a
   nonempty ordinary-file path and Git-blob map with the host manifest present, and independently
   compares both the marketplace checkout and installed Claude/Codex bytes with that immutable map.
   Missing, changed, ignored/untracked extra, linked, special, ambiguous, or malformed tree content
   fails closed. OS permission metadata is not the cross-host identity contract; ordinary-file paths
   and Git blob bytes are. A failed published-tag smoke burns that version. Reservation and release
   tags are never moved, deleted, or reused. Fixes ship under a new patch version.

The publishing App is limited to this repository and exactly `Actions: read`, `Administration: read`,
`Contents: write`, and implied metadata read. The App has no Actions write and cannot dispatch this
workflow. Actions read supplies the prior-run, all-attempt job, and producer-artifact scans;
Administration read checks the environments, ruleset, and immutable-release setting; Contents write
creates the reservation, tag, and Release; metadata read is implied. Its credentials exist only in
the two protected environments, after the distinct reviewer gates. This separation prevents the
dispatch identity from also minting a ruleset-bypassing contents-write token outside an approved job.

The App has no Workflows write. GitHub documents that permission as conditionally required when a
release target adds or changes workflow files relative to the default branch; here the protected tag
already exists at the exact current default-branch SHA, so `target_commitish` is ignored by the
release endpoint. Any future design that publishes a non-default-branch target must reopen this
permission decision instead of silently widening the App.

GitHub documents App-installation requests as attributed to the App, but does not guarantee a stable
`release.author.login`. Final release reconciliation therefore uses an HMAC-SHA256 proof over the
repository, tag, candidate, workflow SHA, run ID, and packet digest. Its 256-bit key exists only in
`release-finalize`; the public proof can be copied only after the exact Release already exists. Key
rotation is forbidden while a run may need unknown-outcome reconciliation.

GitHub exposes `immutable` on release responses but does not promise immediate propagation in the
create response. Finalization therefore performs bounded read-after-write settling and succeeds only
on the exact body with `immutable: true`; absence or a still-mutable exact object becomes
`UNKNOWN_OUTCOME` and never authorizes another write.

## Required live controls

Repository implementation does not activate publication. Before the first dispatch, a human owner
must explicitly authorize and configure all of the following, then attach current API evidence:

- enable GitHub immutable releases;
- create an active tag ruleset for `refs/tags/save-toolkit--v*` restricting creation, update,
  deletion, and non-fast-forward movement, and the same rules for
  `refs/tags/save-toolkit--attempt-v*`, with only the release App as an always-on bypass;
- create environments `release-tag` and `release-finalize`, each with exactly one required user or
  team distinct from the configured human requester, self-review prevented, admin bypass disabled,
  and deployment limited to protected branches;
- install the least-privileged publisher App and store only its ID/private key in both environments;
  store a separate 256-bit lowercase-hex `RELEASE_RECONCILIATION_KEY` only in `release-finalize`;
- set repository Actions variables `RELEASE_REQUEST_ACTOR`, `RELEASE_ENVIRONMENT_REVIEWER`,
  and `RELEASE_TAG_RULESET_ID` to the exact human requester, reviewer login/team slug, and ruleset ID.

Workflow-run/job history and every reservation ref are part of the replay ledger. Deleting either is
a prohibited break-glass action, not cleanup. The ruleset makes reservation deletion unavailable to
normal repository writers; the publisher App has no Actions write and cannot delete workflow history.
An owner with wider administrative authority can still dismantle these controls, so current ruleset,
history, and audit evidence remain activation and incident-response prerequisites rather than claims
that GitHub administrators have been cryptographically removed.

The workflow validates every API-visible control again before an absent tag can be created. Under the
least-privileged token, GitHub may omit ruleset `bypass_actors`; its documented environment response
also omits the current administrator-bypass setting. The owner approval packet and live closure must
therefore prove that the publisher App is the sole always-on ruleset bypass and that administrator
bypass is disabled on both environments. A missing environment is not safe: GitHub can create an
unprotected environment merely because a workflow names it, so the remaining exact reviewer,
self-review, branch-policy, visible ruleset, App-permission, HMAC, and immutability checks are
load-bearing.

## Recovery

Rollback is consumer-side selection of the prior immutable tag, never ref movement. Until a usable
immutable release exists, recovery is uninstall; the strict candidate probe rehearses plugin,
marketplace, and standalone-agent removal. A burned tag without a Release does not end this
first-release phase. Later releases must name a strictly older annotated tag with a published
immutable Release; preflight binds its commit and the smoke job separately proves a strict 12/12
reinstall lifecycle from that tag. Exact commands and stop conditions were recorded in the now
retired `docs/release-runbook.md`.

Destructive yank is not automated. If an exceptional security incident requires deleting an immutable
release, the human owner re-enters the production-change gate with the exact GitHub operation and
accepts that the tag name can never be reused.

## Alternatives rejected

- **Moving release branch:** mutable selector and a second protection surface; conflicts with the
  roadmap's immutable-outcome requirement.
- **Generated archive asset:** rebuilds bytes already represented by the commit and adds an avoidable
  parity/provenance problem.
- **Manual tag and release:** cannot structurally bind exact review evidence, expiry, actor, replay, or
  unknown outcomes.
- **Generic effect broker:** no other approved external-effect consumer exists; the target-specific
  workflow is smaller and does not broaden fleet authority.

## Consequences and reopen conditions

- A normal release requires approvals of two distinct protected environments separated by the
  remote-tag smoke.
- A tag can exist without a GitHub Release if smoke fails; that version remains permanently burned.
- Each attempted effect version retains a non-consumer reservation tag and Actions run record; this
  deliberate audit state is never pruned by the ordinary release process.
- Workflow correctness is provisional until the exact merged workflow runs under the live controls.
- `EFFECT-001` stays deferred until a human approves the separate effect identity and configuration.
  That approval reopens it; the target-specific workflow and first live run must then satisfy its
  effect binding, replay, expiry, rollback, and unknown-outcome acceptance before closure.
- Revisit this ADR if a supported host can no longer consume an immutable tag, GitHub changes immutable
  release or environment semantics, or a second legitimate effect consumer needs shared machinery.

## Sources

- [Claude Code plugin versioning and tags](https://code.claude.com/docs/en/plugin-dependencies)
- [Claude Code plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [Codex plugin distribution](https://developers.openai.com/plugins/build/plugins)
- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [GitHub environment protection](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [GitHub Actions concurrency queues](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [GitHub selective workflow reruns](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs)
- [GitHub `needs` output context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#needs-context)
- [GitHub workflow-run and job APIs](https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2026-03-10)
- [GitHub immutable workflow artifacts](https://github.com/actions/upload-artifact)
- [GitHub release integrity verification](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/verify-release-integrity)
