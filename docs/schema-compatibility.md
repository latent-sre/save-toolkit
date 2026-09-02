# Schema compatibility policy

The repository's machine-readable contracts are listed in
[`schemas/catalog-v1.json`](../schemas/catalog-v1.json). Each catalog entry names one canonical
source, immutable URI, lifecycle status, validator when one exists, and any generated projections
that must remain byte-identical to the canonical source.

## Version rules

- A published schema version is immutable. A shape change uses a new version and URI.
- Objects with fixed contract fields are closed (`additionalProperties: false`), so adding a field
  to one of those objects is a breaking shape change.
- Catalog statuses are `current` (writers emit it), `supported` (readers still accept it),
  `active` (one version with no successor), and `contract-only` (published shape without a
  contract-grade semantic validator).
- Passing a schema or structural validator is never equivalent to authorization, review, merge,
  deployment, or production verification.
- Canonical sources under `schemas/` or `skills/*/assets/` are edited directly. Generated host
  projections change only through `scripts/generate_platform_adapters.py --write`.

## Runbook frontmatter

`runbook-frontmatter-v1` is `contract-only`. It publishes the machine-linkable shape carried by
`skills/runbook/assets/runbook-template.md` so alerts and indexes can link a stable runbook
contract. `scripts/test_runbook_schema.py` checks template/schema shape parity; it is not a
semantic validator. Only human or separately authorized document review changes `last_reviewed`,
and only bound rehearsal evidence changes `last_verified`.

## Retired before the first release

The operational knowledge-update schemas v1-v3, their migrations and drift watcher, the
fleet-improvement v1 schema, `eval-execution-profile-v1`/`v2`, `eval-result-envelope-v1`, and
`evidence-envelope-v1` (with its `fleet_doctor` emitter, itself since removed) were
removed before `save-toolkit--v0.1.0` was published. No GitHub Release or versioned release tag
exposed them as supported consumer contracts. Git history retains their historical bytes; the
active fleet makes no compatibility or migration promise for them.
