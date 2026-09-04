# Workflow execution and runners

Read this reference only when the task involves matrices, timeouts, runner images, caching,
concurrency, artifact promotion, or self-hosted/ephemeral runners. Load `stack-profile` first when
recommending runner placement or CI infrastructure.

## Timeouts and hosted images

Put `timeout-minutes:` on every job so a hang cannot occupy a runner until the platform cap. Pin a
GitHub-hosted image such as `ubuntu-24.04` instead of `ubuntu-latest`. GitHub moves `-latest` over a
one-to-two-month window, so two runs during migration can receive different operating systems.
*[sourced: actions/runner-images README label table and Latest Migration Process; reviewed
2026-08-21]*

## Caching

Cache a dependency store, not build output, and include the lockfile hash in the key. Never let
untrusted pull-request code populate a key that trusted jobs restore.

`astral-sh/setup-uv` v10.0.0 and later disables automatic caching on `pull_request_target`,
`workflow_run`, and `release`; a miss on those events is expected, not a failure.
*[sourced: astral-sh/setup-uv release v10.0.0; reviewed 2026-08-21]*

## Concurrency and artifact promotion

Cancel superseded branch validation (`group: ${{ github.workflow }}-${{ github.ref }}` with
`cancel-in-progress: true`), never a production deployment (a stable group with
`cancel-in-progress: false`). Upload build outputs once, retain their identity or digest, and
download that exact artifact in the deployment job. Do not rebuild from the deployment ref.

## Self-hosted runners

Use a self-hosted runner only when a job needs network or platform access unavailable from a
GitHub-hosted runner. Put runners in restricted groups, limit the repositories and workflows that
can select them, keep the host patched, use a least-privilege service identity, and never attach a
self-hosted runner to a public repository. Prefer `--ephemeral` runners, one fresh runner per job,
which limits persistence from one poisoned job into the next without making untrusted code safe to
run beside credentials or private network access.

Keep the runner binary current. `actions/checkout` moved to Node 24 at v5.0.0, and an older
self-hosted runner can fail before the workflow's own commands begin. GitHub-hosted images receive
the compatible runtime from GitHub; self-hosted runners depend on their operator's update process.
*[sourced: actions/checkout CHANGELOG v5.0.0; reviewed 2026-08-21]*

Record the runner group, labels, network reachability, patch owner, update evidence, and cleanup
behavior in the handoff. If any of those are not observed, keep them `[unverified]`.
