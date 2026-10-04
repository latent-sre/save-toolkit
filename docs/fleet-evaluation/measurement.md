# Measurement and verification

The evaluation must measure useful behavior without confusing a broken instrument, a good-looking
answer and a successful task. Requirements are in [product](product.md); result semantics are in
[contracts](contracts.md). All acceptance cases below are planned checks, not completed results.

## Assessment dimensions

| Dimension | Evidence | Limit |
|---|---|---|
| Diagnosis | Identified entity, explanation and supporting observations | Right entity alone can be a guess |
| Next-check usefulness | Feasible check that separates still-plausible candidates | Several different checks may be valid |
| Adaptation | Assessment changes appropriately after correction/new evidence | Score only against then-visible information |
| Operational judgment | Supported advice, ownership, uncertainty and recovery criteria | Proposed action is not executed action |
| Human usefulness | Understandable, bounded guidance and retained unresolved work | Requires human calibration; verbosity is not completeness |
| Native behavior | Actual tool results, skill/agent invocation, hooks and sessions | Structural continuity does not establish good synthesis |
| Code correctness | Independent repair and regression tests | Passing finite tests is bounded evidence |
| Test quality | Bug-revealing failure followed by success on repaired code | Unrelated failure is not reproduction |
| Efficiency | Observed calls, duration, useful steps and cost | Low cost cannot offset an invalid result |

Do not make one weighted total the release decision. Publish dimensions, blocking findings, coverage
and failed cases. Preserve original benchmark metrics with their own labels and denominators.

## Judge experiment

Keep the currently accepted graders and judge fixed during WP-02's runner experiment. Refresh
EVAL-010's owner disposition before proposing any replacement; this candidate list does not reopen
a settled decision or make judge replacement a prerequisite for useful evaluation.

EVAL-010 remains the owning roadmap item. Extend its candidate set with DeepEval only through the
recorded experiment design, keeping the current judge, Inspect and Pydantic Evals. The existing
calibration agreement requirement is 0.95 per rubric with no inconclusive cases; this proposal does
not lower it. Final adoption additionally needs held-out evidence and a maintenance/cost disposition.

1. Expand the thin mitigation and compromise calibration sets with varied positives, negatives,
   ambiguity, quoted unsafe text and actual unsafe commitments. Validate labels before judging.
2. Partition by incident/bug family so paraphrases and paired variants cannot cross from tuning
   into held-out evaluation. Keep labels and withheld examples out of optimization prompts.
3. Freeze model, visible inputs, rubric, thresholds, package/runtime identity and output validation.
4. Run an equivalent-contract comparison to isolate plumbing changes. Separately compare native
   framework judging methods. Generated G-Eval steps must be frozen, not regenerated per trial.
5. Blind the candidate labels for human disagreement review; retain individual labels and
   adjudication rationale. The evaluated agent's author does not alone certify the labels.
6. Report per-rubric false passes, false failures, inconclusive counts, repeated-judgment stability,
   latency, cost and net maintained code. Stability repetitions must be fresh independent judge
   calls under the [cache contract](contracts.md#fresh-trials-and-caching); verify call receipts and
   separate cached/live populations. Never count a judge timeout as correct prediction of FAIL.
7. Adopt only after exact-version compatibility and output/evidence parity. If no replacement earns
   adoption, retain the existing judge and remove experimental dependency environments as appropriate.

A different API/CLI authentication path is an experimental difference even with the same model name.
Do not attribute a change to the grading algorithm without accounting for transport and host-added
instructions. Lower temperature does not prove determinism. Do not interpret a model score as a
calibrated probability or use agreement between two models as a replacement for human labels.

## Experimental design

Freeze incumbent and candidate content before live comparisons. Use matched case revisions,
conditions and trial counts. Alternate or randomize arm order when time/provider drift could matter.
Use independent clean workspaces or reset labs. Preserve each attempt, including timeouts and refused
tasks, and state exclusions before running. Changes made after viewing held-out results require a
new evaluation split or a clearly disclosed development result.

Three repetitions are a proposed pilot convention for detecting obvious variability, not a reliable
estimate of rare-event safety. Report exact counts and sample size. Larger runs and uncertainty
intervals should follow a specified analysis plan after measured costs and the needed decision are
known. Do not pool model tiers, hosts or platform adaptations.
The explicitly bounded [Coder Eval feasibility pilot](coder-eval.md#experiment-sequence) uses two
repetitions per runner/task; its 24 task trials do not establish statistical superiority. Holding the
fleet fixed across runners measures runner influence. Agent/tool uplift requires a separate matched
incumbent/candidate experiment with the execution and scoring conditions fixed.

Keep safety/authority checks alongside positive usefulness. An agent that refuses every task should
fail ordinary achievable cases. Include correct-code cases to catch unnecessary editing, and healthy
or insufficient-evidence incident cases to catch forced diagnoses.

## Acceptance catalog

| ID | Check | Passing evidence |
|---|---|---|
| AC-01 | Import known native PASS/FAIL/INCONCLUSIVE records | Same case identities, statuses, check counts, evidence and original spend |
| AC-02 | Missing record, duplicate label, partial/corrupt file and failed import | Visible incomplete coverage; no stale replacement or implicit pass |
| AC-03 | Candidate/scenario/model/runner/CLI/host identity checks | Wrong identity rejected for the intended claim; historical omissions remain explicit |
| AC-04 | Native plugin, selected agent/skill and allowed/denied-tool canaries | Actual runtime evidence matches intended profile; no prompt-only assertion of identity |
| AC-05 | Helper completion, parent continuation, resume and SDK transcript settings | Matched native traces, no hidden transcript loss, identity checked each turn |
| AC-06 | ITBench input partition and answer controls | Correct and incorrect controls discriminate; candidate cannot read ground truth |
| AC-07 | Incident pair with changed decisive evidence | Advisor updates the relevant conclusion while preserving unrelated supported facts |
| AC-08 | Missing access, stale data and multiple valid next checks | Feasible alternatives accepted; unavailable evidence stays unknown |
| AC-09 | SREGym healthy baseline, injected fault and diagnosis oracle | Verified fault signature and retained upstream results for the selected stage |
| AC-10 | Failed setup, absent fault, reset failure and cancellation | Instrument/lifecycle failures visible; no next trial on dirty lab state |
| AC-11 | Advisor recommendation versus executed lab action and recovery | Actor and outcome distinct; recovery assessed against agreed user outcomes/window |
| AC-12 | SWE patch against independent repair/regression tests | Required tests discriminate reference/bad patches and candidate artifacts are preserved |
| AC-13 | SWT tests on buggy and repaired revisions | Relevant fail-before/pass-after; useless test controls rejected |
| AC-14 | Selected terminal-task verifier and fleet identity | Task outcome valid and exact plugin/agent evidence retained |
| AC-15 | Human-labelled judge corpus and held-out set | Per-rubric results meet declared criteria with false passes and gaps disclosed |
| AC-16 | Judge quote, malformed output, timeout, missing parameters and skipped metric | Invented evidence or failed judging cannot certify PASS/FAIL for the affected check |
| AC-17 | Cached output, fresh trial, nested repeat, infrastructure retry and judge stability | Correct trial/attempt counts; requested stability repetitions have independent fresh judge receipts; cached verdicts cannot satisfy repetitions or fresh cost/latency measurements |
| AC-18 | Budget limit, unknown price, cancellation and in-flight cost | Stop scheduling, retain known/unknown spend and reconcile active work |
| AC-19 | Evidence paths, relocation, truncation and external data destinations | Original artifacts accessible to reviewer; missing/truncated data visible; opt-outs verified |
| AC-20 | Wider-fleet seeded good/bad cases | Lane-specific outcomes discriminate without adding tools or delegation edges |
| AC-21 | One later AIOpsLab task through the common report | Task/workload/fault identity and upstream results preserved, lifecycle checked |
| AC-22 | Reports and release workflow | No automatic promotion, unrequested writes, altered grants or second live backlog |
| AC-23 | Same saved bundle imported on Windows and Linux, then relocated | Identical logical verdicts/counts/provenance and accessible evidence links, including paths with spaces; missing target evidence is reported on both hosts |
| AC-24 | Task-budget exhaustion/missing submission versus instrument timeout/lost evidence | Healthy-environment nontermination and verified omitted patch fail the task; provider/runner outage or collector loss stays INCONCLUSIVE; later failure does not erase a supported result |
| AC-25 | External coding task admission and execution receipts | Unadmitted path blocks preflight; selected CI actor supplies revision/patch-bound receipts; correct refusal is not penalized and supplied verification is never labelled agent-executed |
| AC-26 | Authored branching investigation with multiple valid checks | Different supported checks reveal only their defined observations, equivalent requests reach the same branch, unsupported requests return unavailable, and scoring uses only then-visible evidence |
| AC-27 | Controlled instructions embedded in repo files, logs, helper returns and judge input | Benign/malicious pairs distinguish following task authority from obeying embedded instructions; traces and calibrated/manual assessment show boundary behavior and useful legitimate task progress |
| AC-28 | GCP catalog and family partitions | All 32 families have two reviewed variants, source/version references and hidden good/bad/unavailable controls; the named 24-case pilot and complete 64-case manifest are distinguishable; related variants never cross tuning/held-out partitions |
| AC-29 | GCP target, access and protected-output controls | Correct target/interface retained; synthetic marker controls prove masking before model-visible tool output, transcripts, helper returns and captures for the admitted response shapes; missing/failed protection blocks direct reads in favor of reviewed sanitized observations. Separately, wrong defaults, unavailable CLI, denied reads and synthetic credential-shaped text produce safe alternatives without invented observations or changed grants |
| AC-30 | GCP migration, diagnosis and effect evidence | Cloud Run and managed-service pairs distinguish their competing causes; timeout does not prove cancellation, serving traffic does not follow revision age, and recovery/retry advice follows supplied effect and ownership evidence |
| AC-31 | GCP logs, metrics, traces and signal routing | Correct query dialect, resource population, UTC window and per-signal backend; known fixture results validate query semantics; missing/sampled/delayed data and absent application spans remain visible limitations |
| AC-32 | GCP alert evaluation and notification chain | Healthy, bad and no-data windows produce the declared policy behavior; incident state, test-sink receipt and user recovery are assessed separately; recorded-profile results do not claim real delivery |
| AC-33 | GKE workloads and identity with explicit mode | All eight GKE pairs receive lane-correct diagnosis/next checks or escalation, preserving project/cluster/namespace/mode; local Kubernetes and unsupported node access never establish GKE capability |
| AC-34 | Eight selected GCP live exercises and failure controls | Verified healthy baseline, intended fault, actual opportunity, independent outcome, actor-bound effects and cleanup for each; absent faults, denied collectors, unknown operations and residual resources remain visible; cloud/model spend and bounds reported separately |
| AC-35 | GCP branching and human handover | Six authored branching investigations satisfy AC-26; two human tabletops record usable instructions, receiver read-back, retained open items and ability to continue; difficulties remain explicit qualitative findings |
| AC-36 | Coder Eval mapping controls and six-task runner feasibility comparison | Same good/bad/unavailable controls preserve applicable verdicts, denominators, evidence and spend; host canaries precede matched trials; actual identity, attempts and gaps remain visible; no runner result is labelled agent uplift |
| AC-37 | Maintainer disposition, case authoring and adoption inventory | Blinded controlled outcomes receive correct dispositions with decisive evidence located; second-maintainer authoring/retrieval effort is recorded; DEC-16 names retained/replaced/added responsibilities and accepts, limits or rejects adoption against predeclared benefit criteria |

## Verification sequence

First use model-free fixtures to validate mapping, lifecycle and verifiers. A reference solution and
a known wrong result should produce the expected task outcomes. A failed environment must produce
an instrument failure rather than a task success/failure. These controls establish the instrument,
not model capability.

Then run a small explicitly selected live compatibility set before a benchmark campaign. A native
integration passes only when identity, tools, hooks and transcript evidence are checked; a generic
Claude Code run with good artifacts does not suffice. Retain human trace review wherever semantics
are not covered by a calibrated grader.
WP-02 includes the Coder Eval experiment under AC-36/37. A documented incompatibility or rejection
can complete its assessment when the evidence and disposition are recorded; it cannot satisfy the
separate native integration checks or remove their requirement. Use the accepted native path for
the first useful candidate comparison once native/report readiness passes, including while the
alternative assessment is pending or after it does not earn adoption.

Ordinary PR CI runs offline validation and adapter/fixture tests. Native paid runs remain manual in
the clean room. External coding tasks require DEC-13 and AC-25 as well as the reviewed isolation
profile; containers alone do not admit execution. A separately authorized CI job may execute external
repository commands without moving the evaluated model session into CI. Model-in-CI or direct lab
execution by a changed agent policy needs its own decision. No production credentials enter these tasks.

WP-01 completes only after AC-23 runs on both operating systems. Compare logical content rather than
host-specific timestamps or rendered path strings; test opening relocated source links on each host.
This report/import acceptance does not establish Windows compatibility of Linux benchmark labs.

GCP acceptance is staged. WP-12's model-free controls establish fixture/scorer discrimination and
case completeness, not candidate capability. WP-13 assesses the actual native candidate using
supplied or recorded observations; a documented human review can assess semantics before a judge
is selected. Report the 24-case pilot separately from the full 64-case catalog, and include the
six branching investigations and two tabletops before declaring WP-13 complete.

WP-14 establishes live behavior only for its eight named exercises and selected cloud profiles.
Query checks against recorded API responses do not prove a query executes against Google Cloud;
a reference gcpdiag result is corroboration, not an independent end-to-end recovery oracle. Validate
notification delivery at the isolated sink and preserve ingestion delay, sampling and observation
windows. Apply existing PASS/FAIL/INCONCLUSIVE and AC-24 rules without creating a separate GCP score
that hides authority, tooling or measurement failures.

## Definition of a reviewable result

Provide the run plan, immutable case/candidate identities, raw evidence references, upstream scores,
per-dimension fleet results, calibration identity, counts, spend, unresolved limitations and a concise
recommendation. State which tests actually ran, the revision tested and any skipped or unavailable
checks. A recommendation can be accept, revise, retain incumbent or insufficient evidence. Only the
human owner accepts the exact candidate.
