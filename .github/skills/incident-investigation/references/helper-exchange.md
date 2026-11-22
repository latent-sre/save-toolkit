# Helper exchange

`incident-investigation` owns responder advice and the board; `sre-assistant` owns only its assigned
read-only question and returns findings to the invoking caller. Examples below are fictional (Sep
14, 2026; exports in UTC), never incident facts.

## Assignment and reconciliation rules

- **Dispatch shape:** Name yourself as invoking caller/return recipient and the human operational
  owner separately (`unknown` if missing). Distinguish **lookup** (exact read/extract, no causal
  verdict) from **investigation** (compare hypotheses within scope). Specify question/decision,
  target/environment, **absolute UTC window**, sources, workspace root/paths, access limits, prior
  findings, and explicit completion evidence.
- **Direct file paths & narrow reads:** Pass supplied absolute paths (or relative paths + workspace
  root) straight to the helper; never preflight-check or rediscover them in the parent or invoke
  tools absent from your session. Request protected observations inside grants, never `cf target -o/-s`,
  raw secrets/auth dumps, or cropped `head`/`tail` excerpts to settle historical gaps (ask for full
  covered records + retention/truncation limits).
- **Boundaries & reconciliation:** Request interim returns only if host-supported; a running helper
  or ack is not a result. Inspect full tool outputs before claiming an omitted statement; an unconfirmed
  omission in one source does not retract an independently human-supplied event time (keep both
  attributed and note collection vs event clock gaps). Use supported findings, reject unsupported
  leaps, continue advising without making the human relay agent packets, and preserve human ownership.

## Intake vs. dispatch boundaries

- Vague opener (`"we have issues with Orders; let's run a drill"`): keep intake with the advisor and
  ask for symptom/window (or offer a labelled fictional drill); do not dispatch or search eval
  fixtures. Runbooks/service cards naming a dashboard authorize dispatching a bounded dashboard read
  without asking delegation approval.
- Bounded export ask (`"Read E1/E2 and compare crashes with the update"`): dispatch immediately even
  if impact share or human owner is still unknown.
- Dispatches omitting caller identity, requesting `cf target` switches, asking for auth dumps, or
  querying an uncovered tail excerpt must be rejected/flagged with their explicit gaps.

## Example: bounded investigation and reconciliation

**Human:** "I'm Riley, INC-61 owner. Orders/prod was slow 09:40–10:00 UTC. Check E1/E2: did its
config change cause the crashes, and what next?"

**Dispatch `sre-assistant`:** Invoking caller/return recipient: incident advisor; human owner:
Riley. Investigation: does `evidence/E2.md`'s config update explain `evidence/E1.md`'s Orders/prod
crashes in `2026-09-14 09:40–10:00 UTC` (`05:40–06:00 EDT`), and which check discriminates next?
Read only those two files under `<workspace_root>`; zero live reads/changes. Complete when both
records, supported interpretation, and coverage limits return.

**Helper return (contains overclaim to reject):** Slice complete. `[sourced: E1]` 2 crashes in
window, aggregate CPU 25%, capture/crash times absent. `[sourced: E2]` config update 09:45 UTC.
Helper claims "crashing now; config caused it; capacity clear" and suggests a live snapshot to find
E1's missing crash time.

**Reconciled reply to Riley (rejecting unsupported leaps, keeping ET display):**

```text
The helper's claims of current crashes, config cause, and cleared capacity exceed E1/E2: establish
crash timestamps from history (a live snapshot cannot recover missing export times). All times ET:

Investigation board:

Impact:     🟡 Orders/prod slow 05:40–06:00 [sourced: Riley]; affected share, trend, and recovery criterion unknown.
Open:       config-change trigger (crash timestamps unknown); resource saturation (aggregate 25% CPU leaves pool waits/limits open). Unowned; no supported ranking.
Checked:    O1 [sourced: E1] | Orders/prod | 2 crashes, aggregate CPU 25% | capture/crash times unknown | window 05:40–06:00, CPU window unknown.
            O2 [sourced: E2] | Orders/prod | config update 05:45 (09:45 UTC), rollout exposure time unknown.
Ruled out:  none.
Actions:    none applied.
Next:       request Orders/prod crash & app-event rows for 05:40–06:00 ET (09:40–10:00 UTC) with zone/coverage from the event owner (Apps Manager -> Orders/prod -> Overview -> app events if view access confirmed). Crashes before config exposure exclude config as initiator; later crashes keep both open. Missing coverage leaves ordering unknown.
Follow-ups: clarify Events access/owner, missing timestamps, impact share, and recovery criterion; owners/due times unknown.
```
