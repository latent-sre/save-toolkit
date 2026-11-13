# WP-04 and WP-08 readiness from refreshed main

[verified] The owner requested both work packages from updated remote main. The source is
`d1a2383dffe27c5a7be8ab510405f3c67bf3746e`, fetched before creating branch
`work/wp04-wp08-main-20261112` in the existing isolated worktree. The original checkout's staged
Python work is separate. The preparation below made zero candidate or judge calls and spent no
new model budget. It neither admits cases nor starts a benchmark campaign.

## Fresh preparation

| Package | Verified result | Remaining boundary |
|---|---|---|
| WP-04 | Rebuilt the five selected cases from the pinned source cache: 458 observable assets, 441,911,602 bytes. Fresh serialized fixtures total 499,755,899 bytes, below 512 MiB. All five generated files were rehashed; rebuilt bindings equal the committed map. Five ground-truth inputs were reverified into a separate evaluator-only output. | Exact case/run admission and a demonstrated native filesystem boundary. No live Windows or Linux candidate ran. |
| WP-08 | Rehashed the pinned parquet, dataset card and ten licences. All 500 JSON rows equal the parquet rows. Regenerated the ten-case complex proposal and compared it with the committed manifest: identical, still `pending-human-acceptance`. | Accepted selection, qualified engine, immutable task images, Linux CLI, optional verifier environment, model binding and separately started smoke/trial/batch. |

[verified] WP-04 dataset revision remains `d0916b08ba421ce5e672e9ad68aa947d938dfef0`;
WP-08 remains `78f471bf655a3137b2e8a75af1501690ec009ec3`. No dataset or task was substituted.
The old WP-04 generated directory returned access denied during inspection and was left alone.
Fresh outputs were regenerated from the readable pinned source cache, without changing its bytes.
The former `fixture_hashes_verified: false` receipt remains historical; the new receipt records
successful hashes for the new generated files.

## Focused qualification

[verified] The coordinated command
`.venv/Scripts/python.exe -B scripts/local_tests.py --suite itbench --suite swebench` passed
**590 tests, with eight skips**, in 48.939 runner seconds. Both source endpoints were clean at
`d1a2383d`. Receipt:
`F:/repos/sre-agents/.git/local-test-runs/20261112T220249Z-83d7f0b1/run.json`.

[verified] Four skips require Linux bubblewrap and/or the installed real Claude CLI, including
the real hidden-answer namespace control. One CPU probe requires Linux containers, two process
controls require POSIX, and one private-mode assertion requires POSIX. These are unverified host
controls. The focused result proves the selected offline contracts, not installed host readiness,
full smoke, native behavior or human acceptance. This run predates the Desktop exception's code
changes; its evidence applies to the clean-main preparation, not the later implementation.

## Hard-quota failure on the current engine

[verified] Docker context `desktop-linux` reports Engine **29.9.3**, commit `70efc0e`, Linux
x86_64, `overlayfs`, with `io.containerd.snapshotter.v1`. The retained October diagnostic was
repeated once with the same already-local immutable Alpine image. There were no image pulls,
network access, mounts or benchmark workloads. The disposable container had two CPUs, 128 MiB
memory, 32 processes, dropped capabilities and no-new-privileges.

| Measurement | Result |
|---|---:|
| Requested writable-layer quota | 33,554,432 bytes (32 MiB) |
| Bounded write attempted and completed | 67,108,864 bytes (64 MiB) |
| Write/container exit | 0 |
| Retained storage option | `size=32M` |
| Quota verdict | **FAIL** |

[verified] Removal of the uniquely labelled owned container returned zero. The initial private
observer nevertheless failed its absence assertion: generic `docker inspect` emits lowercase
`error: no such object`, which its case-sensitive check missed. The failed observer receipt is
retained. A subsequent container-specific inspection proved the resource absent; a separate
generic-inspect receipt confirms the text mismatch. This was an observation defect, not a second
quota trial or evidence that a container remained. No other container was removed.

[sourced: Context7, official Docker documentation] Classic `overlay2` size quotas require an
XFS backing filesystem mounted with `pquota`; containerd uses its separate snapshotter path.
See the [storage-option reference](https://docs.docker.com/reference/cli/docker/container/run/#set-storage-driver-options-per-container---storage-opt)
and [containerd image store](https://docs.docker.com/engine/storage/containerd/).
[sourced: GitHits, upstream source matching the observed commit prefix] Moby
[`createLayer` at 70efc0e3](https://github.com/moby/moby/blob/70efc0e3/daemon/containerd/image_snapshot.go#L49-L97)
accepts `rwLayerOpts` but does not apply it to snapshot preparation. This is consistent with the
measured overrun; the runtime probe is the direct enforcement evidence.

[verified] The diagnostic fails the original hard-quota contract. A retained option, watchdog,
shared VM disk limit or CPU/memory cap does not demonstrate a hard quota. The Docker Desktop
datastore and host configuration were not changed. The owner's subsequent exception below
permits a separately identified monitored mode; it does not alter this failed hard-quota result.

## Approved Desktop storage exception

[sourced] The owner clarified, "i thought i approved that exception", after discussion of the
monitored target, overshoot and shared-storage implications. The
[run-plan amendment](../fleet-evaluation/run-plan-wp08-swebench-repair.md#owner-amendment-docker-desktop-monitored-storage-2026-11-12)
records that authorization. WP-08 can proceed on current Windows Docker Desktop in explicit
monitored mode; no further Linux-host choice is required for this storage exception.

[verified] The implementation preserves strict quota mode as the default and requires both
`storage_mode: monitored` and `storage_quota: false` for the exception. It samples writable-layer
bytes initially, every five seconds and after normal command completion, stops on over-target or
unknown measurement, retains sampled maxima/counts and attempts owned cleanup. The independent
verifier records typed stops; the parent preserves them even when a monitor fails before source
baseline attestation. Unestablished execution remains INCONCLUSIVE. Smoke requires separate
`storage_monitor` evidence; monitored results have a distinct execution profile and cannot pair or
pool with hard-quota results. This exception is scoped to Windows with a local Linux Docker
Desktop engine and bound to observed engine/backend identity.

[verified] Review found and corrected an additional lifecycle gap: a background author process
could otherwise keep writing while independent verification ran. The monitored author is now
removed after patch capture and its absence confirmed before verification; unresolved removal
stops that transition and retains pending cleanup. Focused regression controls reproduced both
this gap and early verifier-stop loss before the fixes, then passed after correction.

[verified] A model-free control used the already-local immutable Alpine image with no pulls,
mounts, credentials or network, with two CPUs, 128 MiB memory, 32 processes, dropped capabilities
and no-new-privileges. The production monitor code used a temporary 32 MiB test target and a
bounded 64 MiB payload. It recorded two samples, a sampled maximum of **67,112,960 bytes**, and
`storage_limit`; inspected cleanup confirmed the owned container absent. The production target
remains 10,737,418,240 bytes. This scaled diagnostic proves the monitor/cleanup path on this engine;
it does not qualify full 10 GiB smoke, exact task images, egress or candidate execution.

[verified] Final integrated verification on the implementation above:

- `.venv/Scripts/python.exe -B scripts/local_tests.py --heavy`: **5,064 passed, 295 skipped,
  5,019 subtests passed**, exit zero, 520.197 runner seconds. Receipt:
  `F:/repos/sre-agents/.git/local-test-runs/20261113T041231Z-29eb8eb8/run.json`.
  The runner's source endpoints are identical. All 13 adapter-module hashes still match the
  measured packet; adapter identity is
  `d8fb6d9ddbb7b20134540c2f53a3fd101684c8529008040c1c6234f44045a0ac`.
- Ruff lint and production-module formatting passed. Linux-platform mypy passed all 13 adapter
  modules. The runtime slice's native Windows mypy diagnostic retains three pre-existing POSIX
  attribute errors; Linux-target typing is not a claim of a clean Windows typing gate.
- Gate A passed 2/2 structural steps. Read-only integration review found early stop loss, the
  background-writer lifecycle gap and stale cleanup uncertainty after a successful retry. Each
  was reproduced, corrected and re-reviewed; no review blocker remains. The reviewer had authored
  the verifier slice, so review independence is limited for that file.

[verified] The 295 skips include optional frontend/SWT and POSIX fixture controls. Four affected
SWE-bench checks require POSIX process groups, a Linux CPU probe or POSIX private-mode assertions;
real WP-04 Linux/bubblewrap/CLI controls remain skipped on Windows. Skips establish no host
qualification. The full benchmark smoke, case admission, live trials and human acceptance remain
unverified. No paid model or judge call occurred.

[verified] Worker-focused red/green receipts, the scaled Docker control and final source/skip
summary are retained under `.eval-runs/wp08-desktop-exception-20261112/`. An earlier full-suite
attempt was stopped after the late cleanup-review finding; its receipt is retained as aborted,
not passed. The completed run above tests the corrected implementation. Only these evidence and
plan-completion notes were updated afterward; executable source was unchanged at that publication.
The later PR review repair below has separate verification.

## PR 496 finalization review repair, 2026-11-13

[sourced] The [P2 review finding](https://github.com/latent-sre/save-toolkit/pull/496#discussion_r4560360039)
identified an exit-path gap in `9e8b3163`: a rejected trace or screening/setup error skipped the
happy-path author retirement, then final billing could block on network I/O before owned cleanup.
A detached writer could remain active through that wait without storage samples or a hard quota.

[verified] Finalization now attempts owned Docker cleanup before billing on every exit path.
Monitored final usage collection additionally requires fresh exact-name inspection proving the
author absent. Present or unknown inspection skips the request; the proxy still closes, final
cleanup inspection and pending recovery remain in place, and missing billing remains unknown.
Quota-mode final usage and the earlier pre-verifier author retirement retain their behavior.

[verified] Seven regression cases cover identity rejection, incomplete trace counts, patch/stream
screening, setup failure and present/unknown author cleanup. The completed focused runner suite
passes **109 tests**. Ruff lint/production formatting and Linux-platform typing pass. Independent
static review found no additional issue. Initial red and first-green receipts are retained,
including correction of an incomplete-trace fixture that initially supplied valid trace input.
The corrected full-suite result and exact repair commit are recorded in the PR follow-up,
separately from the original implementation evidence above. Private repair receipts are retained
under `.eval-runs/pr496-finalization-fix-20261113/`.

[sourced] The separate automated security review did not complete because its paying account
[reached its Codex usage limit](https://github.com/latent-sre/save-toolkit/pull/496#issuecomment-6845912473).
That unavailable review is not a code finding or a passing security assessment. No paid model call
or security-review retry is part of this repair.

## WP-04 runtime boundary

[verified] Generated WP-04 specs are fixture-bearing builds with neither routing nor followups
(`evals/itbench_adapter/native.py`). Consequently `read_boundary_applies()` in
`evals/probe/invocation.py` returns false for them. The ordinary runner's identity/tool records
cannot be presented as trace-level root-check evidence for this profile. The operator instructions
now state that limit explicitly.

[verified] The existing `evals/wp04_linux_cli.py` requires actual Linux and bubblewrap. Its
namespace mounts the selected observations and measured plugin, system runtime and the dedicated
CLI configuration. The chosen host must place evaluator cache, ground truths, bindings and reviewer
material outside those mounted roots. The real namespace and CLI controls must pass on that host. Windows Job
Objects establish process ownership and cleanup, not filesystem isolation.

[verified] WSL inventory lists only Docker Desktop's internal distribution. No usable ordinary
Linux evaluation distribution or selected remote host was established. A reachable Linux Docker
daemon does not by itself establish the existing native WP-04 runtime.

## Concrete next step and retained evidence

[sourced] The owner-approved next path for WP-08 is the current Windows Docker Desktop engine
with the explicit monitored-storage exception. A quota-capable Linux engine remains an alternative
for strict mode, not a requirement for this approved path. No host reconfiguration is needed for
the exception. The pending Linux-host question is superseded for WP-08.

[sourced] First qualify WP-08's selected storage, egress, CPU, verifier and cleanup controls with
the pinned Linux CLI and immutable task images on Desktop. WP-04 still needs a proven filesystem
boundary: the existing wrapper requires Linux/bubblewrap; a dedicated Docker wrapper is feasible
but not implemented or qualified here. A Docker daemon alone supplies no WP-04 candidate boundary.
Then bind exact candidate, selection and runtime
identities. The complex WP-08 proposal remains pending exact acceptance; smoke, first paid trial
and remaining batch retain their separate start/review steps. Use repository Python 3.14; the
older adapter dependency diagnostic's 3.12 threshold is not the current project floor. SWE-bench
has not yet been installed into this interpreter; its pinned environment remains a full-smoke prerequisite.

[verified] Private source and fixture hashes, rebuilt bindings/proposal, command logs, focused
receipt, raw quota/observer records and the successful cleanup verification are retained under
`.eval-runs/wp04-wp08-main-20261112/`. Hidden answers and raw telemetry are not in tracked files.
