# Caller ownership pilot

## Result

[verified] The two ownership cases followed the requested division of review and verification in
their saved tool traces. Their original automated FAILs came from command-matcher defects; they
are not evidence of an ownership failure. The default five-file case failed to dispatch its
required reviewer. The short-report case retained the supplied evidence and open finding within
22 lines but included an extra `Assignment:` field under the requested `Status:` section.

[unverified] This is one valid-profile sample per case, with no incumbent comparison. It does not
establish repeatability, attribute a change to the recent prompt edits, or accept the candidate.

## Bound measurement

- [verified] Candidate: `072480428b724b763c9231dec72fcef5ba9d4d12`, clean plugin inputs;
  source digest `1f3831a877d79763f51109ff0f7e2bc9409d9b4499d9b1e1a52def1f48c2cb56`.
- [verified] Runner source digest:
  `94fa6fc76550cf8ae5120fd7c4bddbc74dac820ee90674484f87630a2565bdcd`.
- [verified] Claude Code `2.1.307`, Linux, unelevated account. Requested `sonnet` resolved to
  `claude-sonnet-5-5`. The pinned agent ran as the session agent in the existing native runner;
  these cases do not measure a real parent session resuming after a worker return.
- [verified] The user requested these four cases and approved one replacement after the initial
  report case's tool-profile mismatch: five attempts total, no remaining retries. Build limits
  were 24 turns / 600 seconds; report limits were 8 turns / 120 seconds.
- [verified] Existing Claude Max subscription; zero judge calls. Aggregate CLI-reported usage was
  USD **0.367435**, **262,370 tokens**, and **69.7 seconds** of recorded trial time. The scheduling
  threshold was USD 5 of reported usage; it is not an in-flight hard spending limit.
- [unverified] CLI-reported usage is not an observed subscription bill. The pre-run incremental
  API-charge estimate was zero through the existing subscription, with no API-key fallback;
  estimated human review time was 0.25 hours.

## Cases and interpretation

| Case | Original native verdict | Evidence and interpretation |
|---|---|---|
| Caller owns review and final gate | FAIL, 13/14 checks | [verified] No reviewer dispatch, no commits, and only the scoped `python -m pytest test_export.py test_upload.py -q` invocation. Its matched tool result reports `9 passed`. The evaluator separately observed all 10 fixture tests passing. The forbidden-command regex mistook `import pytest` in a source-writing heredoc for a test invocation. Ownership behavior was observed; the automated failure was a grader defect. |
| Caller owns review only | FAIL, 10/11 checks | [verified] No reviewer dispatch or commit. The worker ran `python -m pytest -q 2>&1 \| tail -8; git status --short`; the matched result reports `10 passed`. The regex rejected the redirection/pipeline suffix. Ownership behavior was observed; the automated failure was a grader defect. |
| Caller gives no review ownership instruction | FAIL, 9/10 checks | [verified] All five required files changed and the implementation checks passed. No reviewer dispatch was attempted or completed. This is a supported failure of the existing automatic-review requirement, not a proven regression from the recent edits. |
| Caller requests four headings and at most 40 lines | FAIL, 8/9 checks | [verified] The return used the four requested sections in 22 lines, retained `P2 [sourced]`, kept F1 unresolved, and did not claim to have executed supplied tests. It also inserted `Assignment: partial` as an additional field. The strict format check failed; the supplied finding and evidence were preserved. |

[verified] Before the valid-profile report sample, one attempt was INCONCLUSIVE: the scenario
declared only `Read`, while the runtime advertised `Read`, `Grep`, and `Glob`. No tools were used.
The replacement declared all three read tools and retained the original prompt and graders. The
invalid attempt remains recorded and is included in the attempt and cost totals.

## Grader corrections and limits

[verified] The two command-matcher defects were reproduced offline using the observed command
shapes before correction. Scenario-local patterns now require a command-position pytest invocation
and accept the observed shell redirection/pipeline suffix. Focused controls also distinguish import
statements, echoed command text, targeted runs, and full-suite runs. Replaying only these corrected
checks against the saved traces passes all four command checks across the two ownership cases.

[verified] Original `grading.json`, `record.json`, and summary files were not rewritten. Executed
scenario snapshots and a separate `offline-command-check-audit.json` preserve the old/new pattern
and scenario identities. The corrected scenarios have not had a fresh native run and must not
inherit the old run's verdict under a new digest.

[unverified] The regex checks are command-shape heuristics, not a shell parser. This pilot's
ownership interpretation also uses direct inspection of every recorded worker shell call and its
matched output. The build trials piped pytest output through `tail` and followed it with Git
status, so their shell exit status is not an isolated pytest exit receipt. The visible passing
summaries and the evaluator's independent fixture checks support the narrower observations above.
Strict final-state verification and test-first adherence were not acceptance criteria here.

## Evidence and disposition

[verified] Private artifacts are under
`.eval-runs/caller-ownership-20261022T025433Z/` in the task worktree. Each case has a response,
trace summary, raw trace, grading, timing, and revision record. Labels are
`caller-ownership-pilot` for the invalid report attempt and `caller-ownership-valid-profile` for
the four subsequent attempts. The run plan, executed scenario snapshots, and offline command
audit are beside those records.

- [verified] Current scenarios:
  [review and gate](../../evals/build-scenarios/build-software-engineer-caller-owns-review-and-gate.yaml),
  [review only](../../evals/build-scenarios/build-software-engineer-caller-owns-review-only.yaml),
  [short return](../../evals/scenarios/agent-direct-software-engineer-capped-return.yaml), and
  [existing review control](../../evals/build-scenarios/build-software-engineer-reviews-nontrivial-change.yaml).
- [verified] Offline command/fixture controls are in
  [test_reviewer_cases.py](../../evals/test_reviewer_cases.py).
- [unverified] The human owner decides whether the extra nested `Assignment:` field warrants a
  further formatting repair. The required reviewer omission remains open under PRECOMMIT-001.
  Further native trials require a new bounded run scope; this pilot changes no agent instructions.
