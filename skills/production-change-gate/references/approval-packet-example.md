# Approval packet example

Use this only when a concrete example clarifies the required relationships. Values are illustrative
and remain `[unverified]` for any real target.

```text
Request: human release owner approval for one Tier 2 configuration change
Target: checkout application, production environment
Actor: named human release owner using the approved least-privilege role
Change: set FEATURE_X from false to true
Exact effect: reviewed workflow/ref and input FEATURE_X=true; no other input changes
Operation identity: CHG-1234/FEATURE_X/checkout/prod; replacement or replay requires reconciliation
Blast radius: one application; worst case elevated checkout errors
Approval: CHG-1234, approver and UTC timestamp
Effect boundary: protected production environment; self-review disabled; bypass actors recorded
Verification: error rate, latency, and business success signal for 10 minutes
Abort: error rate exceeds the predeclared threshold or telemetry is missing
Rollback: run the reviewed inverse with FEATURE_X=false; verify the same signals
Unknown outcome: inspect the authoritative runtime value and workflow state before retry or rollback
Coordination: outside freeze window; on-call and stakeholders named
```

The packet is complete only when the evidence supports each value. The human owner executes after
approval; the agent prepares and reports the packet.
