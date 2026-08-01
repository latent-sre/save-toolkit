---
schema_version: 1
incident_id: <stable incident/ticket ID>
status: draft | final
severity: <SEV-n>
service_ids: []
started_at: <RFC3339 UTC>
resolved_at: <RFC3339 UTC>
owner: <team/role>
source_revision: <repository@full-sha or reviewed release identifier>
last_reviewed: null
---

# YYYY-MM-DD — <incident name>

- Services affected: <service-card links>
- Duration (first bad signal to resolution):

## Summary

<What failed, impact, duration, detection, and resolution in three to five sentences.>

## Impact

<User-visible effect; magnitude; SLO/error-budget effect; data loss or explicit evidence of none.>

## Timeline (UTC, from evidence)

| Time | Event or decision | Evidence source |
|---|---|---|
|  | First bad signal |  |
|  | Detected |  |
|  | Mitigated |  |
|  | Resolved |  |

## Trigger, root cause, and contributing factors

- Trigger:
- Root cause:
- Contributing factors:
- Diagnosis evidence:

## Five whys

1. <Why did the user-visible symptom occur?>
2. <Why did the preceding condition exist?>
3. <Continue to the systemic control/architecture/process cause; do not stop at a person.>

## Detection and response

- What worked:
- What slowed diagnosis or mitigation:
- Detection gap:

## Where we got lucky

- <Each item should become a preventative action or an explicit accepted risk.>

## Lessons

- <Evidence-bound lesson and the failure class it addresses.>
- <What should remain unchanged because it worked?>

## Action items

| Action | Type | Owner | Due | Tracking link | Durable artifact / proof of done |
|---|---|---|---|---|---|
|  | mitigative |  |  |  |  |
|  | preventative |  |  |  |  |

## Runbook and observability updates

<Name each prepared/linked artifact, or give an explicit proposed/blocked/duplicate/not-applicable
disposition. Never silently omit a missing runbook, service/alert card, SLO, dashboard, or alert.>

## Operational knowledge dispositions

| Artifact | Action | Status | Owner | Path/tracking link | Evidence IDs | Reason |
|---|---|---|---|---|---|---|
| runbook | create/update/link/handoff/none |  |  |  |  |  |
| service card / alert card / knowledge index |  |  |  |  |  |  |
| observability / automation / code / accepted risk |  |  |  |  |  |  |

## Verification gaps

<List every remaining `[unverified]` claim and how it will be confirmed.>
