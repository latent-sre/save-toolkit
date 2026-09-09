# Start from the symptom

Help the human locate the failure without requiring a platform or telemetry stack. The parent
skill owns evidence, mitigation, escalation, and recovery rules.

## Choose a comparison

Pick the impact's row. For a known PCF app, the default first read is Apps Manager → the app → Events
for the impact window — what changed and when. Use a comparison below first when the supplied
evidence makes it more useful or urgent, and explain that choice. Start with an accessible
ticket, safe excerpt, or console view.

| What the person sees | A useful first distinction | What the result would change |
|---|---|---|
| "Users cannot log in" | Where does an affected attempt stop: reaching the login page, submitting credentials, returning from sign-in, or opening a protected action? Compare with a working attempt if one exists. | Failure to reach the page suggests a reachability check. Submission/MFA and callback failures need distinct checks; denial after successful sign-in focuses the permissions/session path. The stage or error wording alone does not prove a cause. |
| "It fails sometimes" | Compare one failed and one successful attempt for the same operation and interval: user cohort, route, region, version, or request identifier, using only available fields. | Differences are leads to confirm; attributes shared by success and failure do not discriminate. No difference leaves the cause open. Green aggregates do not clear an affected minority. |
| "Requests are slow" | Which operation is slow, for whom, and compared with what usual duration? Use available request timing to distinguish waiting before work, work itself, and downstream time. | A slow segment selects its next check; total duration alone does not locate the bottleneck. With no breakdown, obtain one affected sample through its owner before prescribing scaling. |
| "An external monitor or correlation Situation says we are down" | Split the failing vantage points from the passing ones (which agents or regions fail, which pass), then compare with the platform's own view of the apps; read the Situation's scope and first-alert time once, as a hypothesis. | Failures only from outside with the in-network check passing point at the edge, DNS, or network path rather than the apps; running instances do not prove successful requests. Declare when the impact is multi-service or customer-visible and route the path evidence to the edge/network owners; a restart of healthy apps adds impact. |
| "The data is old or wrong" | Compare one affected record's source value/version with the processing result and user-visible value; use timestamps only when their meanings and time zones are known. | The first differing stage narrows investigation to ingestion, processing, publication, or serving. A successful job does not prove fresh/correct data; missing stages and possible integrity loss remain explicit. |
| "The job never finished" | Separate when the run is due (time zone), dated dispatch/start/progress, and required output/delivery. | Not yet due does not settle an earlier promised delivery. Missing history leaves execution unknown; a stalled run needs processing/dependency checks. A completion flag without a matching output leaves processing, publication, and delivery unconfirmed. Reconcile duplicate/partial effects before any rerun. |

Compare like scopes and time windows. One affected recipient versus many establishes impact scope;
processing and delivery faults can each affect either scope. Locate the failing stage by comparing
the same run's input, correct output, handoff, and recipient evidence. If there is no working
comparison, keep that gap and ask for one affected observation. Flat traffic does not establish unchanged request mix; a report window
does not establish onset. Avoid asking the person to reproduce a destructive or sensitive action.
Login evidence excludes passwords, tokens, cookies, and full authentication payloads.

## Turn the result into the next step

State what changed and remains open; give one feasible check with outcome meanings. Blocked access
needs another source or owner. Use platform skills for known-platform navigation/commands.

Example:

Human: "The import says successful, but customers see yesterday's data. I only have its summary
and the customer view."

Advisor: "Success is what the job reported; it does not establish fresh customer data. For one
affected record, compare the processed version or timestamp in that summary with the customer
view, if those fields exist. A newer processed version with an older visible version focuses the
next check on publication/serving. If both are old, compare the source version with what processing
consumed and produced; ingestion and processing remain open. Missing record detail goes to that
owner. Bring back the values and what each timestamp means."

Human: "The summary only shows a total count; no record details."

Advisor: "The count cannot locate where freshness stopped. Keep that unknown. Give the import
owner one safe record identifier and ask which source version was processed and what was published.
We already know the summary lacks that detail; there is no reason to repeat that check."

Job example: "It finished at 08:00; the recipient read it at 08:20."

"Matching recipient readback of the correct output confirms it reached that recipient. Its delivery
time and path remain unknown. These endpoints do not locate a twenty-minute delivery delay. Ask the job owner for this output's
provider-acceptance and delivery events, with their meanings and clocks. Acceptance at 08:02 and
inbox delivery at 08:07 on comparable clocks would establish that five-minute interval, not its
cause. Missing timing does not reopen confirmed receipt or permit a rerun; without output/recipient
evidence, delivery remains open."
