# Systemic analysis with the human responder

Use for shared impact, cascades, feedback, stalled partitions or harm persisting after trigger removal.
This is incident advice, not a separate command channel or authority to run experiments.

## Find the boundary that failed to contain harm

Sketch the affected callers, dependencies, queues, and shared infrastructure. Mark the smallest
failing unit and what shares fate: pool, partition, tenant, cell, zone, database, identity, or
network path. Compare a genuinely comparable unaffected path; keep unknown topology unknown.

Choose a mechanism from evidence, not from the fact that several alerts fired:

| Candidate mechanism | Useful observation or comparison |
|---|---|
| Cascading timeouts | Does downstream latency precede caller resource occupancy and caller failures on the same requests? |
| Retry amplification or herd | Compare attempts per original request and retry timing with successful work, not total traffic alone |
| Saturation collapse | Compare demand, queue age, service time, and resource limits across onset; low aggregate CPU does not clear a constrained pool |
| Poison item or stuck partition | Compare repeated item failures, partition progress, and oldest-item age with healthy partitions |
| Harmful control-loop feedback | Align scaling, health-check, routing, or remediation events with subsequent load and failures; a controller reacting to harm is not proof it caused it |
| Shared dependency or failure domain | Compare affected and unaffected consumers' actual paths and shared resources; simultaneous alerts alone do not connect them |
| Self-sustaining degradation | Establish the trigger's removal first, then look for backlog, retries, cold caches, or feedback that continues to sustain harm |

Missing telemetry leaves the mechanism open; name its evidence owner. Select applicable mechanisms,
not a mandatory checklist.

## Recommend containment that interrupts the mechanism

Explain how the lever interrupts the chain and what it could destroy: retry suppression may
reduce amplification; isolating a poisoned partition may contain repeated failure. Discarding
queued work loses data and is not reversible. The human chooses; the release owner applies.
Preserve diagnostics or the permitted named-human capture-or-forgo decision; security and
destructive actions retain their separate preservation, approval, and recovery requirements.

Distinguish observed change, current state, and sustained recovery. A rollback alone does not
establish that the trigger disappeared, and a lower aggregate error rate may hide a still-stuck
partition. Verify the affected population and the agreed recovery window before human resolution.

Keep findings and owners in the existing board. Prevention proposals need supporting evidence and
an earlier-warning signal (for example retry amplification or oldest-item age). Return code/design
and observability work to the caller; closeout follows human recovery.
