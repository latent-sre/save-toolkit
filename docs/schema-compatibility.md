# Schema compatibility policy

The repository's machine-readable contracts are listed in
[`schemas/catalog-v1.json`](../schemas/catalog-v1.json). Each catalog entry names one canonical
source, immutable URI, lifecycle status, validator when one exists, and any generated projections
that must remain byte-identical to the canonical source.

## Version rules

- A published schema version is immutable. A shape change uses a new version and URI.
- Objects with fixed contract fields are closed (`additionalProperties: false`), so adding a field
  to one of those objects is a breaking shape change. The evidence envelope deliberately leaves
  `source`, `environment`, and `isolation` as extensible metadata maps; its semantic validator
  rejects secret-bearing keys rather than freezing every producer-specific field in JSON Schema.
- Catalog statuses are `current` (writers emit it), `supported` (readers still accept it),
  `active` (one version with no successor), and `contract-only` (published shape without a
  contract-grade semantic validator).
- Passing a schema or structural validator is never equivalent to authorization, review, merge,
  deployment, or production verification.
- Canonical sources under `schemas/` or `skills/*/assets/` are edited directly. Generated host
  projections change only through `scripts/generate_platform_adapters.py --write`.

## Evidence envelope

`evidence-envelope-v1` is the active portable evidence shape used by runtime probes and verification
contracts. Its validator is `scripts/evidence_envelope.py`. The envelope preserves evidence and
provenance; it does not authorize an effect or promote the subject it describes.

## Evaluation contracts

`eval-execution-profile-v2` is current. It binds one engine, requested claims, selected scenarios,
required references, requested and accepted resolved-model identity, reasoning effort, stop
condition, trial count, time limits, cost-budget representation, and separate live-run approval to
the exact frozen evaluator, grader, and scenario-suite bytes.
`eval-execution-profile-v1` remains supported for retained historical evidence but cannot start a
new model process. `evals/execution_profiles.py` is their semantic validator. A current profile
with `approval: null` may be validated and reviewed offline, but cannot start a model process.

`eval-result-envelope-v1` is the active claim-scoped result shape for Claude native-plugin and
Codex resolved-context measurements. `evals/engine_contract.py` rejects unsupported claims,
incomplete traces presented as decisive results, missing canaries presented as reference use, and
dirty candidates presented as promotion-eligible. The envelope records evidence; it never promotes
a candidate, and cross-engine comparison never averages the engines into one score.

## Fleet atlas

`fleet-atlas-v1` is the active shape of `docs/fleet-atlas/generated/atlas.json`, the fleet's
revision-bound knowledge graph (`GRAPH-004`). Its validator is `scripts/fleet_atlas.py check`. The
atlas cites edges that other validators enforce and extracts the rest from canonical bytes; it is a
generated projection with no authority over anything it describes, and a finding it emits changes
nothing until a human edits a canonical file or the roadmap imports it.

## Runbook frontmatter

`runbook-frontmatter-v1` is `contract-only`. It publishes the machine-linkable shape carried by
`skills/runbook/assets/runbook-template.md` so alerts and indexes can link a stable runbook
contract. `scripts/test_runbook_schema.py` checks template/schema shape parity; it is not a
semantic validator. Only human or separately authorized document review changes `last_reviewed`,
and only bound rehearsal evidence changes `last_verified`.

## Retired before the first release

The operational knowledge-update schemas v1-v3, their migrations and drift watcher, and the
fleet-improvement v1 schema were removed before `save-toolkit--v0.1.0` was published. No GitHub
Release or versioned release tag exposed them as supported consumer contracts. Git history retains
their historical bytes; the active fleet makes no compatibility or migration promise for them.
