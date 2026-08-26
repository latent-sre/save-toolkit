# Command and communications

Use this reference to establish command roles, maintain the authoritative incident record, prepare
stakeholder communications, or decide whether to downgrade or close. Technical investigation stays
with the typed `sre` agent, and every production effect stays with the named human release owner.

## Run the response

Once declared, assign an **incident commander** who runs the process rather than the debugging.

- Keep the response moving toward the fastest safe mitigation; delegate technical RCA to the typed
  `sre` agent and remediation to a human release owner.
- Assign Investigation, Operations/remediation, and Communications/timeline owners. For a large P1,
  split Communications and Timeline/Scribe from the commander. During the live incident the scribe
  is a named human, not the typed `scribe` documentation agent.
- Convert every “someone should” into an action with one owner and a visible status.
- Record facts, hypotheses, decisions, attempts, and results in UTC. Mark uncertainty rather than
  smoothing it away.
- Keep the current focus to one sentence so parallel responders know what is being tested or
  mitigated now.

## Sustain command

Command decays over a long incident, and the decay is invisible to the person it is happening to.
These are checkpoints, not judgment calls left to the commander.

- **Unclaimed command is the default failure.** If no commander is present, the first qualified
  responder assumes it and records the name and UTC time. An incident whose commander is assumed
  rather than declared has none.
- **Hand over by read-back.** The incoming commander restates current severity, impact, current
  focus, and open actions with owners; the outgoing commander confirms that restatement before
  releasing. Record both names and the UTC time. A one-way "you have it now" drops state at exactly
  the moment the written record is least complete.
- **Watch span of control.** When open actions outgrow what one commander can track, or independent
  workstreams appear, split into sub-teams with one named lead each reporting a single status line
  up. Splitting late costs more than splitting early.
- **Relief is scheduled, not noticed.** At two hours of continuous command, and hourly after, the
  commander records either the named relief or the reason command is not changing hands. The
  checkpoint is mandatory; changing hands is not. Fatigue cannot be self-detected, so the trigger is
  the clock rather than the commander's sense of being fine — but a handover mid-mitigation carries
  its own risk, and the commander is the one positioned to weigh that against it.

## One authoritative status block

```text
Incident: <title>   Severity: <P1|P2|P3|P4>   Status: <investigating|mitigating|monitoring|resolved>
Impact: <who/what, since when, trend>
Roles: IC=<>   Investigation=<>   Ops=<>   Comms/Timeline=<>
Timeline (UTC): <timestamp — observed event or decision> …
Current focus: <the one thing the response is doing now>
Mitigation decision: <chosen|pending — rationale and human owner>
Open actions: <owner — item — Instrumentation prerequisite: signal/exporter/config or none — ready|blocked — status>
Next update: <HH:MM UTC>
```

Update this block in place. Do not fork separate severity, timeline, and mitigation records.

## Communications cadence

Use the fixed cadence from the severity rubric even when there is no new result: say “still
investigating” and name the next update time. Silence reads as loss of control. Keep every update
plain-language, honest about confidence, and explicit about user impact. For P1, the first external
update goes out within the hour.

- **Initial:** What is known (symptom and impact), provisional severity, scope, when impact began,
  “we are investigating,” and the next update time.
- **Update:** What changed since the previous update, current state (`investigating`, `mitigating`,
  or `monitoring`), mitigation progress or ETA, and the next update time.
- **Resolution:** When impact ended, root-cause summary or `[unverified] — under investigation`,
  what was done, follow-ups with owners, and the required retrospective commitment: a full
  blameless postmortem for P1, a postmortem for P2, or an abbreviated postmortem for P3. P4 follows
  normal work-queue policy.

## Downgrade and resolve

Downgrade only when current impact, scope, and trend fit the lower tier; record why and notify the
same audience that received the higher classification.

Resolve only after the typed `sre` investigator confirms that user impact has ended and the same
golden signals have returned to baseline and remained there for the stated sustained window. A
single green point is not enough for a metastable service. Keep the incident in `monitoring` until
that evidence permits terminal resolution.

Send the resolution update, then return the UTC timeline, its evidence labels, and proposed
next-phase work to the caller. After resolution, the caller separately dispatches typed `scribe`
for the durable postmortem and operational-learning closeout and typed `observability-engineer` for
detection changes. Neither typed lane is part of live recovery confirmation.
