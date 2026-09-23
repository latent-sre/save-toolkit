# Helper exchange

Read before writing an `sre-assistant` assignment or reconciling its return. The parent skill owns
human-facing advice and the board; the helper may interpret an assigned investigation but never
coordinates the incident. The examples are fictional (September 14, 2026; source exports in UTC):
their names and values are never defaults or incident facts.

## Assignment and reconciliation rules

Give the helper one compact assignment:

- Name yourself as invoking caller and return recipient, and the human operational owner separately
  (or unknown). State the question or decision the result will inform.
- Choose **lookup** for exact observations/extraction, or **investigation** for comparison,
  interpretation and testing plausible causes within the named scope. Give the target/environment,
  absolute window/timezone, sources, known file paths/workspace, access limits and relevant prior
  findings with their evidence labels and taint. Do not load the whole advisor into the helper.
- State completion evidence and the caller's limits on sources, reads, time or helpers; for a narrow
  lookup, the named reads and completion condition are enough. Count discovery against the helper
  limit. Pass supplied paths directly; an unresolved path returns as a gap, not a new discovery task.
- Request protected evidence within the helper's grants, never raw authentication output or broader
  command authority. For CF, name the target to confirm; do not ask the helper to change it with
  `cf target -o`/`-s`. An unconfirmed target is a gap. Ask for actual time coverage and retrieval
  limits; available commands or a cropped excerpt do not prove the historical question can be
  answered.

Request useful early findings during an investigation only when the host can deliver interim
updates to this caller. Otherwise ask for a partial return at the next useful boundary and dispatch
the next bounded slice within the remaining task and budget. An acknowledgment or a running helper
is not evidence of a result. Do not promise live progress on an unverified channel.

Reconcile each return against its assignment and source evidence; preserve labels, taint and
unknown times/state. Use supported findings, reject unsupported conclusions, and continue the parent
task without making the human relay the packet or approve routine continuation. For a partial,
blocked or unavailable helper, retain what was learned and use an accessible alternative or continue
independent work; name the missing observation and owner when human access is needed. Helper
completion neither closes the incident nor transfers coordination or change authority. If a helper
overstates cause, coverage or current state, compare it with the examples below before adopting
its claims.

## Example: before an assignment exists

**Human:** "I would like to do a test drill with our new agents and skills. We have issues with Orders."

**Advisor:** "Let's treat this as a simulated incident. What is going wrong with Orders — errors,
slowness, or something else — and when did it start? Are you providing the scenario, or would you
like me to create a fictional one?"

No helper is dispatched yet: nothing names a source to read. If the Orders runbook or service card
listed a Grafana dashboard, the advisor would send the helper to read it for the reported window —
in a drill as in a live incident.

By contrast, "Read the selected exercise exports E1/E2 and compare crashes with the update" is a
bounded assignment and can dispatch immediately. Unknown impact or human-owner identity need
not block that read. Likewise, an authorized runbook step naming a dashboard, question and window
can dispatch without another delegation approval.

## Example: a bounded investigation

**Human:** “I'm Riley, INC-61 owner. Orders/prod was slow 09:40–10:00 UTC. Check E1/E2:
did its config change cause the crashes, and what next?”

**After reading symptom comparisons, dispatch `sre-assistant`:** Invoking caller and return
recipient incident advisor; human owner Riley. Investigation: does the config change explain
Orders/prod's crashes, and which observation would distinguish the remaining explanations?
September 14, 2026, 05:40–06:00 Eastern (EDT), equivalent to 09:40–10:00 UTC in the exports.
Read `evidence/E1.md` and `evidence/E2.md` under the supplied workspace root; those paths are the
fictional exports below. One helper, these two sources, no live reads/changes. Complete when both
records, supported interpretation and limits are returned; a missing record makes the return
partial. Return recipient, status, evidence, gaps/non-actions, parent question and next step.

**Received, not adopted:** To incident advisor; owner Riley; slice complete, incident open.
[sourced: E1] two crashes in that window, aggregate CPU 25%; capture/crash times absent.
[sourced: E2] config update 09:45. No live reads/changes. The helper claims “crashed now; config
caused it; capacity clear” and proposes a fresh read to recover E1's capture time.

**To Riley:**

```text
Times below: September 14, 2026, Eastern (EDT); E2's 09:45 UTC is 05:45 Eastern.
E1: two crashes, aggregate CPU 25%, capture/crash times absent; E2: config 05:45
[sourced]. Neither current state nor ordering/cause follows. Low CPU leaves waits/limits open;
refreshing cannot recover E1's time. Open Apps Manager → Orders/prod → Events for 05:40–06:00
Eastern (09:40–10:00 if the view uses UTC); confirm the view's timezone. Bring back the crash and update
rows with times: a crash before 05:45 Eastern weakens the change as the
trigger; crashes only after it are consistent with cause but do not prove it. Missing coverage
leaves ordering unknown.

Investigation board:

Impact:     🟡 Orders/prod slow 05:40–06:00 [sourced: Riley]; affected share, trend and recovery
            criterion unknown.
Open: config-change trigger — 05:45 update, crash ordering unknown; resource pressure — low CPU
  does not exclude waits/limits. Both unowned; no supported ranking.
Checked: E1 crash count/CPU and E2 update time [sourced]; capture/crash times absent.
Ruled out: none.
Actions: no mitigation reported.
Next: timestamped Events rows for 05:40–06:00 Eastern to compare crashes with the update;
  earlier weakens that trigger, later is consistent but not proof; missing coverage leaves
  ordering unknown.
Follow-ups: Events access/owner unconfirmed; obtain missing timestamps and user-impact scope,
  agree recovery criterion; owners/due times unknown.
```

The advisor continues from the returned facts; Riley does not carry a message between agents.
If another slice fits the existing task and remaining caller limits and the helper has access,
the advisor dispatches it with its own named sources and completion condition. Otherwise the
console request states exactly which evidence Riley can obtain.

For a **lookup** instead — “return E1's reported crash count and CPU; do not assess the cause” —
the helper returns two crashes and 25% aggregate CPU, their labels and missing capture/crash times.
It does not turn that lookup into the investigation above. An immediate material risk is still
reported to the caller.

**Incomplete or conflicting dispatch:** a dispatch that omits the caller's identity, asks the
helper to switch `cf target`, asks for raw authentication output, or asks a historical question of
a cropped `head`/`tail` excerpt gets back a return that rejects those parts and names the gap. A
last-20-lines excerpt spanning 10:05–10:10 cannot exclude crashes at 09:40–10:00; ask for records
with known coverage instead.
