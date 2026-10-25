# Knowledge closeout

Use this method only for an invoked closeout. A durable discovery needs an explicit disposition:
a reviewable repository change or a tracked, owned handoff. Read the
[disposition policy](./disposition-policy.md) before classifying it. Use the
[service card](../assets/service-card-template.md) for an approved new or changed component, the
[alert card](../assets/alert-card-template.md) for an approved new or changed alert, and the
[knowledge index](../assets/knowledge-index-template.md) only when no operations index exists.

## Close the loop

1. **Bind the closeout.** Name target repository and revision, component, trigger, owner, evidence,
   and requested documentation roots. Roots lie under the repository's documented operations or
   docs tree, or the policy's `operations/`, `runbooks/`, and `postmortems/` fallback roots — never
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

   Active incidents permit only `proposed` or `blocked`; return to the human responder with
   `incident-investigation`.
2. **Inventory before creating.** Find the owning artifact and affected links in service cards,
   alert cards, indexes, runbooks, postmortems, and alert definitions. Follow ownership conventions;
   update stable IDs and links instead of forking duplicates.
3. **Bind claims to evidence.** A discovery takes its weakest supporting label. Preserve source,
   target, and conflicting evidence; approval and resolution require supplied evidence, not an
   agent's assertion.
4. **Disposition consequences.** Check runbook, postmortem, service card, alert card, knowledge
   index, observability, automation, code, and accepted risk. Affected artifacts receive `prepared`,
   `proposed`, `blocked`, or `duplicate`; group unaffected categories as `not_applicable` with a
   shared reason. Enrich the existing Follow-ups record using its IDs; consolidate repeated copies
   while preserving distinct scope, owners, status, prerequisites, and evidence. Report affected
   artifacts plus that one grouped line, not a parallel action list.
5. **Prepare the smallest coherent documentation diff.** A service or alert closeout may update
   its cards, index links, and a missing or stale runbook. Read the [runbook method](./runbook.md)
   before writing a procedure. A postmortem remains a separate primary assignment. A stale-contact
   correction stays a contact/link diff when no operational behavior changed.
6. **Return for human PR review.** `prepared` means an actual reviewable documentation diff under
   step 1's path and checkout requirements; it never means approved, reviewed, merged, deployed,
   or live-verified. Credential checks and human diff review remain required before acceptance.

## Artifact boundaries

- A paging alert without an approved runbook target remains `proposed`; an alert card never
  substitutes for the runbook or copies its commands.
- Cards link authoritative configuration and alert definitions rather than duplicating them.
- Approved component changes disposition the service card, knowledge index, and runbook. Approved
  alert changes disposition the alert card, service card, knowledge index, and runbook.
- `duplicate` names the owning artifact and supporting evidence, and needs no checkout. Without
  that evidence, use `proposed` or `blocked`.
- Review and execution stamps follow the [shared evidence rules](../SKILL.md#evidence-and-authority).
  A drill exposing a bad step never verifies its repair.
- Tier 2 or 3 recommendations name explicit human approval and rollback or recovery; agents do
  not apply them. Fleet prompt, skill, or agent failures return to `agent-engineer` with observed
  divergence and a proposed named regression.

## Output

Lead with the discovery and recommended course. Reuse the existing Follow-ups record; link it
when accessible to the recipient, otherwise include the needed rows. Supply:

1. target, revision, checkout binding or its absence, trigger, and owner;
2. evidence with retained labels and conflicts;
3. affected artifact dispositions and owners, plus justified grouped `not_applicable` categories;
4. changed paths and links, or the exact reason each remains proposed or blocked;
5. limitations and one tracked next action;
6. explicit non-actions: no execution, external lookup, delegation, approval, or inferred verification.

Honor a caller-supplied bounded output shape; it grants no authority and is not a parallel record.
Do not invent a persistent packet, schema, procedure, or approval.
