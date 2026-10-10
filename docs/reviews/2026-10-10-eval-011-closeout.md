# EVAL-011 runner closeout

Date: 2026-10-10. Base: `f1ae05c8f3c40d21efb597f3f26fe8e918ba855f`.
Scope: [EVAL-011](../fleet-roadmap.md#eval-011--bring-the-eval-runner-into-line-with-the-accepted-threat-model)
and the remaining runner gaps from [WP-02](2026-10-08-wp02-native-readiness.md), under the accepted
[threat model](../decisions/2026-10-03-eval-harness-threat-model.md).
The owner delegated routine closure decisions on 2026-10-10. This report retains the evidence and
dispositions needed by EVAL-012; it does not accept a fleet candidate or complete a live comparison.

## Result

[verified] The remaining runner repairs are implemented. Both independent oracle findings were
reproduced and repaired, and grading subprocesses now share the trial's disposable temporary root.
Final integrated verification and exact-revision review are being completed before closure.

## Remaining findings and their resolution

| Finding | Resolution and regression evidence |
|---|---|
| R10: `tool_call_count` kept a live verdict instead of remeasuring trace evidence | It declares trace dependence without the override. Rescoring counts recorded calls; absent counts stay INCONCLUSIVE. Completed and cut-short cases cover the floor and ceiling in `test_eval011_grading.py`. |
| R6: audit proxy still accepted requests during grading | Stop admission, drain admitted handlers, and close keep-alive connections before assessment; keep the backing service available for direct read-back. A settlement failure invalidates affected service evidence while retaining a supported forbidden action. |
| D6: legacy native timeout lacks `cut_short` | Recover a cut-short end only when saved raw evidence proves the declared runtime profile and unchanged plugin digest. Cover both initial and resumed invocations; missing identity evidence remains void. |
| JSON equality treated `true` as `1` | Recursive JSON equality separates booleans from numbers, including nested arrays/objects, while preserving numeric `3 == 3.0`. This repairs the demonstrated defect without inventing a numeric-type distinction. |
| Oracle exceptions and candidate failures shared exit 1; early candidate exit 0 could pass | 100 executable commands across 40 scenarios now distinguish FAIL 10 from machinery failure 1. The 93 Python commands require fresh supervised completion evidence and candidate-phase attribution; seven UI commands require the actual assertion report. Eight semantic-review placeholders remain deliberately unavailable. |
| No comprehensive scenario turn limits | Every active scenario declares a limit: 235 added, seven existing limits preserved. Validation and direct trial admission reject missing limits. The two-invocation native budget remains shared. Values and limitations are below. |
| WP-02 gap 6: rubric omitted earlier conversation evidence | Include the initial success, expected receipt and follow-up times; distinguish success from start, send and arrival. Six new semantic controls join calibration. Unchanged saved replies were judged separately under the repaired binding. |
| WP-02 gap 7: ignored plugin files differed between digest and runtime | Hash and stage the same Git inventory: tracked files plus nonignored untracked files. Ignore untracked ignored files in both; retain tracked ignored files. Refuse linked inputs, unreadable/corrupt inventory and contaminated images. |
| WP-02 gap 9: batch-cap paths had not crossed the actual runner | Real subprocess stubs through `run_trial` demonstrate a USD 1 cap schedules two USD 0.50 trials and no third; unknown cost stops scheduling and blocks resumed work before another call. This is execution evidence without model spend. |
| WP-02 gap 10: incomplete argv, account and elevation evidence | Save `invocation.json` before every launch, including single-turn and failed launches; record argv, workspace, start/end, exit state, model/session and observed runtime. Windows process-token SID/elevation or POSIX effective UID identifies the account. CLI admission refuses missing, failed or elevated observations before output or paid work. Legacy records remain readable, but unknown account identity cannot pool. |
| WP-02 gap 11: CLI and candidate temporary residue | Both CLI and oracle environments route `TMP`, `TEMP` and `TMPDIR` beneath the disposable trial root and suppress Python bytecode. `cleanup.json` records removal/retention and errors. A post-assessment cleanup failure preserves the verdict and stops reuse. Actual subprocess controls prove temporary-file removal. The ten old WP-02 residue files were archived and hash-verified. |

## Compatibility and quality decisions

[verified] `Outcome` is now a frozen value whose equality and hash include the three-state verdict,
evidence and flags. Pair unpacking and indexed reads remain supported, but a plain boolean pair
cannot equate FAIL and INCONCLUSIVE through tuple inheritance. Tests demonstrate the former
equality failure and the corrected behavior.

Retain the flat CLI flags as a supported compatibility interface. They normalize into the same
subcommands; historical runner comparisons and scripts still use them. Removing them would break
working callers without improving measurement. Earlier dispositions remain: no second typed grade
schema beside `RecordV1`, no whole-test-suite mypy migration, preserve live-loop end precedence,
and retain distinct admission versus historical aggregation rules.

Add Ruff's syntax, invalid-control-flow and undefined-name checks to `judge.py`, `clean_room.py`
and the oracles in CI. Keep their existing layouts and incremental typing. A wholesale format/type
migration has no measured behavioral benefit and would invalidate byte-bound calibration or case
identities. This is a disposition of the optional migration, with an executable check added to the
previously uncovered files. The judge and clean-room source bytes are unchanged in this closeout.

## Turn-limit evidence and limits of the evidence

[verified] All 242 scenarios validate: 96 build, 61 contract, one native and 84 routing, with 1,050
graded expectations. New limits use their own historical counts when available, otherwise a matched
kind/lane/tool profile. Start from twice the measured peak or peak plus ten, then apply a ceiling
derived from observed seconds per turn toward a 450-second target inside the 900-second guard.
Preserve the seven previously selected limits. The private per-case inventory records donors,
counts, timings and decisions at `.worktrees/eval-011-closeout/.tmp/eval011-turn-limits.json`.
113 scenarios have their own counts and 129 use matched fallback evidence. Five limits fall below
their observed maximum because of the timing ceiling: burn rules 21 versus 42; incidents API 39
versus 65; incidents page 62 versus 72; dashboard routing 4 versus 5; Python-refactoring routing
3 versus 6. The inventory records respectively 19, 11, one, one and one historical trials above
those new limits. These are deliberate work bounds, not claims that those old trials would pass.

[unverified] Historical throughput across different candidates and models does not prove future
timing or passing behavior. A slow individual tool or helper can still reach the wall-clock guard.
Limits below a historical peak deliberately bound work; unmet requirements fail when the CLI ends
at its declared limit. EVAL-012 comparisons must use the new case identities and observe their
completion behavior; this closeout does not truncate old traces and present them as new live runs.

## Verification

[verified] The model-free saved-run gate compared 91 campaign folders and 1,425 runs against the
base runner: zero errors, zero changed run verdicts, zero changed check states and no missing runs.
All 10,313 saved JSON, JSONL and Markdown evidence files retain their SHA-256 hashes. Private
records: `.tmp/eval011-baseline-v2`, `.tmp/eval011-candidate-v2/comparison.json` and their input
manifests. Rescoring retains workspace-dependent historical verdicts; it cannot prove newly
supervised oracle execution, which is exercised by the controls below.

[verified] Oracle regression: 69 focused controls passed, including malformed candidate iterators
and filter responses that initially produced seven failed tests. Actual fixture-pinned Vitest
execution passed all seven reference bars; hidden-loading, render crash, early exit, missing source
and invalid source mutants return 10; an injected oracle crash returns 1. Private artifacts:
`.tmp/eval011-ui-protocol/protocol-results.json`, `protocol-error-results.json`, and
`protocol-malformed-results.json`. Fresh JSON plus JUnit reports also distinguish identical-message
candidate and oracle collection exceptions, missing candidate setup modules, and premature exits.
All 12 dual-report controls and both exit-origin controls pass; missing or ambiguous origins stay
INCONCLUSIVE. Evidence: `protocol-dual-report-controls.json` and `protocol-exit-origin-controls.json`
in the same private folder.

[verified] Rubric calibration: 187/187 cases agree, including all six new controls and all 27
incident-rubric cases. This used 27 new calls and 160 validated cache hits, USD 0.792295. Three
additional judgments of unchanged WP-02 replies cost USD 0.110681: runs 1 and 2 change from FAIL to
PASS; run 3 changes from PASS to FAIL because it relabels the supplied success time as a start time
and asserts an unsupported arrival. Independent manual review supports that failure. Total:
30 calls, USD 0.902976, no unknown costs. Original replies, grades and timing files remain unchanged.
Receipt: `.eval-runs/judge-calibration/20261010T105741Z/identity.json`; separate judgments:
`.eval-runs/wp02-native-readiness-eval011-rubric-rejudgments-20261010T110051Z`.

[verified] All ten old temporary files under `F:/eval-tmp/wp02` were moved, with matching hashes,
to `.eval-runs/wp02-native-readiness-20261008/residue-archive-20261010`. Its private manifest preserves
source paths, sizes and hashes; the original temporary directory is empty.

Final suite, structural gate and committed review verdict are recorded here after the frozen
integration checks finish.

## Code growth and retention

[verified] Against the base, the 19 runner files grow from 7,479 to 7,792 lines (+313, 4.19%),
341,120 to 355,848 LF-normalized bytes (+14,728, 4.32%), 3,728 to 3,903 docstring-free AST statements
(+175, 4.69%), and 49,373 to 51,271 code tokens (+1,898, 3.84%). Oracle/helper Python grows by
16,845 bytes across 22 to 24 files; seven new test files add 52,986 bytes and existing tests add
8,011 net bytes. The private measurement is `.tmp/eval011-closeout-metrics.json`.

The growth pays for observed OS identity, complete invocation/cleanup evidence, aligned file
inventory, drained audit streams and supervised completion. Each mechanism has a reproduced
measurement failure or missing evidence path above; none expands the actor model. The scope avoids
a wholesale type/format migration and keeps one helper for trial temporary ownership and one
supervisor for Python oracles. This is the current DEC-20 growth disposition under the owner's
delegation. The superseded October 6 code-growth and October 7 refactoring reports are retired;
their historical measurements and repairs remain in Git, and their still-relevant compatibility
decisions are preserved here.

## Scope after this closeout

The trusted-host boundary is unchanged. The supervisor prevents ordinary candidate exits from
masquerading as completed assessment; it is not a hostile-code sandbox. POSIX elevation records
effective UID, not every capability or possible privilege path. No new fleet-agent behavioral
campaign ran, no candidate was promoted, and EVAL-012 still owns its planned comparisons and
separate live readiness evidence. Unknown legacy execution identity stays unknown.
