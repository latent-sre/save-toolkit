# ADR: Refactor the eval runner in place, one stage per pull request

- **Date:** 2026-11-02
- **Status:** proposed
- **Decision owner:** the human owner; a maintainer session implements each accepted stage
- **Roadmap item:** none yet; accepting this record creates one
- **Keeps:** [2026-09-03-one-eval-runner](2026-09-03-one-eval-runner.md),
  [2026-09-04-eight-grader-registry](2026-09-04-eight-grader-registry.md),
  [2026-10-03-eval-harness-threat-model](2026-10-03-eval-harness-threat-model.md) result rules 1 to 8,
  [2026-10-25-explicit-native-selections](2026-10-25-explicit-native-selections.md), and the v1 record

## Context

### Problem and context

`evals/probe/` is 8,632 lines in 20 modules and is the only thing that turns a trial into a verdict.
It works: 5,151 offline tests pass on it, CI is green, and every saved result binds its digest. The
cost is in how it is shaped, measured on `bd7fe0b` `[verified]`:

- **The trial lifecycle is written twice.** `trials._run_trial` (168 lines, 29 branches) builds the
  grading context from a live workspace; `rescoring._regrade_run` (165 lines, 35 branches) rebuilds
  it from saved files. Both decide identity failures, inconclusive reasons and tool-count completeness,
  and both assemble the `grading.json` shape by hand: live through `assessment.grade`, regrade inline
  with its own twelve-key dict. `probe/__init__.py` promises "the one grading loop, shared by live
  grades and regrades"; that holds for `assessment.assess`, the check loop, and not for the evidence
  reconstruction and record assembly around it. A result rule touching either has two places to drift.
- **`checking.py` is 1,442 lines and 88 definitions in one file.** About 250 lines are the registry
  mechanism (`declare`, `Context`, `Need`, `CheckType`, `run`, `registered`); the rest are 35 checks
  across six domains: files and text, git and workspace, services over HTTP, Grafana (lines 588 to
  945, with its own PromQL lexer), shell-command parsing including verification detection (1039 to
  1274), and tool, dispatch, state-file and CF-log checks. The two open runner follow-ups in
  EVAL-012 (unittest `--option=value` spellings, SHA-spelled Git ranges; 0 of 303 and 0 of 909 in
  saved traces) sit in the shell block.
- **Two import cycles are held open by lazy imports.** `conversations` imports `catalog` inside
  `problems()` for `SLUG` and `_grader_problems`, while `catalog` imports `conversations`; and
  `conversations` imports `tracing` inside its replay for `parse_trace`, while `tracing` imports
  `conversations` for `saved_folders`. Each is marked `noqa: PLC0415`.
- **`cli.run` is 132 lines, 28 branches, and the most-changed module** (6 commits in 90 days).
- **Ten of twenty modules have no dedicated test file** (`backing`, `cli`, `conversations`,
  `invocation`, `outcomes`, `records`, `selection`, `workspaces`, `exits`, `constants`). They are
  exercised through integration tests, `test_probe_trials.py` at 1,689 lines foremost, so a defect in
  one surfaces as a failure named after another.

Two mechanisms shape any change here:

- **Identity.** `fingerprints.HARNESS_FILES` digests every `probe/*.py`; the digest is part of every
  `scenario_sha256` and of `provenance.json`. A refactor changes the runner identity once per merged
  commit, and a strict `regrade` of a run saved under the old identity reports "saved scenario
  identity is missing or changed" unless `--relax-identity` is given. `case_sha256` survives
  (DEC-22). The glob is `PACKAGE_DIR.glob("*.py")`, so a sub-package would not be digested
  `[verified]` `evals/probe/fingerprints.py:34`.
- **Patch seams.** Tests patch a function where it is defined and a class or constant where it is
  imported; `test_the_entry_point_offers_no_runner_name_to_patch` and
  `test_the_runner_identity_binds_every_module_in_the_package` enforce it. Tests reference
  `probe_fingerprints` 28 times, `probe_backing` 26, `probe_catalog` 21, `probe_invocation` 17,
  `probe_trials` 15, and `checking.CHECKS` 46 times `[verified]` by grep over `evals/test_*.py`.

### Goals / non-goals

Goals: one evidence-reconstruction boundary feeding one record assembler, so each result rule has one
home; a check registry whose mechanism and domains are separate modules; no import cycle; every
public name tests and tools import today still importable from where they import it; identical
`grading.json`, `record.json` and summary bytes for identical inputs, timing and paths aside.

Non-goals: new checks or graders, any change to the v1 record, the CLI, the result rules, the
scenario schema, the campaign adapters, or live model behavior; a per-process scenario cache; a new
runner for other engines, which [2026-10-25](2026-10-25-explicit-native-selections.md) forbids.

### Options

1. **Do nothing.** Costs the duplication above on every result-rule change, and leaves the two open
   shell-detector follow-ups inside a 1,442-line file. Two-way door.
2. **Refactor in place, four bounded stages, each one pull request** (recommended, detailed under
   Decision). Each stage leaves the runner working, changes the identity once, and keeps a facade for
   every moved name. Two-way door per stage: each reverts alone.
3. **Rewrite around a trial-state pipeline object.** Would reach the same end faster on paper, but
   the runner has no live-eval coverage in CI, so a rewrite's defects surface only in paid trials.
   One-way door in practice. Rejected.
4. **Split `checking.py` only.** Stage 1 of option 2 without the rest. Leaves the duplicated
   lifecycle, which is the costlier of the two problems. Acceptable fallback if the owner stops after
   stage 1.

## Decision

We will refactor `evals/probe/` in place in four stages, each a separate pull request that the owner
accepts on its own evidence, in this order.

**Stage 0, goldens (no `probe/` bytes change).** Add a fixture of synthetic saved runs covering the
result-rule branches: a clean pass, a forbidding-check failure, a cut-short run, plugin drift after
assessment, a backing-service failure before and after assessment, a stale judge binding, a
turn-limit end, a native conversation. Record their `grading.json`, `record.json` and summary rows
with timing, paths and digests normalised. A test regrades each fixture and compares. This is the
behavioral oracle for every later stage; it extends `test_probe_rescoring.py`'s existing byte-for-byte
snapshot checks `[verified]` lines 571 to 621, which cover preservation of the saved run, not the
verdict shape.

**Stage 1, the check registry becomes a package.** `probe/checks/registry.py` holds `declare`,
`Context`, `Need`, `CheckType`, `GraderTraits`, `run`, `registered`, `describe`, `is_regradable`
and `CHECKS`; `files.py`, `workspace.py`, `services.py`, `grafana.py`, `shell.py`, `tools.py` and
`fleet.py` hold the checks, imported in today's order so `CHECKS` keeps its insertion order and
`REGRADABLE` its membership. `probe/checking.py` stays as a facade that re-exports every public name,
so `probe_checking.CHECKS` is the same dict object and a patch of a registry entry reaches every
caller as it does today. `fingerprints.HARNESS_FILES` changes from `glob("*.py")` to `rglob("*.py")`
and `test_the_runner_identity_binds_every_module_in_the_package` asserts the sub-package is bound.

**Stage 2, no cycles.** `catalog.SLUG` and `_grader_problems` move to a leaf `probe/specs.py` that
both `catalog` and `conversations` import; `conversations.saved_folders` moves to `layout`, which
`tracing` already imports. `conversations` then imports `tracing` at module level and `catalog`
not at all; the two `noqa: PLC0415` markers go; `probe/__init__.py`'s dependency order is updated,
since it is the package's stated contract.

**Stage 3, one evidence boundary.** A new `probe/evidence.py` defines the inputs `assessment.grade`
needs (trace, git facts, workspace, services, identity, tool-count completeness, the run-level
inconclusive reason) with two constructors: `from_live(...)`, which `trials._run_trial` calls, and
`from_saved(...)`, which `rescoring._regrade_run` calls. `assessment.grade` becomes the only writer of
the grading record, taking a `regraded`/`kept` parameter instead of `_regrade_run` assembling its own
dict. `_run_trial` and `_regrade_run` shrink to orchestration: workspace and services around the
call, files written after it. Target: neither above 80 lines. Stage 0's goldens must be byte-identical
before and after.

**Stage 4, the command line (optional).** `cli.run` splits into the preflight it already has,
scheduling with the budget stop, and the conclusion it already has, each testable without a batch.
The owner may decline this stage; it carries the least value.

Every stage: `python -m ruff check`, `python -m ruff format --check`, `python -m mypy`,
`python evals/build_probe.py validate`, the heavy `test_probe_*.py` files, the seam and identity
contract tests, the record-schema equality test, and Gate A. Stage 3 additionally requires the owner
to run `build_probe.py rescore` on one of their private saved iterations before and after, then
`diff` the two, and to find zero changed verdicts; this repository holds no saved live runs, so
that comparison cannot be run here `[verified]` `.eval-runs/` is ignored and empty.

## Consequences

### Contracts and consumers

Changed: the module layout under `probe/`, the dependency order in `probe/__init__.py`, and the
runner identity once per stage. Unchanged: `build_probe.py` and its subcommands, the v1 record and
its published schema, `grading.json`, `provenance.json`, `timing.json` and summary rows, the scenario
schema, graders, and every result rule.

Known consumers `[verified]` by import grep: `codex_probe`, `muse_probe` (catalog, checking,
workspaces, outcomes, `tracing.TraceSummary`); `compare_runs` (batches, catalog, fingerprints, layout,
exits, outcomes, records); `campaign_report` and `turn_counts` (layout, records, exits);
`evals/catalog.py` (catalog, fingerprints); `testing_block` (catalog, constants, fingerprints, layout,
records); `probe_testkit`; and 107 test files. Facades keep each name importable from today's module.
Consumers outside this repository: unknown `[unverified]`; the private `.eval-runs/` readers are
whatever the owner runs against them.

### Failure modes

- A verdict differs for identical saved evidence after stage 3. Detected by the stage 0 goldens in
  CI and by the owner's private rescore and diff; owned by the implementing session, which reverts
  the stage.
- A test patches a name the runner no longer reads through that module. Detected by the test failing
  and by the seam contract test; the facade is the fix, never a second lookup path.
- The sub-package escapes the harness digest. Detected by the widened identity test; without it,
  check code could change while `runner_source_sha256` stayed, which would misattribute results.
- `CHECKS` order or `REGRADABLE` membership changes, altering `assertion_id` positions. Detected by
  the goldens, whose `scenario_sha256` stamps every position.
- Validation error strings change when `_grader_problems` moves. Detected by the catalog tests that
  pin them; strings move with the function.

### Rollout and recovery

One pull request per stage, in order; a stage merges only on its own evidence. Recovery for any
stage is `git revert` of its commit: the facades mean no consumer changed, and saved runs regrade
under the reverted identity exactly as before. No saved result is rewritten at any stage (threat
model rule 8).

### Operational cost

No production surface. Ongoing: one more package and one more leaf module to keep in
`probe/__init__.py`'s order; `evals/docs/internals.md` "Runner layout" updated at stages 1 to 3.
The owner's time: one private rescore and diff at stage 3.

### Decision needed

- Accept option 2 and the stage order, or stop after stage 1 (option 4).
- Whether stage 4 is in scope.
- Whether the owner will run the private rescore and diff before stage 3 merges, and on which
  iteration; without it, stage 3's evidence is the goldens alone.
- Accept that `runner_source_sha256` changes at each of stages 1 to 3 and that strict regrades of
  earlier runs then need `--relax-identity`.

### Assumptions

- The goldens can be built from the stub-driven trial fixtures `test_probe_trials.py` already uses,
  without a model call `[unverified]` until stage 0 is written.
- No consumer outside this repository imports `probe` internals `[unverified]`.
- `CHECKS` is read only through the registry at grading time, so a facade preserves patch behavior
  `[verified]` for `test_the_entry_point_offers_no_runner_name_to_patch`; other tests' direct calls
  of check functions are plain calls, which the facade also serves.

### Weakest point

Stage 3. The regrade path carries the most branches in the runner (`native_regrade_problem` alone
has 43), and the goldens cover only the branches someone thought to fixture. A reviewer should push
on whether the fixture set covers every inconclusive reason `_run_level_reason` can return, and
should treat a stage-3 PR without the owner's private rescore and diff as weaker evidence than one
with it.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>". -->
