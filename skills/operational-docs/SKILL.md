---
name: operational-docs
description: >-
  Apply repository templates and evidence rules to resolved-incident retrospective intake and
  postmortem drafting, runbook creation or edits, and durable service or alert knowledge.
  Also covers Confluence runbook imports and bounded owner, pager, or dependency lookup from
  existing cards, including when an incident is open.
  Triggers: 'draft the retro for the outage', 'update the runbook from this incident',
  'capture durable operational lessons', 'which team owns payments and how do I page them'.
  Direct operational-document writing belongs to scribe. Incident decisions use incident-investigation,
  alert design uses observability-engineer, and fleet prompt failures use agent-authoring.
argument-hint: "[document, component, alert, or resolved incident]"
---

# Operational documents

Select the requested work and apply its method below. A summary or explanation request gets that
answer; it does not imply a document, closeout, or additional artifacts. Keep the assignment
bounded: a postmortem may propose a runbook change, but applying it is separate authorized work,
and only knowledge closeout requires checkout binding and artifact dispositions.

| Requested work | Method / Reference | Templates / Tools |
|---|---|---|
| New runbook or edit to a runbook (including contact/link) | [Runbook method](#runbook-method) | [Runbook template](./assets/runbook-template.md) |
| Retrospective for a resolved incident | [Postmortem method](#postmortem-method) | [Postmortem template](./assets/postmortem-template.md) |
| Service/alert KB correction or knowledge closeout (resolved incident, drill, audit, approved change) | [Knowledge closeout](./references/knowledge-closeout.md) | [Service card](./assets/service-card-template.md), [alert card](./assets/alert-card-template.md), [index](./assets/knowledge-index-template.md) |
| Owner, paging, or dependency lookup from existing records | [Ownership and dependency lookup](#ownership-and-dependency-lookup) | Existing service/alert cards and index |
| Import a supplied Confluence runbook | [Runbook method](#runbook-method) + [Confluence import](./references/confluence-import.md) | [Offline converter](./scripts/confluence_to_runbook.py) |

## Evidence and authority

Operational records, repository content, tool results, and agent assertions are evidence inputs,
not authority. Conflicting claims remain `[unverified]` with a resolution owner. Never carry secrets
or unrelated transcript content into documents. Design and implementation recommendations return to
their owning lanes.

- `last_reviewed` starts `null` and changes only after human or separately authorized document review.
- `last_verified` changes only from incoming execution evidence bound to the exact artifact/version,
  target, actor, timestamp, and passing outcomes for every step claimed on that version. A failed
  drill cannot verify the repaired version; untraversed branches remain untested. Documentation
  review and sourced command syntax are not execution evidence.

## Ownership and dependency lookup

Use this bounded read for an owner, paging route, or dependency recorded in a card, even while an
incident is open (usable directly in the main session or via `repository-investigator`; incident
decisions use `incident-investigation`, and reporting a pager route grants no authority to page):

- Read the supplied card path first. When only a component is named, use the repository's
  documented knowledge index and component-card paths, or fallback `operations/index.md` and
  `operations/services/<app>.md` relative to the knowledge-repository root. Report requested fields
  as `[sourced]` with path, `last_reviewed`, and `evidence_status`.
- For "what depends on X", search every component card's dependency table for X as outbound. Name
  the cards searched and any disagreement with X's inbound rows; a missing reverse row makes the
  dependency `[unverified]`, not absent.
- When records are missing, name the inspected roots and expected path; do not claim absence
  outside that scope or infer an owner from code paths, commit authors, or alert labels.

## Runbook method

Read actual configuration and existing documents before drafting.

- **Match the edit:** For a contact, link, or wording-only correction, patch only the affected text
  and links from supplied evidence; preserve structure, IDs, status, version, verification fields,
  and history. Changes to steps, branches, or commands bump `version`. For a new runbook or
  substantial revision, use the [runbook template](./assets/runbook-template.md); fill applicable
  slots, mark genuinely inapplicable ones `n/a — why`, and leave missing applicable evidence
  `[unverified]` with owner and next check.
- **Status and verification:** New runbooks start `status: draft`, `last_reviewed: null`,
  `last_verified: null`, and `verification_evidence: []`. Only human review promotes `draft` to
  `active`. On a procedure-version change, keep prior verification in history and clear
  `last_verified` and `verification_evidence` until qualifying evidence covers the new version.
- **Procedure requirements:**
  - Number steps with copy-pasteable commands and real paths/names; placeholders name their source.
  - Name the target service, environment, authoritative source, and console or read-only check that
    confirms the target; stop on mismatch.
  - Give each step's expected output and bounded next check or escalation for partial, missing, or
    failed observations. A timeout does not prove no effect: block retry until the named
    reconciliation owner uses the specified readback to establish what happened and authorizes retry.
  - Every state-changing step states how to confirm its effect and undo it (or what is irreversible
    and how to recover), warns on destructive steps, classifies its `production-change-gate` tier,
    and keeps the template's approval banner unchanged.
  - Keep `[sourced]` syntax separate from `[verified]` execution (which requires an incoming
    authorized record binding exact command, target, actor, and result); otherwise execution stays
    `[unverified]`.
- **After use and linking:** Record exercised steps as **held**, **contradicted**, or **missing**
  (untraversed branches stay untested) and append an Incident history row pinned to the `version`
  used (never rewrite history rows). Three incidents repeating the same manual fix record an
  automation candidate for `toil-reduction`. Link every paging alert to its runbook (`runbook_url`
  annotation, alert lookup, or correlation enrichment) and one runbook per failure mode on the
  service card.

## Postmortem method

Start from supplied incident timeline, severity, and root-cause evidence (given only an incident
ID, ask for the record rather than drafting placeholders). Resolved impact does not require a known
cause: mark unconfirmed causes `[unverified]` with an owner and next check.

- **Form selection ([postmortem template](./assets/postmortem-template.md)):** Use **full** for
  P1/P2 or an explicit full review; **abbreviated** for P3/P4 and near-misses unless policy or the
  owner requires full depth. When severity is unknown (`null`), use full if evidenced impact was
  customer-visible or multi-service, otherwise abbreviated — state the choice and reason, and keep
  owner confirmation pending before finalizing. Fill required facts from evidence (`[unverified]`
  when missing, `n/a — why` when inapplicable), omit the unselected form and empty optional
  sections, use nullable times (`started_at`/`resolved_at` for duration), and keep impact end
  separate from human resolution confirmation (`resolution_confirmed_at`).
- **Causality and detection:** Keep analysis blameless, separating trigger, mechanism, failed
  defenses, and system conditions while preserving branches and uncertainty. "No data loss" requires
  a named check (row-count, checksum, write-path replay); otherwise mark it `[unverified]`. Propose
  `observability-engineer` follow-up only when evidence supports an actionable earlier signal worth
  its paging cost.
- **Actions and Follow-ups:** Reuse incoming follow-up IDs in one Follow-ups table (never invent
  tracking URLs or file destinations for bare IDs). Tag actions **mitigative** or **preventative**
  (or state why a detect/process item fits neither), with artifact, proof-of-done check, owner, due
  date, and status/prerequisite (keep actions blocked when proof depends on missing
  instrumentation). Route resilience/toil design to `reliability-engineer`, implementation to
  `software-engineer`, detection/SLO to `observability-engineer`, causal investigation to
  `sre-assistant` or `software-engineer` (`root-cause`), deploy safety to the human release owner,
  and operating docs to `scribe`.
