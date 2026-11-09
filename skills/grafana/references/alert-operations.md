# Inspect and change Grafana alerts

Console: Alerts & IRM → Alerting → Alert rules; select the folder, rule, and instance. For a missing notification,
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

For a missing page, walk that trace without sending a test message. List
silences on that same Alertmanager; four active silences do not establish which alerts they affect.
Do not expose contact-point credentials or claim delivery/acknowledgement from configuration alone.

## Bind the rule and owner

Read the exact instance/org, folder UID, rule UID, group and interval, datasource UIDs, effective
grants, and stored provenance. File/Terraform/Git-managed rules change only through their owning source and its apply
path. An API-owned rule is editable only when this task's operator owns that provisioning workflow.

A provisioning-API write carrying the `X-Disable-Provenance` header, with any value including
`false`, stores the rule unmanaged; without the header it is recorded as API-provisioned. Grafana
rejects an update only when a stored owner is set and differs, so a header-less write silently
converts a UI-created rule to API-managed, which the console then treats as read-only. Send the
header for an unmanaged rule, omit it entirely for an API-owned rule, and never change provenance
as a side effect.

Where the target serves `rules.alerting.grafana.app/v1beta1` (`alertrules`, `recordingrules`; OSS
13.3.0+), prefer it: it replaces the deprecated rule provisioning endpoints. Discover it with
`GET /apis/rules.alerting.grafana.app/` and use only the paths and fields the target lists. The
helper and the table below use the deprecated legacy API. Unavailable routes are compatibility gaps, not empty inventory.
Do not transplant dashboard concurrency fields. Confirm target behavior before writing.

| Operation | Legacy rule provisioning API |
|---|---|
| Create one rule | `POST /api/v1/provisioning/alert-rules` with an explicit unused `uid` |
| Update or pause/resume one rule | `PUT /api/v1/provisioning/alert-rules/<uid>` with the full valid rule body; pause uses `isPaused` |

An export is recovery/source material, not a replayable update body: provisioning exports use a
different schema. Never use a group PUT for a single-rule edit; it can replace the group's rules and
change the provenance of every rule it modifies, including resetting an API-owned rule to unmanaged.

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
5. On 13.3.0 the legacy-backed `alertrules` store does not compare `metadata.resourceVersion`: do
   not treat it as compare-and-swap unless a stale-write test on this target returns a conflict. The
   provisioning API has none. Without compare-and-swap, establish a coordinated single-writer window
   with the resource owner, re-read immediately before dispatch and stop on drift. A fresh GET alone
   does not close the race. If no window is available, return the prepared change for the owning
   executor.
6. Write the one rule once. On a rule, a 409 is a provenance, optimistic-lock or unique-constraint (used UID) conflict;
   notification resources answer a provenance error with 403. Stop and re-read; do not retry. Retain
   the response and UID; read it back into a fresh result and compare intended fields, UID,
   folder/group, provenance, and pause state. Check evaluation after its next scheduled run with a
   bounded wait. For a pause, confirm it is paused; for a create/update/resume, report query errors,
   no-data, pending, firing, or normal as observed, and name the unverified fire/resolve and delivery.
7. For rollback, compare a fresh read with the state this operation wrote, then restore the prior
   definition through the same ownership/concurrency checks; never overwrite an intervening edit.
   A newly created rule has no prior version: a requested recovery may pause it with an owner and
   deadline; deletion goes to the human/protected executor. Suppressed or sent pages cannot be
   undone by restoring configuration. Return the record for the normal `scribe` handoff.

A timeout or dropped response after dispatch is UNKNOWN under the parent's
[result rule](../SKILL.md#return-the-result): do not repeat the POST/PUT; read the chosen UID and
compare it with the desired and prior definitions and any history/audit evidence, allowing for
concurrent changes and in-flight requests.

## Evidence and scope

Read-only requests never exercise firing conditions or send notifications. Who may make which
rule change is set in the parent skill's [Access and authority](../SKILL.md#access-and-authority).

Live alert write, concurrency, and delivery behavior on the target is unconfirmed until observed.
