# Save Toolkit release runbook

- **What/why:** Publish and recover the multi-host Save Toolkit source artifact; maintainers and users
  notice a failure when the protected workflow blocks or a tagged plugin cannot install.
- **Where:** Repository `latent-sre/save-toolkit`; workflow
  [`.github/workflows/release.yml`](../.github/workflows/release.yml); release contract
  [`scripts/release_contract.py`](../scripts/release_contract.py); GitHub environments `release-tag`
  and `release-finalize`; tags and releases named `save-toolkit--v<version>`.
- **Health:** For an already published tag, the following read-only commands are healthy only when
  release verification succeeds, the release reports immutable, and the tag resolves to the approved
  40-character candidate SHA. These commands are locally syntax-checked but remain **unverified for a
  Save Toolkit release until the first publication exists**.

  ```powershell
  $releaseTag = 'save-toolkit--v<version>' # use the version recorded in the workflow run
  $candidateSha = '<40-character SHA>'     # use candidate_sha from the same run
  gh release verify $releaseTag --repo latent-sre/save-toolkit --format json
  gh api "repos/latent-sre/save-toolkit/releases/tags/$releaseTag" --jq '{tag_name,immutable,target_commitish}'
  gh api "repos/latent-sre/save-toolkit/commits/$releaseTag" --jq .sha
  # Good: verify exits 0, immutable is true, and the last command equals $candidateSha.
  ```

- **Restart:** n/a — there is no daemon. If a write returned an unknown result, do not start a new
  dispatch. Inspect the remote state first. Use GitHub's **Re-run failed jobs** operation for the same
  run; never use **Re-run all jobs**. A selective same-run rerun is reconciliation-only: it may
  recognize an already exact tag or Release, but `github.run_attempt > 1` cannot create a missing
  object. The finalizer requires nonempty exact artifact IDs, then proves both producer artifacts are
  unexpired, from this run, and from one attempt before downloading them. If GitHub does not
  rehydrate successful producer outputs on a selective rerun, this check fails closed; do not replace
  the IDs by names or rerun all jobs. The activation rehearsal must measure this platform behavior.
  If the tag job failed before smoke ever started, its dependent smoke may run once after exact tag
  reconciliation. Once any smoke attempt starts, the workflow permanently rejects another smoke
  attempt. A conflicting, absent, unreadable, `VERSION_RESERVED`, or `SMOKE_BURNED` result stops for
  maintainer resolution and a new patch version.
- **Common failures:**
  - Preflight explicitly fails the dispatch boundary → requester, ref, candidate SHA, or workflow SHA
    is not the configured human/current protected `main` → correct the request and dispatch the exact
    reviewed current-main SHA.
  - `immutable releases are not enabled` → live prerequisite is absent → stop; an authorized owner
    enables it before redispatching.
  - Environment/ruleset/App validation fails → protection or permissions drifted → stop; restore the
    exact ADR controls, do not widen the workflow.
  - Publisher-proof reconciliation fails → the protected HMAC key changed, the release body changed,
    or another writer pre-created the Release → stop; do not rotate the key during an unresolved run
    and never weaken the exact-body comparison.
  - `UNKNOWN_OUTCOME` → an API request may or may not have completed → read the exact tag/release and run
    annotation; never issue a blind retry or a new dispatch for that version.
  - `VERSION_RESERVED` → a permanent `save-toolkit--attempt-v<version>--run-<run-id>` ref or a prior
    started tag-effect job owns the version → preserve both records, reconcile only the original run,
    and choose a new patch version for any new request.
  - `SMOKE_BURNED` → a prior attempt already started the published-tag smoke → do not rerun or
    redispatch it; preserve the evidence and fix under a new patch version.
  - Exact Release remains non-immutable after bounded reconciliation → publication may still be
    settling or the repository setting drifted → stop and inspect read-only; never replay create.
  - Published-host smoke fails → one consumer could not install/inventory/uninstall the protected tag →
    leave the tag unchanged, treat the version as burned, remove it from consumers, fix under a new
    patch version.
  - Final verification fails after release creation → release may already be immutable → reconcile the
    same run; never edit or move the tag.
- **Recovery:** Rollback changes each consumer to the `recovery_tag` and exact commit recorded in the
  approved run. Before publication, the workflow requires that target to be a strictly older annotated
  tag with a stable immutable Release and runs its own strict 12/12 reinstall lifecycle. It does not
  move or delete the failed tag. The manual commands below remain **unverified until exercised by the
  first live rollback rehearsal**.

  Claude Code plugin:

  ```powershell
  $recoveryTag = 'save-toolkit--v<prior-version>'
  claude plugin uninstall save-toolkit@latent-sre
  claude plugin marketplace remove latent-sre
  claude plugin marketplace add "latent-sre/save-toolkit@$recoveryTag"
  claude plugin install save-toolkit@latent-sre
  claude plugin list --json
  ```

  Codex skills plugin:

  ```powershell
  $recoveryTag = 'save-toolkit--v<prior-version>'
  codex plugin remove save-toolkit@latent-sre
  codex plugin marketplace remove latent-sre
  codex plugin marketplace add "latent-sre/save-toolkit@$recoveryTag"
  codex plugin add save-toolkit@latent-sre
  codex plugin list --json
  ```

  Standalone Codex agents and VS Code workspace:

  ```powershell
  $recoveryTag = 'save-toolkit--v<prior-version>'
  git clone --branch $recoveryTag --depth 1 https://github.com/latent-sre/save-toolkit.git save-toolkit-recovery
  py -3 save-toolkit-recovery/scripts/install_codex_agents.py --target '<project>/.codex/agents'
  code save-toolkit-recovery
  ```

  Until the first usable immutable Release exists, recovery uses removal rather than a prior tag;
  burned tag-only attempts do not change that rule:

  ```powershell
  claude plugin uninstall save-toolkit@latent-sre
  claude plugin marketplace remove latent-sre
  codex plugin remove save-toolkit@latent-sre
  codex plugin marketplace remove latent-sre
  py -3 scripts/install_codex_agents.py --target '<project>/.codex/agents' --uninstall
  ```

  Stop repairing and prepare a new patch release when the protected tag exists but its full host smoke
  fails. Do not delete, force-move, or reuse it. Exceptional destructive yank requires a new explicit
  human approval packet and acknowledges that GitHub will permanently prevent tag-name reuse.
- **Dependencies:** Protected `main`; enabled immutable releases; active release-tag ruleset; a human
  workflow requester; exactly one distinct reviewer user or team on each of `release-tag` and
  `release-finalize`; a repository-scoped publisher App with Actions read, Administration read, and
  Contents write but no Actions write; an environment-only release-reconciliation key; a
  non-replacing Actions concurrency queue; retained workflow-run/job history; protected permanent
  reservation refs under `refs/tags/save-toolkit--attempt-v*`; a live selective-rerun rehearsal that
  proves successful producer output rehydration; GitHub Actions; pinned Claude/Codex CLIs; public
  GitHub clone access. Claude, Codex, standalone-agent, and VS Code users depend on the release tag;
  no production service depends on a moving release ref or the reservation namespace.
