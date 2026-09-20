# Temporary silences

A silence suppresses matching notifications for a fixed window; evaluation continues. Recurring
mute timings change scheduled notification behavior; pausing a rule stops evaluation. Do not
substitute one for another. Ending a silence can allow still-firing alerts to notify again.

Console: Alerts & IRM → Alerting → Silences. Select the Alertmanager before creating or editing a
silence. Inspect matching firing instances in the preview, set start/end, and add an owner/reason.
Use Unsilence to end it early. The preview only shows currently firing instances: future alerts
whose labels match will also be suppressed during the window.

## Prepare, apply, verify

1. Bind the instance/org, Alertmanager, service/environment or rule UID, exact matchers, start/end
   in UTC, human owner, and reason/change reference. Never infer the creator identity from the
   service-account name. If the requester supplies a duration, resolve and show the absolute times
   immediately before writing. No expiry or ambiguous environment means ask for the missing scope.
2. Inspect the rule/alert labels and existing silences. Show currently affected instances and the
   matcher's potential wider scope. Prefer exact service/environment or rule-specific matches when
   they express the request. Explain regex, negative, or missing-label matches before using them;
   a preview with no firing instances does not prove the matcher is harmless. Include enough scope
   to avoid silencing a different environment. Do not broaden a failed match to make it work.
3. For an update/early expiry, read the exact silence ID and preserve its prior body. Confirm the
   request covers that silence; do not modify another owner's silence merely because it overlaps.
   Check that an identical active/pending silence does not already satisfy a create request.
4. Show the exact target, matchers, UTC window, affected scope, and recovery action. The invoked
   observability agent may execute within the existing human request once these are established.
   Re-read an existing silence immediately before mutation and stop on drift. These endpoints do
   not promise compare-and-swap: coordinate a single-writer window for changes to a shared silence
   or return the prepared change to its owner. A re-read alone is not mutual exclusion.
5. Write once, retain the returned silence ID, then fetch that ID from the same Alertmanager.
   Verify matchers, timestamps, owner/comment, and active/pending/expired state as appropriate.
   For suppression, check matching instances' silence association when available; for early expiry,
   verify expired state and inspect overlapping silences before claiming notifications can resume.
   Neither result proves delivery or service recovery.
6. Return the ID/link, intended effect, observed state, expiry, and recovery owner. To undo a new
   silence, expire that exact ID. After an edit, restore the captured body only within its original
   still-valid window and the authorized scope. An expired silence cannot be unexpired: any
   replacement is a new silence with a new ID and needs scope covering the remaining window.
   Lost notifications cannot be recovered by rollback.

## Agent API mapping

Use the actual target's supported route and permissions. The Grafana 13.2 client uses:

| Operation | Path under the trusted Grafana origin |
|---|---|
| List | `GET /api/alertmanager/<am>/api/v2/silences` |
| Read one | `GET /api/alertmanager/<am>/api/v2/silence/<id>` |
| Create or update | `POST /api/alertmanager/<am>/api/v2/silences` |
| End early | `DELETE /api/alertmanager/<am>/api/v2/silence/<id>` — expires, not permanent deletion |

`<am>` is `grafana` for the built-in Alertmanager or the discovered datasource UID for the external
one; never substitute its display name. The POST body carries `matchers` (name, value, regex/equality
flags supported by that server), `startsAt`, `endsAt`, `createdBy`, and `comment`. Update includes
the existing `id`; create omits it. A rule-specific silence can use `__alert_rule_uid__=<uid>`;
verify the label applies to this Alertmanager's alerts rather than assuming external alerts carry it.
Discover response ID spelling from the API/tool response and verify it through readback.

A timeout after POST has UNKNOWN outcome. Do not create another silence. Read the returned ID if
known; otherwise list the same Alertmanager's silences and reconcile the full matcher/time/owner/
comment payload and available audit evidence. Check for duplicates and late arrival; an empty list
on one read is not proof of no write. For uncertain expiry, read the exact ID and its status.
Incomplete evidence blocks redispatch and names the human reconciliation owner.

[sourced] [Grafana silence documentation](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/create-silence/)
defines scope and notification semantics; the
[13.2 client routes](https://github.com/grafana/grafana/blob/v13.2.0/public/app/features/alerting/unified/api/alertSilencesApi.ts)
provide the endpoint mapping. Checked 2026-09-19; target writes and HA reconciliation remain
[unverified] until exercised. Refresh after a Grafana/Alertmanager upgrade or conflicting behavior.
