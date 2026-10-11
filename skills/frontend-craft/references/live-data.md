# Live data without losing the investigation

Read for live views, paused history, reconnects and linked live selection. Authentication,
identity changes and transport mechanics belong to [sessions](./sessions.md); request identity,
retry ownership and caching belong to [API](./api.md). Use those contracts here.

## Keep the view's context explicit

Related charts, tables and timelines share service, environment and time range. Distinguish
hover from persistent selection, and show how to clear it. Bind every response to that scope;
cancel or ignore obsolete work so an earlier range cannot replace the currently selected one.
Opening detail and returning keeps the investigation's place. Non-sensitive context that must
survive reload belongs in the URL; credentials and sensitive query content do not.

Separate live-following from paused or historical inspection. Incoming data must not move the
selected window, row or event while someone is examining it. Show the selected time boundary
and any waiting updates; resuming live is a deliberate action. A reconnect or tab becoming
visible must not silently resume a paused view.

## Report what the feed actually establishes

Show connecting, current, stale, reconnecting and failed states from the real connection and
data age. A connected socket alone does not prove fresh data. Keep usable prior data visible
with its age when refresh fails; a failed panel must not blank independent panels.

After a gap, reconcile with the server's current state using the session reference's transport
rules. Deduplicate and order events using the API's actual identifiers or sequence contract;
do not invent exactly-once delivery. When ordering or completeness is unknown, expose that limit.
Keep related panels' range and freshness visible if they cannot refresh atomically.

Preserve missing intervals as gaps, separate from zero. State units, timezone, aggregation and
sampling resolution so linked series are comparable. Temporal coincidence is not a causal link.
Bound retained data and pending redraws as the sessions reference requires; show when older
samples were dropped, and do not evict an inspected selection without explaining how to recover it.

## Completion exercise

Select scope A, switch to B, and deliver B's response before A's. B must remain selected and
rendered. Pause at an event, deliver updates and simulate a reconnect: the selected historical
window must remain stable until resume. Introduce a missing interval and a failed panel; verify
gap, data-age and failure displays without disabling unaffected work. Repeat the selection and
resume path by keyboard, with bounded sample volume and realistic update frequency.
