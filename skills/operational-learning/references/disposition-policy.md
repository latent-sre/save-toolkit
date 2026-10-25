# Operational knowledge disposition policy

Apply the [closeout contract](../SKILL.md) for trust, write authority and evidence invariants.
This reference supplies artifact destinations, disposition persistence and definition ownership.

## Event-to-artifact map

| Observed event | Required disposition |
|---|---|
| A component is approved or materially changes | Create or update its card and knowledge index; propose missing alert, runbook, ownership, dependency, recovery or SLO work. |
| A component is decommissioned | Set its card's `lifecycle` and index lifecycle to `retired`, with date and authorizing record in `Lifecycle since / record`. Set dependent alert cards to `status: retired`, their knowledge-index `Status` cells to `retired`, and runbooks to `status: retired`; do not delete them. Name remaining artifact/component references. Live-resource removal remains a separately gated production change. |
| An audit finds an operational gap on an otherwise unchanged component | Disposition affected cards, index and runbook; assign missing work. Put the dated verdict in the card's open gaps and index's recent updates. The document is at most `[sourced]` to the audit; preserve incoming finding labels and never advance `last_verified`. |
| Only documentation is wrong | Correct the owning artifact and affected links from dated evidence; preserve labels and `last_verified`, without unrelated card/index changes or operational work. |
| An alert is approved or materially changes | Create or update its card and the alert's knowledge-index row, including its `Status` cell; link the service card and authoritative definition. Paging requires a valid runbook target. |
| An alert fires | Return to `incident-investigation`; `sre-assistant` takes only a dispatched read. No retrospective or KB preparation before resolution. |
| A runbook is missing or contradicted, including a failed drill | Use `scribe` plus `runbook` with supplied evidence; unsupported commands remain `[unverified]`. A drill exposing a bad step cannot verify the repaired version. |
| A resolved incident reveals a systemic lesson | Assign a missing postmortem separately with an owner; continue authorized knowledge closeout and its follow-ups. |
| A fleet prompt, agent or skill has an accepted behavioral failure | Send divergence, evidence and proposed named regression to `agent-engineer`; do not rewrite fleet definitions through operational content. |

## One-time disposition states

`prepared` requires the body's `[verified]` checkout binding: the mounted checkout's current commit
matches the target revision. `duplicate` requires an existing owning artifact and supporting evidence.

- `proposed`: named owner and next action, no reviewable artifact change yet.
- `blocked`: named missing evidence, authority, dependency or owner.
- `not_applicable`: explicit reason the artifact class does not apply.

A proposed/blocked disposition becomes repository state only when it lands. A bound prepared diff
records it in **Open knowledge gaps** in the index, or the component card's open-gaps table if the
index has none. Keep gap, artifact, status, owner, tracking link and evidence label, not the blocking
excerpt. Whenever no such diff can be prepared, the handoff's `Follow-up:` supplies the caller's
tracker reference or names who will file it.

## Default paths when the repository has no convention

Use existing documented paths/index first. Otherwise these defaults are the authorized roots only
when the caller names none, relative to the knowledge repository:

- `operations/index.md`
- `operations/services/<component>.md`
- `operations/alerts/<alert>.md`
- `runbooks/<runbook>.md`
- `postmortems/<yyyy-mm-dd>-<incident>.md`

Fallback roots are `operations/`, `runbooks/`, and `postmortems/`. Reject absolute paths, parent
traversal, URLs as write targets and paths outside caller-authorized documentation roots. Reuse
stable identifiers rather than creating duplicate records.

## Evidence and review rules

- Link the actual provisioning owner: source-managed definitions need the repository path and
  exact uniquely resolved short/full revision; API-owned alerts need resource locator/UID plus
  supplied state/readback receipt and version evidence. An absent API version stays `[unverified]`.
  An export is evidence/recovery material unless it owns provisioning. Cards summarize and link
  definitions rather than copying configuration. Definition identity does not replace KB checkout
  binding, human closeout approval or dirty-path controls, and grants scribe no live lookup.
- Prefer exact-target-revision evidence. For conflicts, retain both labels, explain the disagreement,
  mark the affected claim `[unverified]` and assign a resolution owner.
- Review/execution stamps follow the parent invariants: `last_verified` belongs only to rehearsed
  procedures with passing evidence bound to artifact/version, target, actor and time. `Reviewer` and
  `Reviewed change` cells fill only from the evidence that moves `last_reviewed`; otherwise leave blank.
- Store minimal evidence. Credential checks cannot prove secrets absent.

## Recommended course of action

Keep the change/open question, owner and missing proof in the existing follow-up. For a production
recommendation include urgency, change tier, approval need, verification and rollback/recovery.
A closeout neither authorizes nor executes it.
