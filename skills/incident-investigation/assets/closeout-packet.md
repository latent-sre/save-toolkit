# Closeout packet

Use the known facts below; retain material unknowns without padding optional empty slots. Evidence
labels travel unchanged. This supplies the postmortem and knowledge closeout. Return it to the invoking caller
(the human requester for direct use), who arranges the next handoff; this skill authors neither artifact.

```
Closeout — <INC id> · <application> · <platform>
Returning to:     <invoking caller; human requester for direct use>
Human owner:      <role who owned the incident>
Impact ended (UTC): <evidenced end or unknown; user outcome, scope, required window/completion check, evidence> [label]
Resolution call (UTC): <confirming human; call time or unknown> [label]
Impact:           <users, traffic share, duration from impact endpoints, not the call; data loss evidence or [unverified]>
Detection:        <alert or human report; time to notice> · improvement: <actionable earlier signal and noise tradeoff, or n/a — why>
Timeline (UTC):   <ts — event> … (deploys, config, mitigations, recovery)
Cause:            <established cause, or current explanations with scoped evidence and remaining checks> [label]
Mitigation:       <what a human confirmed applied, when, verified how; attempts with UNKNOWN outcome; what was recommended and not taken>
Worked / slow:    <what helped; what cost time; where the team got lucky>
Follow-ups:       <reuse the checkpoint's IDs/rows: discoveries, actions (owner/due/status), decisions (who asked/decided, UTC), and unknowns with evidence; include rows if the recipient cannot access the source>
Knowledge repo:   <root> · read: <paths> · missing or stale: <paths>
Evidence:         <sanitized excerpts or access-controlled references — pasted outputs, sre-assistant agent packets, dashboard ranges — each with its label; credential-bearing output is never carried: record that it was exposed, where, and to whom>

Next owners:
1. `scribe`, postmortem mode — this packet is the source; `incident-command` holds the
   authoritative live timeline if one was kept.
2. `scribe`, knowledge closeout mode — enrich the same Follow-ups record with artifact dispositions,
   preserving distinct scopes/owners/evidence rather than making another list; include the target revision binding the human
   supplies for any `prepared` disposition.
```
