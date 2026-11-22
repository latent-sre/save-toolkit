# Grafana alerting and temporary silences

Alert/SLO design belongs to `obs-analysis`; reading contact points or silences never proves
notification delivery, and never send test alerts to production. For missing notifications, trace:
evaluation -> instance state -> Alertmanager -> matching route -> silence/mute/inhibition ->
grouping/timers -> delivery evidence.

## Rule evaluation, provisioning spellings, and APIs

Keep one evaluation owner per rule. Review all four evaluation knobs: `for` (pending duration),
recovery threshold (query hysteresis), keep-firing hysteresis, and no-data/error handling:

- **Provisioning spellings (`OK` vs UI labels):** HTTP API bodies spell keep-firing as
  **`keep_firing_for`**; file-provisioning YAML and exports spell it **`keepFiringFor`** (e.g.,
  `keepFiringFor: 5m`; unknown keys are silently ignored — verify the running rule). File YAML
  spells normal as **`OK`**: **`noDataState: NoData|Alerting|OK|KeepLast`** and
  **`execErrState: Error|Alerting|OK|KeepLast`** (mapping silent telemetry or query errors on paging
  rules to `OK` creates false all-clears; UI strings **`Normal`** and **`Keep Last State`** are
  **invalid** in provisioning YAML).
- **Separate definitions from evaluation health:** Pair definitions/provenance
  (`GET /api/v1/provisioning/alert-rules` or helper `alerts --uid <uid>`) with evaluation state
  (`GET /api/prometheus/grafana/api/v1/rules` or helper `alerts --folder-uid <uid>`), matching by UID.
  `health=ok` means evaluation succeeded, distinct from firing alerts (`state=firing`); neither proves
  notification delivery (`UNVERIFIED` without delivery evidence). Permission errors != empty rules.
- **Provenance (`X-Disable-Provenance`):** Sending `X-Disable-Provenance` (any value, including
  `false`) stores a rule unmanaged; omitting it marks the rule API-provisioned (read-only in UI).
  Match the existing rule so edits never flip provenance unexpectedly. Provisioned/Git/Terraform
  rules change only through their owning source.
- **Rule write APIs & single-rule boundary:** Discover and prefer `rules.alerting.grafana.app/v1beta1`
  (`alertrules`, `recordingrules`; `notificationSettings.type`: `SimplifiedRouting` or
  `NamedRoutingTree`). Legacy fallback: `POST /api/v1/provisioning/alert-rules` (explicit unused
  `uid`, verify existing `ruleGroup` first) and single-rule `PUT /api/v1/provisioning/alert-rules/<uid>`
  (uses `isPaused` for pause). Through 13.3.1 legacy stores ignore `resourceVersion`, so use a
  single-writer window and re-read right before writing. When authorized to update one rule, **never**
  use a whole-group `PUT` (overwrites sibling rules: outside request) or delete+recreate with a new
  UID (outside request). Export formats (`?format=yaml|json|hcl`) are not replayable HTTP API bodies.
- **Pause vs silence, conflict, verify & rollback:** Pause stops evaluation and never auto-expires
  (require owner and resume deadline; use silences for temporary suppression). Convert dashboard
  macros before creating rules. On `409`/`403` conflict, stop and re-read. After writing, confirm
  fresh **readback and one evaluation interval** while reporting any delivery-evidence gaps. Before
  rollback, check a fresh read against operation-written state; on post-dispatch timeout report
  `UNKNOWN` and reconcile by UID before retrying.
- **Contact points & policy trees (source-managed):** Legacy endpoints are deprecated; Grafana 13.2+
  supports multiple named trees where applying a tree overwrites all policies in that tree. Export
  full before/after trees for PRs.

## Temporary silences

Silences suppress Alertmanager notifications while **rule evaluation continues**. In Grafana 13.3
Alertmanager v2 APIs (`<am>` is `grafana` for built-in or the external Alertmanager datasource UID,
never display name; helper `silences` inspects built-in `grafana` only):

| Operation | Path under trusted Grafana origin |
|---|---|
| List | `GET /api/alertmanager/<am>/api/v2/silences` |
| Read one | `GET /api/alertmanager/<am>/api/v2/silence/<id>` |
| Create or update | `POST /api/alertmanager/<am>/api/v2/silences` (`omit id` on create; include `id` on update) |
| End early (expire) | `DELETE /api/alertmanager/<am>/api/v2/silence/<id>` |

- Bind Alertmanager, exact matchers, absolute UTC `startsAt`/`endsAt`, human owner, and reason.
  Target a single alert rule with matcher **`__alert_rule_uid__=<uid>`** (updating that matcher
  returns `400`; create a new silence instead). Empty preview instances do not prove regex or
  missing-label matchers harmless.
- **ID replacement on update:** Alertmanager preserves `id` *only* on active/pending updates with
  **unchanged matchers** (and unchanged `startsAt` when active); editing matchers **expires the
  original silence and returns a new/different ID** (`silenceID`) — verify both the new active ID and
  the expired original ID.
- **Post-dispatch timeout (`UNKNOWN`):** Never retry, re-post, or create a duplicate after a timed-out
  `POST` (`Redispatch: BLOCKED_PENDING_RECONCILIATION`); reconcile on the **same Alertmanager**
  (`SAME_ALERTMANAGER`) via `GET .../silences` or `GET .../silence/<id>` first. Rollback expires a
  created silence (`DELETE`), or for an ID-replacing update expires the new ID and recreates the
  prior scope if still inside its window.
