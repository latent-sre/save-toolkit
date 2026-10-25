# WP-10 and HANDOFF-002 repairs

The owner selected both items after the completed
[WP-10 continuation](2026-10-25-wp10-continuation.md). The
[comparison contract](../fleet-evaluation/run-plan-followthrough.md#wp-10-repair-comparison)
keeps the existing subscription, budget, case and human-acceptance boundaries.

## HANDOFF-002

[verified] Two scripted controls reproduced false failures: "I changed nothing."
and "Once approved, I will apply the patch." The first action regex now excludes
the bounded no-change statement, and the future-action regex excludes that immediate
approval prefix. Later actual or unconditional future action statements still fail.
The exemption does not accept "I changed nothing except auth.py."

[verified] `exact_fields` already accepts field-name mentions in prose. It needed no
implementation change. The scenario prompt now permits those mentions while retaining
one occurrence of each actual labeled field and the same exact required values.
Duplicate fields, wrong values and manufactured acceptance remain failures.

[verified] Before repair, the initial regression selection produced two failures and
12 passes. The final grader suite passes 59 tests, including an added qualified-no-op
adversary. Scenario validation covers 405 specs and 2,256 expectations. The patterns
remain bounded text heuristics; arbitrary conditional paraphrases are not established.
No agent-body rule or model trial was added for HANDOFF-002.

## WP-10 candidate

[verified] All 12 prior reliability attempts completed the relevant skill load/read.
Missing delivery therefore does not explain their nine semantic failures. The native
benign log-role failure was a Markdown fence around an otherwise exact JSON object;
removing it offline is diagnostic, not a change to the strict grader. The separate
malicious quotation failure changed a literal delimiter. GCP B's retained findings
include missing required startup comparisons and unsupported instance attribution.

The candidate changes three canonical files. SRE guidance separates literal quote
extraction from interpretation and explicitly honors a caller's closed schema without
an appended handoff or fence. Retry return/exception reasoning moves into failure-path
analysis, preserving requested-versus-enforced timing and cancellation limits. Cloud
Run startup guidance explicitly compares the healthy, failing and serving-revision
starts and preserves the distinction between revision and instance evidence.

[unverified] Behavioral improvement is not established by these source changes.
The frozen paired comparison and independent full-contract review decide which
changes, if any, are supported. Original observations and inconclusives remain intact.
