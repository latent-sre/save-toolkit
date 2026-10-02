# Record ownership and freshness

Read for a change, remediation, refresh, retirement, or a freshness-sensitive context lookup.
Use existing cards, runbooks, indexes, and Follow-ups; this is not a new record schema or an
authorization to write. The caller names the human service owner and the invoking caller
separately. An unnamed owner is a gap, never inferred from an agent, commit author, or locator.

## Keep ownership through the return

| Transition | Accountable owner | Evidence and record disposition | Completion or explicit gap |
|---|---|---|---|
| Change | Named service owner; release owner supplies execution receipts | Compare the previous record with the exact changed version and environment. Identify affected cards, runbooks, index links, and dependencies; hand their proposed updates to `scribe`. | The service owner retains the follow-up until independently reviewed records are read back. A changed deployment invalidates applicability of affected older evidence even inside a freshness window. |
| Remediation | Named finding owner, with the service owner retaining record ownership | Keep the finding open until the repair's target-bound result is supplied. Route the changed procedure or configuration reference and its result to `scribe`; distinguish a documentation gap from a missing control. | A proposed fix, merged code, or failed drill does not verify the operating procedure. Preserve the old evidence's scope and mark the affected claim stale or `[unverified]`. |
| Refresh | Existing record owner; a named successor must accept a transfer | Recheck links, ownership, deployment applicability, and aged evidence. Send only supported corrections to `scribe`; a contact correction is a contact diff. | Review can advance `last_reviewed` through the existing review rule. It cannot advance execution verification; unresolved freshness stays visible with owner and next review date. |
| Retirement | Named service owner until each retained resource has an accepting owner | Follow retirement order, then hand execution receipts and retained-resource dispositions to `scribe`. Preserve records as `retired`, update active indexes, and retain historical evidence. | Reviewed record readback plus independent retirement checks are required. Missing recipient acceptance, unknown outcome, or serving traffic keeps the follow-up pending; an old successful resolve cannot prove active status. |

When supporting evidence no longer applies, explicitly identify the stale claim, affected version
and environment, last applicable evidence, owner, and next verification in the existing gaps or
Follow-ups record. The caller reports that gap immediately; `scribe` prepares its durable form
only when the existing closeout and checkout-binding rules permit. Do not silently overwrite
historical verification or create an extra lifecycle file. Handoff delivery is not ownership
acceptance, record readback, or closure. The invoking caller continues tracking the return.

## Keep the three dates distinct

- Catalog `provenance.lastValidated` becomes resolved `lastVerified`: freshness of the catalog
  mapping, not proof of deployment health, procedure success, human review, or active lifecycle.
- Record `last_reviewed` follows the human or separately authorized document review rule.
- Procedure `last_verified` follows the existing operational-learning rule: incoming successful
  execution evidence binds the exact artifact/version, target, actor, timestamp, and every step
  claimed on the version being stamped. A failed drill, changed procedure, newer catalog date,
  or document-only review cannot supply that evidence.

The optional resolver must support the unchanged `v1alpha2` consumer requirements, including
`forbidden` and `freshness`; unsupported contracts are a gap, not permission to remove those fields.
Supply an explicit current UTC `--as-of YYYY-MM-DD` for an actual assessment. A historic date is
only a dated reproduction and must not make stale context appear current.

For `/target/deployment`, `P30D` includes age 30 days; age 31, missing date on a present deployment,
or a future date fails. An absent optional deployment remains an `optionalMissing` gap and has no
freshness check; this permits new-service discovery but does not verify an existing deployment or
retirement. Forbidden paths cause failure if present; they do not approve the remaining output.
An empty failure result must never be replaced with a cached successful bundle without disclosing
its age and failed applicability. Return the failed check and owner action.

The lifecycle consumer requires the service's catalog `lifecycle` and qualified `ownerRef`.
The `v1alpha6` projection also includes both on a present deployment; service and deployment may
have different states. Retired records remain resolvable for audit, explicitly marked `retired`;
do not interpret resolution success as active status. A missing field from an older projection
does not mean active or owned: report incompatibility and do not silently relax the requirements.
These are catalog assertions, not verified ownership transfers or live retirement receipts.
Check them against the authoritative service record and supplied receipts; without those, actual
transition completion stays `[unverified]`. The fixture-only producer retains
`source.nonOperational: true` and `target.actionSelection: prohibited` in every state.
No fixture run proves any real-service transition.

## Acceptance on the selected service

Use the owner's selected service, environment, and authorized record repository. For each row,
retain the original record/revision, named owner, trigger, exact evidence, `scribe` disposition,
independent review/readback, and caller continuation in the existing follow-up. Include a changed
deployment inside 30 days, failed remediation, document-only refresh, and retirement with a retained
shared resource. In each negative case the affected claim must stay visibly stale or pending;
then verify closure only after the missing evidence or accepting owner actually arrives.

The source repository's compatibility checks exercise the actual producer CLI against temporary
synthetic catalogs and this consumer's requirements. Skipped external tests mean unverified
compatibility. Human acceptance of the exact candidate and actual service transitions remains
separate from these checks.
