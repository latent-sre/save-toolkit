# Inspect and change Grafana alerts

Console: Alerts & IRM → Alerting → Alert rules; select the folder, rule, and instance. Inspect its
query, evaluation history, labels, health, and notification destination. For a missing notification,
trace evaluation → instance state → selected Alertmanager → matching route → silence/mute/inhibition
→ grouping/timers → delivery evidence. Reading a contact point does not prove a message arrived.


## Read current state

Separate definitions/provenance (`GET /api/v1/provisioning/alert-rules`) from evaluation/groups/
instances (`GET /api/prometheus/grafana/api/v1/rules`). Discover served paths/fields; permission
failure is not empty inventory. Bound label/history samples.

For a known rule, use the bundled helper's `alerts --uid <rule-uid>` for its exact definition, then
`alerts --folder-uid <folder-uid>` for evaluation state. Match the rule UID across both reads;
names are not unique. Preserve `configuration_only` on the definition and the state read's
truncation/instance limits. A missing sampled instance does not prove a rule is inactive.

Report visible rule totals, evaluation errors, paused/pending/firing counts and scope/time
separately. `health: ok` means no evaluation error, not a healthy condition; a firing rule can be
`ok`. Multiple label sets produce multiple instances, not additional rules.

For a missing page, inspect the relevant instance's effective labels, selected Alertmanager,
silence/inhibition associations, existing route, and timers without sending a test message. List
silences on that same Alertmanager; four active silences do not establish which alerts they affect.
Do not expose contact-point credentials or claim delivery/acknowledgement from configuration alone.

## Bind the rule and owner

Read the exact instance/org, folder UID, rule UID, group and interval, datasource UIDs, effective
grants, and stored provenance. Grafana-managed and datasource-managed rules have different
evaluators. File/Terraform/Git-managed rules change only through their owning source and its apply
path. An API-owned rule is editable only when this task's operator owns that provisioning workflow.

A provisioning-API write with `X-Disable-Provenance: true` stores the rule unmanaged; without the
header it is recorded as API-provisioned. Grafana rejects an update only when a stored owner is set
and differs, so a header-less write silently converts a UI-created rule to API-managed, which the
console then treats as read-only. Send the header for an unmanaged rule, omit it for an API-owned
rule, and never change provenance as a side effect.

The helper uses the deprecated legacy provisioning API below. Discover/pin the target's served
API/schema; unavailable routes are compatibility gaps, not empty inventory. Never invent App
Platform paths or transplant dashboard concurrency fields. Confirm target behavior before writing.

| Operation | Legacy rule provisioning API |
|---|---|
| Inspect one rule | `GET /api/v1/provisioning/alert-rules/<uid>` |
| Inspect its group | `GET /api/v1/provisioning/folder/<folderUid>/rule-groups/<group>` |
| Create one rule | `POST /api/v1/provisioning/alert-rules` with an explicit unused `uid` |
| Update or pause/resume one rule | `PUT /api/v1/provisioning/alert-rules/<uid>` with the full valid rule body; pause uses `isPaused` |

URL-encode resource identifiers. An export is recovery/source material, not a replayable update
body: provisioning exports use a different schema. Never use a group PUT for a single-rule edit;
it can replace the group's rules and change every member's provenance.

## Apply the requested change

1. Bind the human-requested rule/effect/environment and authorization. Pause stops evaluation and
   never auto-expires: require reason, resume deadline and owner. Resume can notify immediately;
   do not pause to hide failures. Temporary suppression instead uses the silence procedure.
2. Capture the existing rule and relevant group/route state. For creation prove UID absence with
   sufficient read grants, read the intended existing group to prove it exists, and name recovery
   ownership. A POST with a mistyped `ruleGroup` silently creates a new group with the default
   interval. Creating a new group or changing a shared interval is a separately scoped group change.
3. Use `obs-alerting` for alert intent and SLO design, and [alerting configuration](./grafana-alerting.md)
   for Grafana condition/evaluation fields, no-data/error states, and provisioning formats.
   Establish owner, severity, and runbook. Preserve unrelated fields, labels, group membership, and notification
   settings. Resolve queries against real datasource metadata; dashboard variables/macros must
   become explicit alert-compatible expressions. Show notification impact, including label changes
   that could create new instances or select another existing route.
4. Validate body/query on bounded healthy/bad windows where available and verify the existing
   destination. Paging requires an owner/approved runbook. Show full diff, target, effect and recovery;
   never validate by sending a test notification to production.
5. Use an enforced version/precondition when the selected API supports it. The legacy contract does
   not promise a dashboard-style compare-and-swap. Without an enforced precondition, establish a
   coordinated single-writer window with the resource owner; re-read immediately before dispatch
   and stop on drift. A fresh GET alone does not close the race. If neither control is available,
   return the prepared change for the owning executor.
6. Write the one rule once. A 409 is a provenance mismatch or an optimistic-lock conflict: stop and
   re-read; do not retry. Retain the response and UID; read it back into a fresh result and compare
   intended fields, UID, folder/group, provenance, and pause state. Check evaluation after its next
   scheduled run with a bounded wait. For a pause, confirm it is paused; for a create/update/resume,
   report query errors, no-data, pending, firing, or normal as observed. Saved configuration is not
   proof of fire/resolve or notification delivery; name those gaps explicitly.
7. For rollback, re-read and compare against the state written by this operation, then restore the
   prior definition through the same ownership/concurrency checks. Never overwrite an intervening
   edit. A newly created rule has no prior version: a requested recovery may pause it with an owner
   and deadline; deletion goes to the human/protected executor. Suppressed or sent pages cannot be
   undone by restoring configuration. Return the record for the normal `scribe` handoff.

On a timeout/dropped response after dispatch, record UNKNOWN and do not repeat the POST/PUT. Read
the chosen UID and compare desired/prior definitions and available history/audit evidence. Account
for concurrent changes and in-flight requests; a single absent or old read does not prove that the
write will never land. Stop with a named reconciliation owner while evidence is incomplete.

## Evidence and scope

Read-only requests never exercise firing conditions or send notifications. Who may make which
rule change is set in the parent skill's [Access and authority](../SKILL.md#access-and-authority).

Live alert write, concurrency, and delivery behavior on the target is unconfirmed until observed.
