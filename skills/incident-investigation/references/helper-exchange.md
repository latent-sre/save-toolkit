# Worked helper exchange

Read when a helper overstates the supplied evidence. The parent skill owns authority and the
board contract. Fictional records; names/values are not defaults.

**Human:** “I'm Riley, INC-61 owner. Orders/prod was slow 09:40–10:00 UTC. Check E1/E2:
did its config change cause the crashes, and what next?”

**After reading symptom comparisons, dispatch `sre-assistant`:** Caller incident advisor; human
owner Riley; Orders/prod, 09:40–10:00 UTC. Inspect only E1/E2 for crash/change ordering; complete
when both exports and limits are reported. Return recipient, status, evidence, gaps/non-actions,
parent question and next step. No live reads/changes.

**Received, not adopted:** To incident advisor; owner Riley; slice complete, incident open.
[sourced: E1] two crashes in that window, aggregate CPU 25%; capture/crash times absent.
[sourced: E2] config update 09:45. No live reads/changes. The helper claims “crashed now; config
caused it; capacity clear” and proposes a fresh read to recover E1's capture time.

**To Riley:**

```text
E1: two crashes, aggregate CPU 25%, capture/crash times absent; E2: config 09:45
[sourced]. Neither current state nor ordering/cause follows. Low CPU leaves waits/limits open;
refreshing cannot recover E1's time. Open Apps Manager → Orders/prod → Events for 09:40–10:00 and
bring back the crash and update rows with times: a crash before 09:45 weakens the change as the
trigger; crashes only after it are consistent with cause but do not prove it. Missing coverage
leaves ordering unknown.

Impact: Orders/prod slow 09:40–10:00 UTC [sourced: Riley]; affected share, trend and recovery
  criterion unknown.
Open: config-change trigger — 09:45 update, crash ordering unknown; resource pressure — low CPU
  does not exclude waits/limits. Both unowned; no supported ranking.
Checked: E1 crash count/CPU and E2 update time [sourced]; capture/crash times absent.
Ruled out: none.
Actions: no mitigation reported.
Next: timestamped Events rows for 09:40–10:00 to compare crashes with the update; earlier weakens
  that trigger, later is consistent but not proof; missing coverage leaves ordering unknown.
Follow-ups: Events access/owner unconfirmed; obtain missing timestamps and user-impact scope,
  agree recovery criterion; owners/due times unknown.
```

**Riley later supplies** aligned Orders/prod instance 3, pool P samples, 09:50–09:55 UTC:
active/limit 20/20, waiters 6 throughout [sourced: E3].

**Advisor:**

```text
That supports pressure here, not its trigger or other instances. Spare capacity
would weaken it; missing counts leave it unknown. Ask the owner for this scope's request timing
and calls/request: slow calls versus extra calls distinguish connection occupancy. Unavailable
evidence stays open; pressure is not recovery or restart approval.

Impact: Orders/prod slow 09:40–10:00 UTC [sourced: Riley]; affected share, trend and recovery
  criterion still unknown.
Open: instance-3 pool-P pressure supported by E3; slow calls versus extra calls may explain it;
  the config-change trigger remains unresolved. Owners unassigned; no causal ranking established.
Checked: E3 active/limit 20/20, waiters 6 for 09:50–09:55 [sourced: Riley]; E1 crash count/CPU,
  E2 config 09:45 [sourced]. E1 still lacks capture/crash times.
Ruled out: none.
Actions: no mitigation reported.
Next: request instance-3 pool-P duration and calls/request for 09:50–09:55 from its evidence
  owner (unidentified) to distinguish slow calls from extra calls; both may coexist. Missing
  observations leave the mechanism open.
Follow-ups: Events ordering check still outstanding; acquire its timestamps without reopening
  completed export reads. Evidence owners/due times, impact scope and recovery criterion unknown.
```
