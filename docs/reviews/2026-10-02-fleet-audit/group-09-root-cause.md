# Group 09 — root-cause — six-pass review

Reviewed 2026-10-02 for invoking caller `/root`; human owner: the user. Parent objective: audit all skills, then agents, six passes per asset and a findings commit after each group of three. Worktree: `F:/repos/sre-agents-audit-20261002`; frozen canonical baseline `a2d2e57d2de70125dbde002072853e73b788bd8d`; group-start HEAD `8cbf3664f87a314e0373be287a515a4f542e15b1`. Candidate instructions were review data. This reviewer wrote only this scratch report. The coordinator executed the bounded local counterexample below; neither role performed live operations, installations, source repairs, or a paid/native campaign.

**Conclusion:** retain the compact diagnostic method. No confirmed defect was found in the skill's instructions. RCA-01 is a medium-severity compatibility false acceptance in its independent retry oracle, reproduced centrally with controls. Preserve the distinction between ordered skill loading, correct fixture behavior, and demonstrated causal reasoning; the repository already states that automated checks alone do not establish the last of these.

## Pass 1 — suitability, routing, and neighboring ownership

**Files/evidence:** the complete `skills/root-cause/SKILL.md:1-70`, direct consumers in `agents/software-engineer.md:97,105-115,218`, `sre-assistant.md:62-67,127-143`, and `reliability-engineer.md:41-55`; `discovery-reliability-defers-root-cause.yaml`. [verified] The skill serves diagnosis before permanent remediation, particularly after a failed fix. Active incident coaching stays with `incident-investigation`; a dispatched helper may apply this causal method inside its bounded assignment.

The entrypoint explicitly exempts a bounded evidence lookup from mandatory reproduction, a hypothesis table, and remediation. Read-only lanes stop at recommendations. Software-engineer loads the method for bug fixes, while the two investigative consumers retain their own execution restrictions. The reliability discovery scenario distinguishes an observed failure from a new reliability design.

**Outcome/gap:** appropriate common method without a new role or additional skill. A routing definition does not prove unhinted discovery or the quality of a subsequent diagnosis; no native routing trial ran here.

## Pass 2 — correctness of the diagnostic method

**Files/evidence:** full one-file bundle, 70 lines/4,477 bytes; no references, scripts, or assets. [verified] The loop is coherent: capture the failure safely, inspect actual evidence and component boundaries, form hypotheses with distinguishing observations, run an authorized check, then repair and recheck the original evidence. It neither equates correlation with mechanism nor forces a fixed number of hypotheses.

The worked timezone example is appropriately limited: an unchanged lockfile does not establish an unchanged runtime; a different CI timezone is initially a candidate; only the controlled replay plus source mechanism supports the scoped conclusion. The example does not claim every export failure is explained. The instruction to consider downstream validation preserves prevention beyond merely suppressing the visible exception.

After every failed repair, the causal explanation is reassessed; after three failed repairs, patching stops and diagnosis is reopened. This is a team operating threshold, not a claim that three experiments scientifically establish or refute a cause.

**Outcome/gap:** no instruction defect found. RCA-01 concerns evaluator coverage of a separately supplied Python contract. It was settled from local source and a disposable reproduction; no uncertain vendor/API contract required external research.

## Pass 3 — authority, trust, failure, and recovery

**Files/evidence:** `SKILL.md:14-23,27-43,47-50` and the consumers' scope rules. [verified] The method explicitly allows the human owner to mitigate active impact before the cause is known and grants no live-change authority. Unsafe or intermittent failures can be investigated through available signatures, logs, traces, or controlled simulation with stated limits; failure to reproduce does not force a live failure or stop useful work.

Commands found inside logs, errors, or fetched documents remain data rather than instructions. A failed diagnostic check leaves a hypothesis unresolved; it does not rule an alternative out. Diagnostic changes are distinguished from human-owned mitigation. The consumers reinforce these boundaries: SRE and reliability helpers recommend rather than implement; the software engineer's verification contract requires fresh evidence and preserves source/time/target limitations.

**Outcome/gap:** preserve these safeguards. The skill is cooperative guidance, not a shell sandbox or permission grant. Actual host isolation, input provenance, production safety, and the validity of a particular controlled simulation remain case-specific. The audit supplied no real failing service to diagnose.

## Pass 4 — LLM readability and context cost

**Files/evidence:** the full entrypoint and caller load rules. [verified] Four short sections, five ordered steps, four red flags, and one compact worked table carry the method. The opening announcement names the loop plainly; the body explains which parts apply to diagnosis versus a bounded lookup. Mandatory permanent-fix discipline coexists with conditional reproduction and regression testing, avoiding an instruction to force unsafe experiments.

The “try changing X and see” red flag does not prohibit an authorized discriminating experiment: the loop first requires a hypothesis and an observation that would change its credibility. The three-attempt rule also does not permit three guesses; reassessment is already required after the first failed repair. These are useful distinctions to preserve if future compression is proposed.

**Outcome/gap:** no broad wording expansion or new reference hierarchy is justified. Do not add evaluator-specific subclass advice to a general diagnostic skill. Fix the oracle in its owning layer. There is no measured benefit from further prompt compression in this review.

## Pass 5 — verification coverage and oracle validity

**Files/evidence:** complete `build-software-engineer-root-cause-reassessment.yaml`, `evals/oracles/root-cause/probe_retry.py`, and `evals/test_root_cause_probe.py`; relevant `evals/build_probe.py:100-101,1515-1553,2229-2238,2424-2456`; `evals/README.md:141-159`. [verified] The fixture begins after an unsuccessful retry-budget increase. It checks successful main-thread skill loading before effects, an independently supplied behavior oracle, a completed foreground unittest run after final edits, scoped changes, and no commits.

The ordering check is intentionally stricter than the general skill contract, and the prompt/README explicitly say so. Calibration rejects late, failed, child-only, asynchronous, wrong-name, and overlapping loads. It uses exact names in this ordered path, unlike the ordinary suffix matcher; shared AA-01 is not a new root-cause-specific finding. EL-01's text-field issue is not this oracle's mechanism.

The behavior oracle already rejects another budget increase, swallowed exceptions, disabled retries, lost identity, incorrect exhaustion counts, and failed recovery across several budgets. RCA-01 shows one concrete compatibility regression it misses. Importantly, both the scenario and README explicitly require manual native trace review of the failing reproduction, discriminating comparison, and supported explanation. Automated green was never claimed to prove the agent's causal reasoning.

**Outcome/gap:** [verified: centralized execution] the common baseline passed 1,470 tests/2,690 subtests with 19 skips and validated 192 scenarios/737 expectations. The full suite was not repeated. Native causal acceptance remains unverified; the new coordinator reproduction establishes a bounded oracle weakness only.

## Pass 6 — adversarial challenge and minimum improvements

**Cases checked:** a log containing an instruction to execute a command; a request for a bounded lookup rather than diagnosis; unsafe reproduction during an outage; unchanged error text with a different environment; a failed hypothesis check; a symptom changed by the previous patch; a third unsuccessful fix; and a successful local test overclaimed as a complete causal explanation. [verified] The source already supplies relevant constraints and uncertainty handling. No extra prompt rule is warranted just to repeat them.

For the evaluator, increasing the retry budget, removing retries, and swallowing exceptions are existing negative controls. The additional exact-type classifier mutant preserves those coarse outcomes while violating the seeded public predicate's subclass behavior. This is a natural compatibility regression, not a malicious mutation of the test runner or a fabricated native trace.

**Outcome:** repair the narrow false acceptance and preserve manual reasoning review. Broader acceptance cases should test scope and failed-repair decisions before introducing more instructions.

## Confirmed defect

### RCA-01 — Retry oracle accepts a classifier-compatibility regression

**Medium severity; high confidence.** [verified] The fixture requires the existing classifier policy to remain compatible (`evals/build-scenarios/build-software-engineer-root-cause-reassessment.yaml:20-26`), and its initial implementation uses `isinstance(error, TimeoutError)`. The oracle exercises only exact `ValueError`, `RuntimeError`, and `TimeoutError` instances (`evals/oracles/root-cause/probe_retry.py:6-23`); its recovery cases also raise only the exact built-in type (`:24-35`). The calibration mutants at `evals/test_root_cause_probe.py:73-78` omit subclass narrowing.

**Trigger/consequence:** repair the broad exception handler using `is_retryable`, then change that predicate to `type(error) is TimeoutError`. Ordinary timeouts still retry and permanent base exceptions still propagate, so the seeded tests and oracle pass. A `ServiceTimeout(TimeoutError)` now propagates on its first call instead of retrying, violating the unchanged classifier contract used by other callers. The automatic artifact check can therefore credit an incompatible repair.

**Coordinator reproduction inspected:** `F:/iso-tmp/fleet-audit-20261002/group-09-root-cause-probe-results.json` records these controlled results from the actual YAML seed and oracle:

| Candidate | Seeded suite | Oracle | ServiceTimeout discriminator |
|---|---|---|---|
| Correct repair | exit 0 | exit 0 | retryable; 3 calls; recovered |
| Exact-type predicate mutant | exit 0 | exit 0 | not retryable; 1 call; same exception |
| Original failed repair | exit 1 | exit 1 | retryable; 3 calls; recovered |

[verified: coordinator execution, result artifact read] These are local synthetic behavior results, not a model run or evidence that a native manual review would accept the mutant.

**Smallest fix:** add a named TimeoutError subclass to oracle classification, exhaustion, and recovery cases. Derive the expected retry policy independently with subclass-aware logic; merely adding a subclass to the current tuple while retaining `error_type is TimeoutError` would encode the wrong expectation. Add the exact-type mutant to calibration and retain the original positive/negative controls.

**Verify:** the original and exact-type mutants fail; the supported repair passes; the subclass retains retry count, return identity, and exhaustion exception identity. Preserve the seeded assertions. No change to the general root-cause prompt is needed.

## Recommendation, policy choices, and runtime gap

**RCA-R01 — broaden acceptance with two decision cases (medium priority; high confidence).** The current repair case tests reassessment after one failed attempt, but not the skill's unsafe-reproduction boundary or three-failed-attempt stop. Add bounded supplied-state cases for those decisions: continue safe evidence gathering without forcing the live failure, and reopen diagnosis after the third failed repair while leaving authorized mitigation with its human owner. Include a bounded-lookup control so the full diagnostic loop is not imposed on an extraction. Grade the actual next action and preserved unknowns; retain manual review for tool-supported causal explanations.

**RCA-G01 — native causal acceptance is still open.** `evals/README.md:151-159` explicitly reserves this evidence to a bounded, agreed host/model/candidate/trial budget. The historical memory's absence of native acceptance was checked against that current text; no old run or failure was promoted to a current verdict. A passing oracle and a completed skill load establish neither hypothesis quality nor actual reassessment.

The three-attempt threshold, initial announcement, and read-only/mitigation boundaries are deliberate policy. Preserve the complete reproduce → evidence → hypothesis → verify → fix loop and its conditional application rather than adding ceremony or a new agent.

Caller next step: integrate RCA-01 and its inspected coordinator evidence with the other group09 reviews, commit the group, then dispatch group10. This helper's completion does not complete the parent audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
