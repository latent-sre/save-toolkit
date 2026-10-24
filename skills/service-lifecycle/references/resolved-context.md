# Resolved-context integration

Read only when configuring, using, or validating a resolver/producer integration under the SRE
operational-context contract ADR. Catalog `lastVerified` records mapping freshness, not document
review, procedure execution, or transition completion.

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

The source repository's compatibility checks exercise the actual producer CLI against temporary
synthetic catalogs and this consumer's requirements. Skipped external tests mean unverified
compatibility. These checks do not establish operational acceptance.
