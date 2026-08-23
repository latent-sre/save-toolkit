# Workflow execution and runners

Read this reference only when the task involves matrices, timeouts, runner images, caching,
concurrency, artifact promotion, or self-hosted/ephemeral runners. Load `stack-profile` first when
recommending runner placement or CI infrastructure.

## Matrix, timeouts, and hosted images

Use a matrix when the same focused job must cover supported versions:

```yaml
strategy:
  matrix:
    python: ["3.11", "3.12"]
```

Put `timeout-minutes:` on every job so a hang cannot occupy a runner until the platform cap. Pin a
GitHub-hosted image such as `ubuntu-24.04` instead of `ubuntu-latest`. GitHub moves `-latest` over a
one-to-two-month window, so two runs during migration can receive different operating systems.
*[sourced: actions/runner-images README label table and Latest Migration Process; reviewed
2026-08-21]*

## Caching

Cache a dependency store, not build output, and include the lockfile hash in the key. A key that
ignores the lockfile can silently restore stale dependencies. Never let untrusted pull-request code
populate a key that trusted jobs restore.

Some setup actions enforce that boundary. `astral-sh/setup-uv` v10.0.0 and later disables automatic
caching on `pull_request_target`, `workflow_run`, and `release`; a miss on those events is expected,
not a failure. *[sourced: astral-sh/setup-uv release v10.0.0; reviewed 2026-08-21]*

## Concurrency and artifact promotion

Cancel superseded branch validation, but never a production deployment:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

Use a stable deployment group with `cancel-in-progress: false` for production. Upload build outputs
once, retain their identity or digest, and download that exact artifact in the deployment job. Do
not rebuild from the deployment ref.

## Self-hosted runners

Use a self-hosted runner only when a job needs network or platform access unavailable from a
GitHub-hosted runner. Put runners in restricted groups, limit the repositories and workflows that
can select them, keep the host patched, and use a least-privilege service identity. Never attach a
self-hosted runner to a public repository.

Prefer `--ephemeral` runners: one job receives a fresh runner and the runner is discarded after the
job. This reduces persistence from one poisoned job into the next; it does not make untrusted code
safe to run beside credentials or private network access.

Keep the runner binary current. `actions/checkout` moved to Node 24 at v5.0.0, and an older
self-hosted runner can fail before the workflow's own commands begin. GitHub-hosted images receive
the compatible runtime from GitHub; self-hosted runners depend on their operator's update process.
*[sourced: actions/checkout CHANGELOG v5.0.0; reviewed 2026-08-21]*

Record the runner group, labels, network reachability, patch owner, update evidence, and cleanup
behavior in the handoff. If any of those are not observed, keep them `[unverified]`.
