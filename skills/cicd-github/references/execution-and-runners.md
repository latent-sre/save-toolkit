# Execution and optimization

Preserve required coverage and the [parent execution boundaries](../SKILL.md).

## Measure before choosing the lever

`gh run list -w <workflow file> -b <default branch> -e <event> -s success -L 20
--json databaseId,attempt,createdAt,updatedAt` selects comparable runs. For each, `gh api --paginate
repos/{owner}/{repo}/actions/runs/<id>/attempts/<attempt>/jobs` supplies that attempt's job/step
timings; queue delay is job `started_at − created_at`. Compare median and slow tail, not one
warm-cache run.

When optimizing, keep the history version/diff tools need, shard tests without losing coverage or
isolation, and keep required-check identities and failure/recovery uploads.

## Matrix and cache decisions

- Collapse only checks proven invariant across the matrix: type checking may depend on Python/OS
  even if lint does not. Only agreed experimental legs are non-blocking; a flaky required test
  stays visible and diagnosed, never retried until green.
- A cache key carries OS/architecture, toolchain, lock and configuration identity, and a hit never
  skips the lock-enforcing install/sync. A tool-supported build cache with complete input keys is
  eligible; measure it cold and warm. A cache is never the release artifact.

## Cache access is scoped by trigger

No credentials, auth homes or private data in caches. Fork PRs can read eligible base caches;
ordinary PR-created caches belong to the merge ref.

Without `cache-mode`, a run from a trusted trigger gets read-write cache access, and a run from a
low-trust trigger (one an outside actor can cause, such as `pull_request_target`, `issue_comment`
or `workflow_run`) gets read-only access to the default-branch scope. Such a workflow restores but
no longer saves: produce the cache from a trusted workflow such as `push`. Do not grant write, or
use the repository's bypass of that restriction, to silence a warning.

`cache-mode` is set at workflow or job level, the job value winning, and takes `read`, `write`,
`write-only` or `none`. On a job that calls a reusable workflow it caps the callee: a callee that
declares more than the cap, or `write-only` against `read`, stops the run at validation. With no
explicit caller value a callee can still request `write` under a low-trust trigger, so caller
`cache-mode: read` is what bounds it; low-trust defaults alone do not. Analyze privileged-event and
custom-cache readers and writers separately; untrusted output must not poison privileged consumers.
Preserve setup-action security defaults unless event/cache scope is reviewed. Check server support
for newer syntax; `actionlint` 1.7.12 reports `cache-mode:` as an unexpected key, so that failure
alone does not make the syntax invalid.

## Events, required checks and cancellation

Avoid duplicate push/PR runs without losing default-branch/release coverage; include `merge_group`
for merge-queue checks. Path-filtered required workflows can remain pending, while skipped jobs
report success: `success`, `skipped` and `neutral` all satisfy a required check, and a job skipped
because a `needs` dependency failed may not block merging. A stable summary job therefore runs
under `always()` and explicitly checks every required dependency, tolerating only intended skips
and rejecting failure/cancellation/missing coverage. Test changed/unchanged paths and a failed
dependency.

Checks from workflow jobs count toward a pull request only when the run was triggered by `push`,
`pull_request`, `pull_request_review`, `pull_request_target`, `deployment` or `deployment_status`.
A run from any other event does not satisfy a required check, even when it passes on the head
commit; checks reported by an external GitHub App are not limited this way.

Workflow-level cancellation is for validation-only workflows; mixed workflows cancel validation jobs
only. Keys need workflow/ref and relevant job/matrix dimensions; reusable calls need a caller-job/target
key distinct from the caller's group. Deploy groups stay stable per target, automatic cancellation off.
`queue: single` still replaces pending work with `cancel-in-progress: false`; where supported,
`queue: max` retains up to 100 pending runs and forbids `cancel-in-progress: true`. FIFO follows
entry into waiting, not dispatch/commit order, and is not guaranteed; a full queue cancels excess arrivals. Verify server
support (`actionlint` 1.7.12 also rejects `queue:` as an unexpected key) and reconcile the candidate
before promotion: concurrency is not a deployment ledger.

## Runner choice

This fleet's new GitHub-hosted Linux jobs use **`ubuntu-latest`** under `stack-profile`; preserve
existing labels rather than substituting fixed OS versions as routine hardening. Diagnose with the
resolved image; labels are mutable. A reviewed container digest can fix userspace. Larger/self-hosted
runners need measured benefit or a network/hardware requirement. GitHub-hosted larger runners offer
RHEL 9 and 10 images on Team and Enterprise Cloud plans; matching the deployment OS that way is a
`stack-profile` decision, not a routine substitution.

Standard GitHub-hosted Linux jobs may run on AWS as well as Azure: automatically on Free, Pro and
Team, by opt-in on Enterprise Cloud. An allowlist or conditional-access policy that admits only
Azure ranges can block those jobs; use every published GitHub Actions range.

For self-hosting, confirm stack boundary, owner/network scope, restricted groups and least
privilege. Keep untrusted jobs off persistent runners with credentials/internal reach. Ephemeral
registration does not erase files: require cleanup/replacement after completion, forced cancellation
and host loss before reuse. Check minimum runner compatibility when upgrading actions. On
github.com, a runner that has not updated within 63 days of a newer version becoming available stops
receiving jobs, and a critical security update can stop them sooner; that availability date can
differ from the release date. Registration needs runner 2.329.0 or later, which is not a floor for
running jobs: the effective minimum advances with each release, and the REST runner-version
end-of-life schedule gives the dates. With auto-update off or no route to the update service,
schedule manual upgrades.
