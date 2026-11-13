# Evidence isolation diagnostics v1

[sourced] Three small, synthetic development arms separate exact extraction from interpreting evidence.
They are proposed diagnostics, not ITBench results or held-out qualification. No model has run them;
human adjudication of the control answers and empirical reviewer calibration remain unmeasured.

| Arm | Input | Measurement |
|---|---|---|
| retrieval | `records.json` in the candidate fixture | Exact values, identity and JSON types; no causal task |
| interpretation-direct | The same fixture plus its exact bytes in the prompt | Source-grounded explanation under manual review |
| interpretation-files | The same fixture, explanation question, tools and turn limit | The same manual review after file retrieval |

[sourced] The two interpretation arms differ only by case identity and direct evidence availability.
They deliberately include a current endpoint mismatch, an explicitly earlier user failure, and an
exit observation whose mechanism is unknown. A blanket unknown answer loses supported facts; a
confident complete causal story exceeds them. The retrieval arm asks a different question and its
exact-match score must never be pooled with interpretation scores.

[sourced] `records.json` is the sole fact set. Each scenario copies its exact bytes into the fixture.
`review.json`, the manifest, selection and run plan are evaluator-only and are not staged in the
fixture or prompt. The [review-v2 contract](../../incident-conversations/review-v2/README.md) governs
claim materiality; its controls are proposals until independently adjudicated. Existing original,
diagnostic-v2 and reserved qualification cases are unchanged.

[sourced] `manifest.json` binds scenario bytes, case fingerprints and evaluator material.
`report-selection.json` describes one slot per arm for inventory/accounting; it grants no run
permission. `run-plan.json` has zero approved trials/spend and unset candidate/model/host. The
16-turn scenario ceiling is a proposed guard, not measured feasibility or authority to spend.

Before future live use, freeze the candidate and condition, adjudicate the controls, and predeclare
repetitions and spend. Compare the two interpretation arms with matched conditions. Report
retrieval accuracy, interpretation material errors, completion, turns and cost separately. Retain
all attempts. A difference in a single pair is not proof that retrieval caused the failure.
No upstream benchmark score, stability estimate or candidate promotion follows from this pack.

[verified] Local tests cover source equality, the one-factor interpretation comparison, grader
positive/negative controls, identity binding and answer separation. They do not measure a model's
reasoning or a reviewer's accuracy. Use `python -m pytest evals/test_evidence_isolation.py` for those
contracts and `python evals/build_probe.py validate` for scenario validation; neither makes API calls.
