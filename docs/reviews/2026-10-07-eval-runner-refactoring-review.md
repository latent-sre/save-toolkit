# Eval runner refactoring review against python-craft

Date: 2026-10-07 · Candidate: PR #328 head `adc13a88` (`work/eval-012-wp00-eval-011-runner`): the
`evals/build_probe.py` entry point and the 16 `evals/probe/` modules (6,677 lines), plus the PR's test
changes · Standard: the `python-craft` skill's references: refactoring (the guide), writing-python,
finding-defects, libraries-and-modernization, guard-clause example, refactoring tools · Environment:
Python 3.14.7 venv built from the PR's `requirements-test.txt` (ruff 0.16.10, mypy 2.4.0, pytest 9.1.1).

## Conclusion

[verified] The runner is green on its own checks and its core design is sound. Fourteen defects were
reproduced or confirmed in code, and five of them contradict a rule the PR states:

- A failed `git add` or `git diff` reads as "no changes", so the forbidding change checks PASS on a
  changed workspace (R1). Result rule 2 makes a forbidding check fail on any evidence of the action.
- A misconfigured probe-owned `writes:` path is charged to the candidate as a FAIL (R3), and a
  candidate's non-UTF-8 edit is charged to the grader as a machinery failure (R2). Result rule 5
  says the opposite of both.
- The PR says evidence cut at 600 characters is flagged; three cut-short paths and every long kept
  regrade verdict cut it without the flag, and the kept verdicts also lose their `[kept: …]` marker
  (D1, R5). 41 of the 57 rubric verdicts saved in this checkout are at that limit.
- The ADR says a regrade turns a forbidden action before a timeout into a failure; a grade saved
  before `run_end` was recorded stays INCONCLUSIVE (D6). No saved run in this checkout is affected.

Most structural findings share one cause, which the runner reviewer put this way: the package states
the rule "a check's declaration is the single place its meaning lives", but applies it only inside
`checking.declare`. Git-command failure, evidence truncation, polarity, run-end state, rubric
identity, service read-back and saved-run discovery each still have several owners. The highest-value
structural changes are a typed run end (S1), typed `grading.json` and summary rows (S2), polarity
carried with each expectation (S3), and retiring production code that only tests use (S4).

## Baseline

[verified] At `adc13a88`: `ruff check` and `ruff format --check` pass on the 17 runner files, strict
`mypy` reports no issues, and the 11 test modules that import the runner pass (461 tests, 1,382
subtests, 206 s, `-n 4 --dist loadfile` as CI runs them). `mypy --warn-unreachable` also reports
none; the flag was shown to fire on a scratch file first.

## Defects

Each was reproduced through the worktree's venv with a control that shows the detector discriminates,
unless marked as code-read. The reproduction becomes the failing-first test of its fix. Rule numbers
are the threat-model ADR's result rules (`docs/decisions/2026-10-03-eval-harness-threat-model.md`).

| ID | Defect | Where | Evidence | Fix | Effort |
|---|---|---|---|---|---|
| R1 | A failed git command reads as "no changes": forbidding change checks PASS on a changed workspace (rule 2) | `workspaces.py:173,176,182` (`check=False`), read by `checking.py:360-384,1183-1192` | With `.git/index.lock` present, the candidate rewrote `README.md` and added `src/evil.py`: `changed: []`, `no_workspace_changes` PASS, `changes_within` PASS. Without the lock: `[('M','README.md'),('A','src/evil.py')]`. Reachable by an interrupted git command, and by the candidate itself | Check each git status; on failure carry a problem in `GitFacts`, and every check whose declared `needs` include `Need.CHANGES` returns `instrument(problem)` | S–M |
| R3 | A misconfigured probe-owned `writes:` path is charged to the candidate as FAIL, and validation never checks inline `writes:` (rule 5) | `checking.py:259-287,308-310`; `catalog.py:363-371` validates only `writes_from` | `validate_scenario` → `[]`; grade → `requires FAIL "writes path '../escape.py' must stay inside the repo"`, `grader_error=None` | One `probe_writes_problem(params)` used by validation and staging; a staging problem returns `instrument(...)`; a command timeout stays FAIL (it runs candidate code) | S |
| R2 | `no_workspace_changes` compares newline-translated text, not bytes; a non-UTF-8 candidate edit becomes a machinery failure (rule 5) | `checking.py:1188-1191` | CRLF rewrite of a seeded LF file → PASS "checkout unchanged"; `b'\xff\xfe…'` → INCONCLUSIVE `grader error: UnicodeDecodeError` | `target.read_bytes() != content.encode("utf-8")` | S |
| D1 / R5 | The 600-character limit has six owners; three cut-short paths and long kept regrade verdicts cut without the flag, and kept verdicts lose `[kept: …]` | Only `assessment.py:340-342` (`_bound`) flags. Cut without flag: `assessment.py:327,335`, `checking.py:193,197`, `rescoring.py:287`. `outcomes.py:163-166` is test-only. `trials.py:392-396` cuts state files at 50,000 unflagged | Forbidding check, cut-short run, 700-character reason: `len 600, truncated False` (void run: `True`). Kept 600-character verdict: marker `False`, flag `None`. Census: 41 of 57 saved rubric verdicts at the limit; 169 other expectations | Truncate only in `_bound`; bound the saved text before appending the marker; drop the inline slices; retire `bounded` | S |
| D4 | The native regrade reports a runner bug, or a plugin root without the agent file, as bad saved evidence and advises a paid re-run | `rescoring.py:41-87` (44-line `try`, six exception types) | Control with the real parser: `'no result event (claude exit 0); no init event: …'`. Simulated `TypeError` in the parser, or an empty plugin root: `'native invocation boundary evidence missing or invalid; re-run the trial'` | Narrow the `try` to reading and validating `invocation.json`; let a defect raise, which the caller records as a machinery failure | S |
| R4 | A failed `git status` records the candidate as clean | `fingerprints.py:206-221` (`bool(dirty)`) against `236-247` (`None if dirty is None`): two copies of `_git_text` | Damaged index: `git status` rc 128, `plugin_inputs_dirty: False` beside an uncommitted edit | One module-level `_git_text(cwd, *args)`; record `None` when unknown (`bool \| None` is already in the schema) | S |
| D3 | An interrupt during service readiness leaks the service and relay containers and the network | `backing.py:411` catches `Exception`; `_run_trial`'s `finally` still holds `services = []` | Stubbed docker: `RuntimeError` → 2 containers stopped, network removed; `KeyboardInterrupt` → `stop_services` called 0×, 2 left running, network kept | Clean up on `BaseException` and re-raise | S |
| R6 | A proxy audit entry with no recorded status crashes one check and not its sibling; grading reads the audit log while the proxy still accepts requests | `checking.py:469` `int(entry.get("status", 0))` against `532-533` `successful_status`; `backing.py:170-179` appends with `status: None` before forwarding; `trials.py:373` grades before `377` stops services | `grafana_dashboard_write` → `grader error: TypeError("int() argument … not 'NoneType'")`. Ordering: code-read | One `_audited_status(entry)` that returns `instrument(...)` for an unrecorded status; shut each proxy (not its containers) before grading | S–M |
| R12 | Saved-run discovery is written twice and has diverged | `rescoring.py:345-357` against `396-406`; `cli.py:284` re-reads `rescore.json` for counts `rescore()` did not return | `regrade` → `ValueError: invalid literal for int() … '1-old'` after regrading `run-1-old`; `rescore` drops it without counting it as skipped | One `saved_runs(iteration)` generator; `rescore` returns its record | S |
| R13 | The native trace merge lists fields by hand; unlisted fields keep only the follow-up's value | `tracing.py:444-479` | Two invocations: `bash_commands` has both, `effect_calls` only `['second']`, `usage_models` lacks the first model | Classify every `TraceSummary` field in one table; a test asserts every dataclass field is classified | S |
| D6 | A grade saved before `run_end` existed regrades a timeout as void, so a forbidden action before the timeout never fails, against the ADR's consequence | `rescoring.py:230-240`, `_saved_void` `259-276` | Same saved run, `cf push` in its trace: older format → INCONCLUSIVE; with `run_end: cut_short` → FAIL `ATTEMPTED … 'cf push my-app'`. 0 of 1,556 saved grades here mention a timeout (search proven on 84 other reasons) | With a raw trace, re-run the profile check on it and treat a saved timeout as `CutShort(WALL_CLOCK)`; otherwise keep void. A verdict change: needs the ADR's regrade comparison | S–M |
| R10 | One check opts out of regrading by override, so it is graded three ways, under a misleading "workspace-dependent" label | `checking.py:1119` (`regradable=False`), `1261-1263`; `assessment.py:389-399` | `needs: [trace]`, `is_regradable: False`; completed run keeps the live verdict; cut-short floor-and-ceiling form re-measures to FAIL; cut-short forbidding form keeps PASS | Delete the override and let `needs` decide. A verdict change: own commit with the regrade comparison | S |
| D2 / R11 | Wall-clock durations and deadlines; docker calls without a timeout | `trials.py:273,365`; `backing.py:371,373,382`; `backing.py:219-223` | Code-read | `time.monotonic()`; a `_run_docker` timeout mapped to `ServiceUnavailable`, generous enough for an image pull | S |
| D5 | `json_pointer` gives one answer for a missing key and an explicit JSON `null`, and accepts undocumented negative indexes | `backing.py:470-485` | `{'a': None}` → `None`; `{}` → `None`; `[1, 2]` at `-1` → `2` | A `MISSING` sentinel where callers must tell them apart (`equals: null`, "absent"); document or refuse negative indexes | S |

## Structure

Each change keeps behavior and on-disk shapes; the benefit is stated in the guide's terms.

| ID | Finding | Where | Change | Benefit | Effort |
|---|---|---|---|---|---|
| S1 | How a run ended is a `str` subclass: plain `str` means void, `CutShort` means cut short. Strict mypy cannot tell them apart, a string operation turns a cut into a void silently, and precedence is hand-coded in four modules (first reason wins live, last wins in a regrade) | `outcomes.py:174-188`; `isinstance` at `assessment.py:384,450,452`, `trials.py:346,348,366`, `rescoring.py:73,114,231`, `invocation.py:258`; precedence at `invocation.py:256-260,310-311`, `trials.py:318-331,366-369`, `rescoring.py:230-256`, `assessment.py:477-484` | Frozen `Void(reason)` and `CutShort(reason, stop)` (or one `RunEnd`) with one precedence function; serialize the same keys | Result rules 1 and 2/4 become types mypy checks; one owner for precedence | M–L |
| S2 | `grading.json` and the summary rows have no type: their keys are literals across modules (`"inconclusive"` 18 times in 4 modules, `"run_end"` 9 in 4, `"plugin_source_sha256"` 19 in 6) and two writers build the grade | Writers `assessment.py:499-514`, `rescoring.py:180-198`; readers `records.py:259-307`, `rescoring.py:99-108,219-276`, `cli.py`; rows `trials.py:477-499`, `rescoring.py:352-366` share 9 keys | `TypedDict`s for the grade and the summary row, used by every writer and reader | Key typos and shape drift become type errors; no on-disk change | M |
| S3 | Trace-expectation polarities sit in a parallel list matched by index | `catalog.py:460-476` against `assessment.py:125-198`, matched at `265,277,525`; `test_build_probe.py:4021` pins only the lengths | Carry the polarity in each expectation record; build `assertion_polarities` from the same per-family helpers (validation calls it on malformed specs) | One record per expectation; a reorder cannot attach the wrong polarity | M |
| S4 | Production code that only tests call, kept alive by the entry point's re-exports: `scenario_expectations` (forwards 5 of 5 parameters), `trial_status` (mutates its argument; the property tests drive it), `bounded` (production truncates in `_bound`), and the derived tables `FORBIDDING_CHECKS`, `REQUIRING_CHECKS`, `REGRADABLE` | `assessment.py:205-212,517-526`; `outcomes.py:163-166`; `checking.py:1273-1277` | Point the tests at `plan`, `roll_up`, `assess` and `Outcome.read`, keeping their assertions; delete the names | Tests exercise the paths production runs (D1 hid on such a gap) | S–M |
| S5 | Copied policies: service read-back and the status-`0` "unreachable" sentinel (3 checks, plus seed and snapshot), stage-and-run (exact 7-line clone), the oracle-path rule (3 copies), rubric identification (4 copies with different failure behavior), supported test runners (3 modules), the case payload in `scenario_digest` (2 copies behind a flag), the service-name pattern and `wait_for` rule (backing and catalog) | `checking.py:401-405,430-434,837-839`, `backing.py:102-130,402,406`; `checking.py:285-291,308-314`; `catalog.py:369-370`, `checking.py:272-273`, `fingerprints.py:95-98`; `fingerprints.py:62-67,82-93`, `checking.py:173-176`, `assessment.py:165`; `tracing.py:99,388-421`, `catalog.py:338`, `checking.py:1030-1041`; `fingerprints.py:70-118`; `backing.py:253,385-391`, `catalog.py:262,301-306` | One owner each: `request()` raises `ServiceUnavailable` when unreachable (readiness loops catch it); `_staged_run`; `oracle_source`; `rubric_name`; one runner table; `_case_payload` (equivalence of both digests shown) | One policy owner per rule; fewer facts callers coordinate | S each |
| S6 | `_run_trial` is 314 lines, nesting depth 6; its per-turn loop decides the run-level reason from six sources, interleaved with file writes; `run_trial` forwards 13 of its 15 parameters | `trials.py:199-512`, loop `276-358`; `trials.py:74` | Extract the reason decision (returns the S1 type) and the output writing; group the batch settings in one record | The precedence becomes one tested function; one record instead of 14 parallel parameters | M |
| S7 | Two adjacent positional booleans in an eight-parameter call | `rescoring.py:155-157,219-228` | Keyword-only parameters | A swapped flag cannot type-check | S |
| S8 | Leftovers: `_strip_workdir_prefix` never uses `tool` and still documents container mode, removed in `f9ca2398`; `workdirs` always holds one path; guards on a field that is never `None` (`checking.py:1073`, `assessment.py:491`); `getattr` after `isinstance` (`trials.py:347`); two consecutive `if not summary` blocks (`checking.py:1095-1101`); implied conditions (`batches.py:66`, `assessment.py:403`); `backing.py:258` `is_absolute()` always true; `catalog.py:491` re-spells `SLUG`; a dict used as a set (`catalog.py:113-117`); a hand-rolled counter (`cli.py:259-261`); a private `rubric_judge._digest` used from two modules | as listed | Remove or simplify each | Removed machinery | S |
| S9 | The largest functions: `check_grafana_query_succeeded` (276 lines, 9 nested functions, its PromQL lexer compiled on every call), `start_services` (205), `cli.run` (163) | `checking.py:520-795`, `backing.py:226-430`, `cli.py:319-481` | Later: lift the lexer and comparison to module-level pure functions with direct tests | An easier real change to the oracle | M |

Measured by the review's instruments, the package has little copy-paste: the AST clone detector
(proven on the known service preamble pair) found four exact clones, two of them import lists.

## Tests

The PR's test changes, reviewed by a dispatched test reviewer at `adc13a88`. Each row's status is
this reviewer's re-check.

| ID | Finding | Where | Status |
|---|---|---|---|
| T1 | Most check tests read only `passed`, so they cannot tell a supported FAIL from an INCONCLUSIVE, the distinction the result rules introduced. 74 assertion sites; the test reviewer's in-process mutants turned each check's FAIL into INCONCLUSIVE and 25 of 32 survived all 461 tests | e.g. `test_build_probe.py:759-786,1009,1045,1130-1134` | [verified] for `no_new_commits` at `1bed111b`: the mutant passed all 325 tests in the two files that run the check, while an always-FAIL control failed 11 of them |
| T2 | The `run` subcommand is untested: dropping it from `COMMANDS` passes, because `assertRaises(SystemExit)` also accepts "unrecognized arguments" | `test_build_probe.py` subcommand parity test | [verified] at `1bed111b`: the mutant passed all 325 tests |
| T3 | Four `mock.patch.object(..., create=True)` patches target `_start_service_proxy`, which exists, so a rename would leave them passing while a real proxy runs | `test_build_probe.py` service tests | [verified] by reading |
| T4 | The entry point's patch refusal named `probe.checking.check_<name>` for the 32 registered checks, but grading calls the registry entry, so a patch there changes nothing | `build_probe.py:313-323` | [verified]: patching the named function left `text_regex` FAIL |
| T5 | The saved-verdict property drives `trial_status`, a wrapper only tests call (S4); what it exercises underneath, `Outcome.read` and `roll_up`, is production code | `test_result_rules_properties.py:65-82` | [verified] by reading |
| T6 | The rescore-diff properties never vary scenario or label, so a diff that keyed runs without the label would pass | `test_result_rules_properties.py:295-306` | [verified] by reading |
| T7 | The batch harness is copied 9 times, fixtures are borrowed across test classes, and the saved-run layout is written in 11 places; 24 local imports duplicate module-level ones | `test_build_probe.py` | [unverified] |

Refuted on re-check: that `plan()` never gives a floor-and-ceiling expectation a kept verdict. A
`tool_call_count` with a positive minimum is one, and its `regradable=False` override keeps it (R10's
reproduction shows `polarity=both kept_as='workspace-dependent'`), so the property's branch is reachable.

## Kept

- The `@declare` registry and the tables derived from it: one owner for each check's polarity and
  evidence, a real extension point.
- Strict pydantic `RecordV1`, `Fraction(str(threshold))` for the decimal threshold, LF-normalized
  digests, and the per-call harness re-hash as a drift guard.
- The publication/measurement split between `run_trial` and `_run_trial`, and `start_services`'
  ordered unwinding, whose composite "…; cleanup also failed" error an `ExitStack` would change. D3
  needs only `BaseException`.
- `json_pointer`, the urllib `request`, and the PromQL lexer: no pinned library replaces them without
  changing their semantics.
- The hand-written `validate_scenario` rules: message wording and order are a pinned contract.
- `judge_spend`'s `sys.modules` lookup, a test patch point.

## Owner decisions

The two reviewers disagree on the compatibility layer; the guide supports both readings, so it is
the owner's call:

| Item | For removal | For keeping |
|---|---|---|
| Re-export list and patch guard (`build_probe.py:64-329`) | Its only consumers are in-repo tests: 876 references to 143 of the 213 names across 11 files, 745 of them in `test_build_probe.py`. All are static `build_probe.<name>` attributes, so a LibCST codemod driven by the entry point's own import table migrates them; the exceptions are 6 renamed aliases and 6 module-valued names, and no test pins the export list, so a migration adds that pin. The guide adds compatibility adapters "only for actual supported consumers"; with the tests on `probe.*`, the guard has nothing to guard (about −280 lines) | The docstring promises "every name the runner has always exported"; tests whose subject is the entry point (the refusal, `main`) keep using it |
| Flat flags (`cli.py:150-194`) | Docs, CI and scripts all use subcommands | 17 tests reach the flat run form (every test that schedules trials), against 2 that use subcommands; a rescore gate may run a pre-#328 runner with the same command line (43 lines) |
| `Outcome` as a `tuple` subclass (`outcomes.py:56-127`) | No runner code uses its tuple protocol; its equality is not transitive (`fail == (False, "x") == unknown`, yet `fail != unknown`) | 174 test sites use it: 136 `[0]` reads and 33 unpackings |

## Fixes

On `work/probe-craft-review`, off `adc13a88`. Each fix began with its reproduction as a failing test,
and each rescore of the 1,317 saved runs against `adc13a88` differed in no verdict.

| Finding | Commit |
|---|---|
| R1 | `b50298e1`, corrected by `08d2af3c` (its temporary directory bypassed `remove_tree`; the overwrite test caught it) |
| R3 | `449bb8eb` |
| R2 | `285fa3e1` |
| D1 / R5 | `853c0ec6` |
| D4 | `1bed111b` |
| R4 | `3c9319f3` |
| D3, D2 / R11 | `c963c0b7` |
| R12 | `0d76443d` |
| T4 | `c929057b` |
| R13 (classification table; `usage_models` merged across invocations) | `46d483b8` |
| R6 (unrecorded status), D5 (validation refuses `equals: null`) | `6e9e3264` |
| T3 | `febf723c` |

Not fixed, with the reason: R6's grading-before-proxy-stop ordering (code-read only; needs a
lingering agent process to matter), D6 (no saved run here is affected; the fix needs the regrade to
re-run the profile check on the raw trace), and R10 (a test pins the override to the earlier
hand-kept regrade set, so removing it is a decision that changes regrades).

## Second review round

The bots' second review of PR #328, fixed on the same branch, with one finding of this review's own
(B11) and one structural change. Each fix began with a test shown failing on the code before it.

| Finding | Source | Commit |
|---|---|---|
| A negative `--run-offset` published `run-0`, which the v1 record refuses | Codex 4202914617 | `91361a52` |
| `validate` crashed on a non-mapping `fixture.branches` or `fake_bin`, or a list `checkout` | Codex 4202914647 | `724678c5` |
| A backing service lost during grading did not stop its scenario | Codex 4202914612 | `44539ffb` |
| The version probe ran a multi-word `--executable` as one file name | Copilot 4202892538, Codex 4202914623 | `ff3086a5` |
| B11: `regrade` crashed while planning a native run whose saved plugin root is gone, though its replay had voided it | this review | `a0c0980c` |
| One function decides how a batch ends (`cli._conclude`); no behavior change | this review | `b3edbea8` |
| An authentication stop exited 2 instead of 4 | Copilot 4202892510 | `fed9ef7a` |
| The spend cap forgot overwritten, superseded and incomplete attempts | Copilot 4202892474, Codex 4202914606 | `56aea752` |
| A trial whose trace names no model was pooled | Codex 4202914610 | `3b081e27` |
| An identity failure did not stop the batch | Codex 4202914626 | `2bf90f91` |
| `regrade` pooled runs across candidates, CLIs, hosts and scenario identities | Copilot 4202892437, Codex 4202914614 | `1c9de5aa` |
| A linked optional plugin input read as absent | Codex 4202914633 | `0371c1f5` |

The owner decided three behaviors: only an identity failure stops a batch (a service that never
started stops its scenario, a failure the candidate causes voids its trial); a failed attempt records
the cost it is known to have had, and a truly unknown cost blocks capped runs of its scenario under
the label; a trial with no model is void at the identity check. Codex 4202914602, requiring
`max_turns`, is still the owner's.

[verified] Rescoring all 1,317 saved runs with `adc13a88` and with `0371c1f5` differs only in the 7
native runs B11 fixes (`baseline-20261004` 3, `reliability-20260930` 2,
`reliability-native-corrected-20260930` 2), from an error to INCONCLUSIVE. The rescores taken
after B4, B11, B7, B3, B1 and B5 differ from one another only in what B11 changed.

## Next

1. Tests that state the expected state (T1): replace each `assertFalse(check(...)[0])` with the
   FAIL or INCONCLUSIVE it means, starting with the forbidding checks; test the `run` subcommand (T2).
2. Structure without behavior change: S1, S2, S3, S5, S7, S8, each gated by a rescore of the saved
   runs that differs in nothing.
3. Test surface: S4, then the owner's decisions above.
4. The deferred findings, D6, R10 and R6's proxy ordering, each with a regrade comparison if it
   changes a verdict.
5. Optional: S6 and S9.
6. Found in the second round and not fixed: a command-line usage error exits 2, INCONCLUSIVE's code;
   `fixture.env` and `services[].env` are iterated unvalidated and crash validation as B10 did; a
   plugin root that is not a git checkout crashes the batch with exit 1; `service_unchanged`'s
   audit-content raise, which a candidate's own request can reach, now stops its scenario as
   machinery (the owner accepted a note); `batch_identity_problem` and `pool_identity` both decide
   what pools; kept attempts are shared by every model of a label, so the cap over-counts a label
   two models share; and S1 would give B3's identity classification a type instead of a field.

## Method and limits

- Two independent readers covered all 17 runner files: this reviewer (14 in full, the rest at the
  cited lines) and a dispatched runner reviewer that read all 17 without this reviewer's findings. A
  third reviewer took the PR's tests. Every finding from another reviewer was re-run or re-read here
  before it was listed; the runner reviewer's six reproduction scripts all reproduced unchanged.
- Instruments, all leads rather than verdicts: Ruff's finding-defects selection (12 hits: `BLE001` ×6
  at the rule-5 boundary and warn-and-continue handlers, `PLW1510` ×6 where every caller reads
  `returncode`; Ruff cannot see R1, because `workspaces._git` passes `check=check` explicitly), Ruff
  size and nesting rules, `mypy --warn-unreachable` (0 issues; proven to fire on a scratch file), an
  AST clone detector, a usage graph of every top-level name, a parameter-forwarding detector, a
  dict-shape comparison, and an exception-handler census.
- Not checked: no real `claude` CLI or docker run, so R6's ordering and R11 are code-read; how often a
  stale `index.lock` occurs in practice (R1); the 50,000-character state-file regrade flip (R5); D6
  on other machines' saved runs. The structural changes are not implemented; of them, only
  `_case_payload`'s digest equivalence is shown behavior-preserving.
- Mutation checks ran in `git archive` exports made git checkouts, against an unmutated baseline and
  an always-FAIL control, comparing failing test IDs. A first attempt without the git checkout failed
  about 60 provenance tests in every variant and was discarded.
- A rescore records a run that raises as an error row, so a run that errors under both runners can
  show no difference: 7 did until B11. Rescores never reach `cli.run`, so the batch-ending changes
  rest on the batch tests, which miss reordering the authentication and FAIL exits until `fed9ef7a`.
