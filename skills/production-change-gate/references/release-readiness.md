# Release readiness

Read only for "is this build ready to ship to an environment". Owned by a human release owner. For
production this establishes readiness only; authorization is the parent `SKILL.md`'s production
section, later, using this record.

| Item | Passes when |
|---|---|
| Merge verdict | A recorded `merge: PASS` exists for the exact candidate commit. |
| One immutable artifact | The version and release notes identify the candidate, and the exact artifact tested in lower environments is the one shipping: build once, promote. Prove immutability through the distribution path's own controls; the [artifact evidence reference](./release-artifact-evidence.md) has the GitHub Release commands and the rule for other paths. |
| Migrations | Schema and configuration migrations are backward-compatible, ordered before the code that needs them, and independently reversible. |
| Flags | Risky behaviour is flag-gated with safe defaults, and the flag transition is tested. |
| Rollback | Exact rollback steps are written with evidence they work. On PCF the rollback method and foundation behaviour stay `[unverified]` until foundation evidence is attached. |
| Monitoring and comms | Success and failure signals and abort criteria are defined before the release, with evidence from `observability-engineer` that alerts and SLOs cover the new behaviour and that new paging alerts have operator guidance; stakeholders and on-call know the window and update cadence. |

A release without a clean, evidenced rollback does not pass. `ci-actions` owns the workflow that
produces the artifact; this checklist consumes its provenance evidence and never invokes it.
