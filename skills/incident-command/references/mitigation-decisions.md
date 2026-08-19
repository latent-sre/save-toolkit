# Mitigation decisions

This reference supports a reliability decision; it does not authorize or execute a production change.
Suspected security or integrity incidents follow the security-owner carve-out in `SKILL.md` instead.

## Decision rule

Prefer the smallest action that can stop user impact, is reversible, has a known target, and has an
observable success signal. A human change owner must confirm current platform behavior and present the
exact action through `production-change-gate` before execution.

| Evidence pattern | Candidate direction | Required check before recommending it |
|---|---|---|
| Impact began with a release | Restore the last known-good artifact or traffic target | Prove which artifact/target was previously healthy and that rollback remains supported |
| A deployment is still in progress and degrading service | Stop or cancel the in-progress operation | Confirm the platform exposes a safe cancel operation and define the post-cancel state |
| A feature flag isolates the failing path | Disable the narrow flag | Confirm scope, propagation time, audit trail, and how to restore it |
| Capacity saturation is observed | Scale or shed load | Distinguish demand from leaks/downstream failure and set a cap plus recovery signal |
| A process is wedged and durable state is safe | Restart the narrowest affected unit | Capture ephemeral evidence first; treat restart as mitigation, not diagnosis |
| Configuration change correlates with impact | Restore the last verified configuration | Identify whether restart/restage/reload is required and how configuration is proven active |
| A dependency is failing | Fail over, degrade, or shed load | Validate dependency health, consistency implications, and the return path |

Do not copy a remembered CLI command into the incident record as if it were current evidence. The
platform-specific deploy or operations skill owns exact syntax and limitations; the human owner
validates it against the target immediately before execution.

## Required decision packet

```text
Evidence: <why this mitigation matches the observed failure>
Target: <environment, service, instance/route/artifact/config as applicable>
Action: <exact human-reviewed operation; `[unverified]` until target-checked>
Authority: <approval record and human executor>
Blast radius: <expected and worst credible impact>
Success signal: <metric, log, trace, probe, or user journey>
Observation window: <service-appropriate duration and rationale>
Rollback/recovery: <how to undo or recover if the action fails>
Stop condition: <signal that blocks or aborts execution>
```

## After the action

Record the observed result, not just command completion. If the signal does not improve, stop and
reassess rather than stacking unrelated changes. Preserve the pre-change and post-change evidence in
the incident timeline, then continue causal investigation through `root-cause`.
