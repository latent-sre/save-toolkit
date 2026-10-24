---
name: runbook
description: >-
  Write or update an operational runbook: check/recover/verify/roll-back/escalate steps for one
  failure mode, the living-runbook accretion that grows it after every incident, and importing
  Confluence runbooks into the repo. Triggers: 'help me write a runbook for restarting pricing',
  'update the runbook from this incident', 'import this Confluence runbook', 'apply the runbook
  structure'. Direct operational-document writing belongs to scribe, which selects runbook mode
  and applies this skill; retrospectives use postmortem.
argument-hint: "[service or tool]"
---

Write for the tired responder: terse, copy-pasteable, unambiguous. Read actual config, unit files,
and existing docs before drafting; memory is not configuration evidence.
A runbook covers one alert, task, or failure mode. Active response stays with the human responder
and `incident-investigation`; this skill documents the procedure.

## Match the edit

For a contact, link, or wording-only correction, patch affected text and links from supplied evidence;
preserve the existing structure, IDs, status and history. Report unrelated gaps without rewriting them.
Changes to actions or decision branches use the procedure-revision path. Bump `version` on any change
to steps, branches, or commands; contact, link, and wording corrections keep it.

For a new runbook or substantial procedure revision, use the [runbook template](./assets/runbook-template.md).
Fill applicable slots; mark only genuinely inapplicable ones `n/a — why`. Missing applicable evidence
stays `[unverified]` with its owner and next check. For a first runbook or thin draft, read the
[worked exemplar](./assets/runbook-example.md); its service, dates and evidence IDs are fictional.

## Status and verification

New runbooks start `status: draft`, with `last_reviewed: null`, `last_verified: null`, and
`verification_evidence: []`. Only human review promotes a draft to `active`; only human/authorized
document review changes `last_reviewed`. Fix a wrong step from evidence or demote to `draft`;
retire a decommissioned service's runbooks.

A named human/service owner runs approved drills; `scribe` records supplied results. Set
`last_verified` only from evidence binding the exact runbook version, target, actor, timestamp,
and passing outcomes for every step claimed. A failed drill or an older version cannot verify the
current procedure; untraversed branches remain untested. On a procedure-version change, retain prior
verification in history and clear `last_verified` and `verification_evidence` until the new version
has qualifying evidence. Otherwise preserve the fields and record missing evidence as `[unverified]`.

## Authoring rules
- **Numbered, imperative steps.** Copy-pasteable commands with real paths/names; placeholders only
  for variable values, each naming its source. No "obviously" or "just".
- **Confirm the target.** Name the service and environment, their authoritative source, and the
  console or read-only check that confirms the current target. A mismatch stops the procedure.
- **Expected output per step** — distinguish an observed result from a cause; give a next check
  or escalation for partial, missing, or failed observations, with a time or attempt bound. A timeout
  does not prove an action had no effect: block retry until the named reconciliation owner uses
  the specified readback to establish what happened and authorizes retry.
- **Verify and recover** — every state-changing action says how to confirm its effect and undo it,
  or what cannot be undone and how to recover. Mark destructive steps with a warning. Classify
  each state-changing step by `production-change-gate`'s tiers and copy the template's approval
  banner unchanged. Record approver, time, and rollback or recovery evidence before execution.
- **Trigger-anchored** — starts from a concrete trigger (this alert/symptom/task), ends at "resolved or
  escalate to <whom>."
- **Preserve command evidence before publishing** — keep `[sourced]` syntax from cited documentation
  separate from execution on the named target. Retain `[verified]` execution only from an incoming
  authorized record binding the exact command, target, actor and result. Without it, execution stays
  `[unverified]`; an unsourced command also stays `[unverified]`. Never execute from this documentation
  lane, including a read-only command, merely to confirm syntax or output.

## Before you publish — read it back as the responder

Read as a responder new to this service. For a procedure change, walk its affected branches in order;
the first unsupported decision is a finding. Check direct branch entry and inherited effects,
inspection before destruction, and repeat-safe rollback. For a bounded correction, check only the
changed claim and links.

Apply the authoring rules above and confirm the escalation contact is staffed, not an unmonitored alias.

## Living runbooks — every incident leaves the runbook better

For steps actually exercised, record **held** (worked as written) or **contradicted** (wrong, unsafe,
or a different result); record **missing** when the responder needed an absent step. Untraversed
branches remain untested. Each observed outcome becomes an `operational-learning` disposition at
closeout. Capture missing, contradicted, or newly required steps from the advisor's Follow-ups or
a helper's `Durable discovery candidates`. A direct request that supplies the resolved incident's
record is also an intake: edit in runbook mode and cite the PR or evidence reference in the history
row; `prepared` and `proposed` appear only when an `operational-learning` closeout produced them.
Append one Incident history row (template slot) pinned to the `version` used; rows are evidence,
never rewritten.
After three incidents repeat the same manual fix, record an automation candidate in the history row's
follow-up column; assess it with `toil-reduction` before filing. Progress from a documented manual
procedure to a checked human-run script, then automation supported by evidence.

## Importing runbooks from Confluence

Import one-way: the repo becomes the living copy. Read
[Confluence import](./references/confluence-import.md) for conversion, mapping, and provenance.
A human or `software-engineer` runs [confluence_to_runbook.py](./scripts/confluence_to_runbook.py)
on the exported page JSON without overwriting an existing runbook. Imported command claims stay `[unverified]`;
keep the source page URL, version, and dates it writes into References.

## Alert and service links

Link every paging alert to its runbook; the service card links one runbook per failure mode.
Return the runbook path and paging-alert names
to the caller; recommend `observability-engineer` for alert-definition changes. Use the existing
alert or notification route's runbook-link mechanism. Grafana commonly uses `runbook_url`; a Splunk
lookup or Moogsoft enrichment is an option only when that route uses it. Missing or contradicted
runbooks follow the closeout path above.
