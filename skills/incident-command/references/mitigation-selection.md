# Mitigation selection

Use this reference when the incident commander must choose among rollback, route remap, restart,
scale, flag, or dependency responses. It prepares a recommendation and approval packet; it never
executes a command.

Suspected compromise, data integrity loss, or another security event is excluded. Preserve evidence
and follow the human security incident owner's exact direction instead.

## Pick the fastest safe, reversible action

Stopping user pain comes before root cause. Prefer an action that can be undone in seconds and make
the decision explicit. The responder, advised by `incident-investigation`, recommends; `sre-assistant`
reports evidence and stops; a human release owner executes.

The commands below are planning examples, not current-foundation evidence. They remain
`[unverified]` until the human release owner validates the exact target, capability, command, and
rollback.

Before classifying `cf restart` as fast-path mitigation, confirm that it reuses the current staged
droplet without building an artifact. An unstaged most-recent package can make restart stage new
bytes; that requires the full release and production gates. Unknown package/droplet state blocks
fast-path classification, not other confirmed already-live rollback options.

| Situation | Mitigation | Planning example — human confirms first |
|---|---|---|
| Errors begin at a bad deploy and the previously live app still exists | Blue-green rollback by remapping the stable production route to the previous app | `cf map-route <previous-app> <domain> --hostname <app>` then `cf unmap-route <current-app> …`; blue and green are roles, not fixed names, so first identify the live app with `cf apps` |
| Bad deploy with revisions enabled | Revision rollback | `cf revisions <app>` to identify the last good revision, then `cf rollback <app> --version <n>` |
| Rolling or canary deployment is still in progress | Abort the active deployment | `cf cancel-deployment <app>` works only while a deployment is active; after completion use revision rollback instead |
| Instances are hung, wedged, or leaking with no recent change | Restart as a time-buying stopgap | `cf restart <app>` or `cf restart-app-instance <app> <i>`; this discards the state that would explain the hang, so decision rule 2 applies |
| Bad variable read only by the app at process start | Revert the value and restart with confirmed existing-droplet reuse | `cf set-env <app> KEY <old>` then `cf restart <app>`; confirm the variable's consumer and package/droplet state first |
| Bad buildpack or staging-time configuration | Revert and restage through the full release and production gates | `cf set-env <app> KEY <old>` then `cf restage <app>` creates a new droplet; it is not fast-path rollback. If the consumer is unknown, establish it before choosing restart or restage |
| Load or capacity saturation | Scale out | `cf scale <app> -i <more>` |
| Bad behavior is feature-flag gated | Disable the flag | Use the owning flag system; no deploy is required |
| Downstream dependency is failing | Fail over, degrade gracefully, or shed load | Follow the dependency's approved operating evidence |

## Decision rules

1. **Reversible first.** Prefer route remap or flag flip over a change that cannot be undone quickly.
2. **Name the perishable evidence before the action destroys it.** Restart and restage discard
   heap, thread, and connection state; scale-in discards the instance holding it; rollback
   discards the running bad build. None of it is recoverable later, so the incident can end with
   service restored and the cause permanently unprovable. State what the chosen action destroys,
   then either capture it or record it as knowingly traded for speed with the deciding human
   named. When the action is instance-scoped, holding one instance back unrestarted preserves
   the evidence for the cost of one instance's recovery.
3. **One change at a time.** The responder, or another authorized human, watches the golden
   signals for 1–2 minutes before the next action, so the response can attribute it. A
   dispatched `sre-assistant` read covers only `cf app`, `cf events`, `cf logs --recent`.
4. **Restart is not root-cause closure.** If restart restores service, preserve the leak, poison
   input, or dependency hypothesis and continue investigation with the human on-call, advised by
   `incident-investigation`.
5. **Record every decision and result in UTC** in the IC-owned timeline.
6. **Confirm before executing.** The packet names the exact target, change, command, blast radius,
   verification window, rollback, human executor, and approving decider. It also records the
   perishable diagnostic evidence captured or knowingly forgone — recorded, never gating. Missing
   diagnostic capture does not delay the approved reversible mitigation; required target, artifact,
   approval, and safety evidence still gates it. The `production-change-gate` incident fast path
   remains the closed list of what blocks covered execution.

The approval shape is the `production-change-gate` incident fast path: human confirmation of the
exact command or an IC-approved bounded envelope, blast radius, backout, and named decider. Other
gate records reconcile after resolution and never delay a reversible mitigation. Shipping a new
artifact, and every destructive or access-path action, remain on the full gate with required
recovery evidence.

After mitigation, confirm user impact has ended but keep the incident open through the sustained
recovery window. The human on-call continues root-cause work with `incident-investigation`
(dispatching the typed `sre-assistant` agent for a bounded read-only slice), the human release
owner owns any fix-forward execution, and the responder owns recovery evidence; `observability-engineer`
owns detection changes after resolution.
