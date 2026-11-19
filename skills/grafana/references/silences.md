# Temporary silences

Recurring mute timings are a different operation. Ending a silence can notify still-firing alerts
again. Console: Alerts & IRM → Alerting → Silences (preview shows only *currently firing* instances,
not future matches). The helper's `silences` / `silences --id <uuid>` reads only the built-in
Grafana Alertmanager.

## Prepare, apply, verify

1. **Bind scope:** instance/org, Alertmanager, service/environment or rule UID, exact matchers,
   explicit UTC `startsAt`/`endsAt` (resolve durations to absolute UTC right before writing), human
   owner, and reason/change reference. Never infer creator from the service-account name. Missing
   expiry or ambiguous environment → ask first.
2. **Check blast radius:** inspect rule/alert labels and existing silences; show currently affected
   instances and wider matcher scope. Prefer exact service/environment or rule-specific matchers.
   Explain regex, negative, or missing-label matchers before use; an empty preview does not prove a
   matcher is harmless. Never broaden a failed matcher to make it match.
3. **Update / early expiry:** read the exact silence ID and preserve its prior body; never modify
   another owner's silence merely because it overlaps. For create, verify no identical active/pending
   silence already covers it.
4. **Coordinate and write once:** show target, matchers, UTC window, affected scope, and recovery.
   These endpoints have no compare-and-swap — coordinate a single-writer window for shared silences,
   re-read immediately before writing, and stop on drift.
5. **Read back and verify:** fetch the returned ID from the same Alertmanager and verify matchers,
   timestamps, owner/comment, and active/pending/expired state.
   - **ID replacement rule:** an update keeps its ID *only* when unexpired with unchanged matchers
     and either active (unchanged `startsAt`, future `endsAt`) or pending (future `startsAt`).
     Otherwise Alertmanager expires the original and returns a **new** ID — read both IDs.
   - For early expiry, also check overlapping silences before claiming notifications can resume.
     Neither create nor expiry proves delivery or service recovery.
6. **Rollback:** verify fresh state matches operation-written state before undoing (stop on
   intervening edits). Undo create by expiring the returned ID; undo an ID-replacing edit by
   expiring the new ID and recreating the prior scope within its still-valid window (an expired
   silence cannot be unexpired); undo an in-place edit by re-applying the captured body. Lost
   notifications cannot be recovered.

## Agent API mapping (Grafana 13.3)

| Operation | Path under the trusted Grafana origin |
|---|---|
| List | `GET /api/alertmanager/<am>/api/v2/silences` |
| Read one | `GET /api/alertmanager/<am>/api/v2/silence/<id>` |
| Create or update | `POST /api/alertmanager/<am>/api/v2/silences` |
| End early | `DELETE /api/alertmanager/<am>/api/v2/silence/<id>` |

`<am>` is `grafana` for the built-in Alertmanager or the discovered datasource UID for an external
one (never its display name). Create omits `id`; update sends existing `id` and can return a new
`silenceID` (reads use `id`; unknown `id` returns NotFound). Rule-specific silences can use
`__alert_rule_uid__=<uid>` where the Alertmanager carries that label; Grafana rejects updating that
matcher with `400` (create a new silence instead).

On timeout after POST, follow the parent's [UNKNOWN rule](../SKILL.md#return-the-result): do not
create a duplicate; read the returned ID if known or list silences on the same Alertmanager and
reconcile matchers/window/owner/comment.
