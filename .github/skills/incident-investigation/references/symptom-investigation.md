# Start from the symptom

## Choose a comparison

For known PCF apps, start with Apps Manager → app → Events unless supplied evidence makes a
comparison below more useful or urgent; explain that choice. Use an accessible ticket, safe excerpt
or console view without requiring the responder to know the telemetry stack.

| What the person sees | A useful first distinction | What the result would change |
|---|---|---|
| "Users cannot log in" | Compare failing/working attempts by stage: page reachability, submission/MFA, callback, protected action. | Each stage selects a different check; denial after sign-in focuses permissions/session. Stage/error wording alone does not prove cause. |
| "It fails sometimes" | Compare failure/success for the same operation and interval by available cohort, route, region, version or request ID. | Differences are leads; shared attributes do not discriminate. No difference leaves the cause open; green aggregates do not clear a minority. |
| "Requests are slow" | Separate pre-work wait, processing and downstream time for the affected operation/cohort against its usual duration. | Total time does not locate a bottleneck. Without a breakdown, obtain an affected sample through its owner before prescribing scaling. |
| "An external monitor or Situation says we are down" | Compare failing/passing vantages with in-network requests and platform state. Treat Situation scope/first-alert time as a hypothesis. | External-only failure points toward edge/DNS/network; running instances do not prove working requests. Name multi-service/customer impact and send path evidence to edge/network owners; restarting healthy apps adds impact. |
| "The data is old or wrong" | Compare one record's source, processing result and visible value/version; timestamp meaning and zone must be known. | The first difference narrows the stage. Job success does not prove freshness/correctness; missing stages and integrity risk stay explicit. |
| "The job never finished" | Compare due time/zone, dated dispatch/start/progress and required output/delivery. | Not-yet-due does not settle earlier promised delivery. Missing history leaves execution unknown; a stalled run needs processing/dependency checks. Completion without matching output leaves processing, publication and delivery unconfirmed. Reconcile partial/duplicate effects before rerun. |

Compare like populations and time windows. Recipient count establishes scope, not whether processing
or delivery failed; either can affect one or many. Compare the same run's input, correct output,
handoff and recipient evidence. Without a working
comparison, retain the gap and request an affected observation. Flat traffic does not prove unchanged
request mix; a report window is not onset. Never request destructive/sensitive reproduction or login
passwords, tokens, cookies or full authentication payloads.

## Turn the result into the next step

Use platform skills for navigation/commands; blocked access needs another source or owner.

**Successful import, stale customer view:** a newer processed record with an older visible version
focuses publication/serving. If both are old, compare source against consumed/produced versions;
ingestion and processing remain open. A summary count cannot locate the failed stage: ask the import
owner for one safe record's source, processed and published versions rather than repeating the count.

**Job finished at 08:00; recipient read at 08:20:** matching readback proves receipt of that correct
output, not its delivery time/path or a twenty-minute delay. Ask for this output's provider-acceptance
and delivery events with clock meanings. Acceptance at 08:02 and delivery at 08:07 on comparable
clocks establishes that five-minute interval, not its cause. Missing timing neither reopens confirmed
receipt nor permits a rerun; absent output/recipient evidence leaves delivery open.
