# Knowledge closeout

Use this method only for an invoked closeout. A durable discovery needs an explicit disposition:
a reviewable repository change or a tracked, owned handoff. Use the
[service card](../assets/service-card-template.md) for an approved new or changed component, the
[alert card](../assets/alert-card-template.md) for an approved new or changed alert, and the
[knowledge index](../assets/knowledge-index-template.md) only when no operations index exists.

## Close the loop

1. **Bind the closeout.** Name target repository and revision, component, trigger, owner, evidence,
   and requested documentation roots under the repository's documented operations/docs tree or the
   fallback roots (`operations/index.md`, `operations/services/<component>.md`,
   `operations/alerts/<alert>.md`, `runbooks/<runbook>.md`,
   `postmortems/<yyyy-mm-dd>-<incident>.md`) — never `agents/`, `skills/`, `hooks/`, `.github/`,
   `.claude/`, or a fleet guide (outside roots are `blocked`, and reject absolute paths, `..`, or
   URLs as write targets).

   Before reporting `prepared`, require a caller-supplied `[verified]` checkout binding confirming
   the mounted checkout's current commit matches the target revision: `git rev-parse --short=8 HEAD`
   (or full `git rev-parse HEAD`) on `Verified:` plus `git status --porcelain` (every dirty path
   listed as pre-existing and excluded from the prepared diff; without status, tree state is
   `[unverified]`). Missing, unresolved, ambiguous, or mismatched binding permits no `prepared`
   diff; changes remain `proposed` or `blocked`. Never derive binding from `.git/` contents.
2. **Inventory before creating.** Locate the owning artifact and affected links across service
   cards, alert cards, indexes, runbooks, postmortems, and alert definitions; update stable IDs and
   links instead of creating duplicates.
3. **Bind claims to evidence.** Label each discovery by its weakest supporting evidence (`[sourced]`
   or `[unverified]`), preserving both sides of any conflict with a resolution owner.
4. **Disposition consequences.** Check runbook, postmortem, service card, alert card, knowledge
   index, observability, automation, code, and accepted risk. Assign each affected artifact
   `prepared`, `proposed` (owner + next action), `blocked` (missing evidence, authority, dependency,
   or owner), or `duplicate` (existing owning artifact + supporting evidence; needs no checkout).
   Group unaffected categories as `not_applicable` with a shared reason. Enrich the existing
   Follow-ups record using its IDs rather than creating a parallel action list.
5. **Prepare the smallest coherent diff.** Follow the [runbook method](../SKILL.md#runbook-method)
   when writing procedures. A stale-contact correction stays a contact/link diff when no
   operational behavior changed (`last_reviewed` and `last_verified` stay unchanged).
6. **Return for human PR review.** `prepared` means a reviewable diff under step 1's path and
   checkout binding — never approved, merged, deployed, or live-verified.

## Event-to-artifact map

| Observed event | Required disposition |
|---|---|
| Component approved or materially changes | Create/update its service card and knowledge index, disposition its runbook, and propose missing alert, runbook, ownership, dependency, recovery, or SLO work. |
| Component decommissioned | Set service card and index lifecycle to `retired` with date and authorization in `Lifecycle since / record`. Retire alert cards and runbooks used only by this component (carry alert status to its index row and retain records); keep shared records usable or leave unclear retirement open with owner and check. |
| Audit finds operational gap on unchanged component | Disposition affected cards, index, and runbook; record the dated verdict in open gaps and recent updates as `[sourced]` to the audit; never advance `last_verified`. |
| Only documentation is wrong | Patch the owning artifact and affected links from dated evidence (`[sourced] <ID>: ...` on the claim line); preserve `last_verified` and `last_reviewed`, with no unrelated edits. |
| Alert approved or materially changes | Create/update its alert card and index row (aligning `status` / `Documentation status`), link the service card and authoritative definition, and disposition service card and runbook. A paging alert without a valid approved runbook stays `proposed` even if already paging. |
| Incident still active or alert needs live response | Return to the human responder with `incident-investigation`; closeout dispositions stay `proposed` or `blocked` until resolved. |
| Runbook missing or contradicted (including failed drill) | Update or draft via the [runbook method](../SKILL.md#runbook-method); a drill exposing a bad step cannot verify the repaired version. |
| Fleet prompt, agent, or skill behavioral failure | Route divergence, evidence, and proposed regression to `agent-authoring`; never rewrite fleet definitions through operational docs. |

## Provenance, gaps, and output

- **Alert definition provenance:** Link the actual provisioning owner — source-managed definitions
  use `<repo-path>@<exact-short-or-full-revision>` (`definition_version` set to that revision);
  API-owned alerts use the API resource locator/UID plus supplied state/readback receipt
  (`source_receipt`) and version evidence (an absent API version keeps `definition_version: null`
  and `Version evidence: [unverified] unknown`). A committed recovery export is evidence/recovery
  material, not the provisioning owner, when the rule is API-owned. Keep the `[sourced] <ID>`
  marker on the same line as the provenance claim.
- **Documentation vs. runtime status:** Alert card `status` and the index status column describe KB
  record readiness; report observed provisioning, enablement, and page delivery separately in
  **Open knowledge gaps** (in the index, or the component card if the index has none) with gap,
  artifact, status, owner, tracking link, and evidence label. When no diff can be prepared,
  `Follow-up:` names the tracker reference or who will file it.
- **Review stamps and production changes:** Fill `Reviewer` and `Reviewed change` only from
  evidence that advances `last_reviewed`. Any production recommendation includes urgency, change
  tier, human approval need (Tier 2/3), verification, and rollback/recovery.
- **Output:** Lead with the discovery and course of action, reusing the Follow-ups record, and
  state: (1) target, revision, checkout binding, trigger, and owner; (2) evidence and conflicts;
  (3) affected artifact dispositions/owners plus grouped `not_applicable` categories; (4) changed
  paths/links or why each is `proposed`/`blocked`; (5) limitations and one tracked next action.
