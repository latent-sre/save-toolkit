---
schema_version: 1
service_id: <stable-service-slug>
name: <human-readable service name>
lifecycle: proposed | active | deprecated | retired
owner: <team/role>
criticality: <critical | high | medium | low>
source_revision: <repository@full-sha or reviewed release identifier>
last_reviewed: null
evidence_status: sourced | unverified
---

# Service: <name>

## Purpose and user journeys

- Purpose: <what capability this service provides>
- Users/journeys affected: <who notices failure and how>
- Out of scope: <what this service does not own>

## Ownership and escalation

| Responsibility | Owner | Contact / escalation path |
|---|---|---|
| Service |  |  |
| On-call |  |  |
| Data |  |  |
| Platform dependency | platform team |  |

## Runtime and boundaries

- Repository and revision: <link + full SHA>
- Runtime: <PCF foundation/org/space and app names, without credentials>
- Routes/endpoints: <access-controlled links; no secrets>
- Deployment source: <manifest/workflow link>
- Platform boundary: <what this team owns vs escalates>

## Dependencies and state

| Dependency / data store | Direction | Failure effect | Owner | Evidence |
|---|---|---|---|---|
|  | inbound / outbound |  |  |  |

- Data classification: <classification or `[unverified]`>
- Backup/restore status: <evidence link, last successful drill, or explicit gap>

## Reliability and observability

- SLI/SLO: <definition link or explicit gap>
- Health signal: <authoritative health-check definition + expected state>
- Dashboard: <link or explicit gap>

| Alert card | Exact alert name | Severity | Runbook | Authoritative definition |
|---|---|---|---|---|
|  |  |  |  |  |

## Deployment, recovery, and operating guidance

- Deploy/promotion: <authoritative workflow/runbook link>
- Rollback/recovery: <runbook link; do not duplicate unverified commands here>
- Routine operating tasks: <runbook links>

## Known risks and open gaps

| Gap / accepted risk | Evidence label | Owner | Due / review date | Tracking link |
|---|---|---|---|---|
|  |  |  |  |  |

## Evidence and provenance

| Claim | Label | Source / exact revision | Limitation |
|---|---|---|---|
|  | `[sourced]` / `[unverified]` |  |  |

## Change log

| Date | PR / revision / evidence reference | Change | Reviewer |
|---|---|---|---|
|  |  |  |  |
