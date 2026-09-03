# Sustained recovery lifecycle

Read this reference only when the caller explicitly assigns lifecycle support, asks `sre-assistant` to
continue an incident through recovery, or supplies an active `monitoring-recovery` record and asks
`sre-assistant` to continue it. An active alert, high severity, or a mitigation recommendation alone does not
select sustained response.

The human SRE or incident commander remains the operational owner. The typed `sre-assistant` lane maintains
the technical incident record until one of the supported terminals below; a human release owner
executes every production mitigation.

## Recovery loop

1. Keep severity, blast radius, UTC timeline, hypotheses, and human-performed or recommended
   mitigation current.
2. After mitigation, enter `monitoring-recovery`. Require the same golden signals to remain at
   baseline for the evidence-backed sustained window. One green point is not recovery.
3. If the uninterrupted healthy start, observation time, or required window is unknown, keep the
   incident active, record the unknown, and name the next observation. Never estimate progress.
4. Record `resolved` only after the recovery gate passes. Record `escalated-security` only after the
   human security incident owner accepts a suspected compromise. Record `no-incident` only after a
   human confirms the proposed finding; this lane proposes that terminal and never records it
   unprompted. `no-incident` is unavailable once a mitigation has been performed or the record has
   entered `monitoring-recovery`: both assert impact that this terminal denies. A blocked turn, failed delegate, or proposed follow-up is not a terminal.
5. Return the authoritative technical record and proposed next-phase work to the caller. Do not
   load `postmortem` or `operational-learning`; the caller starts those later owning lanes.

## Monitoring-recovery record

Keep the human-readable operator report required by `agents/sre-assistant.md`. Its final non-whitespace
content is exactly one backtick-fenced `json` object using schema `incident-state/v2`; no prose or
fence follows its closing marker. The object summarizes the report; it does not replace it. Prose
and record must agree. Put no prose or comments inside the JSON fence, add no fields beyond the
shape below, and emit no other fenced JSON object, including a tilde-fenced one.

Populate every value from current evidence:

- `state` is `monitoring-recovery`, `owner` remains `sre-assistant`, `terminal.recorded` is `false`, and
  `terminal.next` is `resolved_after_recovery_gate` until the sustained gate passes;
- `recovery_gate.signals` maps each signal that must stay healthy to
  `must_remain_at_baseline`. Normalize the caller's signal nouns to lower `snake_case`; do not
  prefix the observed service or resource. For example, "checkout p99 latency and error rate"
  becomes `p99_latency` and `error_rate`. Express recovery durations as integer seconds.
  `required_continuous_seconds` is the evidence-backed gate duration. If the uninterrupted healthy
  start and observation time are both known, set integer `healthy_elapsed_seconds` and
  `remaining_seconds = required_continuous_seconds - healthy_elapsed_seconds`; do not round. If
  either time is unknown, set both progress fields to JSON `null`; never estimate or use zero as
  unknown, and do not assert a recovery-start timestamp the evidence does not establish. While the
  state remains `monitoring-recovery`, known elapsed time is less than the required duration and
  known remaining time is positive;
- `production_action.further_change_authorized` reflects the caller's current authorization and
  `production_action.agent_executed` remains `false` because this lane never applies production
  changes; and
- `follow_ups.dispatch_by` is `caller`, `dispatch_after` is `resolved_recorded`, and `tasks` includes
  only the next-phase work the caller requested. Use `detection` for a requested detection or alert
  gap and `runbook_and_postmortem` when both documents were requested. Keep speculative work in
  prose instead of adding another task. A durable-discovery candidate naming an owner does not add
  that owner to `tasks`: when the caller asks only about detection, runbook, and postmortem work,
  the only task keys are `observability-engineer` and `scribe`; keep a durable `software-engineer`
  follow-up in prose unless the caller explicitly asks for that work in the current turn. Do not
  dispatch any task while the incident is active.

The exact key and type shape is:

```json
{
  "schema": "incident-state/v2",
  "state": "monitoring-recovery",
  "owner": "sre-assistant",
  "terminal": {
    "recorded": false,
    "next": "resolved_after_recovery_gate"
  },
  "recovery_gate": {
    "signals": {
      "latency": "must_remain_at_baseline",
      "error_rate": "must_remain_at_baseline"
    },
    "required_continuous_seconds": 900,
    "healthy_elapsed_seconds": 330,
    "remaining_seconds": 570
  },
  "production_action": {
    "further_change_authorized": false,
    "agent_executed": false
  },
  "follow_ups": {
    "dispatch_by": "caller",
    "dispatch_after": "resolved_recorded",
    "tasks": {
      "observability-engineer": "detection",
      "scribe": "runbook_and_postmortem"
    }
  }
}
```

The example values are illustrative. Replace its signal keys, duration values, authorization, and
task map with the incident's evidence; do not copy them when the evidence differs.
