# Start from the symptom

Use when the person knows what is failing but not where. A service card, platform name, or full
telemetry stack is not a prerequisite. The parent skill owns evidence, mitigation, escalation,
and recovery rules. Help the human locate the next useful observation.

## Choose a comparison

Use the reported impact and what still works. Pick the relevant row, not the whole table. These
are possible checks, not claims that the named sources exist. Ask which observation is accessible
if access is unknown; a ticket, safe error excerpt, or existing console view may be enough to start.

| What the person sees | A useful first distinction | What the result would change |
|---|---|---|
| "Users cannot log in" | Where does an affected attempt stop: reaching the login page, submitting credentials, returning from sign-in, or opening a protected action? Compare with a working attempt if one exists. | Failure to reach the page suggests a reachability check. Submission/MFA and callback failures need distinct checks; denial after successful sign-in focuses the permissions/session path. The stage or error wording alone does not prove a cause. |
| "It fails sometimes" | Compare one failed and one successful attempt for the same operation and interval: user cohort, route, region, version, or request identifier, using only available fields. | Differences are leads to confirm; attributes shared by success and failure do not discriminate. No difference leaves the cause open. Green aggregates do not clear an affected minority. |
| "Requests are slow" | Which operation is slow, for whom, and compared with what usual duration? Use available request timing to distinguish waiting before work, work itself, and downstream time. | A slow segment selects its next check; total duration alone does not locate the bottleneck. With no breakdown, obtain one affected sample through its owner before prescribing scaling. |
| "The data is old or wrong" | Compare one affected record's source value/version with the processing result and user-visible value; use timestamps only when their meanings and time zones are known. | The first differing stage narrows investigation to ingestion, processing, publication, or serving. A successful job does not prove fresh/correct data; missing stages and possible integrity loss remain explicit. |
| "The job never finished" | Compare its expected schedule/deadline with evidence of dispatch, start, progress, completion, and resulting output. | No start record leaves scheduler, delivery, and missing telemetry open. A start with no progress points to processing/dependency checks. A completion with absent output needs outcome verification; do not rerun until duplicate/partial effects are understood. |

Compare like scopes and time windows. If there is no working comparison, keep that gap and ask for
one affected observation. Flat traffic does not establish unchanged request mix; a report window
does not establish onset. Avoid asking the person to reproduce a destructive or sensitive action.
Login evidence excludes passwords, tokens, cookies, and full authentication payloads.

## Turn the result into the next step

Say what the new observation narrows and what remains open, then choose one feasible check and
explain its different outcomes. If the source is inaccessible, use a genuinely different available
observation or name the owner who can obtain it. Do not send the person back to the same blocked
check without a changed reason. Use platform skills for actual navigation/commands once known;
until then, describe the evidence needed rather than inventing a dashboard or query.

Example:

Human: "The import says successful, but customers see yesterday's data. I only have its summary
and the customer view."

Advisor: "Success is what the job reported; it does not establish fresh customer data. For one
affected record, compare the processed version or timestamp in that summary with the customer
view, if those fields exist. A newer processed version with an older visible version focuses the
next check on publication/serving; if both are old, ask the source or import owner about ingestion.
If the summary has no record detail, ask that owner for this comparison. Bring back the values and
what each timestamp means."

Human: "The summary only shows a total count; no record details."

Advisor: "The count cannot locate where freshness stopped. Keep that unknown. Give the import
owner one safe record identifier and ask which source version was processed and what was published.
We already know the summary lacks that detail; there is no reason to repeat that check."
