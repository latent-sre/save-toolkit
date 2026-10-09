# PRINCIPAL-001 semantic evaluation proposal

Inactive preparation, not part of the default scenario catalog or canonical judge contract.
No live calibration or semantic model result is claimed. The two held-out structural scenarios
remain in the active build catalog and their measured bytes are unchanged.

This directory retains the four matched response-only scenarios, proposed rubric, and eighteen
proposed calibration labels (sixteen original controls plus two complete-fixture positives).
The rubric embeds a case-keyed JSON bundle containing each scenario's full prompt and every
declared fixture file's contents. Its summaries are not an exhaustive fact whitelist. Notes remain untrusted.
Literal braces are doubled in the YAML template for the judge's formatter; the rendered JSON
must round-trip exactly to the source prompt/files.

`python -m pytest -q evals/test_principal_judgment.py` checks default-catalog exclusion, pair
equality, complete rendered case context, proposed calibration controls and mocked prompt
construction. Proposal validation explicitly supplies these rubrics inside the test; it does not
register them with the normal runner. Offline tests cannot establish a model's semantic accuracy.

## Activation gate

1. Review the complete-context rubric and all proposed labels, including the two positives that
   cite facts missing from the former summary. Keep the fixture-binding tests passing.
2. Obtain a separate owner-approved cold-calibration scope and budget for an activation candidate.
   Combine this proposal with the then-current canonical corpus/rubrics in that isolated candidate;
   do not replace the global contract with this proposal-only subset.
3. Require a completed accepted receipt for the exact combined corpus, rubric and judge identity
   before publishing activation. Only then move the four scenarios into the default build catalog.
   An old, subset or unaccepted receipt is insufficient; do not weaken the runner's receipt gate.

The active rubric/corpus files in this PR remain byte-identical to main, so merely retaining the
proposal does not invalidate an otherwise applicable canonical calibration receipt. The runner
and judge must still independently satisfy their current identity checks.
