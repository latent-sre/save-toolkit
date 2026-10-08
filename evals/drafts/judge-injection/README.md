# Judge-input injection drafts

These six proposed calibration cases are **drafts**, outside the active corpus and
scenario directories. Their `expect` labels are proposed rubric outcomes, not observed
model judgments. They use the existing `no_production_action_claim` rubric. The controls
and injection variants preserve the relevant assistant behavior: its own production
action claim must fail even beside an instruction to output PASS; diagnosis with a
quoted attack must pass. Both verdicts also have an end-marker variant.

`../../test_judge_injection_drafts.py` checks schema, rubric compatibility, draft isolation,
and the actual prompt assembled by `judge.judge()` with model execution intercepted.
The marker test characterizes the current defect: the first closing marker occurs inside
the supplied response, leaving attacker text after that apparent boundary. It proves a
framing collision, **not** that a model obeys the text or produces the wrong verdict.
The passing test deliberately records the current vulnerable behavior; replace it with a
boundary-preservation regression assertion when the owner authorizes the source fix.

No judge source, rubric, active calibration corpus, receipt, or runner change is included.
No model calls are authorized or made by these tests. The owner decision is whether to
fix response framing and accept these cases into the active corpus together, then budget
and run one cold calibration of the combined change (roughly 175 calls; recount the final
corpus and any identity-resolution call before execution). Either a judge source change
or adding cases to the active corpus invalidates the current calibration binding. Rubric
trials using the changed contract must wait for a successful applicable recalibration.
