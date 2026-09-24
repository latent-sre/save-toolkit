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

## Match the edit

For a contact, link, or wording-only correction, patch affected text and links from supplied evidence;
preserve the existing structure, IDs, status and history. Report unrelated gaps without rewriting them.
Review and rehearsal dates follow their evidence rules below; a small edit proves no operational step.
Changes to actions or decision branches use the procedure-revision path. Bump `version` on any change
to steps, branches, or commands; contact, link, and wording corrections keep it.

For a new runbook or substantial procedure revision, use the [runbook template](./assets/runbook-template.md).
Fill applicable slots; mark only genuinely inapplicable ones `n/a — why`. Missing applicable evidence
stays `[unverified]` with its owner and next check. For a first runbook or thin draft, read the
[worked exemplar](./assets/runbook-example.md); its service, dates and evidence IDs are fictional.

## Keep it current through rehearsal
A runbook answers one alert, task, or failure mode; the service card links one runbook per failure
mode. A named human/service owner runs approved, realistic drills; `scribe` records supplied results.
Change `last_verified` only from evidence bound to exact artifact/version, target, actor, timestamp,
and a passing outcome for every step claimed, on the runbook `version` being stamped; a drill that
exposed a bad step, or ran an older version, never moves it. Otherwise leave it unchanged and label
the rehearsal `[unverified]`.

## Authoring rules
- **Numbered, imperative steps.** Copy-pasteable commands with real paths/names; placeholders only
  for variable values, each naming its source. No "obviously" or "just".
- **Expected output per step** — distinguish an observed result from a cause; give a next check
  or escalation for inconclusive, missing, or failed observations.
- **Verify and recover** — every state-changing action says how to confirm its effect and undo it,
  or what cannot be undone and how to recover. Mark destructive steps with a warning. Classify
  each state-changing step by `production-change-gate`'s tiers and copy the template's approval
  banner unchanged: only actions eligible under its incident-fast-path checklist use that path.
  In a declared incident ITO approves the exact command or bounded envelope in the TLC;
  ineligible actions and Tier 3 retain the full gate. Suspected compromise or integrity loss
  goes to the human security owner. Outside an incident use the full gate. The runbook records
  approver, time, and rollback or recovery evidence before execution.
- **Trigger-anchored** — starts from a concrete trigger (this alert/symptom/task), ends at "resolved or
  escalate to <whom>."
- **Current or demoted** — date it, own it; fix a wrong step from evidence or drop the runbook to
  `status: draft`; a decommissioned service's runbooks go `status: retired`. A wrong active runbook
  is worse than none.
- **Machine-linkable frontmatter** — new runbooks use the template's YAML frontmatter. A new
  runbook starts `status: draft`; only a human review promotes it to `active`. Both dates
  (`last_reviewed`, `last_verified`) start `null`;
  only human/authorized document review changes `last_reviewed`, and only bound rehearsal evidence
  changes `last_verified`.
- **Preserve command evidence before publishing** — keep `[sourced]` syntax from cited documentation
  separate from execution on the named target. Retain `[verified]` execution only from an incoming
  authorized record binding the exact command, target, actor and result. Without it, execution stays
  `[unverified]`; an unsourced command also stays `[unverified]`. Never execute from this documentation
  lane, including a read-only command, merely to confirm syntax or output.

## Before you publish — read it back as the responder

Read as a responder new to this service. For a procedure change, walk its affected branches in order;
the first unsupported decision is a finding. Check target and placeholder sources, inherited effects
when a branch is entered directly, inspection before destruction, and repeat-safe rollback. For a
bounded correction, check the changed claim and links. The [worked exemplar](./assets/runbook-example.md)
demonstrates these checks.

Four questions that surface most of them:

- **Can you paste each command?** Every variable names its source command or panel.
- **What partly worked?** Each expected-output line gives the next step for partial/failed results.
- **When do you stop?** Bound time/attempts and name the escalation or alternate path.
- **Who answers at 3 a.m.?** Confirm the escalation contact is staffed, not an unmonitored alias.

Missing evidence stays `[unverified]`, never invented.

## Living runbooks — every incident leaves the runbook better

For steps actually exercised, record **held** or **contradicted**; record **missing** when the
responder needed a step that did not exist. Untraversed branches remain untested. Each observed
outcome becomes an `operational-learning` disposition at closeout. A direct request that supplies
the resolved incident's record is also an intake: edit in runbook mode and cite the PR or evidence
reference in the history row; `prepared` and `proposed` appear only when an `operational-learning`
closeout produced them. Append an Incident history row (template slot) pinned to the `version`
used; rows are evidence, never rewritten. A contradicted step is fixed now or the runbook drops to
`status: draft`; `last_verified` moves only on binding rehearsal evidence. The full accretion
protocol is in [living runbooks](./references/living-runbooks.md).

## Importing runbooks from Confluence

Import one-way: the repo becomes the living copy. Read
[Confluence import](./references/confluence-import.md) for conversion, mapping, and provenance.
A human or `software-engineer` runs [confluence_to_runbook.py](./scripts/confluence_to_runbook.py)
on the exported page JSON: draft frontmatter, mapped headings, visible unmapped content, counted
macro losses, and no overwrite of an existing runbook. Imported command claims stay `[unverified]`;
keep the source page URL, version, and dates it writes into References.

## Alert → runbook links and the Crawl → Walk → Run path

Link every paging alert to its runbook. The responder investigates with `incident-investigation` and
may dispatch `sre-assistant`; code defects go to `software-engineer`. A missing or contradicted
runbook becomes an `operational-learning` disposition for `scribe`, never a chat-only update or an
unsupported `last_verified` change.

For repeated mechanical steps: document the manual procedure, wrap it in a checked human-run script,
then automate after evidence; assess the candidate with `toil-reduction` before filing it. Store the
runbook link in the backend's native field: Splunk lookup,
Grafana `runbook_url`, Wavefront runbook link, or Moogsoft enrichment.
