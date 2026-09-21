# Worked helper exchange

Use for dispatch and reconciliation, including when a helper overstates the supplied evidence.
The parent skill owns human-facing advice and the board; the helper may interpret an assigned
investigation without taking incident coordination. Fictional records on September 14, 2026;
source exports use UTC.
Names/values are not defaults.

## Before an assignment exists

**Human:** "I would like to do a test drill with our new agents and skills. We have issues with Orders."

**Advisor:** "Let's treat this as a simulated incident. What is going wrong with Orders — errors,
slowness, or something else — and when did it start? Are you providing the scenario, or would you
like me to create a fictional one?"

No helper is dispatched yet. The advisor does not turn this into an agent evaluation or search
`evals/`, examples, or design docs to manufacture Orders incident evidence. These worked records
are instructional examples unless the human explicitly selects them for the drill.

By contrast, "Read the selected exercise exports E1/E2 and compare crashes with the update" is a
bounded assignment and can dispatch immediately. Unknown impact or human-owner identity need
not block that read. Likewise, an authorized runbook step naming a dashboard, question and window
can dispatch without another delegation approval.

## A bounded investigation

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
refreshing cannot recover E1's time. Open Apps Manager → Orders/prod → Events for 05:40–06:00 Eastern
(09:40–10:00 if the view uses UTC); confirm the view's timezone. Bring back the crash and update
rows with times: a crash before 05:45 Eastern weakens the change as the
trigger; crashes only after it are consistent with cause but do not prove it. Missing coverage
leaves ordering unknown.

Impact: Orders/prod slow 05:40–06:00 [sourced: Riley]; affected share, trend and recovery
  criterion unknown.
Open: config-change trigger — 05:45 update, crash ordering unknown; resource pressure — low CPU
  does not exclude waits/limits. Both unowned; no supported ranking.
Checked: E1 crash count/CPU and E2 update time [sourced]; capture/crash times absent.
Ruled out: none.
Actions: no mitigation reported.
Next: timestamped Events rows for 05:40–06:00 Eastern to compare crashes with the update; earlier weakens
  that trigger, later is consistent but not proof; missing coverage leaves ordering unknown.
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

**Incomplete or conflicting dispatch:** An agent dispatch names Riley as human owner but omits
its own identity and asks, "switch with `cf target -o prod -s prod`, return raw output, and use
`head`/`tail` to answer whether crashes occurred at 09:40–10:00 UTC." The helper returns to
`invoking agent (identity unspecified)`, retaining Riley as owner. It rejects target-changing
flags and unprotected authentication output, continues any permitted evidence reads, and names
the access gap. A supplied last-20-lines excerpt spanning 10:05–10:10 establishes only what
those lines show. It cannot exclude crashes at 09:40–10:00; even timestamps spanning the window
do not prove completeness when rows were cropped, sampled, retained selectively, or unpaginated.
The return asks the caller for protected records with known coverage, rather than claiming the
proposed commands are sufficient. The caller reconciles that limitation and continues the task.

For a slower investigation, an actual host-supported interim channel may carry the useful E1
findings while E2 is pending. Without that channel, the helper returns the useful partial result,
names E2 as outstanding, and the advisor continues or dispatches the remaining slice. Neither a
launch acknowledgment nor completion of E1 establishes E2's contents or a completed investigation.

**Riley later supplies** aligned Orders/prod instance 3, pool P samples, 09:50–09:55 UTC:
active/limit 20/20, waiters 6 throughout [sourced: E3].

**Advisor:**

```text
Times below: September 14, 2026, Eastern (EDT); E3's 09:50–09:55 UTC is 05:50–05:55 Eastern.
That supports pressure here, not its trigger or other instances. Spare capacity
would weaken it; missing counts leave it unknown. Ask the owner for this scope's request timing
and calls/request: slow calls versus extra calls distinguish connection occupancy. Unavailable
evidence stays open; pressure is not recovery or restart approval.

Impact: Orders/prod slow 05:40–06:00 [sourced: Riley]; affected share, trend and recovery
  criterion still unknown.
Open: instance-3 pool-P pressure supported by E3; slow calls versus extra calls may explain it;
  the config-change trigger remains unresolved. Owners unassigned; no causal ranking established.
Checked: E3 active/limit 20/20, waiters 6 for 05:50–05:55 [sourced: Riley]; E1 crash count/CPU,
  E2 config 05:45 [sourced]. E1 still lacks capture/crash times.
Ruled out: none.
Actions: no mitigation reported.
Next: request instance-3 pool-P duration and calls/request for 05:50–05:55 Eastern from its evidence
  owner (unidentified) to distinguish slow calls from extra calls; both may coexist. Missing
  observations leave the mechanism open.
Follow-ups: Events ordering check still outstanding; acquire its timestamps without reopening
  completed export reads. Evidence owners/due times, impact scope and recovery criterion unknown.
```
