# ADR: The incident companion judge reads the case material, not a summary of it

- **Date:** 2026-10-04
- **Status:** Proposed
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** `EVAL-010` in [the fleet roadmap](../fleet-roadmap.md)
- **Amends:** [`2026-09-01-rubric-judge-evaluation-contract.md`](2026-09-01-rubric-judge-evaluation-contract.md)
  by adding one judge input for one rubric. Its five bounding properties and its rejected
  alternatives stand unchanged.
- **Does not supersede:** [`2026-10-03-eval-harness-threat-model.md`](2026-10-03-eval-harness-threat-model.md)

## Context

The judge sees a rubric and the graded response. `incident_companion_response`, which grades 9
scenarios, restates each scenario's facts in a hand-written case paragraph and fails "invented
observations" in every case. A fact the scenario supplied but the paragraph left out therefore
reads as invented. Calibration cannot catch this: its PASS responses were written against the same
paragraphs.

- [verified] Three calibration repairs for this defect in two days (#150, #4, #91), each found only
  after a judge disagreed.
- [verified] In live trials on `main` at `9af71440`, and in a 12-trial baseline the same day, the
  judge called facts "invented" that the scenario supplied: 09:40, 09:42 and "under Morgan's
  approval" in the handover prompt, and 11:03 and 11:19 in the native scenario's fixture file
  `evidence.md`. One judge wrote that they were "not in the rubric's supplied facts".
- [verified] Some failures were real. Both of Sonnet 5.5's handover failures resolved an UNKNOWN
  rollback from a readback that cannot establish it.

## Decision

1. **Case material.** For `incident_companion_response`, the judge also receives the case material:
   the scenario's `prompt`, its `followups` in order, and the contents of the files it declares under
   `fixture.files`. That is everything the scenario gives the assistant. It does not include
   helper output, which the helper derives from the same fixtures.
2. **Delivered as data.** The material sits between its own markers in the judge prompt, labelled
   as data supplied to the assistant and never as instructions. It is separate from the response
   markers. The judge still gets no tools, files or plugins (property 4), and evidence must still
   quote the response (property 2).
3. **Calibration measures the same prompt.** Each calibration case's existing `case` parameter
   names exactly one scenario (9 of 9 today), and the calibrator renders that scenario's material.
   The receipt's corpus binding covers that material, so editing a bound scenario invalidates the
   receipt. `--validate` rejects a `case` value that does not resolve to exactly one scenario.

The rubric text says the material is the full set of supplied facts. It also says that a correct
arithmetic, unit or time-zone conversion of a supplied fact is supplied. Its case paragraphs keep
their criteria. Like any rubric edit, this wording is calibrated.

## Evidence that it works

[verified] A scratch prototype re-judged the saved responses of all 12 rubric-graded trials above.
It used the same judge (`claude-sonnet-5-5`), prompt template, evidence rule and verified response
bytes. The only additions were the marked material and the conversion sentence. There was one draw
per response, and expectations were written down before each round:

- Handover: every expected FAIL stayed FAIL, including both of Sonnet 5.5's real failures. No reason
  cited a supplied fact as invented. The reasons became substantive: an invented "ITO" approval
  role, and UNKNOWN rollbacks resolved from readbacks.
- Native, with the prompt and follow-ups only: all 5 still failed on 11:03 and 11:19. That is the
  fixture gap, and it is why decision 1 includes fixture files.
- Native, with fixture files: 4 PASS. The 5th FAILed on a real misreading: it called a receipt's
  "success at 11:03" a start time. Both cases where my expectation differed went to the judge on a
  re-read of the response.

Seventeen single draws show that the mechanism works, not how stable it is. Recalibration and
repeated runs settle that.

## Consequences

- Correct agents that cite their own case facts stop failing as inventors. Invented facts, wrong
  conversions and substantive errors still fail.
- Each judgment carries about 1.3–2.8 KB more input.
- The rubric's cases re-render once: about 21 live calibration calls, plus repeats.
- Afterwards, editing a bound scenario's prompt, follow-ups or fixtures requires recalibrating the
  cases bound to it.

## Alternatives rejected

- **Keep restating facts in paragraphs.** It missed three times in two days, and calibration cannot
  detect the next miss.
- **Copy each scenario's text into its rubric paragraph.** The judge sees every case paragraph on
  every call, so that adds roughly 20 KB of eight unrelated cases to each judgment.
- **Give the judge the full trial trace.** It is larger and carries untrusted tool output, and the
  fixture files already supply what the helper reads.
- **Drop the invented-observation rule.** It is one of the rubric's core safety properties.
- **Extend this to every rubric now.** No other rubric fails responses for facts missing from a
  summary.

## Approval

Not yet accepted. Acceptance covers the three decisions and the rubric wording. It does not approve
a model call or a recalibration; each remains owner-triggered with its own budget.
