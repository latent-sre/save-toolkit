# Closeout packet

Fill every slot or write `n/a — why`. Evidence labels travel exactly as received; this packet never
upgrades one. It supplies the postmortem and knowledge closeout. Return it to the invoking caller
(the human requester for direct use), who arranges the next handoff; this skill authors neither artifact.

```
Closeout — <INC id> · <application> · <platform>
Returning to:     <invoking caller; human requester for direct use>
Human owner:      <role who owned the incident>
Resolved (UTC):   <human confirmation and ts> · criterion met: <affected user outcome, scope, required window or completion check, evidence> [label]
Impact:           <users, share of traffic, duration; data loss checked how, or [unverified]>
Detection:        <alert or human report; time to notice> · improvement: <actionable earlier signal and noise tradeoff, or n/a — why>
Timeline (UTC):   <ts — event> … (deploys, config, mitigations, recovery)
Cause:            <established cause, or current explanations with scoped evidence and remaining checks> [label]
Mitigation:       <what a human confirmed applied, when, verified how; attempts with UNKNOWN outcome; what was recommended and not taken>
Worked / slow:    <what helped; what cost time; where the team got lucky>
Ledger:           <the conversation checkpoints' final Follow-ups, lossless: Discoveries · Actions (what, owner, due) · Decisions (who asked, who decided, UTC) · Unknowns (every check nobody could run, still `[unverified]`)>
Knowledge repo:   <root> · read: <paths> · missing or stale: <paths>
Evidence:         <sanitized excerpts or access-controlled references — pasted outputs, sre-assistant agent packets, dashboard ranges — each with its label; credential-bearing output is never carried: record that it was exposed, where, and to whom>

Next owners:
1. `scribe`, postmortem mode — this packet is the source; `incident-command` holds the
   authoritative live timeline if one was kept.
2. `scribe`, knowledge closeout mode — the Ledger, plus the target revision binding the human
   supplies for any `prepared` disposition.
```
