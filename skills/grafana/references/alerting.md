# Grafana alerting — rules, provisioning, and evaluation

Console: Alerts & IRM → Alert rules. For a missing notification, trace: evaluation →
instance state → selected Alertmanager → matching route → silence/mute/inhibition → grouping/timers
→ delivery evidence. Reading a contact point does not prove delivery; never validate by sending a
test notification to production. Alert/SLO design belongs to `obs-analysis`; temporary suppression
uses [silences](./silences.md).

## Evaluation knobs and provisioning spellings

Keep one evaluation owner per rule (no duplicates across paths). Review all four knobs per rule:

- **`for`** filters flapping on entry; **keep-firing-for** holds a clearing alert in `Recovering` so
  a re-fire returns to `Alerting` without a new notification. The HTTP API body spells it
  **`keep_firing_for`**; file-provisioning YAML and YAML/JSON exports spell it **`keepFiringFor`**.
  A wrong key is silently ignored, not rejected — verify the running rule's state, not just YAML.
- **Recovery threshold** supplies query-side hysteresis.
- **No-data and execution-error states** are per-rule decisions (mapping silent telemetry or query
  errors to Normal on a paging burn-rate rule creates a false all-clear). In file-provisioning YAML,
  Normal is spelled **`OK`**: `noDataState: NoData|Alerting|OK|KeepLast`,
  `execErrState: Error|Alerting|OK|KeepLast`. Literal UI labels `Normal` and `Keep Last State` are
  invalid provisioning values. `KeepLast` preserves prior state, not current health.

## Read state, ownership, and APIs

Separate definitions/provenance (`GET /api/v1/provisioning/alert-rules`) from evaluation/instances
(`GET /api/prometheus/grafana/api/v1/rules`). With the bundled helper, pair `alerts --uid <uid>`
(definition, `configuration_only`) with `alerts --folder-uid <folder-uid>` (evaluation state),
matching by rule UID (names are not unique). Permission failure is not empty inventory.

File/Terraform/Git-managed rules change only through their owning source (controlled restart or
hot-reload). An API-owned rule is editable only when this task's operator owns that workflow.

**`X-Disable-Provenance` trap:** A provisioning-API write with `X-Disable-Provenance` (any value,
including `false`) stores the rule unmanaged; omitting it marks the rule API-provisioned, making it
read-only in the console. Grafana rejects updates only when a *different* stored owner is set, so a
headerless write silently converts a UI-created rule to API-managed. Send the header for unmanaged
rules, omit it for API-owned rules, and never change provenance as a side effect.

Where the target serves `rules.alerting.grafana.app/v1beta1` (`alertrules`, `recordingrules`; OSS
13.3.0+), discover it with `GET /apis/rules.alerting.grafana.app/` and prefer it over the deprecated
legacy endpoints below. In `v1beta1`, an alert rule's `notificationSettings` must carry `type`
(`SimplifiedRouting` with a `receiver`, or `NamedRoutingTree` with a `routingTree`). Through
13.3.1 the legacy-backed `alertrules` store does **not** compare `metadata.resourceVersion` on
update, although the 13.3 API docs say passing it prevents concurrent overwrites, and legacy
provisioning has no token either: establish a coordinated single-writer window, re-read
immediately before writing, and stop on drift.

| Operation | Legacy rule provisioning API |
|---|---|
| Create one rule | `POST /api/v1/provisioning/alert-rules` with explicit unused `uid` |
| Update or pause/resume one rule | `PUT /api/v1/provisioning/alert-rules/<uid>` with full valid body (`isPaused` for pause) |

- Export endpoints (`…/export?format=yaml|json|hcl`) emit file/Terraform formats, **not** replayable
  HTTP API update bodies.
- Never use a group PUT for a single-rule edit — it replaces the whole group and can reset
  provenance across rules.
- A POST with a mistyped `ruleGroup` silently creates a new group with the default interval; verify
  the target group exists first.
- Recording rules write to a Prometheus-compatible target datasource (or `default_datasource_uid`)
  using a valid Prometheus metric name.

## Apply a live rule change

1. **Bind scope and owner.** Pause stops evaluation and never auto-expires — require reason, resume
   deadline, and owner (use a silence for temporary suppression). Resume can notify immediately.
2. **Capture prior state** (existing rule, group, route; for create, prove UID absence and existing
   group, and name the recovery owner).
3. **Prepare and validate.** Convert dashboard variables and macros to explicit alert-compatible
   expressions; `obs-analysis` owns paging fields such as owner and `runbook_url`. Backtest on
   bounded healthy/bad windows where available and show full diff, notification/route impact, and
   recovery.
4. **Write once, read back, verify evaluation.** On `409` (rule provenance/lock/UID conflict) or
   `403` (notification provenance conflict), stop and re-read; do not retry. Read back into a fresh
   result to confirm fields, UID, folder/group, provenance, and pause state; wait one evaluation
   interval and report observed state (`paused`, `normal`, `pending`, `firing`, `no-data`, error)
   separately from unverified delivery.
5. **Rollback / UNKNOWN:** Compare a fresh read against operation-written state before restoring the
   prior definition (never overwrite intervening edits). For a newly created rule, recovery may
   pause it with owner/deadline; deletion goes to a human/protected executor. On post-dispatch
   timeout, follow the parent's [UNKNOWN rule](../SKILL.md#return-the-result) and reconcile by UID
   before any retry.

## Contact points and notification policies (source-managed)

The legacy contact-point, notification-policy, template, and mute-timing provisioning endpoints are
deprecated. **Full-tree warning:** Since Grafana 13.2 an instance can hold multiple named
notification policy trees, and applying a provisioned tree overwrites every policy in that tree.
Export the full current tree immediately before review, preserve every existing branch, and submit
source-managed rule-group and policy changes through PR with before/after exports, validation, and
rollback via source revert.
