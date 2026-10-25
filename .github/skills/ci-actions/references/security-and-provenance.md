# Security and provenance

Follow repository policy; identify policy changes explicitly. The [parent](../SKILL.md) owns execution authority.

## Permissions and untrusted inputs

Grant explicit reads and only job-scoped necessary writes. A read-only `GITHUB_TOKEN` does not
constrain a separate PAT/cloud credential. Separate untrusted validation from privileged delivery.
Use checkout `persist-credentials: false` when later steps need no authenticated Git; it removes
retained Git credentials, not the runtime token or the tested code's capabilities.

Pass event-derived titles/branches through inputs or environment variables, quoted for the shell,
never interpolated into `run:` source. Validate downloaded artifact/output identity, format and
paths before privileged consumption.

Use `pull_request_target` only for its needed privileged context. Neither it nor `workflow_run` may
execute untrusted fork code alongside secrets, writes or private runner access. Upstream low privilege
does not constrain a downstream workflow; never bypass checkout protection to repair a blocked fork run.

## Action and tool versions

Without established policy, pin external actions/reusable workflows to reviewed upstream full SHAs
and `docker://` actions to manifest digests, with release comments and reviewable update automation.
A SHA identifies bytes, not safety. Preserve an approved tag policy but disclose mutability; moving
refs prove neither reproducibility nor an exact release. Never replace reviewed SHAs with tags during
cleanup. Upgrades must meet runtime compatibility and organization allowlists.

Pin installed tools separately from setup actions with locked installs/integrity checks. Separate
latest-version compatibility canaries from reproducible release validation and record resolved
versions. Dependency lifecycle scripts execute code; disable only when the project supports doing so.

## Identity and deployment controls

For a new federation-capable target, prefer short-lived OIDC after verifying issuer/audience/subject
bindings to repository/ref/environment. `id-token: write` permits token issuance, not a cloud role.
Existing target/identity policy governs: this fleet's `stack-profile` environment-secret policy remains
in force. For GCP, present Workload Identity Federation as an owner option; never create a service-account key.

Scope secrets to jobs/environments instead of broad reusable-workflow inheritance. Keep them out of
argv/logs/caches/artifacts; availability does not authorize use on another target.

Verify plan/visibility and actual environment reviewers, branch restrictions, self-review and bypass
settings; an environment name alone is no approval gate. Missing controls need a named gap/existing
alternative, never invented enforcement or weakened protection to make YAML run.

## Verification and supply-chain evidence

Use established `actionlint` and configured security lint such as `zizmor`. Static validity proves
neither execution nor credential isolation; negative event/permission checks must exercise the protection.

Bind releases to source commit, workflow/run attempt and artifact digest. Add attestations/SBOMs when
policy or consumers need them and verify them at consumption; attestations cannot sanitize an unsafe
producer. Prepare/verify immutable-release drafts and assets before publication; recovery afterward
may require another release. The existing human process retains production readiness/execution.

For Python packages, test the built wheel in a clean environment without checkout shadowing: imports,
entry points and package data; build a shipped sdist too. Editable tests do not establish release
contents. Preserve dependency groups/extras and requirements/constraints, without introducing a uv
migration merely for this check. See [installed-package guidance](https://docs.pytest.org/en/stable/explanation/goodpractices.html).
