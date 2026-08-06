# Schema compatibility policy

The repository's machine-readable contracts are listed in
[`schemas/catalog-v1.json`](../schemas/catalog-v1.json). Each catalog entry names one canonical
source, its immutable URI, its lifecycle status, its validator when one exists, and any generated
host projections that must remain byte-identical to the canonical source.

## Version rules

- A published schema version is immutable. Fixes that change accepted or required packet shape use
  a new version and URI.
- Schemas use closed objects (`additionalProperties: false`), so adding a field to an existing object
  is a breaking shape change and requires a new version.
- Catalog lifecycle statuses: `current` (writers emit this version), `supported` (readers and
  validators still accept it), `active` (a single-version contract with no successor), and
  `contract-only` (the schema remains published but its contract-grade semantic validator is parked
  or absent — for `fleet-improvement-v1`, at tag `pre-trim-2026-08-02`). A repository gate may still
  check schema shape; that partial check is not listed as the catalog validator and does not upgrade
  lifecycle support. Readers and validators accept every version marked `current` or `supported`
  until a separately reviewed retirement removes that support.
- A validator may enforce cross-field, repository-state, authority, and safety invariants that JSON
  Schema cannot prove. Passing JSON Schema alone is never equivalent to authorization, review,
  merge, deployment, or production verification.
- Canonical sources under `schemas/` or `skills/*/assets/` are edited directly. Generated host
  projections are updated only through `scripts/generate_platform_adapters.py --write`.

Version 2 reuses immutable v1 definitions through relative `$ref` values that resolve against the
v2 `$id` to the v1 canonical URI. An offline standards validator must preload the catalog's
canonical files into its schema registry under each entry's `uri`; opening v2 alone may otherwise
cause the validator to attempt a network retrieval. The bundled Python knowledge-update validator is
self-contained and does not perform that retrieval. Version 2 inherits every applicable v1
cross-field rule — including the approved-trigger artifact-disposition requirements — and a
repository test asserts the standalone v2 schema never becomes weaker than v1 for the trigger kinds
it retains.

## Operational knowledge updates

Version 2 is the current write format. It replaces the v1 service-only target with stable component
identity (`component_id`, `component_kind`, and `display_name`) and uses `component_added` and
`component_changed` lifecycle triggers. Applications, services, workers, jobs, datastores, platforms,
and otherwise-classified components can therefore share the same closeout contract.

Version 1 remains supported. The deterministic
[`migrate_v1_to_v2.py`](../skills/operational-learning/scripts/migrate_v1_to_v2.py) command maps a v1
service to a v2 `service` component, preserves evidence and dispositions, and translates only the two
service lifecycle triggers. It does not infer environment or definition location, so both fields are
`null` after migration. The migration never mutates its input, does not downgrade v2 packets, and
validates its own output — an input that would migrate into an invalid v2 packet fails instead of
being emitted. Packets carrying prepared dispositions or documentation duplicates need the same
`--target-root` and `--allowed-knowledge-root` context the validator requires; without it their
migration fails closed.

Example packets live beside the schemas in
[`skills/operational-learning/assets/examples/`](../skills/operational-learning/assets/examples/).
Repository tests validate both examples and the v1-to-v2 result with the stronger Python validator.
