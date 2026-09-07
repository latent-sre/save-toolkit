---
schema_version: 1
runbook_id: checkout-p95-burn-fast
service_id: checkout
status: active
alert_names: [checkout-p95-burn-fast]
owner: payments-oncall
severity: P2 / page
source_revision: checkout@4f2b9c1e8a7d6350fa1c2b9e4d7a8c3f5e6b1902
last_reviewed: "2026-02-18"
last_verified: "2026-02-11"
verification_evidence: [drill-2026-02-11-checkout-restart]
version: 4
---

> **This is a teaching exemplar, not a live runbook.** `checkout` is a fictional service. The
> dates, evidence ids, and history illustrate the [template](./runbook-template.md); they bind
> nothing. A copy starts with `last_reviewed: null`, `last_verified: null`, and an empty history.

# Runbook: checkout p95 latency burning fast error budget

## Purpose & scope
Handles `checkout-p95-burn-fast`: checkout p95 latency above the SLO with a burn rate that exhausts
the 30-day budget in under 6 hours.

**Out of scope** (do NOT use this for): checkout returning 5xx (that is
`checkout-error-rate`); payment-path investigation (see `payments-vendor-degraded`).

## Trigger
Alert `checkout-p95-burn-fast` fires: `p95(checkout_request_duration_seconds) > 0.8` sustained 10 min
with fast-burn multiplier ≥ 14.4.
Dashboard: `https://grafana.example.internal/d/checkout-slo`  ·  Source/repo: `git@example.internal:payments/checkout`

## Prerequisites
- Access: Apps Manager for the `payments` org, `prod` space; Splunk `payments_*` index; Wavefront
  or PCF App Metrics; Grafana viewer. `cf` CLI v8 only if you have it.
- Tools: Apps Manager is the console this team uses. Confirm before you start that its breadcrumb
  reads `payments` / `prod`. With the `cf` CLI the equivalent is `cf target` printing
  `org: payments` / `space: prod`; if it prints anything else run `cf target -o payments -s prod` —
  every `cf` command below assumes that target and none of them name the space explicitly.
- Useful links: SLO definition `checkout-availability`, prior postmortem `2026-01-19-checkout-pool`.

## Triage / first checks

1. **Which requests are slow?** Open the SLO dashboard, panel "p95 by route", for the reported
   impact window. Confirm it includes affected user requests, not just probes.
   - Elevated on `/checkout/submit` only → focus on that path; continue.
   - Elevated across routes, including `/healthz` → compare the `platform-router-latency` panel
     and other apps. A matching cross-app pattern merits platform escalation, not proven platform
     fault; shared dependencies remain possible. With only checkout affected, continue app-side.
   - Missing/stale data → impact and scope unknown. Ask for an affected request and timestamp;
     escalate if unavailable, not a healthy-traffic conclusion.

2. **Are all instances serving?**
   ```bash
   cf app checkout
   ```
   Expected: `instances: 6/6 running`.
   - `6/6 running` → processes are running, not proof that requests succeed. Go to step 3.
   - Fewer than 6, or any `crashed`/`starting` → capacity/readiness differs from the expected state.
     **Do not restart anything**; preserve events/logs and go to Procedure step 4.
   - Failed or incomplete read → instance state is unknown; escalate with the failed observation.

3. **Is one instance dragging the percentile, or all of them?**
   ```bash
   cf app checkout | tail -n +6
   ```
   Expected: a per-instance table. Compare the `cpu` and `memory` columns.
   - One instance higher → compare request latency/errors and load in the same window. Only a
     corroborated single-instance problem leads to Procedure step 1.
   - All instances similar → neither saturation nor health is established. Procedure step 2.
   - Missing evidence → inconclusive; Procedure step 2 or escalate if unavailable. A CPU/memory
     snapshot alone does not justify restart.

## Procedure

> Mark destructive steps ⚠️. Tier 2/3: record explicit human approval for the exact command/target
> plus rollback or recovery evidence before execution.

1. ⚠️ **Restart the single degraded instance.** (Tier 2 — needs explicit human approval naming
   `checkout` and the instance index.)
   ```bash
   cf restart-app-instance checkout <idx>
   ```
   `<idx>` is the instance index in step 3's table, zero-based. Capacity drops to 5/6 until it
   returns (~90 s). Before approval, confirm the other five serve requests with headroom over the
   impact window; CPU below ~70% alone does not establish that. If their capacity or readiness is
   uncertain, skip to step 2 rather than removing capacity. The restart can interrupt in-flight
   work and discard process-local state; it cannot be undone.
   Expected: the command returns `OK` within ~5 s, and `cf app checkout` shows that index
   `starting` then `running` within 90 s.
   - Still `starting` after 3 min → it is not coming back cleanly. Go to step 4.
   - Returns to `running` but p95 does not improve within 10 min → the restart did not restore
     latency; cause remains open. **Do not restart it again.** Go to step 2 before any scaling.

2. **Check the downstream payment path before scaling.** Extra app instances can increase
   pressure on a constrained dependency; this read checks for that risk, not just timeout counts.
   ```bash
   cf logs checkout --recent > /tmp/checkout-recent.log &&
     awk '/vendor_timeout/ {n++} END {print n+0}' /tmp/checkout-recent.log
   ```
   Expected: a count within 30 s. Bind the captured log window and request volume; raw abundance
   alone does not locate the delay, and this short buffer may omit the affected requests.
   - Elevated timeouts → use `payments-vendor-degraded` to check client pool, network, and vendor.
     **Do not scale** while dependency pressure remains plausible.
   - Few or no timeouts → the vendor is not cleared. Compare dependency latency and app saturation
     over the impact window; go to step 3 only when its prerequisites are established.
   - No count, error, incomplete coverage, or a hang past 30 s → inconclusive observation, not
     platform fault. Stop this check; use historical Splunk logs or escalate with the gap.

3. ⚠️ **Scale out.** (Tier 2 — needs approval naming the target instance count.) Proceed only with
   evidence of app capacity pressure and dependency headroom over the impact window. Without those
   observations, escalate rather than treating a low timeout count as permission to scale.
   ```bash
   cf scale checkout -i 9
   ```
   Expected: `OK`, then `9/9 running` within 3 min. p95 should fall within 10 min of the last
   instance reaching `running` — not before, so do not judge this early.
   - `9/9 running` and p95 under 0.8 s within that window → go to Verification.
   - `9/9 running`, p95 lower but still above 0.8 s at 10 min → partial recovery: hold the
     count, **do not scale further**, and escalate on the table's scale-out row with both readings.
   - Not `9/9 running` after 3 min → the intended capacity change was not established; its latency
     effect is inconclusive. **Do not scale further.** Escalate with requested and observed counts.
   - `9/9 running`, p95 unchanged at 10 min → this intervention did not restore latency; it does
     not rule out every capacity constraint. **Do not scale further.** Escalate with both readings.
   Scaling is a stopgap that buys time; it does not fix a leak or a slow dependency. File the
   follow-up before you leave the incident.

4. **Instances are missing, starting, or crashing (from triage step 2 or step 1).** Do not restart.
   Capture evidence before process replacement loses transient state:
   ```bash
   cf logs checkout --recent > /tmp/checkout-crash-$(date -u +%Y%m%dT%H%M%SZ).log
   ```
   Expected: a non-empty file within 30 s.
   - Non-empty → inspect events/logs for the affected instances, attach them, and escalate per the
     table below. A non-empty capture does not itself establish a crash loop; this runbook ends here.
   - Empty, or the capture errors twice → escalate with what you have rather than trying a
     third time.

## Verification
p95 under 0.8 s for 15 continuous minutes on the SLO dashboard's "p95 by route" panel, **and** the
burn-rate panel back under 1.0. The alert auto-resolves ~5 min after the second condition holds.

If p95 is healthy but the burn-rate panel is still above 1.0, the budget is still being consumed by
the earlier damage — that is expected and not a reason to keep acting.

## Rollback / cleanup
- Step 1 (restart): no rollback restores the old process or interrupted work. Verify replacement
  readiness and affected requests; follow step 1's stop/escalation conditions, not another restart.
- Step 3 (scale out): return to the baseline count once p95 has been healthy for 30 min.
  ```bash
  cf scale checkout -i 6
  ```
  Expected: `6/6 running`. Watch p95 for 10 min after; if it climbs again, scale back to 9 and treat
  the underlying cause as unresolved.
- Abort: stop further changes and hand over observed instance states/count, requests, and completed
  actions. A started restart or scale continues after you stop; service may remain degraded. Check
  readiness and latency, and have the human owner choose recovery using the entries above.

## Escalation
| When (condition / time elapsed) | Escalate to | How to reach |
|---|---|---|
| Not resolved 20 min after Procedure step 2 | payments engineering lead | pager `payments-lead`, `#payments-oncall` |
| Scale-out has not reached `9/9 running` after 3 min, or p95 is still above 0.8 s 10 min after reaching it | payments engineering lead | pager `payments-lead`, `#payments-oncall` |
| Instances missing/starting/crashing, or observation unavailable (Procedure step 4) | payments engineering lead | same, with captured evidence and gaps |
| Multiple unrelated apps slow in the same space | platform on-call | pager `tas-platform`, `#platform-oncall` |

Hand over: trigger, evidence, attempted steps, current state, and the current owner.

## Communication
- Notify: `#payments-oncall`, and `#status-internal` if customer-visible · Cadence while active: 30 min
- Initial / update / resolved message owner: incident commander, or the responder until one is named

## Post-Incident
- [ ] Append an Incident history row: version used, steps that held, steps that failed or were
      missing, follow-up id.
- [ ] Create a learning disposition for every missing, contradicted, or newly useful step.
- [ ] **Update this runbook** from supplied evidence when a disposition requires it.
- [ ] Change `last_verified` only when incoming rehearsal evidence binds this exact runbook version,
      target, actor, timestamp, and outcome; otherwise leave it unchanged and record the gap.
- [ ] File follow-up **automation candidates** (Crawl→Walk→Run) as tickets.
- [ ] If this was an incident, after recovery, hand the timeline and evidence to `scribe`.

## Incident history (living-runbook accretion)
> Append one row per incident or rehearsal that used this runbook — newest first. Rows are evidence:
> never rewrite or delete them.

| Date (UTC) | Incident / drill ref | Version used | Steps that held | Steps that failed / were missing | Follow-up (disposition / PR or evidence reference) |
|---|---|---|---|---|---|
| 2026-02-11 | drill-2026-02-11-checkout-restart | 3 | Triage 1–3, Procedure 1 | — | `prepared` — added the zero-based `<idx>` note after the responder guessed wrong twice |
| 2026-01-19 | postmortem 2026-01-19-checkout-pool | 2 | Triage 1–2 | Procedure 2 had no rollback; responder left checkout at 9 instances for six days | PR #412 — added the Rollback entry and the 30-min wait |
| 2025-12-03 | INC-8841 | 1 | Triage 1 | No vendor check existed; 40 min spent scaling against a slow vendor | PR #388 — added Procedure step 2 |

## References
- Related runbooks: `checkout-error-rate`, `payments-vendor-degraded`, `platform-router-latency`
- Postmortems: `2026-01-19-checkout-pool`
- Alert definition / SLO: `checkout-availability` (SLO), `checkout-p95-burn-fast` (alert rule)
- Service card / alert card / knowledge index: service card `checkout`
- Provenance: PR #412, `checkout@4f2b9c1e`, drill evidence `drill-2026-02-11-checkout-restart`
