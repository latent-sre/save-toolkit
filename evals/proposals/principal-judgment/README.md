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

The original offline controls checked catalog exclusion, pair equality, fixture rendering, and
mocked prompt construction. Those tests are archived in Git history. The proposed rubrics are
outside the normal runner.

## Activation gate

1. Review the complete-context rubric and all proposed labels, including the two positives that
   cite facts missing from the former summary. Verify that the rendered fixtures match their sources.
2. Obtain a separate owner-approved cold-calibration scope and budget for an activation candidate.
   Combine this proposal with the then-current canonical corpus/rubrics in that isolated candidate;
   do not replace the global contract with this proposal-only subset.
3. Require a completed accepted receipt for the exact combined corpus, rubric and judge identity
   before publishing activation. Only then move the four scenarios into the default build catalog.
   An old, subset or unaccepted receipt is insufficient; do not weaken the runner's receipt gate.

A calibration receipt applies only to the corpus, rubrics, runner, and judge identities it covers.
