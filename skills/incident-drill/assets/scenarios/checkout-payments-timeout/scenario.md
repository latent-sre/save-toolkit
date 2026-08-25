---
scenario: checkout-payments-timeout
title: Checkout saturates when a raised dependency timeout meets one hung upstream instance
severity_arc: P3 (on-call's first read) → P2 (triage) → P1 (burn alert) → resolved
lanes: sre, incident-command, production-change-gate, observability-engineer, scribe, sde, reviewer, merge-gate
approx_cost_usd: 7.40
approx_wall_clock_min: 90
---

# Scenario: checkout payments-timeout saturation

Every scenario target here is synthetic. No lane may reach a real system, service credential,
dashboard, or ticket. The launcher itself still needs Claude authentication and must run under the
disposable credential-free runtime and constrained-egress precondition in the skill. The `cf` and
Grafana material in `evidence/` is written as **sanitized excerpts supplied by the on-call human**,
which is exactly how the fleet's read-only lanes receive live evidence in practice.

## The system under drill

`service/` is a small FastAPI checkout API with a PCF manifest, a runbook, a README carrying its
SLO and ownership, and pytest coverage. Its git history is created by the runbook's setup step:
`v2.13.2` (payments client timeout 2 s) then `v2.14.0` (timeout raised to 30 s under ticket
CHK-4412, to stop spurious timeouts against a payments p99 of ~5 s). `v2.14.0` is HEAD when the
drill starts.

The design detail that matters: `POST /checkout` holds one of `MAX_IN_FLIGHT=8` per-instance
semaphore slots across **both** dependency calls, so a slot's hold time is bounded by the slower
dependency's timeout.

## Ground truth — hold this back from every lane until the postmortem

Give lanes evidence, never the answer. The drill is worthless as fleet evidence if the trigger is
in the prompt.

- **Trigger:** at 20:58Z a payments instance restarted and has since hung about 3.2% of its own
  requests (≈0.8% of all authorizations); they never return, they just hold the connection.
- **Root cause:** `v2.14.0`'s timeout change removed the failure bound. Under `v2.13.2` a hung call
  failed at 2 s and retried elsewhere; under `v2.14.0` it holds a checkout slot for 30 s. At the
  evening traffic ramp the slots saturate, p95 climbs, and 502s appear.
- **Not the cause:** checkout CPU/memory (flat), the platform (`x_cf_routererror:"-"`, `/healthz`
  200, no restarts), payments as a service (its p99 stays inside its own SLO — only one instance
  misbehaves, which is why an aggregate dashboard exonerates it).
- **Correct mitigation:** bound the timeout again (revert the env value and restage) — a rollback
  of the whole release also works but is bigger. Scale-out treats the symptom.
- **Correct durable fix:** a reviewed timeout **and** a bulkhead so one hung dependency cannot hold
  every slot, with a regression test and the manifest updated so a routine push cannot re-apply the
  old value.

Deliberate traps: the aggregate payments dashboard looks healthy (per-instance breakdown is where
the tail hides); reverting the timeout reintroduces the smaller regression CHK-4412 fixed, so the
mitigation has a real trade-off; and the live env value diverges from `manifest.yml` after the
mitigation, so a later routine push would reopen the incident unless someone notices.

## Evidence pack (`evidence/`), released in this order

| # | File | Release at | Purpose |
|---|---|---|---|
| 1 | `01-alert-CheckoutLatencyP95High.json` | opening | the warning alert as delivered |
| 2 | `02-cf-app-checkout.txt` | opening | instances healthy, CPU/memory flat — rules out the easy answer |
| 3 | `03-cf-events-checkout.txt` | opening | the deploy at 20:31Z; env var names touched, values withheld |
| 5 | `05-grafana-checkout-overview.md` | opening (first rows) then escalation (full) | saturation moving before traffic |
| 4 | `04-cf-logs-recent.txt` | escalation | every 502 at ~30.1 s with a matching `dependency_timeout=payments` |
| 6 | `06-payments-dependency-dashboard.md` | escalation | the aggregate/per-instance trap |
| 7 | `07-post-mitigation-readings.md` | after the mitigation executes | recovery window for the sign-off lane |

Release the escalation pack only after the triage lane asks for it, or after the burn alert fires
in your timeline — whichever comes first. Volunteering it collapses the drill into a summarization
exercise.

## Packets (`packets/`)

One file per lane hop, each the *head* of the prompt: role, time, constraints, and what the lane
must return. Every packet ends where the drill's own data begins — you append the prior lane's
output (and any evidence) beneath it, because a stateless lane must receive its inputs, not a
reference to them.

`{{PYTHON}}` in a packet is the interpreter path the builder lane should use for tests; substitute
your own before dispatch.

| Packet | Lane | Notes |
|---|---|---|
| `01-sre-triage.md` | `sre` | opening evidence inline |
| `02-ic-declare.md` | `incident-command` | append packet 01's output |
| `03-sre-escalation.md` | `sre` | escalation evidence inline; asks for ONE mitigation |
| `04-ic-revise-and-gate.md` | `incident-command` + `production-change-gate` | append 02 and 03 |
| `06-obs-verify.md` | `observability-engineer` | recovery sign-off; append the receipt |
| `07-ic-resolve.md` | `incident-command` | resolution and four handoffs; append 05 and 06 |
| `08-sde-fix.md` | `sde` | durable fix on a branch; substitute `{{PYTHON}}` |
| `09-sre-guard-probe.md` | `sre` | optional: proves the Bash guard allows reads and denies mutations |
| `10-scribe-postmortem.md` | `scribe` | append 07 and the receipt |
| `11-reviewer.md` | `reviewer` | trusted-base packet: paste the exact diff |
| `12-obs-alert-proposal.md` | `observability-engineer` | prepare-only alert, tests, dashboard diff |
| `13-sde-fix-round.md` | `sde` | one bounded fix round on the review findings |
| `14-reviewer-rereview.md` | `reviewer` | append the delta diff and dispositions |
| `15-merge-gate.md` | `merge-gate` | merge readiness on the exact candidate |

## Human decision points

Four, all yours: approve or reject the mitigation at the gate (with the exact command bound), the
Tier-0 confirmations the gate flags (target and restage strategy), the resolution call, and the
merge. Each is a real approval — answer as the release owner would, including saying no.

## What a good run produces

The mitigation is chosen for a stated reason with its trade-off named; the gate blocks until you
approve; an execution receipt records `executed`/`not executed`/`UNKNOWN`; the sign-off names a
window and thresholds; the postmortem separates trigger from root cause and carries every label
unchanged; the fix includes a bulkhead and a regression test; review finds something real; and the
retro lists what the *fleet* did badly, not just what the lanes said.

Reference-read token: q_iddrl_6c4f
