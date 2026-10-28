# EVAL-012 Windows preparation and remaining acceptance

EVAL-012 remains open. This review completes source preparation on the available Windows host
and records the failures preventing its benchmark execution; it does not accept a candidate or
amend the selected execution profile. The owner requested Windows/Docker campaign preparation
on 2026-10-27. Live status remains in the [roadmap](../fleet-roadmap.md#eval-012--plan-incident-and-coding-evaluations-for-the-fleet).

## Subject and evidence boundary

[verified] The source subject is clean main revision `fe9649bd54d56dd72d5a5d19638d78ab4a19d1bb`,
inspected in a separate managed worktree. The original checkout's staged and unstaged changes
were not incorporated. These documentation corrections do not change measured plugin or runner bytes.

| Identity | SHA-256 |
|---|---|
| Canonical plugin | `57b98795fe93ec7ac35c9555039b6d1b4f3fdb8615cdfe5bfaba3659265790ee` |
| Native runner | `eca1db5ff951259d505d290737bc759e7ae3ae13dde1138c93bc1c052188f889` |
| WP-08 adapter and bound dependencies | `bd8e9d4f283f0dbda47ec34c81322ad7b57854d15c171400173c27ce96985257` |

[verified] Private preparation is retained under `.eval-runs/eval012-preparation-20261027/`
in the original checkout. `readiness.json` binds source, manifests, generated fixtures and the
receipts below. No candidate or rubric-judge calls, credential provisioning, benchmark-code
execution, commits or publication were performed. Docker was started for the host checks;
its configuration was not changed and both owned probe containers were removed.

[sourced: committed historical reports] The [follow-through](2026-10-25-followthrough.md) and
[88-attempt comparison](2026-10-25-wp10-handoff-repairs.md) retain their original results and
human-acceptance gaps. Their `.eval-runs/followthrough/` bundles were not present in the original
checkout or its project-local worktrees. Those traces and the reported USD 12.477564 total were
not re-audited here; unknown subscription costs remain unknown. No fresh spending allowance is
inferred from the historical USD 40 cap.

## Prepared sources

[unverified] At the 2026-10-28 commit boundary, filesystem permissions prevented re-reading
the generated ITBench YAML files for an independent rehash. The successful preparation receipt
and its recorded hashes are retained; fresh fixture rehashing remains outstanding.

| Package | Fresh local result | Remaining gate |
|---|---|---|
| WP-04 ITBench | [verified] Downloaded and hash-checked 458 observable assets plus five hidden ground truths. The observations total 441,911,602 bytes. Regenerated five native fixtures totalling 499,755,899 bytes, within the 512 MiB preparation bound. Rebuilt bindings agree with the frozen 65-entry map. | Windows candidate access must exclude the evaluator cache and review material; exact admission and native execution remain pending. Linux results do not prove this Windows boundary. |
| WP-05 conversations | [verified] All 18 scenario and six review-file hashes agree with their manifest; INC-05/06 remain held out. Current catalog/scenario validation passes. | Human semantic case admission and frozen runtime/run conditions; Windows publication failures below must be understood before relying on saved evidence. |
| WP-08 repair | [verified] Restored all 500 original dataset rows at `78f471bf655a3137b2e8a75af1501690ec009ec3`, verified the 6,304,616-byte parquet and dataset card, and re-fetched ten base-bound licence files. The rebuilt ten-case complex proposal exactly matches the committed proposal. | Complex selection is still pending human acceptance. Hard quotas, native Linux CLI, immutable task images, optional verifier environment and full smoke are not qualified. |
| WP-09 SWT | [verified] Clean source `330a649a764fab2fadaea632776eeae87272f74b`; all five source rows satisfy the frozen selection/filter. Prepared separate author/verifier trees and a false-by-default admission packet. | Optional upstream environment, compatible images, full smoke, exact acceptance and test-relevance review. |
| WP-09 Terminal-Bench | [verified] Clean source `2fd12b88aafdd04a52c298e3940bcb189f9766d6`; all five source packets passed the adapter's hash checks and were staged with hidden tests/solutions separate. | Optional pinned Harbor environment, ten immutable author/verifier images, per-case smoke and exact acceptance. |

[verified] These are source and structural results. The prepared author/verifier directory split
is not proof of runtime containment. Original admission fields remain pending. The shared interpreter
is Python 3.14.7 with Polars 2.0.0; it has no SWE-bench or Harbor installation. Their documented
separate environments remain prerequisites rather than changes to the shared environment.

## Docker quota failure

[verified] The quota receipts observed Docker Engine **29.9.2**, Linux x86_64, `overlayfs`, with
`driver-type=io.containerd.snapshotter.v1`. An earlier inventory reported 29.8.2; the receipts keep
their own observed identity, and a future campaign must freeze the settled runtime again.

[verified] The create-only probe accepted `--storage-opt size=10G`. A separate diagnostic then
requested **33,554,432 bytes** (`32M`) and wrote **67,108,864 bytes** successfully to the container's
writable layer. Docker inspection still reported `StorageOpt: {"size":"32M"}`. Both the write and
container exited 0. There were no mounts, network access, image pulls or benchmark workloads.
The two receipts confirm the exact probe containers absent after cleanup.

This falsifies the assumption that successful creation or a retained StorageOpt proves enforcement
on this engine. It is a bounded diagnostic, not a successful 10 GiB smoke. WP-08/SWT/Harbor must not
proceed under this host configuration: the [accepted profile](../fleet-evaluation/run-plan-wp08-swebench-repair.md)
requires an actual hard quota for author and verifier containers. The existing
[smoke](../../evals/swebench_adapter/smoke.py) still requires observed quota rejection; its checks
were not relaxed.

[sourced: official documentation via Context7, checked against the published page] Docker documents
the size option for selected classic drivers and requires XFS with `pquota` for `overlay2`.
The [storage-option reference](https://docs.docker.com/reference/cli/docker/container/run/#set-storage-driver-options-per-container---storage-opt)
and [containerd image-store guide](https://docs.docker.com/engine/storage/containerd/) distinguish
that driver from the containerd `overlayfs` snapshotter.
[sourced: upstream source via GitHits] Moby at `4237bc6c` passes StorageOpt into
[createLayer](https://github.com/moby/moby/blob/4237bc6c/daemon/containerd/image_snapshot.go#L25-L96),
but that function does not apply those options when preparing the snapshot. This supports the
observed failure mechanism; it is not a claim that the inspected upstream commit is the installed binary.

Recommended next design decision: retain the hard-quota requirement and qualify a dedicated Linux
evaluation engine using a supported quota-capable filesystem/driver, such as `overlay2` on XFS with
`pquota`. Changing the Windows Docker Desktop host selection requires the owner's amendment to
DEC-03 and the run conditions. Reconfiguring the shared Desktop data store or substituting polling,
a whole-VM disk limit, or a typed `storage_quota: true` does not establish the per-container contract.
Any replacement needs the actual 10 GiB fill, network, CPU, verifier and cleanup smoke before trials.

## Windows check results

[verified] Existing checks ran against the source revision above, with no product/test changes:

- `evals/catalog.py check`: 35 suites, 409 native cases, 23 tracks; valid.
- `evals/build_probe.py validate`: 409 specifications and 2,260 expectations; valid.
- `evals/itbench_pilot.py validate`: five cases valid; admission pending.
- `evals/harbor_pilot.py validate`: five cases valid; execution/admission pending.
- Focused Windows pytest selection: **247 passed, 26 failed, 7 skipped in 71.88 seconds**;
  `pytest-host.xml` retains every result. The first sandboxed attempt had 230 passes, 43 failures
  and seven skips; access to the configured `C:\fleet-eval-tmp` root required an authorized host rerun.
  The rerun is a changed environment, not a replacement of the first result.

The focused selection comprises the five `test_itbench_*`/`test_wp04_linux_cli.py` files,
`test_incident_conversations.py`, `test_swebench_configuration.py`, `test_swebench_limits.py`,
`test_swebench_smoke_runtime.py`, `test_swebench_complex_selection.py`, `test_swt_adapter.py`,
and `test_harbor_adapter.py`. Linux-only and POSIX-only controls remain skipped on Windows.

| Failures | Evidence and remediation direction |
|---|---|
| 4 symlink setup failures | [verified] WinError 1314 before the intended assertion: this account lacks the needed symlink privilege. Preserve the controls and establish an authorized Windows environment capable of exercising them. |
| 17 smoke checks | [verified] Their shared stub requires a verifier path ending in literal `/swebench_adapter/verifier.py`, while the actual Windows argument uses backslashes. The retained smoke reports unresolved host-process cleanup before any verifier call. Use path components in the test fixture, then rerun the controls; do not weaken the production cleanup gate. |
| 1 subprocess-output check | [verified] The test's `print` child emits CRLF on Windows but expects literal LF bytes. Make the fixture emit explicit bytes or state a platform-aware output contract while preserving byte-faithful capture. |
| 1 committed-selection check | [verified] The exact-byte assertion fails on the temporary Git fixture. [unverified] Default newline conversion is the leading source-level explanation; compare worktree/blob bytes before repairing the fixture. |
| 1 interruption check | [verified] The isolated SIGINT driver exits 2 instead of returning the expected interruption receipt. [unverified] Windows signal-delivery behavior needs a focused reproduction. |
| 2 conversation publications | [verified] WinError 5 renaming the hidden attempt to `run-1`, including an interrupted session. [unverified] The lock/handle owner is not established; retain the attempts and diagnose the publication boundary before adding any retry. |

These failures predate this documentation change. They prevent a passing Windows-readiness claim.
No full suite or model campaign was started to mask the focused failures. The observed Docker quota
failure is independent of these offline fixtures.

## Completion audit

[sourced: accepted specification and current roadmap] The original EVAL-012 program includes the
following obligations. This table is a dated audit of the [delivery contract](../fleet-evaluation/delivery.md),
not a replacement backlog or a new scope amendment.

| Packages | Evidence/disposition still required |
|---|---|
| WP-00/01/02 | Existing accepted foundation and native-readiness records remain scoped to their exact historical revisions and hosts. |
| WP-03 | Deferred judge comparison remains under EVAL-015; a new judge campaign requires its own admission/calibration. |
| WP-04/05 | Complete independent operational/semantic review, Windows runtime qualification where selected, and exact bounded campaign acceptance. Five historical Linux WP-04 attempts do not supply upstream judge or human semantic results. |
| WP-06/07 | SREGym live diagnosis and guided recovery still need the selected lab, lifecycle controls, actor/budget decisions and observed outcomes. No repository adapter entrypoint is recorded in the current track catalog. |
| WP-08/09 | Resolve the measured host failure and other prerequisites above; then perform owner-started smoke, first-trial review and bounded campaigns under their accepted plans. |
| WP-10 | Recover the private Linux evidence for exact review; resolve/disposition Terra reliability, GCP B, quotation/instrument gaps and wider-fleet/judge coverage. The retained combination differs from the measured three-file experiment; no automatic rerun or promotion. |
| WP-11 | Later AIOpsLab expansion still requires its selected coverage goal and lifecycle/report evidence. |
| WP-12/13 | Complete under the recorded owner decisions. BRANCH-001 and HANDOVER-001 retain the separately owned branching/human exercises; they do not reopen WP-13. |
| WP-14 | Live GCP remains a separate selected-project/actor/budget decision and eight observed exercise outcomes; synthetic cases do not substitute. |
| WP-15 | Coder Eval remains postponed to its useful-comparison prerequisite and owner go/no-go; no adoption is inferred. |

Finishing this program requires those acceptance outcomes or an explicit owner-approved scope
amendment. Source preparation, merged adapters and structural checks alone cannot close EVAL-012.
