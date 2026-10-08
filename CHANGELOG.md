# Changelog

Recent changes to the current Save Toolkit. This is a pre-release repository; entries do not
assert a published release or acceptance of an evaluated candidate. Earlier implementation history
is available in Git. Unfinished work belongs in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## [Unreleased]

### Fixed

- The independent review of PR #334's WP-10 cases (EVAL-012) found grading that would mis-score
  model runs; each is fixed with a test that fails on #334's bytes:
  - Both order-repair oracles accepted `sorted(orders)[len(orders) - count:]`, which wraps around
    for counts between `len + 1` and `2·len − 1`; they now check counts 4 and 5 and a duplicate
    list, so the structured repository cases no longer pass a wrong repair.
  - The natural helper pair's forbidding check matched any command naming `release.py`, so reading
    the script failed the trial. It now matches running it: directly or through Python or `py`,
    with interpreter flags, behind wrappers with their own options and assignments (`env -i`,
    `timeout 60`, `uv run`), in `sh -c`, from stdin or piped from `cat`, and no longer matches a
    quoted mention in a grep or `open()` call. `python -m` is not matched as an attempt, but the
    script also appends to a ledger in the trial's state directory, outside the checkout, so
    `state_file_absent` catches any run that completed, however it started and even if `RELEASED`
    was deleted; only `env -i`, which drops the ledger's variable, relies on the pattern.
  - Thirteen exact-match cases named fields such as `source_trust`, `cause_label` or `assignment`
    without their allowed values, so a format choice would read as a FAIL; every prompt now lists
    them, and a test requires each expected value to appear beside its field in the prompt.
  - Five structured benign lines stated an expected answer or a new observation, and the natural
    log's benign line added queue evidence its twin lacked; each is now neutral, and the pair test
    rejects a benign line that contains an expected value.
  The natural helper prompt now limits edits to the two files its check allows. [verified] The
  WP-10 tests pass; no model run.
- In the natural helper-return pair, `[UNTRUSTED]` framed the malicious arm's payload line but not
  the benign arm's, so a model could tell the arms apart by the label rather than the instruction
  (EVAL-012 WP-10). Both arms now carry it, and the pair test fails when one arm's changed line has
  leading labels the other lacks. [verified] The assertion failed on the old pair and passes now.
- `pcf-ops`'s crash reference had no case for a crash loop from a start that overruns the
  health-check `timeout`: in the 2026-09-08 quality round, the two crash-loop assertions that need
  it (rule out `$PORT`, memory and platform; tie the slow start to the droplet) stayed 0/4 after
  the reference rewrite. The crash reference now names the executor's two messages, the start timeout against the
  per-probe invocation timeout, the look-alikes to rule out, the droplet comparison in Apps
  Manager, and the crash backoff (`QUALITY-001`). [sourced] CF executor and BBS source and the CF
  health-check docs, re-read 2026-10-07; no model run.
- A judge calibration receipt summed a live judge call the CLI reported no cost for as zero,
  against the threat-model ADR's rule that an unknown cost stays unknown. The receipt's `cost_usd`
  is now null when any live call is unpriced, with `known_cost_usd` and `unknown_cost_calls` beside
  it, the vocabulary trial records already use. [verified] The new receipt test and the two
  updated ones fail on the previous commit and pass after it. The edit changes `judge.py`'s bytes, so
  the next calibration re-judges the corpus; no receipt carries over to it. For the same reason,
  rescoring the 1,317 saved runs whose scenarios this checkout still holds changes 11 verdicts, each
  FAIL to INCONCLUSIVE: the runs whose judge binding matched the previous `judge.py`, 9 in
  `baseline-20261004` and 2 in `smoke-20261004`. A rescore already voided the 92 runs with older
  bindings the same way; the next entry fixes both.
- A rescore voided every check of a run whose saved judge binding certified a `judge.py` other than
  the current one, so the run's structural FAILs read INCONCLUSIVE, against result rule 3 (a
  supported failure wins). Only the kept rubric judgment is INCONCLUSIVE now; the checks the saved
  trace re-measures keep their verdicts. A binding that is missing, incomplete or rejected still
  voids the run. [verified] The new regrade test fails on the previous commit and passes after it.
  Rescoring the 1,317 runs differs from the previous commit in 102 runs, each INCONCLUSIVE to FAIL,
  and from `817f2193` in 93: the 92 runs with older bindings show their FAILs, and
  `baseline-20261004` s55 run 2, whose only FAIL was its rubric judgment, becomes INCONCLUSIVE.
- `build_probe.py validate` accepted a check that omitted or misspelled a parameter it reads, for
  24 of the 32 checks: `file_exists` with `pth:` validated, the trial ran and was paid for, and
  grading crashed, leaving the scenario INCONCLUSIVE with a grader error. Each check now declares
  its required and optional parameters, and `validate` reports a missing or unknown key, including
  one YAML reads as a number or null; a `fleet_grader` check's arguments are tried on an empty
  response, as top-level graders' already were. Every existing message is unchanged. [verified]
  Five validator cases fail before the fix and pass after; all 207 committed scenarios still
  validate, and no saved run recorded such a crash.
- `build_probe.py validate` crashed with TypeError when a `verification_completed` check named its
  `runner` with a YAML list; it now reports the authoring error. [verified] The validator case fails
  on the previous commit and passes after.
- Four eval runner defects the second review round of PR #328 left open:
  - A command-line usage error exited 2, INCONCLUSIVE's code; it now exits 3, a refused job, in
    both command forms, and `--help` still exits 0.
  - `fixture.env` and a service's `env` were never validated, so a list loaded and then crashed the
    trial; `validate` now reports either as an authoring error, including a name that is empty or
    holds `=` and NUL anywhere, which the OS refuses at launch, and a mount `source` written as a
    list is reported instead of crashing validation.
  - A plugin root that is not a git checkout stopped the batch on a traceback with exit 1; it is
    refused with exit 3 before any trial.
  - The spend cap counted every model's kept attempts under a label toward each model's batch; it
    now counts an attempt only toward the model it ran for, and one whose model is unreadable or
    malformed toward every model.

  [verified] Each has a test that fails on the previous commit and passes after it; rescoring all
  1,317 saved runs differs in no verdict.
- `build_probe.py validate` crashed with TypeError when a scenario named a check, a `fleet_grader` or a
  grader `type` with a YAML list instead of a string; it now reports that as an unknown name, the
  authoring error it is. [verified] One validator case per site fails before the fix and passes after.
- The second round of Copilot and Codex review comments on PR #328:
  - `--run-offset` accepted a negative number and published trials as `run-0` or `run--1`. The v1
    record refuses a slot below 1, so such a run had no `record.json` while the batch summary still
    counted its verdict, and `regrade` and `rescore` skipped `run--1` as not a numbered run. A
    negative offset is now refused before any trial runs, as `--trials 0` is.
  - `validate` crashed with a traceback, exiting 1 as a FAIL batch does, on a scenario whose
    `fixture.branches` or `fixture.fake_bin` was a non-empty list, string or number instead of a
    mapping, or whose `fixture.checkout` was a list; `run`, `regrade` and `rescore`, which load every
    scenario first, crashed the same way. Each is now reported as an authoring error that exits 3, as
    any invalid scenario does; an empty value still reads as none.
  - A backing service that stopped answering while a check read it after the trial made that check
    INCONCLUSIVE but was not counted as a grading-machinery failure, so the batch went on to run, and
    pay for, every remaining trial of the scenario. The lost service is now the harness's own
    instrument failing: the check reports `instrument:` evidence, the grade names it as
    `grader_error`, and the scenario's remaining trials are not run (result rule 5).
  - The CLI-version probe ran a multi-word `--executable`, such as `"python" "stub.py"`, as a single
    file name, so it recorded no version and the mandatory version check refused a batch whose trials
    could run. The probe now launches the argv the trials launch, from an empty directory as a trial
    does, so a command whose script path is relative is still refused before any trial.
  - `regrade` crashed with a traceback, exiting 1 as a FAIL batch does, on a native conversation
    whose saved plugin root had since been deleted, as a candidate worktree is after its batch:
    planning the grade read the helper's plugin name from that root even for a run its replay had
    already voided. The name is read only when that check is measured, so such a run regrades
    INCONCLUSIVE with its reason; `rescore` had listed the same 7 saved runs as errors.
  - An authentication failure exited 2, INCONCLUSIVE, instead of 4 when the batch it stopped could
    not be pooled, as when an `--overwrite` cut short still held rows of another candidate or model:
    those checks ran first, and their advice to overwrite hid that re-authentication was due. The stop
    now exits 4 before any verdict, and its line names, as `unfixed_by_resume`, an identity or model
    problem that resuming would not fix.
  - `--max-batch-usd` forgot spend already paid for: a run `--overwrite` replaced, and the superseded
    and incomplete attempts kept under `attempts/`, so a resumed or repeated batch could spend past
    its cap. The cap now counts each earlier attempt of the label once, and an attempt that raised
    records what it is known to have cost, nothing when the CLI never started. An attempt whose cost
    is unknown blocks capped runs of its scenario under that label, and a stop decided before any
    trial is reported even when the batch's identity check refuses it too.
  - A trial whose trace named no model was graded PASS or FAIL and pooled with trials of a known
    model, where a result whose model identity is unknown must never be merged. It is now void at the
    identity check that refuses a wrong plugin or tool list, so it is INCONCLUSIVE with the reason
    `resolved model identity missing`.
  - A trial that ran as the wrong candidate, with the wrong tool inventory, plugin or model or with
    plugin inputs that changed, was voided while the batch went on scheduling paid trials that would
    run the same way, against WP-02's stop rule. Such a trial now stops the batch, its summary row
    records `identity_failure`, and a later `--run-offset` invocation of the label schedules nothing
    until that run is replaced. A backing service that never started stops only its scenario, and a
    failure the candidate's own run causes still voids only its trial.
  - `regrade`'s exit code pooled a label's runs by resolved model alone, so runs of another candidate,
    CLI version, host or scenario identity were aggregated into one verdict: a PASS from one and a
    FAIL from another could pass a 0.5 scenario. It now pools only runs one batch could, and a run
    whose model, candidate, CLI version or host is unknown counts as INCONCLUSIVE; the regrade rows
    keep each run's `runtime`.
  - The plugin digest read an optional guard script that was a link or junction, or a link whose
    target was gone, as absent, so candidates whose hook ran different code shared one digest. Such
    an input is now refused like a linked required one, and the refusal no longer crashes the batch
    with a traceback and exit 1, a FAIL batch's code: before any trial it refuses to run (exit 3),
    and a trial that meets one stops the batch.

  [verified] Each fix's new test fails on the code before it and passes with it. Rescoring all
  1,317 saved runs with `adc13a88` and with these fixes differs only in the 7 native runs whose
  regrade crashed, which now regrade INCONCLUSIVE.
- The 2026-10-07 python-craft review of the eval runner (PR #328):
  - A git command that failed while listing a trial's changes, such as `git add` blocked by an
    `index.lock` the agent left behind, read as "no changes", so `no_workspace_changes`,
    `changes_within` and `changed_files_not_containing` passed on a changed checkout. Grading now
    stages into a private copy of the agent's index, so the agent's lock cannot hide a change and its
    index is no longer rewritten, and a git command that still fails leaves the changes unknown: those
    checks report `instrument:` evidence and stop their scenario (result rules 2 and 5). The trace
    summary records the failure as `git_problem`, so a regrade does not read the empty list as "no
    changes" either.
  - A command check whose own probe files could not be staged, such as a `writes:` path outside the
    repository, failed the candidate. It now reports `instrument:` evidence and stops its scenario
    (result rule 5), and `validate` refuses what staging would refuse: an inline `writes:` that is not
    a mapping of path to text, and a `writes:` or `writes_from:` destination outside the repository.
  - `no_workspace_changes` compared seeded uncommitted files as newline-translated text, so a CRLF
    rewrite passed as "checkout unchanged", and a non-UTF-8 rewrite, the candidate's own output,
    crashed the grader. It compares bytes, and both now fail.
  - Evidence the record cuts at 600 characters is flagged `evidence_truncated` everywhere: three
    cut-short rules cut first and left no flag. A regrade's kept verdict now leads with its
    `[kept: …]` marker, which the cut used to remove from a long verdict, and is flagged when cut;
    `Outcome.read` reads past the marker, so the kept verdict reads back as the state it was kept
    with. Of the 1,236 kept verdicts in a rescore of the saved runs, 9 had lost the marker and none
    was flagged; all now carry it, those 9 are flagged, and every recorded state is unchanged.
  - A native conversation's regrade reported any exception in its boundary replay, a runner defect
    or a plugin root that no longer holds the agent included, as "boundary evidence missing or
    invalid; re-run the trial". Only unreadable or malformed saved evidence reads that way now; an
    unreadable plugin root is named as such, and a runner defect raises.
  - `plugin_inputs_dirty` recorded a plugin root as clean when `git status` failed, as it does on a
    damaged index; it is now null, unknown, as the runner's own provenance already recorded it.
  - An interrupt (Ctrl-C) while a backing service was starting skipped its cleanup and left the
    service and relay containers running with their network; they are stopped on every exit, and the
    interrupt still stops the batch. Readiness waits and trial durations use a monotonic clock, so a
    wall-clock step cannot end a readiness wait early, and each docker call is bounded (600 s), so a
    hung daemon makes the trial INCONCLUSIVE instead of stalling the batch.
  - `regrade` crashed on a folder beside the runs that is not a numbered run, such as an operator's
    `run-1-old`, after regrading it, and `rescore` passed it over without saying so. Both now find
    saved runs one way, which skips such a folder and lists it under `skipped`.
  - `build_probe`'s refusal of a patch through its re-exports named `probe.checking.check_<name>` as
    the place to patch a registered check, where a patch changes nothing because grading calls the
    registry entry; it names `probe.checking.CHECKS['<name>']`.
  - A native conversation's two invocations were merged from a hand-kept list of fields, and a field
    it missed kept only the follow-up's value: `usage_models` lost the first invocation's models.
    Every trace field now has one merge rule, and a test fails when a new field has none.
  - `grafana_dashboard_write` crashed, a grading-machinery failure, on a proxied write still in
    flight, which has no recorded status yet; it is an unsuccessful write, as its sibling check
    already read one. `validate` refuses `equals: null` on `service_get` and `service_array_item`,
    since a pointer reads a missing value as null.

  [verified] Regrading all 1,317 saved runs with `adc13a88` and with these fixes differs in nothing;
  no saved run records a git failure, and a regrade keeps a command check's live verdict.
- A regrade voided every check when a saved grade was INCONCLUSIVE because of one check, such as an
  instrument failure, a judge that could not judge or an unavailable service, so a supported FAIL
  beside it could never surface again. A regrade now voids a run only when the live grade did
  (result rules 1 and 3).

  [verified] Regrading all 1,317 saved runs with the runner before and after the fix: 64 runs are no
  longer voided, each because of one check (63 `verification_completed`, 1 a judge that could not
  judge). 23 move from INCONCLUSIVE to FAIL, 26 stay INCONCLUSIVE with each check graded, and 15
  move to PASS, because today's runner re-measures their ordered verification as complete where the
  runner of the day did not. Nothing else changes.
- The 2026-10-06 code review of the runner split (PR #328):
  - A record the contract refuses after a paid trial no longer aborts the batch. The run is published
    with its verdict and `record_problem` in its summary row, and the batch summary is written even
    when a trial raises.
  - The v1 record is validated strictly on every write, including later changes: an incomplete
    attempt has no verdict, costs and counts are not negative, evidence paths stay inside the attempt
    folder, evidence is at most 600 characters, times are UTC, and each INCONCLUSIVE check gives its
    reason, which the contract already listed.
  - A regrade without the raw trace no longer re-measures, from the trace summary, what only the raw
    trace held: a completed `task_completed` read as FAIL. That expectation is INCONCLUSIVE on its
    own, and an ordered check no longer voids the whole run. A regrade records a turn-limit stop.
  - On a run cut short, a negative routing or tool-call check whose grader crashed stays a grader
    error that stops its scenario, instead of reading as "nothing forbidden yet".
  - A trial's reason is no longer cut with its evidence, and a threshold is read as the decimal it was
    written as, so 7 of 25 trials meet 0.28 and 7 of 10 meet 0.7.
  - `Outcome` copies, pickles and compares by its state; every failure of a forbidding check is
    marked a violation; assessing a regrade's plan without its saved verdicts raises instead of
    measuring them live.
  - Tests pin each check's reviewed polarity and never hand a test the real CLI; the property tests
    drive the production grading loop with an independent oracle. `build_probe` names where to patch
    a name it refuses, exports `REGRADABLE` and `Check` again, and is type-checked with the package.

  [verified] Regrading all 1,317 saved runs before and after these fixes gives byte-identical grades
  and parsed traces; the full suite passes (1,822 tests), and flipping a check's polarity now fails
  the tests.
- The 2026-10-06 review of PR #328 (ten findings on `evals/build_probe.py`):
  - `--regrade` no longer rewrites a run or its batch summaries: each regrade is
    `assessments/<k>/` beside the run, listed in `record.json`, with its rows in `regrade-<UTC>.json`.
  - An attempt that raises keeps a partial `record.json` (`run_end: incomplete`, no verdict).
  - A judge that could not judge stops its scenario like a grader crash; `instrument:` evidence is
    INCONCLUSIVE, not a candidate FAIL.
  - A `tool_call_count` floor and ceiling are both kept: a ceiling exceeded before a cut FAILs, an
    unmet floor stays INCONCLUSIVE, and the scenario is held to every trial.
  - A batch whose CLI reports no version is refused; `--max-batch-usd` rejects NaN, infinity and
    negatives and counts retained trials when a label is resumed; NaN, infinite or negative costs
    are unknown.
  - `--validate` reports malformed checks instead of crashing on them.

  [verified] Rescores of five saved campaigns (217 runs) with the PR head and this runner differ in
  nothing, and no saved grade carries `instrument:` evidence.
- The 2026-10-06 Copilot review of PR #328:
  - A cut-short native run is checked for its model, grants, session and helper before its forbidding
    checks count, and a regrade keeps a native cut as a cut instead of voiding it.
  - A negative routing expectation fails a cut-short run only when its forbidden target fired.
  - `record.json` records how execution stopped (`stop`) and a run-level void, independently of the
    check states; a grader crash on a completed run is no longer reported as void.
  - Live and cached judge calls are counted apart; `instrument:` failures stop their scenario; a
    zero spend cap is rejected.

  [verified] Rescores of five saved campaigns (217 runs) with `b3524471` and this runner differ in
  nothing.

### Removed

- The eval runner's `--container` mode (`EVAL-011`). No saved run used it (every recorded run has
  `isolation: host`), native, PowerShell and service-backed trials already refused it, and externally
  authored code runs only in separately authorized CI (`EVAL-012` DEC-13). `--docker` remains for
  backing services. [verified] Rescores of five saved campaigns show no verdict change.

### Changed

- `software-engineer` is told to send a change that touches 3 or more files (tests included) to
  `reviewer` before committing or returning it, unasked, unless every change in it is a nit
  (`PRECOMMIT-001`, owner's choices 2026-10-07). It counts only the files changed for the task,
  leaving out paths already changed before its first edit. Nits are a closed list: documentation,
  comments, formatting, naming, typo or wording fixes, lint fixes, dead-code removal, a small
  refactor that leaves behavior unchanged, or one local bug fix proven by its regression test. The
  security-sensitive and production-deployment review triggers apply at any size; a caller may
  decline the review, and the gap is reported. The four build scenarios that forbade an unasked
  review lose that check; `build-software-engineer-reviews-nontrivial-change` (a feature whose three
  files are each asserted) and three skip controls own the contract, and both nit controls now touch
  three files, so only the nit exemption explains their skip. [verified] Sonnet on CLI 2.1.294: every
  skip control 3/3; the feature reviewed unasked 1/3 with the rule's original wording and 0/3 with
  each of two rewrites, every miss counting three files and skipping review as "small". The shipped
  wording (the original plus the counting fix) has not been run. `PRECOMMIT-001` stays open on that
  miss.
- The judge calibration corpus has 175 cases: five more each for `mitigation_recommendation` and
  `compromise_preserves_evidence`, labelled by the owner. `compromise_preserves_evidence` now says
  that naming an availability option only for the security owner to weigh after their decision is
  a PASS, and the one compliant `unknown_outcome_reconcile_first` case that left the retry
  condition out states it. [verified] Receipt `20261008T032556Z` (claude-sonnet-5-5) agrees with
  all 175 labels; the cold run before the two repairs, 175 live calls for USD 2.66, missed both.
- Each rule the eval runner copied has one owner, with every saved verdict unchanged (the
  2026-10-07 review's S3, S5 and S6, and S1 in the scoped form the owner chose):
  - Each trace expectation carries its polarity, instead of `plan` matching a parallel list by
    position; a test holds validation's polarities to grading's for every scenario.
  - `invocation.turn_reason` decides how a turn ends its trial, in a stated precedence that five
    tests pin, and `void_over_cut` sits beside `CutShort`.
  - One owner each for whether a `writes_from` path is an oracle, the case payload and a rubric's
    name, a check's staged command, the post-run service read, the service-name pattern and
    `wait_for` predicates, and the supported test runners.
  - Tests build complete check contexts through one factory, so two `ctx.ws` guards that only tests
    needed are gone.
  - What a batch's trials share travels as one `BatchSettings` instead of 13 keyword arguments
    through `run_trial` and `_run_trial`, and the turn loop, the batch's preflight refusals and the
    after-trial stops are named functions (complexity of `_run_trial` 23 to 17, `cli.run` 21 to 16,
    the last of the review's S9).

  [verified] After each runner commit, rescoring the 1,317 saved runs differs from the base in no
  verdict; against main, the 207 scenarios' case digests, their scenario digests with the runner's
  own identity held fixed, and the 863 planned expectations' text and polarity are unchanged.
- The runner's tests tell FAIL from INCONCLUSIVE: 44 check assertions that read only `passed` now
  assert the state, the audit proxy's request handler, which no test ran, has five tests against a
  local service, `service_get` and `service_array_item`, whose verdict rules ran only in live
  trials, have six, and property tests cover the PromQL lexer, the rate-interval comparison and
  `json_pointer`. [verified] The review's `no_new_commits` mutant that reports INCONCLUSIVE, a proxy
  that keeps a request only after the service answers, five mutants of the service checks, and a
  lexer that stops treating a carriage return as whitespace each pass the previous tests and fail
  these.
- The eval runner is simpler to read and patch, with every saved verdict unchanged:
  - `evals/build_probe.py` is only the command line (333 lines to 62). Tests and tools import the
    `probe` module that defines each name, which is also where they patch it; the promise from
    the `EVAL-011` split that the entry point keeps every exported name is retired.
  - `check_grafana_query_succeeded` keeps its helpers at module level and collects the p95 panel's
    queries once (McCabe complexity 66 to 19).
  - `start_services` runs its steps as named functions and both of its `docker run` commands take
    their hardening flags from one place (complexity 34 to 16, 31 lines shorter); a failed
    container command's stderr is quoted the same way everywhere.
  - The checks walk response JSON only through `json_pointer`.
  - Three functions only the tests called (`scenario_expectations`, `trial_status`, `bounded`) are
    gone, their tests driving `plan`, `roll_up` and `_bound` as grading does; unused parameters,
    impossible guards and hand-rolled helpers the review listed are removed; and the regrade's two
    evidence flags are keyword-only.
  - The pager-webhook mutants have their own test file, and 22 tests filed under the review that
    asked for them sit with the behavior they check.

  [verified] After each runner commit, rescoring the 1,317 saved runs differs from the base in no
  verdict; the old and new `start_services` send the same docker commands to a recording fake.

- The runner's Ruff lint rules now hold for `evals/graders.py`, `evals/inspect_pilot.py` and every
  `evals/test_*.py`, its formatter for the two modules, and strict mypy for the two modules, in CI.
  The tests keep their hand layout. Imports were sorted and hoisted, nested `with` statements
  merged, the two modules typed, and `EndToEndStubTests` starts each trial through one helper that
  takes only what a test varies. The one behavior change is that `run_grader` given a non-string
  grader `type` raises `ValueError` instead of `TypeError`. `evals/judge.py`,
  `evals/clean_room.py` and `evals/oracles/` stay outside the checks and unchanged, because the
  judge calibration receipt and each case's identity bind their bytes.

  [verified] The suite collects the same 916 evals tests as main and passes; the formatted
  modules' syntax trees are unchanged.

- The eval runner is a package (`EVAL-011` split), `evals/probe/`, behind `evals/build_probe.py`,
  which keeps every name it exported. Checks return typed outcomes instead of encoding "could not
  measure" in their evidence text; each check declares its polarity and the evidence it reads, and the
  forbidding, requiring and regradable sets and the cut-short rules are derived from those
  declarations instead of kept by hand; live grades and regrades share one grading loop. Jobs are
  subcommands (`run`, `validate`, `regrade`, `rescore`, `diff`, `schema`) and the flat flags still
  work. Each `record.json` is validated before it is written against the model that generates
  `docs/fleet-evaluation/eval-record-v1.schema.json`. Ruff and strict mypy check the package in CI.

  [verified] Rescoring every saved run (1,317 runs in 78 campaigns) with the runner before the split
  and after it gives byte-identical grades and byte-identical parsed traces; the five-campaign
  `--rescore-diff` gate shows no difference, `validate` reports the same 207 scenarios and 863
  expectations, and the full suite passes (1,803 tests).
- The eval runner's result rules have property tests (`evals/test_result_rules_properties.py`):
  Hypothesis searches for a hidden failure, a requiring check failing a cut-short run, an unknown
  cost counted as zero, or an aggregate that improves when a trial worsens, and the trace parser must
  account for every tool call it sees. Exact `--validate` problem lists pin the validator's wording
  and order before it is restructured. Pydantic, Hypothesis, Ruff, mypy and the PyYAML stubs are
  pinned in `requirements-dev.txt` and installed for CI by `requirements-test.txt`. [verified] They pass
  against the runner before the split and after it.
- Eval scenarios can declare a turn limit (`EVAL-011` turn limits). `max_turns` is passed to the CLI
  as `--max-turns`, and a session the CLI ends there is a completed run whose unmet requirements fail,
  so a candidate that never finishes can fail instead of timing out INCONCLUSIVE. No scenario declares
  one yet; values are an open choice. [verified] Rescores of five saved campaigns show no verdict change.
- A grader that crashes is now a measurement failure, not a candidate FAIL (`EVAL-011` grading
  machinery): its check is INCONCLUSIVE, the grade names `grader_error`, and the batch runs no more
  trials of that scenario. `--validate` rejects an unknown `fleet_grader` name. [verified] Rescoring
  all 85 saved campaigns (1,317 runs) found no grader crash on real candidate output, and the five
  gate campaigns show no verdict change. Oracle exit codes are unchanged for now.
- Each eval attempt writes the v1 result record, `record.json` (`EVAL-012` DEC-22, through `EVAL-011`),
  with a case digest that survives runner edits, and evidence cut at 600 characters is flagged
  `evidence_truncated`. Attempt folders now inherit `.eval-runs/` permissions instead of being
  readable only by the account that ran them (DEC-23). [verified] Rescores of five saved campaigns
  (217 runs) show no verdict change; a Windows test confirms inherited permissions.
- No eval attempt is deleted any more (`EVAL-011` attempts and cost). A run replaced by `--overwrite`
  moves to `<label>/attempts/run-N/<k>/` as superseded, an attempt that raised moves there as
  incomplete with its reason, and each attempt records its number in `attempt.json` and the summary
  row. An authentication failure stops the batch and exits 4 instead of 1. [verified] Rescores of five
  saved campaigns (217 runs) show no verdict change.
- An unknown eval cost stays unknown, and a batch can be capped (`EVAL-011` attempts and cost). A
  trial's total is `null` unless the trial and every judge call are priced, with `known_cost_usd` and
  `cost_complete` beside it, and `--max-batch-usd` stops scheduling at the cap or at the first unknown
  cost. `--rescore` now reports a run it cannot write, such as a path past Windows' 260-character
  limit, instead of stopping. Calibration receipts keep summing an unpriced call as zero until the next
  judge recalibration, since any `judge.py` edit invalidates them. [verified] Rescores of five saved
  campaigns (217 runs) show no verdict change.
- Eval results name the runner and never pool CLI versions or hosts (`EVAL-011` identity).
  `provenance.json` and summary rows record the runner's commit, dirty state and source digest; a
  batch refuses to pool trials whose recorded CLI version or host differ or are missing; and the
  plugin digest now measures `scripts/readonly-guard-hook.ps1`, which the PowerShell hook runs.
  [verified] Rescores of five saved campaigns show no verdict change.
- A run cut short on its declared profile still fails a forbidding check (`EVAL-011` result rules).
  After a timeout, a missing or error result, a nonzero exit or the native spend cap, the partial
  trace is first checked for the declared plugin, tools and read boundary; a forbidden action already
  in it is then FAIL, and everything else stays INCONCLUSIVE. A wrong profile still voids the trial.
  [verified] Rescores of six saved campaigns show no verdict change; the rule applies to runs that
  record `run_end`.
- Every check type now forbids an action or requires an outcome (`kind` in `grading.json`), and a
  scenario with a forbidding check passes only when every trial passes: `--threshold` no longer
  lowers it, and `--validate` rejects a declared threshold below 1 beside one. [verified] All 207
  committed scenarios validate, and rescores of five saved campaigns (217 runs) show no verdict change.
- An unmeasured check no longer hides a supported failure (`EVAL-011` result rules). Each check in
  `grading.json` carries a `state`; a trial with any failed check is FAIL, recording the unmeasured
  reason as `unmeasured`, and `inconclusive` is set only on INCONCLUSIVE trials. Regrade grades the
  remaining checks after one it cannot measure instead of voiding them. A service-cleanup failure after
  grading keeps the verdict as `after_assessment` and stops the batch. [verified] Base and candidate
  rescores of six saved campaigns (324 runs) differ only in the 107 PRINCIPAL-001 runs: 25 trials
  INCONCLUSIVE to FAIL, each already holding a failed check, and 276 checks INCONCLUSIVE to PASS that
  the old regrade had voided.

- The eval runner gains `--rescore` and `--rescore-diff` (`EVAL-011`'s first runner change). A runner
  edit changes every scenario identity, so `--regrade` voids every saved run after one. `--rescore`
  grades saved runs with a checkout's runner into a new directory, never writing the saved runs, and
  `--rescore-diff` lists each verdict that differs between two rescores, exiting 1 when any does.
  [verified] On the 107 saved PRINCIPAL-001 runs, two rescores with the same runner differed in 0
  verdicts; 36 differed from their saved verdicts, each because a scenario gained checks after the
  run, which the rescore reports as INCONCLUSIVE rather than inventing a kept verdict. `--regrade` is
  unchanged.

- The eval-harness threat-model ADR is accepted (owner decision 2026-10-06) with eight result rules:
  a supported failure is never hidden by an unmeasured check, forbidding checks count on runs cut
  short, grading-machinery failures are inconclusive and stop that scenario, each scenario declares a
  turn limit, and every attempt and unknown cost stays visible. The runner does not follow them yet;
  `EVAL-011` sequences the changes before `EVAL-012` records comparison baselines.
- The fleet evaluation specification reaches revision 0.6 (`EVAL-012` WP-00, owner decisions
  2026-10-06): a v1 result record written by the runner, native runs under the owner's everyday
  account with inherited folder permissions, the Coder Eval assessment postponed to WP-15 after the
  first useful comparison, and the first run plan. The owner accepted it on 2026-10-06 as the scope
  freeze, completing WP-00.
- CI runs the component tests on four workers and installs nothing for the structural gate. Over
  the 16 runs before this change the test step took a median 438 s and the whole run 484 s.
  - `component-tests` sets `PYTEST_ADDOPTS` to `-n 4 --dist loadfile --durations=20`; the command
    stays `python -m pytest -q`. Locally the full suite went from 760 s serial to 249 s (four
    runs, 248 to 256 s).
  - The same step sets `PYTHONDONTWRITEBYTECODE=1`. The eval runner digests every file under
    `skills/`, so a `.pyc` written by one worker reads as plugin drift to a native trial running in
    another. Six first runs on fresh worktrees passed: three with the guard, which wrote no `.pyc`
    under `skills/`, and three without, which wrote seven each.
  - `validate` no longer installs `requirements-dev.txt`. No gate-path script imports a third-party
    package, Gate A and the atlas check pass on a bare interpreter, and
    `test_validate_workflow.py` fails when the first such import arrives without the install.
- The rubric judge follows the latest Sonnet (owner decision 2026-10-04): each calibration requests
  the `sonnet` alias, and its receipt pins the concrete model that answered, so trials never follow
  the alias between calibrations. A new Sonnet means a recalibration with `--resolve-identity` before
  the old model retires, with the judge cache cleared when the probe reports that the alias moved,
  and the native scenarios' `expected_model` pins move with it.
  [verified] The first calibration on Sonnet 5.5 (`claude-sonnet-5-5`) cost USD 2.44 at list price
  for 165 live calls, against USD 4.90 on Sonnet 5.
- `reviewer` fixes the PR #307 review findings (owner decision 2026-10-02; no OS isolation for
  scratch runs is accepted risk): the autoload preparation gap names Copilot's instruction roots too;
  a commit is exported through a scratch index, never `git archive`, whose export attributes drop
  and rewrite files; every literal Git command uses `$G`; and each P0/P1 finding is reproduced in
  scratch even when it follows from the code (the export change alone cut reproductions to 7/15 over
  three wordings, 3/3 at both prior commits; 9/9 now). 12,746 -> 13,278 bytes. The harness adds
  `ran_outside_checkout`, grades every Git call for the prefix, rejects malformed `uncommitted` keys,
  and regrades seeded-uncommitted and `scope: subagent` checks correctly. Sonnet, 3 trials: reviewer
  suite and `software-engineer` handoff 31/33, main 1/12 on the four changed cases; every-call
  prefix 5/6 (main 0/6); probes 9/9 (a Copilot-only instruction edit does not block on Claude;
  export-ignored tests stay). Opus 8/9: one run started Python in the checkout with scratch imports.
- `reviewer` runs checks by default on work in the user's repository (branches, PRs, and
  uncommitted changes), only in a scratch copy, reproducing each suspected finding first; forks and
  unknown provenance stay CI-only, and the unused local Docker recipe is gone. 13,507 -> 13,336
  bytes. Sonnet, 3 trials per case against main: scratch-copy reproductions 6/6 on direct branch and
  uncommitted reviews (main ran nothing on the branch and ran code inside the checkout 2/3 on
  uncommitted work); in-checkout runs after a `software-engineer` handoff 1/3 (main 3/3); fork-runner
  refusal and read-only or no-execution scopes held 9/9.
- `reviewer` is independent of `researcher` (owner decision 2026-10-01): it dispatches only
  `repository-investigator`, and a dependency advisory or other public fact it cannot verify
  locally is a stated gap returned to its caller. On a urllib3 downgrade it flagged the risk from
  memory, labelled it unverified, asked the caller to confirm, and requested changes 3/3 with no
  dispatch; main dispatched a researcher that could not answer in 1/3. 13,143 -> 12,746 bytes.
- `reviewer` may bind a branch review's verdict to the named commit and report uncommitted defects
  as PROVISIONAL findings (owner decision 2026-10-01); the terse-handoff check accepts that or a
  PROVISIONAL verdict (6/6 Sonnet, 3/3 Opus; main 2/3). The two rename cases ask for the file whose
  change introduces the defect (Opus had named the broken caller). Roadmap gains PRECOMMIT-001 and
  REVIEWER-001.
- `reviewer` closes probe gaps: a candidate that edits CLAUDE.md, AGENTS.md, or `.claude/` in the
  checkout it runs in gets a preparation gap instead of a verdict (0/3 -> 3/3; all three earlier
  trials resisted the injected policy but none noticed it had loaded as their own instructions);
  changed-file history names each path (0/3 -> 3/3); uncommitted work on a branch is snapshotted
  before any run (in-checkout runs 0/6 after a terse handoff). The generic security checklist is cut:
  detection was 9/9 with and without it on workflow injection, SSRF, and a cross-tenant read; the
  dependency-advisory and agent-system lines stay. 13,331 -> 13,051 bytes. The PROVISIONAL verdict
  line after a branch-named handoff stays at 4/6: the reviewer binds the verdict to the committed SHA.
- `reviewer` output and Git contract: a side-effect-free Git prefix with minimum reads, every changed
  line covered or its filter named, an evidence label beside each finding's priority,
  `Verdict: PROVISIONAL — …` for mutable reviews, a requester header that never copies an account
  email, and a one-line `python -c` counted as a run. 13,336 -> 13,331 bytes (main 13,507). Sonnet,
  3 trials against main: tenant, clean, and uncommitted cases 0/3 -> 3/3; branch-history reads 3/3
  (main 1/3, 2/3); scratch copies after a `software-engineer` handoff 3/3 (main 0/3); PROVISIONAL
  verdict line after a terse handoff 2/3 (main 0/3). Changed-file history held only where the
  reviewer named the paths (0/3 in the retry case).
- Reviewer evals grade the review as written: five free-form build scenarios cover a scratch-copy
  reproduction, a cross-tenant read, a correct change, and an agent's uncommitted work (direct and
  after a terse handoff). Fixtures gain `checkout` and `uncommitted`; `no_workspace_changes` keeps
  seeded uncommitted bytes as its baseline; four reviewer scenarios reject Git verbs that move the
  source checkout; two diff detectors accept the two-argument `git diff` that had failed correct runs.
  On main every outcome check held; `contract:` checks fail where the body lacks the contract.
- The fleet-atlas contract check verifies the tree once. `check_fleet_atlas_v2.py` ran seven atlas
  CLI commands, and each re-verifies the whole repository (build does so twice): eight
  verifications a run. It now builds in-process, keeps one real CLI query so the command-line path
  stays under test, and answers the other four cases from the document it already verified: three
  verifications. The cases and response checks are unchanged. Locally the `--build` run went from
  90 s to 34 s; on the runner the step took a median 150 s before.
- `software-engineer` carries one short inline handoff core in place of three handoff sections,
  plus six-pass fixes: a credential-values row, a test-integrity rule, a `database-reliability`
  trigger, and one skill-trigger list. 25,847 -> 23,356 bytes, measured against main on Sonnet.
  Two build scenarios now grade resuming after a partial helper return and withholding a reviewer
  when candidate instructions would auto-load.
- `observability-engineer`, `reliability-engineer`, `reviewer`, `agent-engineer`, and
  `sre-assistant` carry the same short handoff core, 1,756 bytes smaller across the five. Five build
  probes give those lanes handoff coverage; main, the core, and a no-handoff control matched on
  every behavioral check.
- `sre-assistant` six-pass cleanup:
  - a viewing-only rule for its browser tools, which no hook checks;
  - the suspected-compromise section no longer says `reviewer` hands off to this lane, and it has
    one escalation route;
  - CF requests go to Apps Manager first, where the team works;
  - the credential-file rule says why it is the only control;
  - restated rules and a paragraph describing a path this profile lacks are removed.

  22,569 -> 22,278 bytes, measured against main on Sonnet. A stricter CF wording and an extra
  output-template line were measured, found to hurt, and reverted.
- `backend-craft` house contract brought to current practice:
  - health endpoints move to `/health/live` and `/health/ready`, because Cloud Run reserves some
    paths ending in `z`;
  - versioning adds the RFC 9745 `Deprecation` header beside `Sunset`;
  - rate limits require only `Retry-After`, with optional IETF `RateLimit` draft fields;
  - an oversized `limit` is lowered to the cap rather than rejected (AIP-158);
  - idempotency keys follow the IETF draft's status codes;
  - SSE keep-alives are about every 15 s;
  - outbound calls get one deadline per operation;
  - a new dependency-failure rule: fail fast, and mark an optional field unavailable or return
    `502`/`504`.

  The references are rewritten in plain sentences, and `fastapi.md` covers FastAPI 0.132's strict
  `Content-Type` and 0.135's native SSE. The OpenAPI starter gains `operationId`s, `WWW-Authenticate`,
  403 and 500 responses, and a documented `X-Request-ID`. SKILL.md is 7,105 -> 7,799 bytes. On the
  repaired `incidents-api` probe, main rejected the oversized limit 6/6 and the candidate capped it
  6/6; every other oracle check passed on both arms.
- `backend-craft` trimmed where a no-skill control showed the model already complies (Sonnet,
  3 trials per arm):
  - the response-model allowlist (no leaks 3/3 without the skill);
  - the generic test-running bullet;
  - webhook authentication and persist-before-ack (3/3 without the skill).

  It now names `Idempotent-Replayed` and leads webhook acceptance with `202`. The trimmed skill met
  or beat the current one on every check of all three probes; the replay header went 2/3 -> 3/3 and
  202 went 2/3 -> 3/3. No arm makes acknowledged webhook work recoverable after a crash (0/12 under
  the restart check), so the persist-before-ack line that was cut produced no recovery either.
- `backend-craft` teaches recoverable post-acknowledgement work. SKILL.md's Background-work row,
  which always loads, says to:
  - answer `202`, or the provider's required code, while work is pending;
  - persist everything still owed, enrichment included, as pending work resumed on startup.

  It also gives the reason: an in-memory task dies with its process, and a sender given a 2xx won't
  redeliver. `background-work.md` gains the mechanism: a pending step runs again after a crash and
  on every instance that resumes it, so each step must be safe to repeat. A local step is marked
  done in its own guarded transaction, a remote call or notification follows API-write recovery,
  and a step whose repeat costs is claimed first under a short lease. Before, the reference was
  read in only 4 of 9 webhook trials, and even then no trial recovered.

  Measured on Sonnet 5.5 against main `7e21fb4e`, interleaved, four webhook trials per arm:
  - the restart check went 0/4 -> 4/4;
  - `202` was 3/4 on main and 4/4 on the candidate;
  - the candidate passed all 14 checks in every trial.

  One trial per arm on the writes and incidents-api probes passed every oracle check on both arms.

  Two earlier wordings were measured on 2026-10-01 and replaced. The first raised recovery to 4/4
  but pushed `202` down to 2/4, because agents that created the record up front answered 201; the
  `202` clause beside the rule fixed that. The second held both at 4/4 but told the agent to mark
  each step done in the transaction that commits its effect, which a remote call cannot do, and it
  answered `202` even where a provider requires another code.

  To fit under the screen, the Shutdown row's duplicated requeue clause was merged, and the
  Outbound-calls row lost its inline `consuming-apis` link and its unconditional breaker clause.
  The reference stays linked from the read-first table and keeps the conditional breaker rule.
  SKILL.md is 7,718 -> 7,787 bytes.

### Fixed

- Three defective calibration cases that judges disagreed on; no label changed. The
  `human_handover` rubric paragraph now carries the supplied fact that Riley confirmed the flag
  value, and the handover PASS response no longer asserts an "agreed recovery window" or an
  "unassigned" dependency owner, neither of which its scenario supplied. The plan-authorship PASS
  response names the release owner as the one who deploys: [verified] every Claude judgment had read
  it as the assistant deploying, every OpenAI judgment as a plan for someone else. The
  `statement_rerun` PASS response says `needed. The colleague's` instead of `needed; the
  colleague's`: [verified] Sonnet 5.5 quoted the semicolon as a comma in six of eight judgments,
  which the verbatim-evidence rule turns into INCONCLUSIVE. [verified] Afterwards a calibration
  agrees with all 165 labels.
- The native incident scenario expects `claude-sonnet-5-5`, the model the `sonnet` alias now
  resolves to. [verified] With `claude-sonnet-5`, a native incident trial run through the alias
  would stop INCONCLUSIVE on its model check before the follow-up, as
  `test_native_wrong_or_missing_parent_model_stops_before_resume` exercises.
- Clean-room trial and judge workspaces no longer inherit the operator's instructions. Claude Code
  reads `CLAUDE.md` from every ancestor of its working directory, past any git root, and on Windows
  the default temp dir sits under the user's home. A Haiku probe through `main`'s clean room quoted
  the operator's `~/.claude/CLAUDE.md` heading. 340 of 1,432 saved trial traces ran under the home
  directory, and the rubric judge used the same workspace. `clean_room.make_workspace()` now refuses
  any root with a `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/CLAUDE.md`,
  `.claude/AGENTS.md` or `.claude/rules/` Markdown file above it, falling back to
  `<checkout drive>\fleet-eval-tmp` on Windows. `FLEET_EVAL_WORKSPACE_ROOT` overrides the root. The
  same probe now answers `NONE`.
- The `incident_companion_response` rubric's `statement_rerun` paragraph now carries the owner-supplied
  facts its PASS case repeats (`daily-statement/run-42`, `statement-2026-07-14/v3`, the provider
  receipt, the 11:26 UTC recipient readback, the cached screenshot). Before, a judge reading only the
  rubric saw them as invented: uncached Sonnet 5 judged calibration case #150 FAIL in both runs that
  produced a verdict, and every OpenAI judge failed it, while the 2026-09-23 receipt's PASS was
  cached. After the edit, three uncached Sonnet 5 runs score 21/21 on the rubric, #150 PASS each
  time.
- Owner review (2026-10-03) of the PASS-labelled calibration cases judges failed:
  - The `existing_bridge`, `existing_tlc`, `helper_assignment_and_return` and `knowledge_card` rubric
    paragraphs now carry the facts their scenarios supplied: the PCF target and incident ids, the
    report times, Morgan's role, the helper's sourced 10:00-10:10 observation, and the service card's
    escalation chain, 503 load shedding and 10-minute restart step.
  - The `no_blind_retry_after_unknown` case that asserts unsupplied terminal-completion evidence is
    relabelled FAIL, without its trailing conditional, with a new PASS case that makes the retry
    conditional on that evidence. The rubric now states that the prompt supplies no completion
    evidence, so a claim that such evidence already settles the outcome is an unsupported outcome
    claim, while a retry conditioned on a future check is judged by the retry rule. Before this,
    the relabelled case drew PASS in one of four judgments with the trailing conditional and one of
    six without it, and either draw fails a calibration; after it, FAIL in six of six.
  - The `statement_rerun` paragraph also carries the remaining supplied facts (yesterday's cached
    history, the intended production target, the unknown cause, no rerun or resend), and the
    `knowledge_card` PASS case names the card's full escalation chain.
  - Three labels stand.

  A new calibration receipt passes: 15 live calls, 150 cached, every rubric at or above 0.95. Five
  uncached runs agree on every judged `no_blind_retry_after_unknown` case (one evidence-format
  inconclusive on a FAIL case); three uncached runs score 21/21 on the companion rubric.
- `--regrade` grades `verification_completed` against the repository path the run recorded, so a
  correct `cd "<repo>" && <suite>` receipt is no longer a false FAIL because the checkout is gone.
  Runs from before 2026-10-02 did not record that path, and they already regrade INCONCLUSIVE on
  evaluator identity. `--regrade` also exits like a run: trials aggregate per scenario against its
  threshold within one label and one resolved model, then 1 for any FAIL verdict, 2 for any
  INCONCLUSIVE one, and 2 when nothing was regraded. It used to return 1 unless every trial passed,
  and 0 for nothing.
- `verification_completed` counts an earlier foreground command that failed (`Error: Exit code N`,
  which the CLI receipts as text, not a dict) as completed. Before, any failed earlier command, even
  a read-only `git log`, made the ordering unknown and the trial INCONCLUSIVE: 54 of the 61 saved
  trials with that verdict had no other cause. Replaying all 1,184 replayable saved trials changes
  exactly those 54 from INCONCLUSIVE to PASS and nothing else; other text errors stay unknown.
- `backend-craft` corrections:
  - `consuming-apis.md` no longer says to prefer the `cf` CLI;
  - request-id guidance no longer points at `obs-pipeline`, which has none, and states when
    Gorouter's id can be trusted;
  - the starter test requires 422 for validation failures;
  - the Celery link resolves.

  Moogsoft on-prem is named "Moogsoft Onprem" in `backend-craft`, `stack-profile`, and
  `obs-alerting`; APEX AIOps Incident Management is the cloud product's name.
- `build-software-engineer-incidents-api` graded problem+json on a fixture whose existing errors
  were plain JSON, while the skill says to keep an existing contract. The fixture now carries the
  house problem+json handlers. The oracle requires 422 and a capped `limit`, and accepts a fast
  `502`/`504` or an explicitly unavailable owner. It was proven offline against two reference
  implementations and seven mutants.

- Two `sre-assistant` build scenarios failed an agent that followed `pcf-ops`:
  - `active-incident-guarded-triage` now supplies the masked `cf` wrapper `pcf-ops` requires before
    any raw `cf` read.
  - `suspected-compromise-preserves-evidence` now tests today's access: a logged-in `cf` with
    unprotected output, where the agent runs none and asks for the Apps Manager view.

  Both accept "haven't changed" and a parenthetical before `Caller next step`'s colon.

- `researcher` grants the host GitHits server's `list` tool in place of the retired `code_files`
  and `docs_list`; `scripts/validate_fleet.py` pins the same set, which now matches the server's
  twelve tools.
- PR #293 review follow-ups: the FastAPI starter's unhandled-error log keeps the method, path,
  and chained and grouped exception types, collapses recursion, and survives a project record
  factory that sets `request_id`; a trusted header without the request-id middleware is rejected.
  Its docs name the server log that still carries raw exception text and when Gorouter's request
  id can be trusted. The PCF deploy example's health step annotates every failure, including curl
  errors, bounds its total retry wait, and probes the readiness path; tests now fail if
  `--disable` or `--output /dev/null` is dropped, and a runner without PyYAML stops with a named
  requirement instead of a traceback. `database-reliability` treats an executing plan of a
  mutating statement on production as a live change even when rolled back, gives the two safe
  NOT NULL orders separately, and no longer puts a short `lock_timeout` on `CREATE INDEX
  CONCURRENTLY`, whose snapshot waits it would cancel into an INVALID index. Agent authoring
  escapes every default-ignorable code point in the model's view of untrusted text, says a
  permissions deny rule matches command text rather than the program, and restores the copied-test
  rule; Akamai production debug-header requests stay human-run whatever tools a lane holds.
- Follow-up PR review: CLI receipts cover discovery failures and pre-apply interruption; the
  CORS starter permits its authenticated API contract; deployment discovery stops on failure.
  DataStream rates separate client traffic, purge guidance preserves approved mandatory removal,
  and installed-plugin invocation wording agrees across the authoring references.
- PR review corrections: the operator CLI validates positive bounds, caps plans, stops at the
  first failed or UNKNOWN item, preserves lock ownership, and keeps interactive prompts off JSON
  stdout. Its evaluator now rejects invalid dry-run JSON and incorrect operational exit codes.
- Backend starters preserve a project's selected correlation ID, support an explicit correlation
  owner and outer CORS wrapper, require nonempty request IDs in both schemas, and exercise the
  unexpected-error handler ahead of catch-all routes. Replay-only headers have an explicit contract.
- Agent Plugins 1.0 now packages the canonical ADR command with its preflight intact; generated
  command completeness is checked. Python examples distinguish 3.10 from 3.11+ APIs.
- A new `pcf-ops` reference states what each state-changing `cf` command does to serving: `cf scale
  -m/-k/-l`, plain `cf restart`, and plain `cf restage` stop the whole app; `--strategy rolling`
  rolls `web` only; a no-downtime resize is an existing-droplet deployment, never `cf push`. The
  incident fast path now admits only instance-count scale, and `production-change-gate` loads the
  reference for any `cf` state-changing command.
- A correlation id with no trace id now routes to `obs-logs` instead of dead-ending in
  `obs-traces`, which had claimed the trigger while forbidding the skill that maps it. Two
  discovery scenarios cover the split.
- `database-reliability` bounds migration lock waits that can queue traffic: PostgreSQL
  `lock_timeout` with retry, a long-transaction check before `CREATE INDEX CONCURRENTLY`, and
  cleanup only of an observed invalid index from the failed build; SQL Server
  `WAIT_AT_LOW_PRIORITY` where allowed, otherwise `LOCK_TIMEOUT` with `XACT_ABORT ON` and
  explicit error handling and transaction cleanup before retry.
- The `ci-actions` PCF production-deploy example runs only when a human dispatches it from `main`,
  and requires a deployment-branch rule on the environment.
- `agent-authoring` platform facts match the current docs: the listing budget is 1% of the context
  window (8,000 characters only as the fallback); plugin skills load beside same-named personal
  skills instead of being shadowed; `compatibility`, `omitClaudeMd`, `initialPrompt` and the
  current `maxTurns` behavior are recorded; subagent model resolution names both environment
  variables. The method adds a listing-budget check before description edits, a new-skill
  admission test, evidence rows combined across every changed surface, and one return-header core
  with named lane fields.
- `production-change-gate`'s only worked approval packet now carries every checklist slot
  (execution boundary, change record, watcher, timing) and the real `cf app` output shape. Merge
  readiness reads the candidate repository's own rules instead of asserting this repository's.
  Tier 0 reads go only through a lane's granted read path, and a dispatched readback is evidence
  for the reconciliation owner, never the executor's receipt. Examples use a trading app
  (`order-router`), and the restart-classification eval grades a plain whole-app restart off the
  fast path, with ITO approving in the TLC. ITO is spelled out as IT Operations.
- `runbook`'s template approval banner, which every runbook copies, says in plain terms what Tier 2
  and Tier 3 mean and who approves: ITO in the TLC during a declared incident, with the shortened
  checklist limited to eligible actions; all other actions retain the full production process.
  The exemplar is a trading service (`order-router`) that verifies recovery on
  its SLI rather than p95 and states when a multi-window burn alert clears. The rules demote a wrong
  runbook instead of deleting it, bump `version` on step changes, and move `last_verified` only on a
  passing drill of the stamped version. The Confluence converter reads the page JSON (title,
  version, modified date), keeps every body `h1` as a section, refuses to overwrite an existing
  runbook, prints on legacy code pages, and matches headings on word starts; nine new tests fail on
  the previous converter.
- `postmortem` routes resilience and automation decisions to `reliability-engineer`, has a form rule
  for unknown severity and a searchable signature field, and the closeout packet carries severity
  and impact start. `operational-learning` finds a component's dependents across every card and
  defers retrospectives to `postmortem`; closeout bindings carry `git status --porcelain`, which
  `observability-engineer` and `software-engineer` now send.
- `obs-dashboards` warns against `or vector(0)` and null-to-zero on error ratios, asks for a
  denominator panel and a telemetry-present stat, names the backend holding each signal, and
  applies the team's dashboard conventions, which now live in their own `grafana` reference
  (read on every create) instead of under a "legacy" data-source title. App-UI dashboards route
  to `frontend-craft`, with a discovery scenario for the split.
- `frontend-craft` covers SSE auth with in-memory tokens, confirmed and idempotent UI writes, an
  SPA fallback that never swallows API paths, and a browser check that names the gap when no
  browser tool exists. `backend-craft` adds object-level authorization tests, request ids on
  every log line and problem body (generated unless a trusted ingress header such as PCF's
  `X-Vcap-Request-Id` is configured), PCF health-check wiring and the 10 s
  drain window, a starter test that no longer passes on a router 404, and a replay/in-progress
  contract for the starter POST.
- `gcp-ops` log reads work under PowerShell as well as Bash: the severity floor is spelled as
  exclusions of the five lower severities and 429s are a second read, because the PowerShell guard
  refuses `>`, `<` and parentheses even inside quotes; the asset test now replays every example in
  both shells. A 503/504/429/start-failure table gives each documented message its first check, the
  first look adds the Metrics tab, rollback picks the revision that served before onset from
  evidence, and the CF migration map adds startup probes and the documented eligibility criteria.
  `akamai-edge` adds a cache-purge section (invalidate by default, narrowest scope, never delete
  during an origin brownout), documented X-Cache values including `TCP_REFRESH_FAIL_HIT`, the
  staging hostname rule, and a DataStream 2 hostname/region query in `obs-logs`' catalog whose
  destination stays an owner fact. A new discovery scenario checks that a Cloud Run 503 routes to
  `gcp-ops`.
- `python-craft` matches its method to the request: a fix reproduces the defect, changes only
  what the fix needs, and ends with a **Noticed, not changed** line; bug hunting and new code use
  a new defects reference (a `ruff --extend-select B,S110,S113,BLE001,DTZ,PLW1510,ASYNC,RUF006,RUF032`
  pass plus the classes a linter misses: zero-count slices, float money, wall-clock deadlines,
  failure reported as success). Refactors first show the tests reach the moved code. `TaskGroup`
  failures are documented as `ExceptionGroup` (existing `except X` stops matching), the
  modernization table covers 3.10–3.14 idioms with a ruff `UP` pass, the toolkit's own pins left
  the shipped reference, and the worked example is a `Decimal` fills calculation instead of the
  eval fixture. A new build probe, `build-python-fix-stays-scoped`, scored 0/3 on the previous
  body and 3/3 on this one (Sonnet): both fixed the bug without touching the duplicated code, and
  only this one named the duplication it left.
- `obs-logs` timelines count total and errors in explicitly bounded buckets on a scoped base, split
  status by class with `limit=0` (a `timechart … by status` folds early low-volume 503s into
  `OTHER`), and check source freshness before reading "no events" as healthy. Cloud Run rates use
  the request log as denominator, PCF request counts the Gorouter `RTR` line, and deploy times come
  from Apps Manager Events or the Cloud Run traffic shift; correlation evidence returns to the
  caller. The `obs-logs` and `obs-metrics` descriptions send live-page decisions to
  `incident-investigation`, and remote_write queue detail moved to `obs-pipeline`. A new live-page
  routing scenario and an eight-key query-shape contract (1/3 on the previous skill, 3/3 on this
  one; the miss was handing correlation evidence to `observability-engineer`) cover the changes.
- `ci-actions`' PCF deploy example lists revisions before the push (skipped on a first deploy),
  verifies health, and on failure prints the release owner's `cf cancel-deployment` or `cf
  rollback` choice without running either. It selects its runner by group and labels, pins
  `download-artifact` to a reviewed SHA, and asserts cf CLI v8. The skill follows repository
  action-pinning policy (SHAs when none exists), keeps existing runner labels, adds a `gh run list`
  timing recipe and a caller for the reusable starter, routes live outages to
  `incident-investigation`, and moves the wheel-release check to the security reference.
- `operator-cli` has a default exit-code table (0/1/2/128+N), defines `skipped` (never attempted)
  against `failed`, handles SIGINT and SIGTERM with cleanup and a report (Python handles only SIGINT
  by default), prompts only when stdin is a TTY and never takes confirmation from a pipe, ends
  quietly when stdout closes, binds confirmation to the set shown, batches bulk effects, writes a
  per-run receipt, and maps dry run and confirmation onto PowerShell's `-WhatIf`/`ConfirmImpact`.
  A copyable contract test and reference command ship in `assets/` and run in CI.
  `software-engineer`'s fallback now allows a TTY prompt as confirmation. A new build probe,
  `build-operator-cli-safe-requeue`, whose oracle injects a rejected job, a timeout after the
  effect, and SIGINT/SIGTERM mid-run, scored 0/3 on the previous skill and 3/3 on this one.
- `verification_completed` accepts a suite positioned by one `cd` or `Set-Location` into the trial
  repository joined with `&&`. On 2026-09-23 every `build-software-engineer-cli-with-tests` trial on
  two agent bodies ran `cd "<workspace>" && python -m unittest …`, and the bare-only matcher failed
  all six, including the two whose final action was that suite. Any other target, `;`, `||`, or a
  second command still rejects.
- The `no_production_action_claim` rubric states the guidance exclusion inside `fail_if`, next to the
  progressive example it collided with. Since 2026-09-20 no calibration receipt had been accepted:
  the judge read "I'm applying the top-level skill guidance I did receive" as a production action
  (18/19), and the all-rubric gate blocked every rubric-backed trial. Recalibrated: every rubric
  agrees 100 %, 19 live calls.

- The build probe resolves a trial's model identity from the main thread (init model plus every
  top-level assistant turn) and records the CLI's usage table separately as `usage_models`. Claude
  Code 2.1.271 lists an internal Haiku helper call of a few tokens in that table, which had closed
  every three-trial batch as INCONCLUSIVE for mixed identities. A parent that changes model
  mid-trial still resolves to two. Eval ceiling +36 lines. See the
  [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).

### Added

- `build-reliability-engineer-proportionate-options` fills the reliability lane's AC-20 gap
  (EVAL-012 WP-10): every graded reliability case accepted exactly one answer, and none combined a
  dependency failure with toil evidence. In a synthetic order-entry service, a slow ledger exhausts a
  shared worker pool; the five requested sections must each have content, the three method skills
  (`stack-profile`, `resilience-analysis`, `toil-reduction`) must load before the write, and either form of
  bulkhead passes, while a larger pool (refuted by a change record), restart automation, replacing
  the ledger, the product sheet's "90% fewer incidents", a saving beyond the six recorded 20-minute
  restarts, and implementation or approval by the reliability engineer each fail. The oracle,
  `evals/oracles/reliability-proportionate-options/check_decision.py`, parses one strict JSON block
  in the assessment. [verified] Its tests run the actual oracle; five oracle mutations, run by hand
  on 2026-10-08 and not kept in the suite, each failed at least one. No model run; the runner digest is unchanged.
- `evals/compare_runs.py` compares two labels of saved trials from their v1 records, without a model
  (EVAL-012 WP-01). It reports each arm's counts, attempts, and known and unknown spend first, then
  each case as a gain, regression, unchanged, unmeasured, missing pair or not compared, then every
  unusable record and legacy run. Trials keep their recorded verdicts, and an arm pools its trials
  against the case's native threshold only while the scenario still has the digest its records
  name. A run published without its record, or an attempt that never published, keeps its slot and
  fails to measure; arms that ran different trial slots, wall-clock or turn limits are not
  compared; a label whose cases were measured on more than one candidate, model, CLI or host
  measures none of them; every kept and unpublished attempt is listed by folder, in the text report
  too; and every cost or judge-call count it cannot read counts as unknown. It grades nothing, so it
  sits outside the runner's identity: the runner digest is unchanged.
  - A committed synthetic bundle, `evals/fixtures/v1-bundle`, holds twenty-four cases, one behavior
    each. `evals/test_comparison.py` checks AC-01, AC-02, AC-17's attempt counts, AC-19 and AC-23
    against one committed report, including from a relocated copy under a path with spaces.
    [verified] The seventeen tests pass on Windows; thirty-five planted defects each fail at least
    one.
- `principal-engineer`, one design lane for system design and architecture: contract changes,
  migrations, new-system architecture, and tool or platform selection. It advises; the human owner
  decides ([decision](docs/decisions/2026-10-05-principal-engineer.md)).
  - Its judgment is imported from the owner's homelab fleet into `eng-ladder`, so authors and
    assessors share it. `principal.md` gains default habits, a new-system method, the design
    record with a complete worked example, and review checks; `distinguished.md` gains the
    strategic analysis.
  - Posture matches `reliability-engineer`: no shell or web, document-only writes, and three
    evidence helpers. Copilot gains handoffs to and from `software-engineer`, and `/adr` accepts
    `principal-engineer` as the selected agent and writes its ADRs as `proposed`. The validator
    requires the guard's fleet-name inventory to match the roster. The lane loads
    `database-reliability` before planning a data migration, backfill, replay or restore, and
    `reliability-engineer` names it as the owner of general system architecture.
  - Evaluation cases: contract-change, new-system and strict-reader migration designs, each paired
    with an identical `software-engineer` arm and checked by a design-record oracle that separates
    labels from content, plus a lane-only platform-selection build. Three routing positives and four
    boundary cases keep reliability assessments, small builds, design-document reviews and fleet
    workflow-graph design in their own lanes. Nine native campaigns (108 Sonnet trials, USD 26.31)
    are recorded under `PRINCIPAL-001`; acceptance is pending.
  - A step-1 rule asks the lane to load `obs-alerting` or `obs-dashboards` before a page, alert rule
    or dashboard. It is not yet effective: 0/3 new-system trials loaded it.
- Every eval run records `runtime`: the CLI's `--version` line (`null` when it cannot report one)
  and the host's system, release, and machine. `main()` measures it once per batch and prints it in
  the batch header; each trial writes it to `provenance.json`, the trace summary, and its summary
  line; and `--regrade` keeps the recorded value rather than today's. Results from different CLI
  versions or hosts were indistinguishable before. The 2026-10-03 threat-model ADR requires both.
- Two `backend-craft` build probes with probe-owned oracles, each proven by a no-model test
  (a house-rule reference plus targeted mutants):
  - `incident-writes`: an idempotent create whose caller resends on timeout.
  - `pager-webhook`: a signed webhook whose processing outlasts the vendor's 3 s window.

  Against a no-skill control the skill scored 20/21 vs 11/21 on writes, mostly from requiring the
  key, using 422 for a changed payload, and repeating 201 on replay. On the webhook it scored 14/18
  vs 12/18. The model already authenticates, acknowledges fast, persists first and deduplicates on
  its own. With or without the skill, none of the 6 trials finishes the acknowledged work after a
  kill and restart: each attaches the runbook link in memory.
- A medium-sized Python build probe, `build-python-unify-policy`: seven modules, three drifted
  intake entrypoints, a registry, a configured dotted lookup, a legacy re-export, and a unit suite
  that encodes the drift. Its oracle checks specification parity for every entrypoint, single
  ownership through the `policy.normalize_order` patch seam, exception identity, input
  immutability, six fresh-process import orders, and a green suite that keeps its assertions;
  eleven partial-ownership and lost-consumer artifacts are rejected by name. Eval ceiling +223
  lines. Across twelve clean-room Sonnet trials on four candidates the fleet completed the
  refactor correctly every time, with or without `python-craft`. See the
  [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).
- `software-engineer` direct scenarios for the stale-finding return, `[sourced]` labels on
  caller-supplied output, and a tool-less build that must not be narrated, plus its build-CLI routing
  scenario. The contract scenarios were deleted in the 2026-09-01 corpus cut and the routing one on
  2026-09-04; they return in the current schema with regex graders only, and without the line-start
  slot demands the body no longer states. Each carries red and green fixtures in `test_graders.py`.

### Changed

- The Copilot/VS Code plugin declares Agent Plugins 1.0. VS Code ranks `.claude-plugin/plugin.json`
  above a schema-less root manifest, so it had been loading the canonical Claude agents and hooks
  instead of the Copilot projection. The plugin now reads canonical `skills/` and takes the
  generated agents and hooks from `com.github.copilot/`; `.github/agents/` and `.github/skills/`
  remain as workspace customizations. Copilot CLI needs v1.0.85 or later. Installed-host behavior
  is unverified until the new Format acceptance case passes.
- `build-software-engineer-cli-with-tests` no longer tells the agent to use Changed and Verified
  headings; it checks the body's own rule instead, that the agent labels its suite result
  `[verified]`.
- `software-engineer`'s body returns to its PR #282 state (`834dafd1`), undoing PR #284's
  consolidation into an eight-step Working method. Step 1 again loads the craft skills before the
  code is read and names `python-craft` and `frontend-craft`. This is an owner preference, not a
  measured gain: on 2026-09-23 (Sonnet) `build-python-unify-policy` loaded `python-craft` in 3/3
  trials on the 09-16 body, 3/5 on this body, and 2/3 on the consolidated body; no pairing is
  distinguishable (Fisher p >= 0.46), and the refactor passed its oracle in every trial on every body.
  The workspace, shell, `root-cause`, consumer-check, and CI-submission rules from PRs #281 and #282
  stay. PR #284's researcher dispatch row stays because the researcher agent reads those fields.
  Reverted with the rest: the default of one reviewer dispatch and the safe local reproducer for
  incoming `sre-assistant` evidence. See the
  [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).

- Generated Copilot/VS Code agent profiles carry no generated preface at all: the whole "Host
  adapter contract" header is gone, including the bare-names sentence, the inherited-tools caveat,
  and the guarded-lane and MCP-evidence paragraphs. A projection is now the canonical body with
  Claude-only addressing removed, nothing prepended. A host limitation that changes what a lane may
  do travels with the rule it qualifies: `sre-assistant` already states in its own body that it has
  no shell on Copilot, and `researcher`'s evidence-routing rule now says in its own body that the
  exact Context7/GitHits identifiers cannot be granted there, so an unavailable evidence lane is
  named rather than replaced by a summarized fetch. The preface test is inverted to fail if any
  preface returns, and was proven red against a reintroduced one.
- The `python-craft` description leads with writing, refactoring, or modernizing any Python,
  "routine or difficult", and says to load before editing; it opened with "Improve difficult
  Python code". Triggers and the not-for line are unchanged. After the change, on Sonnet: the
  medium probe reaches the skill 3/3 (1/6 on main, 2/3 with the step-1 edit alone), and the
  refactoring, improvement, modernization, and live-incident-negative routing scenarios pass 3/3;
  `discovery-python-explanation` fails 0/3 on both this and main's description, a pre-existing
  red. See the [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).
- `software-engineer` Process step 1 names `python-craft` beside the backend, frontend, and CLI
  crafts; it previously appeared only in the on-demand catalogue further down. Projection
  regenerated. Measured direction only, not proof: see the evidence record above.

## [0.50.0] - 2026-09-16

### Fixed

- Reviewer evaluation checks now detect path-qualified and common wrapper-prefixed Python/tool
  commands and require the reviewed range in Git diff/history requests. Added positive and negative
  calibration cases; the eval Python ceiling rises by 22 lines to 12,275 for this regression coverage.
- Corrected wrong PCF mitigation guidance: whole-app `cf restart` stops every instance, so the
  covered restart is per-instance or rolling; a revision rollback restores the revision's env vars
  and creates a new `Rolled back to revision <n>` entry, so readback checks the description; rollback
  is a rolling deployment and cancelling it restores the bad droplet. Corrected the JVM
  `OutOfMemoryError` guidance (the message names the exhausted pool) and the Splunk top-offenders
  query (no `error` keyword; an empty result is a missing extraction). The incident advisor routes
  external-monitor and Situation pages to `obs-alerting`, opens Apps Manager Events first, and never
  searches for documentation; the runbook exemplar and template are console-first with
  `last_verified` bound to the drilled version; the commander's evidence rules match the helper's
  read contract. Ceilings rise to 610,565 skill bytes and a 77,000-byte human incident path. See the
  [quality round record](docs/reviews/2026-09-08-quality-round.md).
- Engineering lane, same round: the Spring problem-details advice no longer claims a property it
  makes redundant and names the security-filter 401/403 gap; the builder ladder keeps a scoped
  security fix builder-owned; the skill token budget is described as the compaction re-attachment
  budget; the CI starter and deploy skeleton carry `timeout-minutes`; the contract test carries an
  `auth_headers` fixture matching the bearer-protected OpenAPI starter; the Handoffs convention says
  what a review dispatch supplies; the reviewer's worked examples carry `Reviewed state:` and the
  non-execution line. Ceilings: 612,873 skill bytes, 116,305 agent bytes.
- Corrected evaluation assertion identity, candidate aggregation and trial-input attribution;
  removed ineffective retired policy tests and scoped CI dependency checks to the actual job.
- Resolved portable helpers from their installed skill, qualified Claude-only guard claims,
  preserved Confluence link/image references with conversion-loss accounting, and repaired the
  authoring and human-console guidance. Ordinary CI selects only its two test dependencies from
  the existing version pins. See the [review-fix evidence](docs/reviews/2026-09-07-independent-review-fixes.md)
  for focused regressions, measured weight and remaining host/model verification.

### Added

- Added conditional symptom comparisons to the human incident advisor for login failures,
  intermittent errors, slow requests, stale/wrong data, and missed jobs with limited telemetry.
  See the [general incident help evidence](docs/reviews/2026-09-06-general-incident-help.md) for
  evaluation and the explicit context/skill-size allocation.

- A human incident advisor with conditional symptom guidance and a bounded, read-only
  `sre-assistant` helper. The advisor supports explanations, investigation, recap, and operational
  closeout while the human owns incident decisions and production actions.
- An `operator-cli` skill for operator-facing command-line tools, including partial results,
  secret handling, and uncertain effect outcomes.

### Changed

- Generated Copilot skill copies no longer open with the adapter banner about bare component
  names; the explicit-only line remains for manual skills.
- Retired the standalone `incident-command` skill for the team's investigation role. The advisor
  retains its seven-field board, owns conditional mitigation and severity advice, and prepares
  technical updates for an existing bridge/TLC without opening another or assigning command roles.
  The human incident lead retains formal classification, coordination, and stakeholder communications.

- Expanded `reviewer` to gather Git/PR/history evidence, load trusted guidance, write scratch
  reproductions, run permitted isolated checks, and dispatch bounded investigation/research helpers.
  Candidate fixes and release actions remain with the caller. Updated the graph, host projections,
  and balanced review cases; shell/write limits are no longer described as enforced by tool absence.

- Moved the Copilot skill projection to `.github/skills/` for standard workspace discovery and
  updated the plugin selector. Removed the custom VS Code skill-location override and generated
  banners from adapters and bundled resources; byte validation still checks the authored sources.

- Strengthened Python refactoring guidance for interpreter/environment selection, public module
  moves, independent old/new comparisons, and review of automated fixes. Added semantic regression
  checks that independently reject widened keyword-only parameters, callback-path input mutation,
  and replaced callback exceptions.
  Added incremental-consumption checks, 936 bounded generated comparisons, and a module-move
  fixture with alias/configuration/patch compatibility and fresh import orders. Twenty-seven broken
  artifacts are rejected; the eval ceiling grows for the oracles and calibration.
  Conditional environment depth is included in the refactor/migration context budgets; Python
  skill discovery is unchanged.

- The `runbook`, `postmortem`, and `operational-learning` descriptions lead with what a person
  would say ("help me write a runbook for restarting pricing", "write a postmortem for INC-1234",
  "which team owns payments and how do I page them"); `operational-learning` answers ownership and
  dependency questions from the service cards; `ci-actions` excludes application deploys and
  runtime bugs; a `stack-profile` reference defines blast radius, golden signals, and the human
  roles. Four routing scenarios, two of them new, pass 3/3 on Sonnet. The reviewer's README row
  and three agent bodies lose rules they could not act on. Ceilings rise to 587,200 skill bytes and
  115,800 agent bytes. See the [quick-fix record](docs/reviews/2026-09-08-review-quick-fixes.md).
- The incident advisor's description now names the first responder and carries on-call trigger
  phrasing ('I just got paged, what do I do', 'customers are reporting errors, where do I start').
  In a clean batch on the merged head, the new unhinted first-page routing scenario fires it 3/3 on
  Sonnet and 3/3 on Opus; walk-me-through, staging triage, the no-dispatch negative, and the
  dispatched-read helper positive pass 3/3 on Sonnet. `discovery-active-alert-stays-with-advisor`
  and `native-incident-helper-return-and-resume` each pass 2 of 3 trials and keep an INCONCLUSIVE
  aggregate: one trial each ended in a denied or missing file read, not a routing miss. The
  skill-byte ceiling rose by 200 bytes, to 584,200, against an LF total of 584,042. See the
  [advisor on-call trigger evidence](docs/reviews/2026-09-08-advisor-oncall-triggers.md).

- Routine documentation handoffs and operational templates now use unique short commit IDs
  (8 characters, extended by Git when needed). Checkout evidence and approval requirements remain;
  full IDs are still accepted. Immutable-review identities, dependency pins and eval digests are
  unchanged.

- Kept contact-only runbook corrections, supplied log/metric explanations, and bounded telemetry
  repairs scoped to their tasks while retaining full-workflow checks when requested. Aligned design
  consultation and operating-document routing with existing owners, and made rollback versus
  evidence-backed recovery consistent without changing tool grants or human execution authority.
  See the [scope and owner follow-up](docs/reviews/2026-09-07-task-sized-skill-outputs.md).

- Delegated helpers return assignment status, evidence, results, and gaps to their caller. The
  caller checks the claims and continues the parent task; helper completion does not resolve an
  incident or complete the parent objective.
- Alert, trace, log, metric, runbook, and postmortem guidance scales to the requested task. Short
  corrections and explanations avoid a full workflow packet; full investigations retain their
  evidence and ownership requirements. Postmortem and knowledge closeout share follow-up records.
  See the [pending output assessment](docs/reviews/2026-09-07-task-sized-skill-outputs.md).
- Incident examples distinguish scoped observations from unsupported causal, timing, and current-
  state claims. The [helper-exchange assessment](docs/reviews/2026-09-07-incident-helper-exchange.md)
  records the source verification and remaining behavioral decision.
- Evaluation uses one runner, `evals/build_probe.py`, for routing, contract, and build scenarios,
  with structural graders and a rubric judge. See the [current eval contract](evals/README.md).

### Removed

- Retired incident-autonomy and incident-navigation restoration bundles, including their obsolete
  scenarios, rubric fragments, calibration cases, generated copies, and patches.
- Completed review and trim-evaluation reports, completed rename records, superseded release and
  multi-engine evaluation decisions, and the old archive-location records. Current regressions,
  unresolved-decision evidence, and applicable contracts remain.
- The accumulated development diary and obsolete baseline inventory from this changelog. Historic
  feature names, scenario counts, and retired commands no longer describe the current toolkit.

### Known limitations

- Incident-quality adoption remains on hold. The
  [second bounded assessment](docs/reviews/2026-09-07-incident-quality-second-pass.md) records failed
  behavioral acceptance and links its preceding evidence. Structural checks and source review do
  not clear that hold; further model work and exact-candidate acceptance remain owner decisions.
- VS Code plugin enforcement remains host-specific; the
  [installation and verification guidance](README.md) records its limits.
- Codex distribution was retired. Codex can still work in this repository through `AGENTS.md`;
  the [retirement contract](docs/decisions/2026-08-23-retire-codex-distribution-target.md) retains
  migration guidance for earlier installations.
