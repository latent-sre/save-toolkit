# WP-08 Desktop monitored-storage exception implementation plan

> **For agentic workers:** Execute the assigned source slice through test-driven development;
> the root session owns integration, the one final coordinated heavy run and independent review.

**Goal:** Implement the owner's clarified Docker Desktop storage exception without representing
periodic monitoring as a hard quota or changing unrelated campaign admission.

**Architecture:** Preserve the default quota profile. An explicit monitored mode uses the existing
10 GiB target, periodic and final writable-layer observations, fatal monitor failures and owned
cleanup. Bind mode into smoke identity and a distinct common-result execution profile; retain
actual observations outside comparison identity.

**Tech Stack:** Python 3.14, pinned Docker SDK/SWE-bench, Docker Desktop Linux containers.

**Spec:** The owner amendment in
[`run-plan-wp08-swebench-repair.md`](../../fleet-evaluation/run-plan-wp08-swebench-repair.md).
The owner clarified the Desktop exception in this session; implementation proceeds inline with
bounded source ownership and an independent final review.

## Global constraints

- Quota mode remains the default and still requires real `ENOSPC`/`EDQUOT` enforcement evidence.
- Monitored mode requires explicit `storage_mode: monitored` and `storage_quota: false`.
- The target remains `10 * 1024**3`; sampled observations do not guarantee an instantaneous bound.
- Models, key handling, static authoring, independent verification, egress, two CPUs, 2 GiB memory,
  256 processes, case admission, deadlines and separate campaign starts retain their contracts.
- No candidate or judge call is authorized by this implementation step.

## Review focus

1. A false quota flag without explicit mode must remain rejected.
2. Hard and monitored smoke/first-trial bindings and pooled results must remain separate.
3. A short-lived write completing between samples must still receive a final measurement.
4. Missing, invalid or timed-out measurement must stop the attempt and retain cleanup uncertainty.
5. Verifier storage stops must survive host-process receipt finalization without becoming task FAILs.

## Task 1: Explicit configuration and identity

**Files:** `storage.py`, `configuration.py`, `test_swebench_configuration.py`.
**Interface:** `validate_storage_mode(*, quota: object, mode: object = "quota")` accepts only
`(True, "quota")` and `(False, "monitored")`; export monitored sampling interval 5 seconds.

- [x] Demonstrate red controls for normalized mode, malformed/contradictory pairs and mode bindings.
- [x] Add optional configuration mode, normalize it and bind it into runtime/smoke identity.
- [x] Require `storage_cap` for quota; require separate `storage_monitor` for monitored.
- [x] Run focused configuration controls and lint.

## Task 2: Monitored execution and telemetry

**Files:** `containers.py`, `limits.py`, their focused tests.
**Interface:** `start_agent(..., storage_quota, storage_mode="quota")`; cumulative per-container
`storage_observations`; `BoundedContainer(..., storage_observation=None)` shares receipt telemetry.

- [x] Demonstrate red controls for explicit launch, sampled overrun, final overrun and measurement failure.
- [x] Omit unsupported quota options only in explicit monitored mode; preserve all other hardening.
- [x] Measure every five seconds in monitored mode and after normal completion; retain sampled peak/count.
- [x] Preserve typed execution stops, bounded capture and inspected owned cleanup; run focused controls.

## Task 3: Verifier, smoke and result integration

**Files:** `runner.py`, `verifier.py`, `smoke.py`, `artifacts.py`, matching tests and operator docs.

- [x] Demonstrate red controls for verifier mode forwarding/attestation and retained storage stop.
- [x] Preserve required explicit verifier CLI selection: hard quota or monitored storage.
- [x] Give monitored results a distinct execution-profile name and preserve default quota identity.
- [x] Require measured monitored threshold stop and clean cleanup; never turn it into `storage_cap: true`.
- [x] Retain mode, target, sampled peak/count and stop in agent/verifier evidence, outside pooling identity.
- [x] Qualify monitored runtime against the approved Windows Docker Desktop host class.
- [x] Run matching focused checks, source-appropriate lint/format/typing, one coordinated heavy suite,
  a bounded model-free Docker monitor control, and independent final review.
- [x] Update source/evidence notes and retain old quota/observer failures. Publication and paid campaign
  starts remain separate from implementation qualification.
