# Runbook method

A runbook covers one alert, task, or failure mode. Read actual configuration and existing documents
before drafting; memory is not configuration evidence.

## Match the edit

For a contact, link, or wording-only correction, patch affected text and links from supplied evidence;
preserve structure, IDs, status, version, verification fields, and history. Report unrelated gaps
without rewriting them. Changes to steps, branches, or commands bump `version`.

For a new runbook or substantial procedure revision, use the [runbook template](../assets/runbook-template.md).
Fill applicable slots; mark only genuinely inapplicable ones `n/a — why`. Missing applicable evidence
stays `[unverified]` with its owner and next check. For a first runbook or thin draft, read the
[worked exemplar](../assets/runbook-example.md); its service, dates and evidence IDs are fictional.

## Status and verification

New runbooks start `status: draft`, `last_reviewed: null`, `last_verified: null`, and
`verification_evidence: []`. Only human review promotes a draft to `active`. Fix a wrong step from
evidence or demote to `draft`; retire a decommissioned service's runbooks.

A named human/service owner runs approved drills; `scribe` records supplied results under the
[shared evidence rules](../SKILL.md#evidence-and-authority). An older version cannot verify the
current procedure. On a procedure-version change, retain prior verification in history and clear
`last_verified` and `verification_evidence` until the new version has qualifying evidence.
Otherwise preserve the fields and record missing evidence as `[unverified]`.

## Procedure requirements

- Number steps and supply copy-pasteable commands with real paths/names. Variable placeholders
  name their source.
- Name the service and environment, their authoritative source, and the console or read-only
  check that confirms the current target. A mismatch stops the procedure.
- Give each step's expected output and a bounded next check or escalation for partial, missing,
  or failed observations. An observed result is not automatically a cause. A timeout does not
  prove an action had no effect: block retry until the named reconciliation owner uses the
  specified readback to establish what happened and authorizes retry.
- Every state-changing action says how to confirm its effect and undo it, or what cannot be
  undone and how to recover. Warn on destructive steps. Classify each state-changing step by
  `production-change-gate`'s tiers and copy the template's approval banner unchanged. Record
  approver, time, and rollback or recovery evidence before execution.
- Start from a concrete trigger and end at resolution or a named escalation contact. Confirm
  that contact is staffed rather than an unmonitored alias.
- Keep `[sourced]` syntax from cited documentation separate from execution on the named target.
  Retain `[verified]` execution only from an incoming authorized record binding the exact command,
  target, actor and result. Without it, execution stays `[unverified]`; an unsourced command also
  stays `[unverified]`. Never execute from the documentation lane, even a read-only command, to
  fill syntax or output evidence gaps.

Before publishing a procedure change, walk the affected branches in order as a responder new to
the service; the first unsupported decision is a finding. Check direct branch entry, inherited
effects, inspection before destruction, and repeat-safe rollback. For a bounded correction,
check only the changed claim and links.

## After use

For steps actually exercised, record **held** (worked as written), **contradicted** (wrong, unsafe,
or different result), or **missing** (an absent needed step). Untraversed branches remain untested.
Capture missing, contradicted, or newly required steps from the advisor's Follow-ups, a helper's
`Durable discovery candidates`, or a direct request supplying the resolved incident record.
Append an Incident history row pinned to the `version` used, with the PR or evidence reference;
history rows are evidence, never rewritten.

At an invoked [knowledge closeout](./knowledge-closeout.md), each observed outcome receives a
disposition. `prepared` and `proposed` appear only when that closeout produced them; a direct
runbook edit does not create a separate closeout record. After three incidents repeat the same
manual fix, record an automation candidate in the history row's follow-up column; assess it with
`toil-reduction` before filing. Progress from a documented manual procedure to a checked human-run
script, then automation supported by evidence.

## Imports and links

For one-way Confluence import, read [Confluence import](./confluence-import.md). A human or
`software-engineer` runs [confluence_to_runbook.py](../scripts/confluence_to_runbook.py) on supplied
exported bytes without overwriting an existing runbook. Keep source URL, version, and dates;
imported command claims stay `[unverified]`.

Link every paging alert to its runbook; the service card links one runbook per failure mode. Return
the runbook path and paging-alert names to the caller; recommend `observability-engineer` for
alert-definition changes. Use the existing alert or notification route's link mechanism. Grafana
commonly uses `runbook_url`; a Splunk lookup or Moogsoft enrichment applies only where that route
uses it. Missing or contradicted runbooks follow the closeout path above.
