# Resolved-context integration

For resolver/producer integration under the SRE operational-context contract ADR, require the
[consumer's v1alpha2 contract](../context-requirements.yaml), including `forbidden` and `freshness`.
Report incompatibility rather than deleting unsupported requirements or assuming missing fields.
Catalog `lastVerified` is mapping freshness, not document review, execution or transition completion.

## Freshness and failure

Use explicit current UTC `--as-of YYYY-MM-DD`; a historical date establishes only a reproduction.
For `/target/deployment`, `P30D` includes day 30; day 31, future dates or a missing date on a present
deployment fail. An absent optional deployment instead produces `optionalMissing`, without a
freshness check: discovery may continue, but no existing deployment or retirement is verified.

Present forbidden paths fail resolution; their absence grants no authority. Return failed checks
with an owner action. Never substitute cached success for empty failure output without disclosing
the cache's age and failed applicability.

## Projection and evidence

The service requires catalog `lifecycle` and qualified `ownerRef`; `v1alpha6` also projects both
for a present deployment. Their states may differ. Retired records remain resolvable for audit,
explicitly marked `retired`; resolution success means neither active status nor verified ownership
transfer. Check catalog
assertions against authoritative service records and receipts; unsupported transition claims stay
`[unverified]`.

The fixture-only producer preserves `source.nonOperational: true` and
`target.actionSelection: prohibited` in every state. Compatibility checks run the actual producer
CLI against temporary synthetic catalogs and this consumer's requirements; skipped external tests
leave compatibility unverified. Even passing fixture checks prove no real-service transition or
operational acceptance.
