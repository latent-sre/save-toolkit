# Mitigation selection

Recommend reversible mitigation or reconcile interrupted attempts; the human responder owns
investigation, ITO approves in the existing TLC, and the human release owner executes. Exclude
suspected security compromise or integrity loss (preserve state, run no restart/redeploy, escalate
to the human security incident owner).

## Runtime confirmation and safe reversible actions

Confirm serving runtime from the service card, route evidence, or owner first. For Cloud Run
(`gcp-ops`), map the failing hostname/path to the active revision and inspect effective routing vs
last known-good before changing traffic. Disabling a feature flag through its owner's control can
qualify for the fast path in a declared incident; dependency failover or load shedding follows its
owner procedure under the full gate (dropping queued/in-flight work is destructive).

### Confirmed PCF apps (Apps Manager primary; `cf` CLI v8 fallback)

Open the foundation, org, and space in Apps Manager matching the approved packet (UI controls vary by
foundation; if absent or unclear, hand the release owner the target, action, backout, and readback
for their approved pipeline/CLI — responders need not install `cf`). Never substitute **Restage** for
an existing-droplet restart. Before classifying `cf restart` as fast-path, confirm it reuses the
current staged droplet; an unstaged package or unknown droplet state requires the full gate (other
confirmed already-live rollback paths stay eligible).

| Situation | Action & gate (declared incident) | Apps Manager path | CLI / pipeline fallback (release owner confirms first) |
|---|---|---|---|
| Errors at bad deploy; prior app still live | Route remap (**Fast path**) | Inspect both apps' **Routes** (host, domain, path); map previous / unmap current | `cf map-route <prev> <domain> --hostname <app>` then `cf unmap-route <curr> ...` (confirm live/previous apps explicitly) |
| Bad deploy with revisions enabled | Revision rollback (**Fast path**) | **Revisions** -> last good row (confirm **Redeploy** behavior with owner) | `cf revisions <app>` (row marked `deployable`) -> `cf rollback <app> --version <n>`. Creates a NEW higher revision `Rolled back to revision <n>`, reverting any env var changed since `<n>` (including mid-incident `set-env`), without changing bindings, routes, or instance count |
| Rollout/canary still active | Abort active deploy (**Full gate**) | Confirm active deployment & pipeline cancel control | `cf cancel-deployment <app>` only while active — cancelling an active rollback restores the bad droplet! Does not revert vars/bindings |
| Hung/wedged/leaking instances, no recent change | Restart stopgap (**Fast path** only if per-instance or rolling + serving headroom + existing droplet; else **Full gate**) | **Overview** -> confirm process/instance scope; never use Restage | Preferred: `cf restart-app-instance <app> <i> --process <type>` (0-based index, verify vs UI row) when survivors have headroom to hold one instance back for diagnostics. Whole-app `cf restart` drops all instances during startup (outage on single-instance/saturated apps -> full gate); `--strategy rolling` restarts non-web processes all at once after web |
| Bad startup env var | Revert env + restart (**Full gate**) | **Settings** privately (never copy secret values into packet) | `cf set-env <app> KEY <old>` + `cf restart <app> --strategy rolling` (confirm consumer and droplet state first) |
| Bad buildpack / staging config | Revert + restage (**Full gate**) | Approved pipeline / **Restage** (rebuilds droplet) | `cf set-env <app> KEY <old>` + `cf restage <app>` |
| Load/capacity saturation | Scale out (**Fast path** instance count only) | **Overview** -> selected process **Scale** | `cf scale <app> --process <type> -i <count>` (CLI defaults to `web`). Unbinds App Autoscaler — add Follow-up to re-bind |

## Six decision rules

1. **Reversible first:** Route remap / flag flip before restarts or irreversible queues/deletes.
2. **Disposition perishable evidence:** Restart/restage discard heap, thread, and connection state;
   scale-in drops instances. Before proposing, ask for capture or an explicit owner waiver; for
   reported actions record capture, explicit waiver, or `unknown` (missing capture is never a
   waiver). Hold one instance back when headroom exists; unknown headroom blocks fast-path restart.
3. **One change at a time; separate execution, effective state, and recovery:** Compare signals
   between actions. Evaluate user recovery strictly by the quoted agreement (exact operators,
   tolerances, population, window, and user confirmation). Accept a qualifying window even if it
   began before the action unless post-change start is required; never use readback time as start
   time. One green sample does not prove sustained recovery. `sre-assistant` runs read-only checks
   only.
4. **Restart is not root-cause closure:** Keep causal hypotheses as owned follow-ups; `observability-engineer` owns post-incident detection improvements.
5. **Record decisions with source, owner, and time** on the board or helper return packet.
6. **Bind approval packet:** Target, artifact/config, command, blast radius, verification window &
   stop criteria, rollback, human executor, monitoring owner, approver, and capture/waiver status.
   In a declared incident, `production-change-gate` fast path governs blockers and ITO's TLC
   envelope governs validity/identity (expired or outside-envelope actions need new approval).

## Read back an interrupted attempt

Reconcile unknown execution or disconnects before retrying: confirm effective flag/route/Cloud Run
revision, or for PCF rollback verify completed deployment, intended droplet across instances, and any
env-based mitigation the rollback might have reverted (creating revision `n+k` is expected; do not
expect the revision number to equal `<n>`). Current state proves neither when a change landed nor
causality; missing action readback is a history/causality gap and never erases an independent
user-recovery receipt.
