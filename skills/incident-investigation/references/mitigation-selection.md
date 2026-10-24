# Mitigation selection

Recommend mitigation or reconcile an attempted change; the responder owns the investigation,
ITO approves in the existing TLC, and the human release owner executes. This reference grants
neither incident command nor execution authority.

## Contents

- Pick the fastest safe, reversible action
- Decision rules
- Read back an interrupted attempt

Suspected compromise, data integrity loss, or another security event is excluded. Preserve evidence
and follow the human security incident owner's exact direction instead.

## Pick the fastest safe, reversible action

Start in Apps Manager: open the app from its foundation, org, and space, and match that identity to
the approved packet. The human paths below are conditional navigation from the TAS 2.12 guide;
controls, permissions, and revision support on this foundation remain unconfirmed. If a control
is absent or its effect is unclear, give the release owner the same target, action, backout, and
readback request for their approved pipeline or CLI. The responder need not install `cf`.

UI actions and CLI commands are planning examples until the human release owner validates their
exact target, capability, effect, and rollback. A restage control is not an existing-droplet restart.

Before classifying `cf restart` as fast-path mitigation, confirm that it reuses the current staged
droplet without building an artifact. An unstaged most-recent package can make restart stage new
bytes; that requires the full release and production gates. Unknown package/droplet state blocks
fast-path classification, not other confirmed already-live rollback options.

| Situation | Mitigation | Human path | CLI or pipeline fallback — release owner confirms first |
|---|---|---|---|
| Errors begin at a bad deploy and the previously live app still exists | Remap the production route to the previous app | Inspect both apps' **Routes**, including hostname, domain, path, and current mappings; use the confirmed map/unmap controls | `cf map-route <previous-app> <domain> --hostname <app>` then `cf unmap-route <current-app> …`; identify the live/previous apps without assuming blue/green names |
| Bad deploy with revisions enabled | Revision rollback | Inspect **Revisions** and the last good row; use **Redeploy** only when the owner confirms it performs the intended rollback | `cf revisions <app>` — pick a row marked `deployable` — then `cf rollback <app> --version <n>`. Rollback redeploys that revision's droplet, environment variables, and start command as a NEW revision described `Rolled back to revision <n>`, so it also reverts any variable changed since `<n>` (including a mid-incident `set-env`); it does not touch service bindings, routes, or instance count |
| Rolling or canary deployment is still in progress | Abort the active deployment | Have the release owner confirm the active deployment and its pipeline cancellation path; a revisions list alone does not prove deployment completion | `cf cancel-deployment <app>` only while active (a rollback in progress is itself an active deployment — cancelling it puts the bad droplet back); after completion use revision rollback. Cancellation does not revert variables or service bindings |
| Instances are hung, wedged, or leaking with no recent change | Restart as a time-buying stopgap | On **Overview**, confirm the affected process/instance and whether the control restarts one instance or the whole app; otherwise request the release owner's per-instance path. Do not substitute **Restage** | `cf restart-app-instance <app> <i> --process <process-type>` for the affected instance (preferred when the remaining instances have serving headroom for the restarted instance's share, which keeps rule 2's held-back instance possible; a single-instance app or already-saturated survivors have no such headroom — then any restart is an outage for its duration and needs ITO's explicit approval, not a fast-path classification). `<i>` is zero-based; confirm the console row's matching CLI index rather than assuming "instance #3" means index 3. Whole-app `cf restart <app>` stops every instance before starting any — downtime for the whole start-up window; every v8 CLI supports `--strategy rolling`, which rolls `web` only; state that blast radius in the packet. Confirm existing-droplet reuse and preserve or disposition diagnostic state under rule 2 |
| Bad variable read only at process start | Revert and restart | Human executor uses **Settings** privately for the exact approved variable, then the confirmed restart path; carry no secret value into the incident packet | `cf set-env <app> KEY <old>` then `cf restart <app> --strategy rolling` (a plain restart stops every instance first — see the restart row); first confirm the consumer and package/droplet state |
| Bad buildpack or staging-time configuration | Revert and restage through the full release gates | Human executor uses the approved configuration/pipeline path; a **Restage** control creates new staged bytes | `cf set-env <app> KEY <old>` then `cf restage <app>`; unknown consumer blocks the restart/restage choice |
| Load or capacity saturation | Scale out | On **Overview**, select the affected process's **Scale** control and approved **Instances** count, if exposed | `cf scale <app> --process <process-type> -i <approved-count>`; preserve the selected process because the CLI defaults to `web` |
| Bad behavior is feature-flag gated | Disable the flag | Use the owning flag system's approved control | Follow that system's operating evidence; no deploy is required |
| Downstream dependency is failing | Fail over, degrade gracefully, or shed load | Use the dependency owner's approved console or operating procedure | Follow the dependency's approved operating evidence; queued/in-flight work loss is destructive |

Rollback runs as a rolling deployment by default in the current CLI (the installed version is
unconfirmed), so until it completes both revisions serve and `cf cancel-deployment` during a
rollback restores the previous — bad — droplet; readback waits for completion and checks the new
revision's description, not that the current revision number equals the target. The backout of a
rollback is another rollback: redeploy the revision that was live before it, which stays in
**Revisions** while its droplet is retained, or roll forward with a fix through the full gate.

After every attempt, obtain timestamped effective-state and affected-user readback from the human
or a bounded `sre-assistant` read. Readback does not replace execution evidence; a receipt alone
does not establish user recovery. Reconcile uncertainty
under [Read back an interrupted attempt](#read-back-an-interrupted-attempt).

## Decision rules

1. **Reversible first.** Prefer route remap or flag flip over a change that cannot be undone quickly.
2. **Disposition perishable evidence.** Restart/restage discard heap, thread and connection state;
   scale-in removes the instance; rollback discards the running bad build. Capture affected evidence
   or name the human deciding to forgo it. An instance-scoped restart can hold one instance back for
   diagnosis; whole-app restart cannot. Confirm serving headroom; unknown headroom blocks restart.
3. **One change at a time.** Have the responder or another authorized human watch the relevant
   signals before the next action so its effect can be attributed. Recovery requires the agreed
   user-outcome signal holding for its agreed window, not one green point or quiet minute.
   `sre-assistant` may return permitted read-only instance state, events, recent logs, routes and
   revisions; it never executes the change.
4. **Restart is not root-cause closure.** If restart restores service, preserve the leak, poison
   input, or dependency hypothesis and continue investigation with the human on-call, advised by
   `incident-investigation`.
5. **Record every decision and result using the parent skill's time rule** in the investigation board; prepare the technical
   update for the existing bridge/TLC.
6. **Bind the approval packet.** Name the exact target, artifact/configuration, change/command,
   blast radius, verification window and stop criteria, rollback, human executor, monitoring owner,
   and approving decider. Record diagnostics captured or knowingly forgone; unavailable capture
   does not delay approved covered mitigation. Required target, artifact, approval and safety
   evidence still gates it.

`production-change-gate`'s incident fast path owns the closed list of execution blockers for a
**declared incident**. ITO's TLC approval may cover an exact command or bounded envelope: retain
its validity period/end condition and recheck target/action/actor/identity binding before each
attempt. Reuse approval within that envelope; expiry, mismatch or an outside action needs new
approval. Already-live rollback reuses its artifact records; deferred administrative records
reconcile after resolution. New artifacts and destructive/access-path actions remain on the full
gate with required recovery evidence.

Keep the incident open through sustained recovery. The responder owns recovery evidence; the
human on-call continues causal work, the human release owner executes fixes, and
`observability-engineer` owns detection changes after resolution.

## Read back an interrupted attempt

Read back the effective flag value or route mapping for those actions. For revision rollback,
confirm completed deployment and the intended droplet on the expected instances: rollback creates
a new, higher revision described `Rolled back to revision <n>`, so a matching target number is not
required and a description alone is insufficient. Recheck any environment-based mitigation the
rollback could have undone, using sanitized results.

Current state does not establish when the attempt landed or whether it caused recovery. Reconcile
with the executor and receipts/events before retrying; missing evidence leaves the attempt UNKNOWN.
Judge recovery over an established post-change interval.

Navigation source: VMware's [TAS 2.12 guide, pp. 1145–1157](https://manuals.plus/m/f716ea2ede1f52c2fb9c9496bd199abbede3c0aa1727dab518af606551e1b71f)
(2023 manual; target-foundation UI unverified). Command semantics: Cloud Foundry
[rolling deployments](https://docs.cloudfoundry.org/devguide/deploy-apps/rolling-deploy.html),
[cancel-deployment](https://cli.cloudfoundry.org/en-US/v8/cancel-deployment.html), and
[process scaling](https://cli.cloudfoundry.org/en-US/v8/scale.html).
[Instance restart](https://cli.cloudfoundry.org/en-US/v8/restart-app-instance.html) also defaults to `web`.
