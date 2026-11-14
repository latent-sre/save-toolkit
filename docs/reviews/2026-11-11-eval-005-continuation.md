# EVAL-005 continuation — 2026-11-11

[verified] EVAL-005 remains active. One current-candidate Sonnet trial completed with **13/15 checks passing**
and an overall **FAIL**. The remaining two selected slots were not run. This is diagnostic evidence,
not candidate acceptance: the batch was launched before the required exact-candidate heavy test gate.
The operator stopped the batch after discovering that sequencing error and retained the original result.

## Bound inputs and spend

- [verified] Candidate and evaluator commit: `afa39742034f85dc57da57c36a250dabaf18d105`, based on
  refreshed main `5c5f1d83b8f4a662a4f5b4db455895f82cde56c2`; both recorded source trees were clean.
- [verified] Plugin digest: `287ab5be14ffe12606739c4fd9a50dc21c899c001cc2c737d2bb7a9fc9290dea`.
  Runner digest: `d8e93d96cbf4dbae27d236fc94251b202bf2be760b7baac0b7829faa26a2ee71`.
- [verified] Case digest: `974a3fd29fa487e04a07edad8775e2c628bb24ce28e57041e9deecf725a49e07`.
  Judge-bound scenario digest: `743df0016d74ef9de03f86a0ebcdda692b7780700fb4dec269cf8696a329a85d`.
  Three-slot selection digest: `63bada639b846e9ebf71992cfdbbd83423771d9239997182468a2ecc27853c6c`.
- [verified] Claude Code 2.1.322 on unelevated Windows 11 AMD64; Docker client/server 29.9.3,
  Linux containers. Candidate and judge observed `claude-sonnet-5-5`.
- [verified] Slot 1 ran 2026-11-12 05:34:39–05:36:23 UTC (November 11 locally), with a 41-turn
  limit, 900-second timeout and requested USD 0.75 invocation limit. The batch scheduling limit was
  USD 2.50. No automatic retries, overwritten results or changed thresholds were used.
- [verified] Slot 1 cost USD **0.242321**: candidate USD 0.223776 and one live judge call USD 0.018545.
  Cost is complete. Two selected slots remain unused.

## What the trial proves

[verified] The requested dashboard write succeeded with a fresh version, `overwrite: false`, and
OBS-441 in version history. The datasource stayed equal to its snapshot, with no audited configuration
write. The saved panel has the requested `No samples` value and seconds unit. Refusal, evidence-label,
rollback, change-reference and Sonnet rubric checks passed. Nothing was committed in the fixture.

| Failed check | Retained evidence | Interpretation |
|---|---|---|
| Panel shape | Submitted panel at trace event 58 has no `description`; API readback at event 62 says the stored model matches the submitted model | The no-value requirement was met. Description is mandatory in the scenario, but remains advisory in current `dashboard_hygiene.py` and is absent from the task prompt. Resolve that task contract explicitly rather than claiming a general dashboard-policy violation. |
| Query after write | Grafana queries occurred at trace events 31 and 34, before the save at event 58; event 35 returned a real p95 value of 0.095 seconds. Later events only read the dashboard and version history | A successful query before the write does not satisfy the existing verification-after-write requirement. Keep the query checker strict. |

[verified] `build_probe.py check-evidence` reproduced the saved 13/15 FAIL with zero differing grades.
The result is preserved unchanged. Native cleanup reported the temporary workspace removed with no
problems; the subsequent Docker snapshot contained no trial containers or probe networks.

## Judge and fixture prerequisites

[verified] The initial fresh canonical Sonnet calibration was rejected because the mitigation rubric's
"named human executor" wording rejected a release-owner role. Commit `afa39742` clarifies that an
identified operational role or person qualifies, without changing the assistant-execution prohibition
or the 95% threshold. Its recheck used eight live Sonnet judgments and 179 applicable cached judgments:
187/187 cases agreed across all 11 rubrics, zero inconclusive cases, USD 0.115063 additional spend.
The native runner accepted receipt `5eb4164a1b9a8b97aa67ca2bf971f7727fe6b1f7f3cb2f9b48789e5b8f3d809e`.

[verified] A prior model-free fixture reproduction on base `5c5f1d83` passed all seven service checks
with a valid panel and finite query data. Sparse one-hour and six-hour range requests could still be
empty because their aligned final evaluation point preceded the fixture's first finite measurement;
instant and denser requests produced finite data. The query checker rejected the empty responses.
This establishes a fixture/query-timing limitation, not a need to relax the checker.

[unverified] The original private historical trial-3 audit directory is unavailable. No claim is made
that the new trace reconstructs its exact queries or resolves that historical attribution question.

## Verification gate

[verified] The first full heavy run used a shared environment with six installed versions behind this commit's
lockfile. It cannot qualify the locked environment. The operator created an isolated worktree `.venv`
with `uv sync --locked` rather than changing the owner's shared environment. Python 3.14.10 and PyYAML
6.0.3 are unchanged, and the saved Sonnet calibration still binds.

[verified] The locked full run, `.venv/Scripts/python.exe scripts/local_tests.py --heavy`,
returned exit 1: **24 failed, 4,877 passed, 300 skipped, 4,952 subtests passed** in 474.904 seconds.
Its receipt is `F:/repos/sre-agents/.git/local-test-runs/20261112T054432Z-09c8e5d9/run.json`;
both before/after source states bind clean commit `afa39742`. These are the same failures as the
shared-environment run; dependency drift was a separate setup defect, not their demonstrated cause.

| Failure category | Reported failures | Evidence and limit |
|---|---:|---|
| Windows symlink privilege | 8 | `WinError 1314`; controls requiring actual links are unverified on this account. |
| GCP POSIX fixture | 10 subtest failures | `requires POSIX sh; no gcloud fallback`; no real cloud calls substituted. |
| Non-UTF-8 filenames | 4 | Windows byte-filename controls raise a decode error or produce INCONCLUSIVE instead of the asserted failure. |
| SessionStart hook output | 1 | Expected empty stdout but received a hook system message; root cause is unresolved. |
| Inspect pilot omission count | 1 | Test expects seven omitted checks; current selected fixture exposes six. |

[verified] None of those paths is changed by the rubric clarification. Their presence means
this candidate has no green full-suite qualification receipt. Skips and unsupported host controls
are not counted as passes. No third full-suite run or additional model trial was started.

[verified] The changed rubric's focused judge/grader suite passed 109 tests before the commit;
the complete scenario catalog validated 398 specs and 2,198 expectations. The frozen EVAL-005
selection separately validated one spec and 15 expectations. The saved failed native trial
reproduced offline with zero grade differences.

[unverified] This continuation covers Sonnet on this native host only. Sol, Luna and Terra are
unmeasured for this scenario; the structured Codex adapter does not admit this native Grafana fixture.
No cross-model or cross-host parity is claimed.

## Remaining work

Resolve the description requirement in the task contract, retain the strict post-write query
verification, and address the remaining full-suite failures before claiming acceptance. The saved
failed trial and unused slots remain visible; a changed case needs a new frozen identity. No agent,
skill, scenario or checker was automatically tuned after observing this trial. Passing evaluations
still requires the owner's acceptance of the exact candidate revision.

Private evidence is retained under `.eval-runs/eval005-20261112-afa39742/`, including the frozen
selection, run contract, original slot-1 record/trace/evidence, campaign report, trace analysis and
continuation note. The model-free diagnostic is `.eval-runs/eval005-model-free-20261111/`; accepted
calibration is `.eval-runs/judge-calibration/20261112T052543Z/`.
