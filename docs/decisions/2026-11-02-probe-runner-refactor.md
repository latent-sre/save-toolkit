# ADR: Rewrite the eval runner's core around a persisted evidence artifact

- **Date:** 2026-11-02
- **Status:** accepted for implementation by the owner on 2026-11-02; each stage's exact candidate is
  accepted separately on its own evidence
- **Amended:** 2026-11-02, by the decision owner: the decisions under "Decision needed" are made and
  recorded under "Decisions made"
- **Amended:** 2026-11-03, by the decision owner: the shadow gate is waived and stage 4 proceeds on
  the goldens alone; recorded under "Decisions made"
- **Amended:** 2026-11-03, by the decision owner, after stage 4 landed: stage 5 is in scope as its
  own change; recorded under "Decisions made"
- **Decision owner:** the human owner; a maintainer session implements each accepted stage
- **Roadmap item:** `RUNNER-001` in [the fleet roadmap](../fleet-roadmap.md)
- **Keeps:** [2026-09-03-one-eval-runner](2026-09-03-one-eval-runner.md),
  [2026-09-04-eight-grader-registry](2026-09-04-eight-grader-registry.md),
  [2026-10-03-eval-harness-threat-model](2026-10-03-eval-harness-threat-model.md) result rules 1 to 8,
  [2026-10-25-explicit-native-selections](2026-10-25-explicit-native-selections.md), and the v1 record

## Context

### Problem and context

`evals/probe/` is 8,632 lines in 20 modules and is the only thing that turns a trial into a verdict.
It works: 5,151 offline tests pass on it and every saved result binds its digest. The shape is the
cost, measured on `bd7fe0b` `[verified]`:

- **Evidence is never one thing.** A live trial grades from a `Context` assembled in
  `trials._run_trial` (168 lines, 29 branches) out of the workspace, the parsed trace, git facts and
  running services. A regrade rebuilds an equivalent `Context` in `rescoring._regrade_run` (165
  lines, 35 branches) from a dozen saved artifacts: `stdout.jsonl`, `invocation.json`,
  `response.md`, `trace-summary.json`, `grading.json`, the summary row, state files, and
  `conversation.json` for native runs. It does so with reconstruction heuristics
  (`_saved_tool_counts`, `tracing.from_saved`, a `_run_level_reason` with eleven parameters, a
  `native_regrade_problem` with 43 branches), each a guess about what the live run knew. Both paths
  then assemble the grading record by hand. The package docstring promises "the one grading loop";
  that holds for `assessment.assess` and not for what surrounds it.
- **The result rules are implicit.** Rules 1 to 8 of the threat model are spread across identity
  checks in two functions, `void_over_cut`, `CutShort`, `assessment.roll_up`, cleanup handling and
  `Ending`. No module names a rule; a reviewer verifying rule 6 reads four files.
- **Live-only and pure checks are not distinguished at the boundary.** Of 32 registered checks, 20
  grade from saved evidence and 12 need the live workspace (`file_exists`, `glob_exists`,
  `file_contains`, `command_exit_zero`, `command_output_regex`, `changed_files_not_containing`,
  `ran_outside_checkout`, `service_get`, `service_array_item`, `service_unchanged`,
  `grafana_dashboard_write`, `grafana_query_succeeded`) `[verified]` `checking.REGRADABLE`. A regrade
  keeps their live verdicts through `kept`, which is correct, but the knowledge of what a regrade can
  establish lives in the registry flags rather than in the evidence itself.
- **`checking.py` is 1,442 lines in one file**, registry mechanism and six check domains together;
  two import cycles survive on lazy imports; `cli.run` is 132 lines and the most-changed module; ten
  of twenty modules have no dedicated test file.

Two mechanisms shape any change: the runner identity (`fingerprints.HARNESS_FILES` digests
`probe/*.py` only, by `glob`, so a sub-package escapes it `[verified]` `fingerprints.py:34`), and the
patch-seam convention that 107 test files rely on (`checking.CHECKS` 46 references,
`probe_fingerprints` 28, `probe_backing` 26, `probe_catalog` 21, `probe_invocation` 17).

### Goals / non-goals

Goals: an attempt produces one versioned evidence artifact that grading reads and nothing else;
grading is a pure function of scenario and evidence, so live grade and regrade are the same call;
each threat-model rule is a named unit with its own test; the twelve live-only checks run once as
probes whose results are evidence; every CLI subcommand, saved-run interface, v1 record and result
rule is unchanged; every public name tests and tools import today stays importable.

Non-goals: new checks or graders; any change to the v1 record, the scenario schema or the result
rules; a generic runner for other engines, which the 2026-10-25 decision forbids; retiring campaign
adapters; live model behavior.

### Options

1. **Do nothing.** Two-way door; the duplication above is paid on every result-rule change.
2. **Refactor in place in four stages** (the first version of this record): a check package with a
   facade, cycles removed, one `evidence.py` boundary with `from_live` and `from_saved`
   constructors. Keeps the reconstruction heuristics, since regrade still reads a dozen artifacts;
   gives each rule one home but not a name. Two-way door per stage. Fallback if option 3 is declined.
3. **Rewrite the core around a persisted evidence artifact; port the leaves; cut over in shadow**
   (recommended, detailed under Decision). The six core modules (`trials`, `rescoring`,
   `assessment`, `cli`, `invocation`, `batches`: 3,324 lines) are rewritten; the thirteen leaf
   modules (5,280 lines: tracing, backing, workspaces, fingerprints, records, layout, outcomes,
   constants, exits, selection, conversations, catalog, checking) are ported with the registry split
   and cycle removal from option 2. Costs a new persisted contract, a shadow period on the owner's
   paid trials, and the rewrite of roughly 3,000 test lines. Two-way until cut-over, which reverts by
   restoring the old engine behind the same CLI.
4. **Rewrite everything, leaves included.** Rejected: the leaves are the best-tested code in the
   package (`tracing` 737 test lines, `backing` 9 test files, `catalog` 30), hold no duplication,
   and carry the file-format knowledge a rewrite would have to rediscover.

## Decision

We will rewrite the runner's core around an evidence artifact, port its leaves, and cut over only
after the new engine has graded the owner's real attempts identically in shadow.

### The target shape

- **`evidence.json`, evidence-v1.** Written once per attempt beside today's artifacts, versioned,
  validated by a Pydantic model the way `records.RecordV1` is. It holds: candidate and runner
  identity, the scenario identity and judge binding, the parsed trace facts (the `TraceSummary`
  fields, plus a digest of `stdout.jsonl` so the raw trace stays the primary source), git facts and
  the workspace change list, service observations, tool counts with an explicit completeness flag,
  how the run ended (`Stop` and `Ending`), the native conversation's per-turn facts, and the
  outcomes of the probes. It carries no verdicts.
- **Probes and checks.** The twelve live-only checks become *probes*: they run once, at trial time,
  in the workspace, and their outcomes are stored in the evidence. The twenty pure checks become
  *checks* over evidence. The registry and `@declare` survive; a declaration says which of the two
  a name is. A regrade therefore never needs a workspace, a service or a judge call: a probe's
  outcome is evidence, and a rubric judge's verdict is kept the way it is today.
- **`grade(scenario, evidence, kept) -> Verdict`.** Pure and deterministic. The live path and the
  regrade path call it with the same evidence object, so there is no `from_saved` and no
  reconstruction. `Verdict` is what `grading.json` and the v1 record are rendered from, by one
  renderer.
- **`rules.py`.** Rules 1 to 8 as named functions (`rule_1_identity`, `rule_2_polarity_on_cut`,
  `rule_3_roll_up`, `rule_4_turn_limit`, `rule_5_machinery_failure`, `rule_6_after_assessment`,
  `rule_7_attempts_kept`, `rule_8_regrade_adds`), each with its own test, each cited from the
  threat model by number. `grade` and the attempt state machine call them by name.
- **`attempt.py`, an explicit state machine.** `prepared -> served -> seeded -> invoked -> observed
  -> probed -> graded -> published`, with the failure transitions the rules define: identity mismatch
  voids the attempt (rule 1), a machinery failure stops the scenario (rule 5), a cleanup failure
  after grading is recorded beside the verdict and blocks environment reuse (rule 6). Every attempt
  is kept (rule 7). The state is one object, written to `attempt.json` at each transition, so an
  attempt that raised shows where it stopped.
- **`legacy.py`.** The only place today's reconstruction survives: it loads a pre-evidence run
  directory into an evidence object so `regrade` and `rescore` keep working on every saved
  iteration. It is quarantined, tested against the stage-0 goldens, and never used for a run that
  has `evidence.json`.
- **The CLI, `batches`, and the identity scheme are unchanged** in interface. `HARNESS_FILES`
  widens to `rglob` so the new sub-packages are bound; `case_sha256` is untouched (DEC-22).

### Stages, one pull request each

0. **Goldens.** A fixture of synthetic saved runs covering each rule and each `Ending`, with their
   `grading.json`, `record.json` and summary rows normalised. Extends `test_probe_rescoring.py`'s
   byte-for-byte snapshots `[verified]` lines 571 to 621. No runner bytes change.
1. **Expand: write `evidence.json` from the current runner.** The live path serialises what it
   already has; the regrade path writes it after reconstruction. Nothing reads it yet. The model and
   schema land with it; `legacy.py` is this stage's reconstruction code, moved, not rewritten.
2. **Port the leaves.** The check registry becomes `probe/checks/` (registry plus domain modules)
   with `checking.py` as a facade and probes marked; the two cycles go (`SLUG` and
   `_grader_problems` to a leaf `specs.py`, `saved_folders` to `layout`); `HARNESS_FILES` widens and
   its identity test asserts the sub-packages.
3. **The new engine in shadow.** `rules.py`, `attempt.py`, `grade`, the `Verdict` renderer. Every
   live trial and every regrade runs both engines; the old one stays authoritative; the new one's
   verdict is written to `shadow.json` and any disagreement is a test failure offline and a reported
   row in the owner's runs. Gate to stage 4: the goldens agree, and the owner's private iterations
   show zero disagreements across a count the owner sets. Shadow grading spends nothing extra:
   grading is offline and rubric verdicts are kept.
4. **Contract: cut over.** The new engine becomes authoritative; `trials`, `rescoring` and the old
   `assessment` loop are deleted; `legacy.py` remains for old directories. Recovery: revert this one
   commit; stage 3 left the old engine intact behind the same CLI.
5. **The command line (optional).** `cli.run` splits into preflight, scheduling with the budget
   stop, and conclusion.

Every stage: `python -m ruff check`, `python -m ruff format --check`, `python -m mypy`,
`python evals/build_probe.py validate`, the heavy `test_probe_*.py` files, the seam and identity
contract tests, the record-schema equality test, Gate A, and the goldens. Stage 4 additionally
requires the owner's shadow count and a `rescore` then `diff` of one private iteration with zero
changed verdicts; this repository holds no saved live runs `[verified]` `.eval-runs/` is ignored
and empty, so those two checks can only run on the owner's machine.

## Consequences

### Contracts and consumers

Created: `evidence.json` (evidence-v1), `attempt.json`'s state transitions, and `shadow.json`
during stage 3. Changed: the module layout under `probe/`, the dependency order in
`probe/__init__.py`, and the runner identity once per code stage. Unchanged: `build_probe.py` and
its subcommands, the v1 record and its published schema, `grading.json`, `provenance.json`,
`timing.json` and summary rows, the scenario schema, graders, and every result rule.

Known consumers `[verified]` by import grep: `codex_probe` and `muse_probe` (catalog, checking,
workspaces, outcomes, `tracing.TraceSummary`); `compare_runs` (batches, catalog, fingerprints,
layout, exits, outcomes, records); `campaign_report` and `turn_counts` (layout, records, exits);
`evals/catalog.py`; `testing_block`; `probe_testkit`; and 107 test files. Facades keep each name
importable from today's module through stage 4; after cut-over the deleted modules' names are
re-exported from their replacements until the last test moves. Consumers outside this repository:
unknown `[unverified]`; the private `.eval-runs/` readers are whatever the owner runs against them.
A consequence, not a goal: `codex_probe` and `muse_probe` could produce evidence objects and reuse
`grade` instead of importing `checking` directly; that is a later decision and not this one.

### Failure modes

- The new engine disagrees with the old on real evidence. Detected in shadow before it is
  authoritative; owned by the implementing session, which fixes the engine or the golden, never the
  evidence.
- `evidence.json` omits something a check needs, so a regrade of a new-format run is weaker than a
  regrade of an old one. Detected by regrading the goldens from evidence alone and by the
  twenty-check inventory, which the evidence model's tests enumerate.
- A test patches a name the runner no longer reads through that module. Detected by the test and
  the seam contract test; the facade is the fix.
- The sub-packages escape the harness digest. Detected by the widened identity test.
- `legacy.py` drifts from the directories it must read. Detected by the goldens, which are
  old-format directories by construction.

### Rollout and recovery

One pull request per stage, in order; each merges only on its own evidence. Stages 0 to 3 revert
independently with no consumer change. Stage 4 reverts by restoring the old engine, which stage 3
kept behind the same command line. No saved result is rewritten at any stage (rule 8), and old
directories stay readable through `legacy.py` for as long as the owner keeps them.

### Verification

Proposed, none run: the goldens per rule and per ending; a test per rule in `rules.py`; the
evidence model's round-trip and completeness tests; shadow agreement on the goldens in CI and on the
owner's private iterations; the existing seam, identity and schema contract tests; the owner's
rescore and diff before stage 4.

### Operational cost

No production surface. Ongoing: three new modules and one new artifact to keep documented in
`evals/docs/internals.md`; roughly 3,000 test lines rewritten across stages 3 and 4 `[unverified]`
estimate from `test_probe_trials.py` 1,689, `test_probe_rescoring.py` 823 and
`test_probe_assessment.py` 492. The owner's time: setting the shadow count, running the shadow
trials they would run anyway, and one rescore and diff.

### Decisions made

Made by the decision owner on 2026-11-02, after stage 0 landed:

- Option 3 is accepted.
- `evidence.json` carries the parsed trace facts in full.
- The shadow gate is 30 private attempts with zero disagreements, and among them at least one
  native conversation, one cut-short run and one machinery failure; fewer attempts, or a count that
  lacks any of the three, holds stage 4.
- Stage 5 is out of scope; it is proposed again on its own if wanted.
- `runner_source_sha256` changes at stages 1 to 4; strict regrades of earlier runs then need
  `--relax-identity`.
- Two stage 0 findings are resolved by the result-rules ADR's amendment of the same date: a backing
  service that never starts is a rule 5 measurement failure with no ending, and a cleanup failure
  after grading is the live attempt's evidence that a regrade does not carry. The third is a defect:
  a regrade records a grading-machinery failure in rule 1's form; stage 3's engine records it as a
  grader error on a live grade and on a regrade alike, and the `machinery_failure` golden is
  regenerated in that stage with the changed view explained.

Made by the decision owner on 2026-11-03, after stage 3 landed:

- The shadow gate is waived. No private iteration ran under stage 3, so the goldens are the only
  agreement evidence; stage 4 proceeds on them, and the cut-over is unproven on real runs, as the
  weakest point below says, until the owner's first rescore and diff of a private iteration under
  the cut-over runner. The `shadow` command and `shadow.json` are removed with the cut-over.

Made by the decision owner on 2026-11-03, after stage 4 landed:

- Stage 5, the optional command-line split, is in scope and proposed as its own change: `cli.run`
  splits into the batch's plan, its scheduling with the budget stop, and its conclusion, with no
  result rule, saved-run interface, exit code or command-line flag changed.

### Decision needed

- Accept option 3, or hold at option 2.
- The shadow gate: how many private attempts with zero disagreements before cut-over.
- Whether stage 5 is in scope.
- Accept that `runner_source_sha256` changes at stages 1 to 4 and that strict regrades of earlier
  runs then need `--relax-identity`.
- Whether `evidence.json` may carry the parsed trace facts in full, or only a digest with the raw
  trace as the source; the first makes regrade independent of `stdout.jsonl`, the second keeps the
  artifact small. Recommended: in full, since the raw trace is already owner-only.

### Assumptions

- The twelve live-only checks can be run as probes at trial time without changing their verdicts
  `[verified]` they already run then; a regrade keeps their verdicts today.
- The goldens can be built from the stub-driven fixtures `test_probe_trials.py` uses, without a
  model call `[unverified]` until stage 0 is written.
- No consumer outside this repository imports `probe` internals `[unverified]`.
- The owner runs enough real trials during stage 3 for the shadow count to mean something
  `[unverified]`; if not, stage 4 waits.

### Weakest point

The shadow gate. The goldens prove agreement on fixtured runs; only the owner's real iterations
prove it on the branches nobody fixtured, and this repository cannot run them. A reviewer should
push on whether the chosen shadow count covers a native conversation, a cut-short run and a
machinery failure, not only clean passes, and should treat a cut-over without that coverage as
unproven.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>". -->
