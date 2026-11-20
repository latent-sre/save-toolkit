# Temporary silences

Recurring mute timings are a different operation. Ending a silence can notify still-firing alerts
again. Console: Alerts & IRM → Alerting → Silences (preview shows only *currently firing* instances,
not future matches). The helper's `silences` / `silences --id <uuid>` reads only the built-in
Grafana Alertmanager.

## Prepare, apply, verify

1. **Bind scope:** Alertmanager, exact matchers, absolute UTC `startsAt`/`endsAt` (resolve a
   duration right before writing), human owner and reason. Never infer the creator from the
   service-account name; ask when expiry or environment is missing.
2. **Check blast radius:** show currently affected instances and existing silences. An empty
   preview does not prove a regex, negative or missing-label matcher harmless; never broaden a
   failed matcher to make it match.
3. **Update or expire** only the exact silence ID, preserving its prior body and its owner's
   silences; for a create, check that no identical active or pending silence exists.
4. **Write once:** these endpoints have no compare-and-swap, so coordinate a single-writer window
   for shared silences, re-read immediately before writing, and stop on drift.
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
