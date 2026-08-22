---
name: runbook
description: >-
  Apply the standard operational-runbook structure after the scribe agent selects runbook mode, or
  when a user explicitly invokes this skill. Covers check/recover/verify/roll-back/escalate
  structure for one failure mode, the living-runbook accretion protocol that grows a runbook after
  every incident, and importing Confluence runbooks into the repo. Direct operational-document
  writing belongs to scribe; retrospectives use postmortem. Triggers: 'runbook mode selected',
  'apply the runbook structure', 'update the runbook from this incident', 'import this Confluence
  runbook'.
argument-hint: "[service or tool]"
---

Runbooks are read at 3 a.m. by someone who is tired — usually future-you. Terse, copy-pasteable, zero ambiguity.

Investigate before writing: read the actual config, compose/unit files, and any existing docs. A runbook written from memory documents the lab you *think* you have.

## Required structure (every slot filled or marked "n/a — why")

Full fill-in template: [runbook template](./assets/runbook-template.md) — copy it to start; it
carries every required slot.

Rules:
- Every command copy-pasteable as written — real paths and real names. A `<placeholder>` is allowed only for truly variable values, and then say where to find the value.
- "Common failures" lists only what has been observed or is clearly plausible for this service — no padding to make the section look complete.
- If supplied evidence is insufficient to establish that a command works (service not running, no
  access), mark it `[unverified]` rather than presenting it as tested.

## Runbook vs playbook vs SOP
- **Runbook** — steps to handle *one* alert/task/failure mode (this template).
- **Playbook** — a broader response *strategy* orchestrating multiple runbooks (e.g. a major-incident
  playbook). Ownership map only—not a load: the `incident-command` skill owns live-incident coordination.
- **SOP** — a fixed procedure for routine operations (not incident-driven).

Keep them current through evidence-backed rehearsal. A named human or service owner runs game days
or drills under approved, realistic conditions; `scribe` only records the supplied results. Preserve
`last_verified` only when incoming evidence binds the exact artifact/version, target, actor,
timestamp, and outcome. Otherwise leave it unchanged and label the rehearsal `[unverified]`.

## Authoring rules
- **Numbered, imperative steps.** Copy-pasteable commands with real values or clearly templated
  `<PLACEHOLDER>`s. No "obviously" or "just".
- **Expected output per step** — so the reader knows it worked before moving on.
- **Verify and roll back** — every state-changing action has "how to confirm it worked" and "how to undo
  it." Mark destructive steps with a warning. Tier 2/3: record explicit human approval for the exact
  command/target plus rollback evidence before execution.
- **Trigger-anchored** — starts from a concrete trigger (this alert/symptom/task), ends at "resolved or
  escalate to <whom>."
- **Current or deleted** — date it, own it, prune what's wrong. A wrong runbook is worse than none.
- **Machine-linkable frontmatter** — give each runbook the template's YAML frontmatter. Both dates
  (`last_reviewed`, `last_verified`) start `null`;
  only human/authorized document review changes `last_reviewed`, and only bound rehearsal evidence
  changes `last_verified`.
- **Preserve command evidence before publishing** — use only supplied, authorized execution evidence
  for command claims. If that evidence is absent, mark the command `[unverified]`; never execute from
  this documentation lane, including a read-only command, merely to confirm syntax or output.

## Living runbooks — every incident leaves the runbook better

Every incident or drill that touches a runbook yields one outcome per step — **held**,
**contradicted**, or **missing** — and each becomes an `operational-learning` disposition at
closeout. Append an Incident history row (template slot) pinned to the `version` used; rows are
evidence, never rewritten. A contradicted step is fixed now or the runbook drops to
`status: draft`; `last_verified` moves only on binding rehearsal evidence. The full accretion
protocol and its sourced rationale (playbooks ≈ 3x MTTR improvement) are in
[living runbooks](./references/living-runbooks.md).

## Importing runbooks from Confluence

Existing Confluence runbooks are imported into the repo — one direction, repo becomes the living
copy. The conversion procedure, slot mapping, and provenance rules are in
[Confluence import](./references/confluence-import.md), and
[confluence_to_runbook.py](./scripts/confluence_to_runbook.py) does the mechanical part: a human
(or the `sde` agent) runs it on an exported page to produce a draft with frontmatter pre-filled,
headings mapped to template slots, unmapped content kept visible, and macro losses counted. Two
rules travel ahead of the detail: imported command claims arrive `[unverified]` no matter how
authoritative the page looked, and the source page URL plus export date land in the runbook's
References section so the paper trail survives the move.

## Alert → runbook links and the Crawl → Walk → Run path

Link every paging alert to its runbook. When investigation is needed, hand the trigger and evidence
to the `sre` agent; when code remediation is needed, hand the defect and evidence to the `sde` agent.
When a new alert/service, drill, audit, or resolved incident exposes a missing or contradicted
runbook, record an `operational-learning` disposition and have `scribe` prepare the evidence-bound
create/update. Do not let a chat-only observation disappear or silently bump `last_verified`.
If a step is fully mechanical, recommend automating it along the **Crawl → Walk → Run** path: document
the manual steps (crawl), wrap them in a checked script the on-call runs by hand (walk), then trigger
it automatically once proven (run). Data-drive the alert→runbook link so saved searches/alerts surface
the right runbook automatically — each tool in our stack has a mechanism:
- **Splunk:** `... | lookup instructions_lookup alert_type OUTPUT runbook_url`.
- **Grafana:** a `runbook_url` annotation on the alert rule (templated by labels).
- **Wavefront:** the alert's resolution/runbook link, with Mustache-templated targets.
- **Moogsoft:** enrichment that attaches the runbook URL + escalation path to the alert/Situation.

### Worked excerpt — tier-marked steps with provenance

> **Trigger**: alert `checkout-p95-burn-fast` (page).
> **First checks**: `cf app checkout` → expect `6/6 running` [unverified] (illustrative; no transcript is bundled).
> **Procedure step 1** ⚠️ (Tier 2 — needs explicit human approval for this command/target):
> `cf restart-app-instance checkout <idx>` — restarts ONE instance; the other five keep serving.
> **Verification**: p95 back under 800 ms within 10 min on the checkout dashboard.
> **Rollback**: none needed — the restart is the reset. If step 1 ran twice without effect, STOP:
> restart is a stopgap, not a fix — escalate per the Escalation table.
> **Provenance**: this excerpt is illustrative only. First checks, procedure step 1, and any later
> step remain [unverified] until a human tests and records the exact command, target, actor, and result.
