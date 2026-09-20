# Inspect and change Grafana alerts

Console: Alerts & IRM → Alerting → Alert rules; select the folder, rule, and instance. Inspect its
query, evaluation history, labels, health, and notification destination. For a missing notification,
trace evaluation → instance state → selected Alertmanager → matching route → silence/mute/inhibition
→ grouping/timers → delivery evidence. Reading a contact point does not prove a message arrived.

## Read current state

Read definitions and evaluation state separately. On the documented Grafana-managed path,
`GET /api/v1/provisioning/alert-rules` supplies definitions and provenance, while
`GET /api/prometheus/grafana/api/v1/rules` supplies groups, rule health/state, and instances. Discover
which paths and fields the target serves; record permission failures rather than treating them as
an empty inventory. Bound the sample when examining instance labels or history.

Report total visible rules, evaluation-health errors, paused rules, pending/firing rules, and the
scope/time of the read separately. `health: ok` means the evaluator reports no execution error;
it does not mean the condition is healthy. A firing rule can have healthy evaluation. A rule with
multiple label sets can have several instances, so rule counts are not alert-instance counts.

For a missing page, inspect the relevant instance's effective labels, selected Alertmanager,
silence/inhibition associations, existing route, and timers without sending a test message. List
silences on that same Alertmanager; four active silences do not establish which alerts they affect.
Do not expose contact-point credentials or claim delivery/acknowledgement from configuration alone.

## Bind the rule and owner

Read the exact instance/org, folder UID, rule UID, group and interval, datasource UIDs, effective
grants, and provisioning owner. Grafana-managed and datasource-managed rules have different
evaluators. File/Terraform/Git-managed rules require a change to their owning source and its apply
path; do not clear provenance or use `X-Disable-Provenance` to take ownership. An API-owned rule is
editable only when this task's operator owns that provisioning workflow.

For an agent, discover the target's served API/schema. Grafana 13 still serves the legacy rule
provisioning API below; do not invent App Platform paths or transplant dashboard concurrency fields
into an alert request. Pin the selected API family and confirm its target behavior before writing.

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

1. Establish the human-requested rule, effect, environment, and existing authorization. A pause
   requires a reason, resume deadline, and named resume owner; it stops evaluation and does not
   auto-expire. For temporary notification suppression use the silence procedure instead. Resume
   can immediately generate notifications. Do not pause merely to hide an error or failed check.
2. Capture the existing rule and relevant group/route state. For creation prove UID absence with
   sufficient read grants, discover an appropriate existing group, and name recovery ownership.
   Creating a new group or changing a shared interval is a separately scoped group change.
3. Use `obs-alerting` for alert intent and SLO design, and [alerting configuration](./grafana-alerting.md)
   for Grafana condition/evaluation fields, no-data/error states, and provisioning formats.
   Establish owner, severity, and runbook. Preserve unrelated fields, labels, group membership, and notification
   settings. Resolve queries against real datasource metadata; dashboard variables/macros must
   become explicit alert-compatible expressions. Show notification impact, including label changes
   that could create new instances or select another existing route.
4. Validate the body and query on bounded healthy/bad windows where available; verify the intended
   existing destination. A paging rule needs an owner and approved runbook target. Show the full
   before/after diff, target, expected effect, and recovery before dispatch. Do not send a test
   notification to a production receiver as part of validation.
5. Use an enforced version/precondition when the selected API supports it. The legacy contract does
   not promise a dashboard-style compare-and-swap. Without an enforced precondition, establish a
   coordinated single-writer window with the resource owner; re-read immediately before dispatch
   and stop on drift. A fresh GET alone does not close the race. If neither control is available,
   return the prepared change for the owning executor.
6. Write the one rule once. Retain the response and UID; read it back into a fresh result and compare
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

Read-only requests never exercise firing conditions or send notifications. Rule deletion,
whole-group replacement, backend rule applies, recording rules, shared routing, and contact-point
changes stay with `production-change-gate`. Direct rule changes are only for the invoked
`observability-engineer` under its complete Grafana write rule.

[sourced] [Grafana rule provisioning API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/alerting_provisioning/)
and [evaluation behavior](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/),
checked 2026-09-19. API shapes are sourced; no live alert write, concurrency, or delivery acceptance
is established here. Refresh for the exact installed version before relying on changed APIs.
