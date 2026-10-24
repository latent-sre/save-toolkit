# Execution and optimization

Preserve required coverage and the [parent execution boundaries](../SKILL.md).

## Measure before choosing the lever

Compare queue time, critical path, setup/install/test/upload, cache hits/misses, retries, runner
class and concurrency across normal and slow attempts. Separate elapsed time from total runner use.

`gh run list -w <workflow file> -b <default branch> -e <event> -s success -L 20
--json databaseId,attempt,createdAt,updatedAt` selects comparable runs. For each, `gh api --paginate
repos/{owner}/{repo}/actions/runs/<id>/jobs` supplies job/step timings; queue delay is job
`started_at − created_at`. Compare median and slow tail, not one warm-cache run.

| Bottleneck | Candidate change and constraint |
|---|---|
| Queue | Remove duplicate runs/cancel superseded validation; more capacity cannot shorten serial work |
| Checkout/setup | Avoid unnecessary history/submodules/LFS, retaining history needed by version/diff tools |
| Dependencies/build | Compatible lock-aware cache only when restore/upload costs less than rebuilding |
| Tests | Duration-balanced shards with complete coverage, isolated shared state and bounded pressure |
| Matrix | Remove unsupported axes; retain supported targets and required-check identities |
| Uploads | Narrow paths/compression/retention while preserving failure and release/recovery evidence |

## Jobs, matrices and failure behavior

- `needs` represents a consumed result or intentional early-failure gate; each extra job repeats setup.
- Derive axes from supported runtimes/platforms, exceptions with `include`/`exclude`, pressure with
  `max-parallel`. Collapse only invariant checks: type checking may depend on Python/OS even if lint does not.
- Choose `fail-fast` for cancellation versus remaining compatibility evidence. Only agreed experimental
  legs are non-blocking; ordinary failures stay visible.
- Base job timeouts on slow-run evidence. Preserve exit codes through wrappers/pipes. Retry bounded
  known-transient operations, never the whole suite until green; track flakes explicitly.

## Caches are accelerators, artifacts are outputs

Cache package downloads or tool-supported build outputs with input-aware invalidation. Keys include
relevant OS/architecture, runtime/toolchain, lock and configuration identity. Do not duplicate setup-action
caches. Restore prefixes require compatible states; always perform the lock-enforcing install/sync.
Whole environments/workspaces need proven relocation/invalidation. Measure hit rate, size and transfer
cost; a miss must still build correctly, and a cache is never the release artifact.

No credentials, auth homes or private data in caches. Fork PRs can read eligible base caches;
ordinary PR-created caches belong to the merge ref. Analyze privileged-event/custom-cache readers
and writers separately; untrusted output must not poison privileged consumers. Preserve setup-action
security defaults unless event/cache scope is reviewed. Where supported, caller `cache-mode: read`
bounds reusable-workflow callee access; low-trust defaults alone do not. Do not grant write to silence
a warning: use a trusted producer. Check server/validator support for newer syntax.

Give matrix artifacts unique names and fail on a missing required release artifact. Tune compression
for the data and retention for its purpose. Promote the producing run's digest-bound bytes, never
ambiguous latest artifacts or a deploy-job rebuild.

## Events, required checks and cancellation

Avoid duplicate push/PR runs without losing default-branch/release coverage; include `merge_group`
for merge-queue checks. Path-filtered required workflows can remain pending, while skipped jobs can
report success. A stable summary job must explicitly check every required dependency, tolerating
only intended skips and rejecting failure/cancellation/missing coverage. Test changed/unchanged paths
and a failed dependency.

Workflow-level cancellation is for validation-only workflows; mixed workflows cancel validation jobs
only. Keys need workflow/ref and relevant job/matrix dimensions; reusable calls need a caller-job/target
key distinct from the caller's group. Deploy groups stay stable per target, automatic cancellation off.
`queue: single` still replaces pending work with `cancel-in-progress: false`; where supported,
`queue: max` retains up to 100 pending runs and forbids `cancel-in-progress: true`. FIFO follows
entry into waiting, not dispatch/commit order; a full queue cancels excess arrivals. Verify server/
validator support and reconcile the candidate before promotion: concurrency is not a deployment ledger.

## Runner choice

This fleet's new GitHub-hosted Linux jobs use **`ubuntu-latest`** under `stack-profile`; preserve
existing labels rather than substituting fixed OS versions as routine hardening. Diagnose with the
resolved image; labels are mutable. A reviewed container digest can fix userspace. Larger/self-hosted
runners need measured benefit or a network/hardware requirement.

For self-hosting, confirm stack boundary, owner/network scope, restricted groups and least privilege.
Keep untrusted jobs off persistent runners with credentials/internal reach. Ephemeral registration
does not erase files: require cleanup/replacement after completion, forced cancellation and host loss
before reuse. Check minimum runner compatibility when upgrading actions.
