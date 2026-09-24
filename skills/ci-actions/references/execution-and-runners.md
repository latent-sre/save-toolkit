# Execution and optimization

Read for workflow speed, cost, matrices, caching, concurrency, artifacts or runners. Optimize the
measured bottleneck while preserving the project's required coverage and execution authority.

## Contents

- Measure before choosing the lever
- Jobs, matrices and failure behavior
- Caches are accelerators, artifacts are outputs
- Events, required checks and cancellation
- Runner choice

## Measure before choosing the lever

Separate queue delay from execution. From comparable run attempts, record the critical path,
checkout/setup/install/test/upload durations, cache hit/miss, retries, runner class and concurrency.
Compare normal and slow runs rather than treating one warm-cache run as the baseline.

Baseline recipe: `gh run list -w <workflow file> -b <default branch> -e <event> -s success -L 20
--json databaseId,attempt,createdAt,updatedAt` lists comparable runs. For each, `gh api --paginate
repos/{owner}/{repo}/actions/runs/<id>/jobs` gives job `created_at`/`started_at`/`completed_at` and
step `started_at`/`completed_at`; queue time is `started_at − created_at`. Compare the median and the
slow tail, not one run. *[verified: gh 2.94.0 against this fleet's validate workflow]*

| Dominant cost | Try first | Check the tradeoff |
|---|---|---|
| Queue time | Remove duplicate event runs; cancel superseded validation; adjust concurrency or capacity | More workers may raise cost without reducing serial work |
| Checkout/setup | Default shallow checkout unless history is needed; avoid unnecessary submodules, LFS and repeated installs | Versioning, changelog and diff tools may require history |
| Dependency/build work | Lock-aware package cache or compatible compiler/build cache | Restore/upload may cost more than rebuilding; warm and cold runs must agree |
| One long test job | Duration-balanced shards or independent suites | All tests must still run; isolate shared state and cap service/runner pressure |
| Large matrix | Remove unsupported combinations; run invariant lint once; separate experimental coverage | Retain the supported OS/runtime contract and required-check identities |
| Uploads | Narrow paths, compress according to data, shorten retention where appropriate | Keep failure evidence and release/recovery artifacts for their required lifetime |

Do not promise a percentage improvement without before/after measurements on comparable code,
events and runners. A shorter critical path can consume more total runner minutes.

## Jobs, matrices and failure behavior

- Use `needs` only when a job consumes another job's result or the dependency intentionally avoids
  expensive work after an early failure. More jobs are not automatically faster: each starts fresh.
- Derive matrix axes from supported versions/platforms. Use `include`/`exclude` for meaningful
  exceptions rather than a Cartesian product by habit. Use `max-parallel` to bound runner and
  downstream service pressure.
- Collapse only checks proved invariant. Type checking can depend on Python version and platform;
  keep those targets covered even when formatting and version-independent lint run once.
- Choose `fail-fast` deliberately: cancellation saves work after a blocking failure; disabling it
  gathers the remaining compatibility results. Mark an experimental leg non-blocking only when
  that is the agreed policy; keep ordinary failures visible.
- Give every job a timeout based on observed slow runs. Preserve the failing exit code through
  wrappers and pipelines. Retry known transient operations with a bound, not the entire suite
  until green; track flakes instead of converting them to success.

## Caches are accelerators, artifacts are outputs

Use the package manager's download store or supported compiler/build cache. Build outputs can be
cached when the tool's invalidation covers their inputs; a cache is never the authoritative release
artifact. Include relevant OS, architecture, toolchain/runtime, lockfile and configuration identity
in keys. Do not duplicate a setup action's existing cache with another cache of the same paths.

Use restore prefixes only across compatible states. After restoring dependencies, still perform
the lock-enforcing install/sync; a hit is not proof the environment is complete. Avoid caching a
whole virtual environment or workspace unless its relocation and invalidation are established.
Measure cache size, hit rate and restore/save time; remove a cache that makes runs slower.

No credentials, authentication homes or private data belong in caches. Fork PRs can read eligible
base-branch caches; ordinary PR-created caches are scoped to their merge ref. Privileged events
and custom external caches need separate writer/reader trust analysis. Do not let untrusted code
poison a cache later used by a privileged job. Retain setup-action security defaults unless the
changed event and cache scope have been reviewed.
Where the target supports `cache-mode`, an explicit `read` limit on a reusable-workflow caller
prevents its callee from requesting cache writes. Low-trust defaults alone are not that explicit
limit. Do not add `write` to silence a cache warning; retain the restricted mode and let a trusted
producer refresh the cache. Check server and validator support before adding newer syntax.

Use artifacts to move test reports and built release bytes between jobs. Give matrix artifacts
unique names; fail when a required release artifact is absent. Tune compression for the actual
data (already-compressed bundles rarely benefit), and retain diagnostics and releases according to
their purpose. Bind promotion to the producing run and artifact digest, never an ambiguous latest
artifact; do not rebuild a different binary in the deploy job.

## Events, required checks and cancellation

Avoid redundant push/PR runs for the same intended validation, without losing default-branch or
release coverage. Include `merge_group` when the repository's merge queue needs those checks.
Path filters can leave required workflow checks pending. A conditionally skipped job can report
success. If using change detection and a stable required summary job, evaluate every required
dependency result explicitly: tolerate only the intentionally skipped work, and fail on unexpected
failure, cancellation or missing coverage. Test affected and unaffected paths and a failed dependency.

Cancel superseded work at workflow level only for a validation-only workflow. In a mixed workflow,
keep cancelling groups on validation jobs. Include workflow/ref and job or matrix dimensions as
needed; reusable calls need a caller-job/target key distinct from the caller's group. Keep deployment
groups stable per target with automatic cancellation off. Choose whether superseded pending
deployments may be dropped: the default `queue: single` replaces an existing pending run even with
`cancel-in-progress: false`. Where supported, `queue: max` retains up to 100 pending runs and cannot
be combined with `cancel-in-progress: true`. FIFO is by when work starts waiting, not dispatch or
commit order; a full queue cancels excess arrivals. Check server/validator support and reconcile
the candidate before promotion rather than treating concurrency as a durable deployment ledger.

## Runner choice

Follow the project's runner policy. New GitHub-hosted Linux jobs in this fleet use
**`ubuntu-latest`** (`stack-profile`); keep an existing job's label, and do not substitute a fixed OS
release as routine hardening. Record the resolved image when diagnosing failures; a runner label
is not an immutable image. Use a reviewed container digest when the workload needs fixed userspace.
Larger runners, local caches and self-hosting need measured benefit or a network/hardware requirement.

For self-hosted runners, load the team's stack boundary, record the owner and network access, and
use restricted runner groups and least privilege. Keep untrusted jobs away from persistent runners
with credentials or internal reach. Ephemeral registration alone does not erase files: require
cleanup/replacement after normal completion, forced cancellation and host loss before reuse.
Check the action runtime's minimum runner version before upgrading actions.

Sources: [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[dependency cache semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching),
[workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
and [reusable workflow choices](https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations).
