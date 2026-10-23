# Resolved-context integration

Read only when configuring, using, or validating a resolver/producer integration under the SRE
operational-context contract ADR. Apply [record ownership and freshness](./record-transitions.md)
before relying on resolved dates or transition claims.

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
