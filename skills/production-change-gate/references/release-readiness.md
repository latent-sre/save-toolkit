# Release readiness

The human release owner assesses readiness; the [parent production gate](../SKILL.md#production-authorization)
separately authorizes production using this record.

| Item | Passes when |
|---|---|
| Merge verdict | `gate: merge`, `verdict: PASS` exists for the exact candidate commit. |
| One immutable artifact | Version/release notes identify the candidate. Build once, promote the exact lower-environment-tested artifact; prove its byte identity and immutability using [distribution-specific evidence](./release-artifact-evidence.md). |
| Migrations | Schema/config stays compatible with supported consumers at each stage. Expand before dependent code; contract only after old consumers retire. Each stage has tested recovery preserving accepted writes/data. |
| Consumer retirement | Confirm retirement before contraction. Then validate remaining consumers and versions needed for recovery, without requiring retired readers to remain compatible. Before retirement, old readers still need compatibility evidence. |
| Flags | Risky behaviour is flag-gated with safe defaults and a tested transition. |
| Backout / recovery | Exact rollback where feasible; otherwise identify non-reversible effects and evidenced recovery preserving accepted writes/data. Record commands, verification and stops. PCF method/foundation behaviour stays `[unverified]` until foundation evidence is attached. |
| Monitoring and comms | Define success/failure signals and abort criteria before release. `observability-engineer` supplies coverage evidence for new behaviour, including operator guidance for new paging alerts. Stakeholders/on-call know the window and update cadence. |

Missing recovery evidence or uncovered migration stages block release. `ci-actions` owns artifact
production; this checklist consumes provenance without invoking that workflow.
