# Discovery and selection implementation plan

**Goal:** Implement the approved discovery-first design over existing tests and evals.

**Architecture:** A read-only catalog owns suite parsing and export. The coordinated pytest runner
consumes its test projection. The native runner admits frozen selections through its existing path.

**Tech stack:** Existing Python 3.12-compatible code, JSON, argparse, pytest; no new dependencies.

**Spec:** [Discovery and selection design](discovery-and-selection-design.md).
**Base:** refreshed main `4d9d368d`; implementation branch `work/eval-discovery-selection`.

## Constraints and review focus

Preserve current paths, IDs, grading, legacy commands, CI shards, and evidence. Organize first and
hash finalized definitions. Do not launch live evals, overwrite historical records, or add another
execution framework. Keep the new four-model testing block and profile admissions intact.

Review selection errors before live effects; trial windows versus report denominators; pytest
option values versus positional paths; test-only lookup without optional SDK imports; preservation
of README anchors and links when moving prose. Tests below cover each boundary.

## Task 1: catalog and explicit suites

Files: new `evals/catalog.py`, `evals/suites/*.json`, `evals/test_catalog.py`; update `pyproject.toml`.
Interface: `main(argv=None) -> int`; JSON envelope `{schema_version: 1, view, items}`; tests view
has `{path, selected_by}`. Native rows derive from `probe.catalog`, never mutate scenario mappings.

- [x] Add failing CLI tests for inventory, union/filtering, safe references, malformed suites,
  and test-only lookup in a minimal copied repository without native imports.
- [x] Implement discovery/check/show and the five initial suites; run focused tests to green.
- [x] Add failing export tests for exclusive output, case hashes, trial bounds, and reporter reuse;
  implement `select` and rerun catalog tests.

## Task 2: coordinated offline selection

Files: `scripts/local_tests.py`, `scripts/test_local_tests.py`.
Consumes Task 1's test JSON with the same interpreter; retains suite resolution in the receipt.

- [x] Add failing real-process tests for suite execution, narrowing, unknown suites, extra
  paths, duplicate suites, inherited options, and no effect on legacy execution.
- [x] Implement wrapper options, bounded catalog invocation, and pytest-parsed positional checks.
- [x] Run local runner and heavy-selection tests to green.

## Task 3: frozen native selection

Files: new `evals/probe/selection.py`, `evals/test_native_selection.py`; `evals/probe/cli.py`;
new narrow successor ADR and its index entry.
Consumes `native-selection-v1` with top-level trials and case hashes; produces retained exact
selection bytes without changing v1 records. Export and admission use the same documented shape.

- [x] Add failing tests for snapshot admission, stale/missing/duplicate cases, slot windows,
  CLI conflicts, failure before preflight, exact-byte retention, and publication failure.
- [x] Implement admission and existing runner integration; verify old defaults/flags still work.
- [x] Run selection, catalog, runner CLI, fingerprint, and campaign-report tests to green.

## Task 4: documentation and integration

Files: `evals/README.md`, new `evals/docs/*.md`, `CONTRIBUTING.md`, design/index documents.

- [x] Move existing prose into running, authoring, internals, and case guides; keep old anchors
  as links and update moved relative links. Put working catalog/suite commands in the landing page.
- [x] Run links, Ruff, formatter, mypy, scenario validation, and focused integration checks.
- [x] Compare old/new saved-run rescoring, then run the coordinated full suite with `--heavy`; repeat only for a material fix.
- [x] Obtain one fresh whole-change review, resolve material findings, and retain evidence.

## Execution notes

The user authorized implementation of the design; no further plan approval is needed. Changes
remain local and uncommitted unless separately requested. Existing accepted ADR bytes stay intact.
Task 1 produces the JSON projection consumed by Task 2 and frozen shape consumed by Task 3; Task 4
documents those interfaces. No interface conflicts found at preflight.


## Completion evidence

This section records the initial five-suite implementation. The owner subsequently approved the
coverage expansion below; later evidence is recorded separately.

[verified] Implemented on the refreshed `4d9d368d` base, in the local uncommitted worktree on
`work/eval-discovery-selection`. The catalog validates five suites and all 405 native scenarios;
scenario validation reports 2,256 expectations. The eval landing page is 133 lines, with the
original detailed sections moved into four guides and old anchors preserved.

[verified] Final `python scripts/local_tests.py --heavy` passed with 5,231 tests and 5,162 subtests;
94 checks were skipped. The skipped checks require Windows/PowerShell, explicit UI/Docker opt-in,
external producer/source fixtures, or the separate optional SWT environment. Python was 3.14.8;
the run used the normal ten-worker setting and completed in 84.388 seconds. The local receipt,
JUnit report, and log are in the common Git directory under
`local-test-runs/20261025T231910Z-0855f4ba/`. No live model trials ran.

[verified] Ruff, formatting, mypy (72 source files), link checks, and Gate A (2/2 steps) passed.
The synthetic native CLI integration ran one of three frozen slots, reported two missing, and
resumed the remaining two from the retained selection after the original file was removed.

[verified] Base and candidate runners rescored the same 15 saved Python-scope trials, including
both passing and failing results. The diff reports zero verdict/check-state changes, with no rescore
errors. Comparison artifacts remain private under
`.eval-runs/discovery-selection-verification/{base-rescore,candidate-rescore}/`. The saved candidate
runner digest was checked against the final native runner. Historical run records were not rewritten.

[verified] The independent static reviewer inspected tracked and untracked changes and identified
one material issue: a mixed native/offline-only suite export silently omitted the offline-only
suite. Its new regression failed before the fix and passed afterward. The exporter now refuses
any requested suite with no native cases. The full suite above ran after that repair. No additional
review findings remain unresolved; static review of an uncommitted checkout is not human acceptance
of an immutable candidate.

The explicit trial-count parser also has regression coverage for argparse's accepted abbreviated
spelling, so `--trial=2` cannot be mistaken for an omitted count. Existing native model/budget and
host checks, offline lease/receipt behavior, CI partitions, and strict v1 records remain in place.

## Approved coverage expansion

The owner approved inventorying every repository evaluation track, assigning existing cases and
test files to useful suites, and mapping capabilities to current coverage and useful missing evals.
This extends the initial five-suite population without changing scenario definitions or running models.

Implementation sequence:

1. Expand explicit suite membership by capability, covering all current native scenarios and root
   pytest files. Keep independent sandbox suites outside root pytest collection.
2. Add a small track index for implemented runners/adapters, offline proposals, independent
   sandboxes, and planned integrations. Link existing selections through their owning suites;
   a runner without a selection does not become a fictional campaign.
3. Add read-only `tracks` and `coverage` catalog views. Coverage reports membership, actual grader
   kinds, and unassigned entries; it does not infer model quality or acceptance.
4. Add a capability map with evidence limits and prioritized additional evaluation designs,
   referencing the existing roadmap instead of creating a second live backlog.
5. Verify catalog behavior and full membership, run the required offline checks, and review the
   expansion. Preserve the earlier native-runner rescore evidence because native code is unchanged.


## Coverage expansion evidence

[verified] The expanded explicit registry assigns all 405 native cases and all 148 root test files
across 34 capability suites. The track index records 15 present implementations, two inactive
proposals and six planned integrations. Six existing campaign manifests are linked; their execution
and acceptance requirements remain with the original adapters. Independent sandbox tests remain
outside root pytest collection and are discoverable through their track guides.

[verified] `catalog.py coverage` reports unique assignment counts, per-suite native kinds and
explicit check/grader types, including per-turn graders. A regression with a newly unassigned case
and test file proves omissions remain visible. `tracks` validates references and implementation
categories without importing entrypoints; malformed/proposed/readiness claims are covered by tests.
The capability map distinguishes authored cases from measured model quality and proposes useful
additional experiments without creating new scenario definitions or a second live backlog.

[verified] The 34 catalog tests pass. Final `python scripts/local_tests.py` passed with 4,465 tests,
4,396 subtests and 92 skips in 31.15 seconds. The receipt is in the common Git directory under
`local-test-runs/20261025T233801Z-29e6d7a8/`. Ruff, formatting, mypy and link checks pass. The earlier
heavy-suite result remains applicable to the unchanged native runner, graders, fixtures and heavy
selection. Its runner fingerprint still matches the retained zero-difference saved-trace comparison.

[verified] A fresh static review of the expansion found no actionable issues. It inspected all new
suite definitions, track records, discovery/coverage code, tests and source-backed gap claims.
This remains local, uncommitted work, not immutable candidate acceptance. No model, cloud, sandbox
or benchmark campaign was launched by this expansion.
