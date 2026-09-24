---
schema_version: 1
runbook_id: <stable-runbook-slug>
service_id: <stable-service-slug>
status: draft | active | retired
alert_names: []
owner: <team/role>
severity: <P1|P2|P3|P4 / page | ticket>
source_revision: <repository@short-commit or reviewed release identifier>
last_reviewed: null
last_verified: null
verification_evidence: []
version: 1
---

# Runbook: <concise title / the alert this answers>

## Purpose & scope
What this runbook handles: <…>
**Out of scope** (do NOT use this for): <…>

## Trigger
The exact alert/symptom that brings you here: <alert name + condition, or observed symptom>
Dashboard: <link>  ·  Source/repo: <link>

## Prerequisites
- Access: <roles, Apps Manager org/space, VPN, tools>
- Tools: <Apps Manager or Cloud Console, Grafana, Splunk, Wavefront or PCF App Metrics; cf CLI v8 or gcloud only if installed>
- Useful links: <dashboard, saved search, prior postmortem>

## Triage / first checks
1. Confirm impact (golden signals): <Apps Manager view, Grafana panel, Splunk search, or Wavefront chart>
2. Decision tree:
   - If <condition A> → go to Procedure step <n>.
   - If <condition B> → this isn't the right runbook; see <other runbook> / escalate.

## Procedure
> Mark destructive steps ⚠️. A Tier 2 step (reversible live change) or Tier 3 step (destructive or
> access-path change) needs approval before you run it. In a declared incident, ITO approves the
> exact command, or a bounded set of them, in the TLC. Use `production-change-gate`'s incident
> fast-path checklist only for eligible actions. All other actions retain the full process,
> including a whole-app restart or resize, restage, a new artifact, unknown droplet state, and Tier 3.
> Suspected compromise or integrity loss exits the shortcut to the human security owner.
> Outside an incident, use the full process.
> Record approver, time, and rollback with the change. Impact growing or customer-visible and no
> incident open → start one through the team's incident process first.

1. <imperative step>
   Apps Manager (PCF) or Cloud Console (Cloud Run): <org / space → app → view → control and value>, or
   ```bash
   <cf or gcloud command — the console action's equivalent, for responders who have the CLI>
   ```
   Expected: <what you should see, in console terms first>, sorted into worked / partly worked / failed, each with where to go
   If not within <N min or N attempts>: → <the step or escalation row to go to> (every step that
   changes state or might not work carries this line; it is the step's own exit)
2. <next step> — every step gets its Expected line, including waits and evidence captures …

## Verification
How to confirm the issue is resolved: <command/dashboard + expected healthy state>

## Rollback / cleanup
How to undo each change above (reverse order): <exact steps>
Safe-abort: <how to stop mid-procedure without making it worse>

## Escalation
| When (condition / time elapsed) | Escalate to | How to reach |
|---|---|---|
| <e.g. not resolved in 15 min, or blast radius growing> | <role/team> | <pager / channel> |
| <platform-side signal: many apps / failing cells> | platform team | <…> |

Hand over: trigger, evidence, attempted steps, current state, and the current owner.

## Communication
- Notify: <channel / stakeholders> · Cadence while active: <the incident's agreed update interval>
- Initial / update / resolved message owner: <role>

## Post-Incident
- [ ] Append an Incident history row (below): version used, steps that held, steps that failed or
      were missing, follow-up id.
- [ ] Create a learning disposition for every missing, contradicted, or newly useful step.
- [ ] **Update this runbook** from supplied evidence when a disposition requires it.
- [ ] Change `last_verified` only when incoming rehearsal evidence binds this exact runbook version,
      target, actor, timestamp, and outcome; otherwise leave it unchanged (including `null`) and
      record the gap.
- [ ] File follow-up **automation candidates** (Crawl→Walk→Run) as tickets after a toil assessment
      of frequency, effort, and maintenance cost.
- [ ] If this was an incident, after recovery, hand the timeline and evidence to the `scribe` agent for retrospective documentation.

## Incident history (living-runbook accretion)
> Append one row per incident or rehearsal that used this runbook — newest first. Rows are evidence:
> never rewrite or delete them. A "failed / missing" cell that stays empty across many incidents is
> signal too. Three rows with the same manual fix ⇒ file the Crawl→Walk→Run automation candidate.

| Date (UTC) | Incident / drill ref | Version used | Steps that held | Steps that failed / were missing | Follow-up (disposition / PR or evidence reference) |
|---|---|---|---|---|---|
| <YYYY-MM-DD> | <postmortem or drill link> | <n> | <e.g. steps 1–3> | <e.g. step 4 output differed; no rollback for step 5> | <PR or evidence reference; closeout disposition id if one exists> |

## References
- Related runbooks: <…>
- Postmortems: <…>
- Alert definition / SLO: <…>
- Service card / alert card / knowledge index: <…>
- Provenance: <PR, target revision, and evidence references>
