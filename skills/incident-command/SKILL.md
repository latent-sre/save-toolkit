---
name: incident-command
description: >-
  Run a live incident — classify SEV1–SEV4 by user impact × scope × trend, assign roles, keep the
  authoritative timeline, drive to mitigation (fastest reversible action: route remap, rollback, restart,
  scale, flag flip), send initial/update/resolution comms. Triggers: 'declare an incident', 'what severity
  is this', 'send a status update', 'should we roll back'. Mitigation is executed by a human; the sre agent
  investigates.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Incident severity, command & communications

The first consequential call in any incident is **"how bad is this, and who needs to know?"**
**Over-classify, then downgrade** — declaring is cheap; under-declaring is expensive. Set a
*provisional* severity in the first minutes from what you can see, and revise as the blast radius
becomes clear.

## Severity rubric (round up when unsure)

| SEV | Definition (user impact × scope) | What it triggers |
|-----|----------------------------------|------------------|
| **SEV1** | Customer-facing outage for all/most users, **or** data-loss / integrity / security event | Declare **now**; assign an incident commander (run the process below); page on-call + service owner + leadership; status updates every **15 min**; full blameless postmortem |
| **SEV2** | Major degradation, or a single critical service/journey down for a subset of users | Declare; assign an incident commander (run the process below); page on-call + service owner; updates every **30 min**; postmortem required |
| **SEV3** | Minor / contained impairment; core journeys work or a workaround exists | On-call owns the lifecycle; no IC required; update stakeholders at start + resolution; abbreviated postmortem |
| **SEV4** | Cosmetic / informational; no user impact | Normal work queue; no incident process |

## How to classify

- **Impact × scope × trend.** Multiply *how bad for a user* by *how many users / which journeys*, then
  weigh *direction* — a SEV3 that's **growing** is escalating toward SEV2; say so and re-page.
- **Bound the blast radius.** One app/route/instance ⇒ likely app-side (yours). Many apps at once, or
  failing/evacuating Diego cells ⇒ platform-side ⇒ escalate to the platform team with evidence: capture
  `cf apps`, `cf app`, `cf events`, and bounded `cf logs --recent` output, or give the packet to the typed
  `sre` agent. If you **can't yet bound** the blast radius, that alone justifies SEV2 and declaring.
- **Time-box the responder.** First on scene and not stabilized in **~15 min**, or the impact is
  growing → declare and assign an incident commander (run the process below); don't keep digging solo.

### Security/integrity carve-out — preserve evidence first

Suspected compromise or a security/integrity event exits the generic reliability-mitigation path.
Immediately escalate to the human security incident owner and preserve state and forensic evidence.
Do not restart, redeploy, scale, remap routes, or apply the mitigation table unless that owner directs
the exact action. The typed `sre` agent is limited to the named read-only signal collection requested by
that owner; it does not contain, eradicate, or recover the compromised system.

## Running the incident (command)

Once declared, someone owns the **response** — the **incident commander** (often the on-call lead), who
runs the *process*, not the debugging, keeping the response moving toward mitigation.

- **Coordinate, don't solo-debug.** The moment the IC is heads-down in logs, nobody is commanding.
  Delegate technical RCA to the typed `sre` agent and remediation to a human release owner.
- **Mitigate first.** User pain stops before root cause is found — push for the fastest safe, reversible
  mitigation using the inline decision below, and make that call explicit; a human executes it.
- **One source of truth.** Keep a single running **timeline** (UTC) of what is known, tried, and next.
- **Assign roles:** Investigation lead (typed `sre` agent), Ops/remediation (a human release owner),
  Comms/scribe (the IC or typed `sre-steward` agent on a large SEV1). Confirm who owns what.
- **Track every action** — each "someone should…" becomes an owned, tracked item.
- **Resolve & close.** Confirm impact has ended (verify via the investigator and typed `sre-steward` agent),
  send the **Resolution** update, and hand the timeline to the typed `sre-steward` agent for the durable
  retrospective.

### Status — one authoritative block, kept live

```text
Incident: <title>   Severity: <SEV-n>   Status: <investigating|mitigating|monitoring|resolved>
Impact: <who/what, since when, trend>
Roles: Investigation=<>, Ops=<>, Comms=<>
Timeline (UTC): <ts — event/decision> …
Current focus: <the one thing the response is doing now>
Mitigation decision: <chosen / pending — rationale>
Open action items: <owner — item — status>
Next update: <time>
```

## Communications cadence

Update on the **fixed cadence for the severity above, even with no news** ("still investigating, next
update by HH:MM") — silence reads as loss of control. Keep it honest and jargon-free: never overstate
confidence or understate impact. For SEV1, the first external update goes out within the hour. For a
large SEV1, split **Comms lead** and **Scribe** off from the IC; otherwise the IC owns both.

### Templates

- **Initial** — *What we know* (symptom + impact), *Severity*, *Scope* (who/what affected, since when),
  *We are investigating*, *Next update by* `<HH:MM UTC>`.
- **Update** — *What changed since last update*, *Current status* (investigating | mitigating |
  monitoring), *Mitigation in progress / ETA*, *Next update by* `<HH:MM UTC>`.
- **Resolution** — *Impact has ended* (and since when), *Root-cause summary* (or "`[unverified]` — under
  investigation"), *What we did*, *Follow-ups + owners*, *Postmortem to follow* (SEV1/SEV2).

## Downgrade & resolve

Downgrade or resolve only when the **golden signals are back to baseline and stay there** for a
sustained window (not just "the graph turned green" — a metastable system can re-break). Verify recovery
via the investigator and typed `sre-steward` agent first, then send the **Resolution** update and give the
typed `sre-steward` agent the timeline with preserved `[verified]`, `[sourced]`, and `[unverified]` labels.

## Choose the mitigation (the rollback decision)

**Mitigate before you fully understand.** Stopping user pain comes before root cause. Pick the
**fastest safe, reversible** action. The decision boundary is explicit: the sre agent recommends; a human
executes with human sign-off; in a major incident the incident commander owns the decision.

This reliability table excludes suspected compromise and security/integrity events; the carve-out above
controls those incidents.

The commands below are planning examples, not current foundation evidence; they remain `[unverified]`
until the human release owner validates the exact target, capability, command, and rollback.

| Situation | Mitigation | Command (confirm first) |
|---|---|---|
| **Bad deploy** (errors start at deploy time), previous app still exists | **Blue-green rollback** — remap the production route to the previously-live app | `cf map-route <previous-app> <domain> --hostname <app>` then `cf unmap-route <current-app> …` (blue/green are *roles*, not fixed names — the previous live app keeps running under the stable name until the post-soak rotation; confirm which app is live with `cf apps` first) |
| Bad deploy, revisions enabled | **Revision rollback** | `cf revisions <app>` (find last good `<n>`) → `cf rollback <app> --version <n>` |
| Rolling/canary deploy in flight going wrong | **Abort the deploy** | `cf cancel-deployment <app>` — **in-progress only**; once the deploy has completed it **errors** ("No active deployment found"), so use **revision rollback** (`cf rollback <app> --version <n>`) instead |
| Instances hung / wedged / leaking, no recent change | **Restart** (buys time; doesn't fix cause) | `cf restart <app>` or `cf restart-app-instance <app> <i>` |
| Bad config/env change | Revert env + restage | `cf set-env <app> KEY <old>` → `cf restage <app>` |
| Load/capacity-driven saturation | **Scale out** | `cf scale <app> -i <more>` |
| Feature-flag-gated bad behavior | **Disable the flag** (often fastest of all) | flag system — no deploy needed |
| Downstream dependency failing | Fail over / degrade gracefully / shed load | per dependency operating evidence |

### Rules

1. **Reversible first.** Prefer an action you can undo in seconds (route remap, flag flip) over one you
   can't. Blue-green route remap is the gold standard — instant and reversible.
2. **One change at a time**, then observe. Have the typed `sre-steward` agent or named human watch the
   golden signals for 1–2 minutes before the next action — so you know what worked.
3. **Restart is a stopgap, not a fix.** If a restart "fixes" it, the cause is still there (leak, poison
   input, dependency) — capture `cf events`/logs first, then keep investigating with the typed `sre` agent.
4. **Record everything** (UTC) for the timeline and give it to the typed `sre-steward` agent.
5. **Confirm before executing.** Every command here changes production. Show the exact target, command,
   blast radius, verification, and rollback; attach existing human approval, then the human executes.

### After mitigation

User pain stopped ≠ incident over. Hand root-cause work to the typed `sre` agent and fix-forward execution
to a human release owner; the typed `sre-steward` agent confirms recovery and the typed `sre-steward` agent captures
durable operating guidance.

## Pairs with

Ownership map only—not a load: the `eng-ladder` skill owns response altitude and the `postmortem` skill
owns the durable retrospective.
