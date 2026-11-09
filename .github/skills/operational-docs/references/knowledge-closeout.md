# Knowledge closeout

Use this method only for an invoked closeout. A durable discovery needs an explicit disposition:
a reviewable repository change or a tracked, owned handoff. Use the
[service card](../assets/service-card-template.md) for an approved new or changed component, the
[alert card](../assets/alert-card-template.md) for an approved new or changed alert, and the
[knowledge index](../assets/knowledge-index-template.md) only when no operations index exists.

## Close the loop

1. **Bind the closeout.** Name target repository and revision, component, trigger, owner, evidence,
   and requested documentation roots. Roots lie under the repository's documented operations or
   docs tree, or the `operations/`, `runbooks/`, and `postmortems/` fallback roots — never
   `agents/`, `skills/`, `hooks/`, `.github/`, `.claude/`, or a fleet guide. An outside root is
   `blocked`; when none is named, follow repository conventions and fallback paths.

   Before `prepared`, require a caller-supplied `[verified]` checkout binding confirming that the
   mounted checkout's current commit matches the target revision. A Bash-holding caller or human
   resolves the target there and supplies `git rev-parse --short=8 HEAD` with its output on
   `Verified:`, plus `git status --porcelain`. Name every listed path as pre-existing and exclude
   it from the prepared diff; without status, tree state is `[unverified]`. Git extends IDs for
   uniqueness; full IDs (`git rev-parse HEAD`) remain valid. A bare assertion is `[unverified]`.
   Missing, unresolved, ambiguous, or mismatched binding permits no prepared diff; changes remain
   `proposed` or `blocked`. This lane never derives binding from `.git/` contents.
2. **Inventory before creating.** Find the owning artifact and affected links in service cards,
   alert cards, indexes, runbooks, postmortems, and alert definitions. Follow ownership conventions;
   update stable IDs and links instead of forking duplicates.
3. **Bind claims to evidence.** Label a discovery by its weakest supporting evidence. Preserve source,
   target, and conflicting evidence; approval and resolution require supplied evidence, not an
   agent's assertion.
4. **Disposition consequences.** Classify the event with the map below. Check runbook, postmortem,
   service card, alert card, knowledge index, observability, automation, code, and accepted risk.
   Affected artifacts receive `prepared`, `proposed`, `blocked`, or `duplicate`; group unaffected
   categories as `not_applicable` with a shared reason. Enrich the existing Follow-ups record using
   its IDs; consolidate repeated copies while preserving distinct scope, owners, status,
   prerequisites, and evidence. Report affected artifacts plus that one grouped line, not a parallel
   action list.
5. **Prepare the smallest coherent documentation diff.** A service or alert closeout may update
   its cards, index links, and a missing or stale runbook. Read the [runbook method](./runbook.md)
   before writing a procedure. A postmortem remains a separate primary assignment. A stale-contact
   correction stays a contact/link diff when no operational behavior changed.
6. **Return for human PR review.** `prepared` means an actual reviewable documentation diff under
   step 1's path and checkout requirements; it never means approved, reviewed, merged, deployed,
   or live-verified. Credential checks and human diff review remain required before acceptance.

## Event-to-artifact map

| Observed event | Required disposition |
|---|---|
| A component is approved or materially changes | Create or update its card and knowledge index, disposition its runbook, and propose missing alert, runbook, ownership, dependency, recovery or SLO work. |
| A component is decommissioned | Set its card's `lifecycle` and index lifecycle to `retired`, with date and authorizing record in `Lifecycle since / record`. Set dependent alert cards to `status: retired`, their knowledge-index `Status` cells to `retired`, and runbooks to `status: retired`; do not delete them. Name remaining artifact/component references. Live-resource removal remains a separately gated production change. |
| An audit finds an operational gap on an otherwise unchanged component | Disposition affected cards, index and runbook; assign missing work. Put the dated verdict in the card's open gaps and index's recent updates. The document is at most `[sourced]` to the audit; never advance `last_verified`. |
| Only documentation is wrong | Correct the owning artifact and affected links from dated evidence; preserve `last_verified`, without unrelated card/index changes or operational work. |
| An alert is approved or materially changes | Create or update its card and the alert's knowledge-index row, including its `Status` cell; link the service card and authoritative definition, and disposition the service card and runbook. Paging requires a valid, approved runbook target; without one the alert remains `proposed`. An alert card never substitutes for the runbook or copies its commands. |
| An alert fires or an incident is active | Return to the human responder with `incident-investigation`; `sre-assistant` takes only a dispatched read. Dispositions stay `proposed` or `blocked`, with no retrospective or KB preparation before resolution. |
| A runbook is missing or contradicted, including a failed drill | Use `scribe` with the [runbook method](./runbook.md) and supplied evidence; unsupported commands remain `[unverified]`. A drill exposing a bad step cannot verify the repaired version. |
| A resolved incident reveals a systemic lesson | Assign a missing postmortem separately with an owner; continue authorized knowledge closeout and its follow-ups. |
| A fleet prompt, agent or skill has an accepted behavioral failure | Send divergence, evidence and proposed named regression to `agent-authoring`; do not rewrite fleet definitions through operational content. |

## One-time disposition states

- `duplicate`: names the existing owning artifact and supporting evidence, and needs no checkout.
  Without that evidence, use `proposed` or `blocked`.
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
when the caller names none, relative to the knowledge repository: `operations/index.md`,
`operations/services/<component>.md`, `operations/alerts/<alert>.md`, `runbooks/<runbook>.md`, and
`postmortems/<yyyy-mm-dd>-<incident>.md`. Reject absolute paths, parent traversal, URLs as write
targets and paths outside caller-authorized documentation roots.

## Evidence and review rules

- Link the actual provisioning owner: source-managed definitions need the repository path and
  exact uniquely resolved short/full revision; API-owned alerts need resource locator/UID plus
  supplied state/readback receipt and version evidence. An absent API version stays `[unverified]`.
  An export is evidence/recovery material unless it owns provisioning. Cards summarize and link
  definitions rather than copying configuration. Definition identity does not replace KB checkout
  binding, human closeout approval or dirty-path controls, and grants scribe no live lookup.
- Prefer exact-target-revision evidence. For conflicts, state both claims, explain the disagreement,
  mark the affected claim `[unverified]` and assign a resolution owner.
- Review and execution stamps follow the [shared evidence rules](../SKILL.md#evidence-and-authority).
  `Reviewer` and `Reviewed change` cells fill only from the evidence that moves `last_reviewed`;
  otherwise leave blank.
- Store minimal evidence. Credential checks cannot prove secrets absent.
- Keep the change or open question, owner and missing proof in the existing follow-up. A production
  recommendation includes urgency, change tier, approval need (explicit human approval for Tier 2
  or 3), verification and rollback or recovery. A closeout neither authorizes nor executes it, and
  agents do not apply it.

## Output

Lead with the discovery and recommended course. Reuse the existing Follow-ups record; link it
when accessible to the recipient, otherwise include the needed rows. Supply:

1. target, revision, checkout binding or its absence, trigger, and owner;
2. evidence and conflicts;
3. affected artifact dispositions and owners, plus justified grouped `not_applicable` categories;
4. changed paths and links, or the exact reason each remains proposed or blocked;
5. limitations and one tracked next action.

Honor a caller-supplied bounded output shape; it grants no authority and is not a parallel record.
Do not invent a persistent packet, schema, procedure, or approval.
