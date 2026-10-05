# Group 10: toil-reduction — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting audit HEAD `062d1bfe6748675ee114685307c17c3fdb22abb0` contains preceding reports. Initial tree clean; the bundle matched the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains the six-pass fleet review, skills before agents, three assets per group, with findings committed before proceeding.

**Conclusion:** no confirmed correctness or authority defect was found in this scope. The method makes sound time-economics distinctions, accounts for residual/transferred work, and refuses to treat proposed automation or arithmetic payback as proven operational benefit. Preserve its compact form. Two bounded recommendations would improve decision coverage: expand the existing calibration beyond positive/negative fixed inputs, and consider useful lifetime/adoption timing when a long payback materially affects the choice.

Both bundle files were read completely: `SKILL.md` and `references/worked-examples.md`. Together they contain 7,105 bytes, 118 lines, and approximately 977 whitespace-delimited words; the entrypoint is 643 words. There are no scripts, templates, or executable assets. `[verified]` denotes inspected current source or identified local evidence; `[sourced]` denotes documentary support; `[unverified]` denotes target/model/outcome facts not established. Only this scratch report was written. No implementation, installation, live operation, paid/native evaluation, or repeated full-suite run occurred.

## Pass 1 — suitability, routing, and adjacent responsibilities

**Sources:** complete entrypoint; `agents/reliability-engineer.md:21-55,122-125`; `agents/scribe.md:175`; `skills/runbook/SKILL.md:111-114` and its living-runbooks reference `36-38`; toil/reliability discovery scenarios.

[verified] The skill owns the decision about recurring work, rather than merely selecting an automation technology. It compares elimination, cause correction, simpler defaults/workflows, self-service, automation, and explicit acceptance. Its trigger covers repeated interventions, maintenance economics, and transferred effort. Active incidents remain with incident investigation; implementation remains with software engineering or the application owner.

[verified] The caller requires stack ownership before interpreting a service/design. Scribe routes an unresolved automation decision here, while accepted implementation follows a separate lane. Runbook's repeated-manual-fix trigger creates an assessment candidate; it does not override toil-reduction's requirement to compare alternatives or mandate automation. These contracts are compatible.

[verified] `discovery-toil-reduction.yaml:3-11` tests method selection for a full recurring-work question. `discovery-reliability-toil-assessment.yaml:4-13` selects the specialist for a scoped design judgment; `discovery-reliability-defers-small-toil-arithmetic.yaml:4-12` keeps a simple hours calculation inline. This is a useful boundary against unnecessary orchestration.

**Gap:** specification coverage does not establish native-host selection, complete record discovery, or quality on an unfamiliar operational workflow. This report does not perform the later whole-agent review.

## Pass 2 — correctness, units, assumptions, and primary method

**Sources:** `SKILL.md:18-56,66-81`; complete worked examples; current [Google SRE workbook: Eliminating Toil](https://sre.google/workbook/eliminating-toil/), checked 2026-10-02 after local inspection.

[verified] The arithmetic and dimensions are consistent. Twenty-four interventions per month at fifteen minutes each give 360 minutes, or six human-hours per month. Subtracting two hours of residual work and two of maintenance leaves two hours saved per month; forty hours of one-time effort divided by that rate gives twenty months. The uncertain example's outer bounds are 30/3 = 10 months and 50/1 = 50 months. It correctly cautions that dependence between estimates matters; those bounds are not a probability interval or a promised completion date.

[verified] The negative example includes another team's four maintenance hours plus three residual hours against the six-hour baseline: minus one hour per month. The method does not manufacture a positive payback by taking an absolute value or excluding transferred work. Zero savings is also explicitly covered in the entrypoint: no positive time-saving break-even. Separate safety benefits can justify a different human decision, but require their own evidence.

[sourced] The primary method supports measuring operational burden, preferring lasting fixes where appropriate, examining ongoing automation costs, and retaining safety checks and human fallback. The skill makes those principles concrete without importing Google's organization-specific operational-work cap as fleet policy. The reference's fictional numbers are labeled as examples, not industry thresholds or measured fleet performance.

**Gap:** these are time-only calculations under stated assumptions. They do not establish financial return, causal error reduction, realized staff capacity, deployment safety, or future demand. No executable calculator is present or needed to validate the illustrated arithmetic. API/CLI/library contract research was unnecessary for this method-only bundle.

## Pass 3 — authority, trust, failure, and recovery

**Sources:** `SKILL.md:14-16,20-28,37-42,58-75`; worked examples `25-37`; reliability caller `21-39,78-86,107-125`.

[verified] The skill grants analysis/design authority only. Live actions retain the production gate and applying owner; the caller arranges implementation and operational documentation. Its prohibition on durable operational-record updates is compatible with the caller's separate ability to write an explicitly requested assessment/design document. It does not authorize rewriting an accepted service record through an engineering proposal.

[verified] The workload model explicitly includes interruptions, approvals, rework, residual handling, failures, support, and maintenance across affected teams. Record duplication cannot inflate frequency. The method requires evidence dates and coverage gaps and preserves untrusted taint. Supplied records support bounded historical claims; they do not become current measured outcomes merely because the arithmetic is exact.

[verified] Recurring restarts are treated as evidence of an intervention, not proof of cause or permission to restart automatically. The example names duplicate processing, lost work, and concealed underlying failure as costs to investigate. Proposed automation must address target binding, idempotency, partial/unknown outcomes, retry limits, observability, recovery, and manual fallback where applicable. These directly address residual failure effects and human burden rather than assuming that script execution eliminates them.

**Gap:** no real implementation, fallback staffing, maintenance ownership, operational risk, or independent acceptance was exercised. A complete assessment can still leave those outcomes open; the method says so.

## Pass 4 — LLM readability, ambiguity, and context cost

**Sources:** both bundle files, especially entrypoint `18-28,30-56,58-75` and reference `3,13-15,33-37`.

[verified] The order is easy to follow: establish the recurring mechanism, compare options, calculate with units, design a bounded intervention, and measure the result. The formula block provides a compact reusable model while the reference provides positive, negative, recurring-restart, and unknown-baseline cases. There is no package catalogue, large checklist, universal percentage, or instruction to invent a numeric return for weak data.

[verified] Important qualifiers are placed next to the claim they limit: costs counted once; comparable windows; positive denominator; ranges instead of false precision; estimates distinct from measurements; no unauthorized effects. “Fewer tickets” and “faster script” are explicitly insufficient, preventing proxy measures from replacing total human work or user outcomes.

**Deletion-first conclusion:** no substantial compression is warranted. Keep formulas and interpretation together. If the method grows, add one focused worked example rather than another mandatory reporting template or an overlapping ROI checklist. Preserve the instruction to keep measurement itself proportionate; an elaborate collection process can create more burden than the candidate task.

**Gap:** concise prose and sensible structure are source-level strengths. Their native comprehension and adherence have not been measured on this exact candidate.

## Pass 5 — verification coverage and oracle boundaries

**Sources:** both `agent-direct-reliability-engineer-toil-*.yaml` scenarios; `evals/test_reliability_cases.py:25-35,82-95`; bounded reliability build/caller coverage; `evals/README.md:502-518`; current `docs/fleet-roadmap.md:41-59`.

[verified] Positive and negative direct cases supply distinct monthly events, effort, nonoverlapping future costs, unchanged demand, and explicitly unmeasured implementation. Their expected JSON values correctly require 6/2/20 or 6/-1, estimated benefit, transferred maintenance, and no production approval/action. The calibration tests accept the intended object and reject an empty answer or each changed expected field. These are useful arithmetic/classification controls with independent expected values.

[verified] Their `tools: [Read]` posture and supplied inputs deliberately avoid execution or source-discovery work. They do not demonstrate that the skill loaded, that records were deduplicated, that a representative window was chosen, or that an alternative was implemented successfully. The README expressly describes these as supplied-state judgments and keeps native acceptance open. Adjacent document-scope and redelivery probes cover different responsibilities; they cannot substitute for toil-outcome evidence.

The parent's frozen-source offline baseline remains **1,470 passed, 19 skipped, one warning, 2,690 subtests**, with **192 scenario specifications/737 expectations** validated, both exit 0 under Python 3.14.7. Those results establish structural/calibration evidence. No new executable counterexample was necessary or claimed. Current RELIABILITY-001 still records unresolved native acceptance; historical counts, model trials, and previously approved budgets were not treated as current authorization.

**Gap:** zero net savings, an interval spanning zero, missing baseline, duplicate intervention records, mismatched units/windows, changed demand, and observed post-launch burdens do not have toil-specific executable coverage in the inspected family. That is a recommendation for discriminating evidence, not a claim that the existing bounded oracles violate their advertised contract.

## Pass 6 — adversarial challenge and prioritized recommendations

The review challenged nine cases: one incident mistaken for recurrence; duplicate tickets; a necessary rare drill mislabeled as toil; hidden approvals/support; another team's maintenance omitted; zero/negative net savings; uncertain correlated inputs; restart-as-cure reasoning; and a smaller ticket count despite unchanged total work. The current prose gives an appropriate answer to each. No confirmed defect or compelled policy change resulted.

### TOIL-R01 — extend existing calibration to incomplete and incomparable evidence

**Recommendation; Medium priority; high confidence in the coverage gap, native outcome unverified.** Locations: `SKILL.md:20-23,37-55,66-69`; worked examples `33-37`; the two direct toil scenarios and `test_reliability_cases.py:82-95`.

**Trigger → consequence:** a future assessment receives duplicate records, an unknown baseline, differing monthly/weekly cost windows, a savings interval crossing zero, or fewer interventions caused by reduced demand. Correct answers to the current fully specified positive/negative cases would not establish sound judgment on those inputs; unsupported payback or claimed benefit could escape the current coverage.

**Smallest improvement:** add a few supplied-state cases to the existing calibration, with independent expected units, deduplication treatment, unknown/conditional payback, and explicit measurement status. Include unchanged or worse total work after effort moves to another team. Keep a correct positive case and a zero-savings boundary. If later evaluating end-to-end method use, separately inspect source reads, task/period definitions, skill loading, ownership, and follow-up evidence; do not infer them from a numeric answer or demand a new paid campaign now.

**Verification:** reject fabricated dates/ROI, omitted transferred costs, double-counted records, and favorable claims based only on ticket count. Accept an honest qualitative opportunity with a small measurement plan when data are missing. Preserve the existing no-live-action and estimated-benefit controls.

### TOIL-R02 — consider useful lifetime and adoption timing for consequential payback

**Recommendation; Low priority; high confidence in usefulness, no confirmed contract defect.** Locations: `SKILL.md:40-55`; worked positive/range example `7-15`.

**Trigger → consequence:** a proposal estimates a twenty-month steady-state payback, but its workflow is expected to retire or materially change sooner, or a long rollout delays most of the recurring savings. The existing example correctly states assumptions and does not recommend unconditional investment, but a reader could still compare only monthly rates while overlooking how long those rates can apply.

**Smallest improvement:** when this fact could change the decision, add useful lifetime/adoption timing to the existing assumptions or append one contrasting sentence to the example. Compare cumulative expected effort over the relevant horizon, retain uncertainty, and avoid adding discounted-finance machinery to ordinary operational choices. This is a refinement of option selection, not a reason to reject all long-payback or risk-reduction projects.

**Verification:** a short-lived workflow should not be recommended for time savings merely because its eventual algebraic break-even is positive. A durable workflow with supported adoption assumptions may retain the original result. Any independent safety benefit still requires its own evidence and human tradeoff.

**Caller next step:** record these recommendations and the no-confirmed-defect conclusion within AUDIT-001, assemble and commit group 10 before starting the agents. Keep the existing RELIABILITY-001 native/outcome gate open; this review neither promotes a candidate nor authorizes new evaluation spending.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
