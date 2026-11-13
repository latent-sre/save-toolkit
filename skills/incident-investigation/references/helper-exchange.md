# Helper exchange

The parent skill owns advice and the board; `sre-assistant` owns only its assigned read-only
question. Examples below are fictional (September 14, 2026; exports in UTC), never incident facts
or defaults.

## Contents

- [Rules](#assignment-and-reconciliation-rules)
- [Before dispatch](#example-before-an-assignment-exists)
- [Bounded investigation](#example-a-bounded-investigation)

## Assignment and reconciliation rules

- Name yourself as invoking caller and return recipient, and the human operational owner separately
  (or unknown). State the question or decision the result will inform.
- Choose **lookup** for exact observations/extraction, or **investigation** for comparison,
  interpretation and testing plausible causes within the named scope. Give the target/environment,
  absolute window/timezone, sources, known file paths/workspace, access limits and relevant prior
  findings. Do not load the whole advisor into the helper.
- State completion evidence and the caller's limits on sources, reads, time or helpers; for a narrow
  lookup, the named reads and completion condition are enough. Count discovery against the helper
  limit. Dispatch a supplied file path directly: copy an absolute path, or pass the relative path
  together with its supplied workspace root. Joining those strings needs no tool call. Do not
  rediscover or preflight that file in the parent; the helper's permitted read establishes access
  and returns a gap if it fails. Your own tool set may be narrower than the helper's: call only
  tools exposed to you in this session, never a familiar but unavailable discovery tool.
- Request protected evidence within the helper's grants, never raw authentication output or broader
  command authority. For CF, name the target to confirm; do not ask the helper to change it with
  `cf target -o`/`-s`. An unconfirmed target is a gap. Ask for actual time coverage and retrieval
  limits; available commands or a cropped excerpt do not prove the historical question can be
  answered.

Request interim findings only when the host can deliver them to this caller; otherwise request a
partial return at a useful boundary, then dispatch within the remaining task/budget. A running
helper or acknowledgment is not a result; do not promise progress on an unverified channel.

Reconcile each return against its assignment and source evidence; preserve unknown
times/state. Before declaring that a source lacks a reported statement, inspect its relevant full
record or complete tool result. An abbreviated quotation does not establish what the source omits.
If the original is unavailable, keep the claim attributed and unverified rather than declaring it
false. Separate a source's limits from the parent's accumulated evidence. If the human reported an
event time but the inspected file gives only collection time, retain the reported event time as
human-supplied; the file does not independently confirm it. That omission is not a correction of
the human's report. Supersede prior evidence only with an explicit correction or a reconciled
contradiction, retaining source and scope. Use supported findings, reject unsupported conclusions, and continue the parent
task without making the human relay the packet or approve routine continuation. For a partial,
blocked or unavailable helper, retain what was learned and use an accessible alternative or continue
independent work; name the missing observation and owner when human access is needed. Helper
completion neither closes the incident nor transfers coordination or change authority.

## Example: before an assignment exists

“We have issues with Orders; let's run a drill” names no source or symptom. Keep intake with the
advisor: ask for the simulated symptom/window or offer a labelled fictional scenario. A runbook or
service card naming a dashboard permits a read for the reported window, in a drill or live incident.

“Read selected exercise exports E1/E2 and compare crashes with the update” is bounded and can
dispatch immediately. Unknown impact or human-owner identity need not block that read; an authorized
runbook step naming a dashboard, question and window needs no extra delegation approval.

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
The helper's claims about current state, cause and cleared capacity exceed its evidence.
Establish crash ordering from timestamped history; a fresh snapshot cannot recover the old
export's missing time. All times below are September 14, 2026, Eastern (EDT).

Investigation board:

Impact:     🟡 Orders/prod slow 05:40–06:00 [sourced: Riley]; affected share, trend and recovery
            criterion unknown.
Open: config-change trigger — crash ordering unknown; resource pressure — aggregate CPU leaves
  waits/limits open. Both unowned; no supported ranking.
Checked: O1 [sourced: E1] | Orders/prod | two crashes, aggregate CPU 25% | capture/crash times unknown
  | report window 05:40–06:00, CPU window unknown.
  O2 [sourced: E2] | Orders/prod | config update 05:45 (09:45 UTC), effect time unknown.
Ruled out: none.
Actions: no mitigation reported.
Next: request the app-event owner's Orders/prod crash/update rows for 05:40–06:00 Eastern
  (09:40–10:00 UTC), including coverage and timezone; with confirmed view access, use Apps Manager
  → Orders/prod → Overview → app events. Crashes before confirmed change exposure exclude it as
  their initiator; later crashes remain compatible, not proof. Then compare revisions and crash
  details; missing coverage leaves ordering open with that owner.
Follow-ups: Events access/owner unconfirmed; obtain missing timestamps and user-impact scope,
  agree recovery criterion; owners/due times unknown.
```

Dispatch a further slice only within the existing task, remaining limits and helper access, with
named sources and completion evidence. Otherwise give Riley the exact console evidence request;
do not make Riley relay packets between agents.

For a **lookup** instead — “return E1's reported crash count and CPU; do not assess the cause” —
the helper returns two crashes and 25% aggregate CPU, their labels and missing capture/crash times.
It does not turn that lookup into the investigation above. An immediate material risk is still
reported to the caller.

**Incomplete or conflicting dispatch:** a dispatch that omits the caller's identity, asks the
helper to switch `cf target`, asks for raw authentication output, or asks a historical question of
a cropped `head`/`tail` excerpt gets back a return that rejects those parts and names the gap. A
last-20-lines excerpt spanning 10:05–10:10 cannot exclude crashes at 09:40–10:00; ask for records
with known coverage instead.
