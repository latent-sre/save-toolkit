# Ground truth — checkout payments-timeout saturation

Held back from every lane until the postmortem. Open this file exactly twice: while writing the
timeline's premise, and when grading the postmortem. Never have it open while composing or
appending to a packet — it lives apart from `scenario.md` precisely so its phrases cannot migrate
into what a lane reads.

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

## Deliberate traps

The aggregate payments dashboard looks healthy (per-instance breakdown is where the tail hides);
reverting the timeout reintroduces the smaller regression CHK-4412 fixed, so the mitigation has a
real trade-off; and the live env value diverges from `manifest.yml` after the mitigation, so a
later routine push would reopen the incident unless someone notices.

Reference-read token: q_idgt_2f8b
