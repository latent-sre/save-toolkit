# Explicit native evaluation selections

- Date: 2026-10-25
- Status: accepted for implementation by the repository owner's instruction to implement the design;
  the implementing candidate still requires the normal human acceptance decision
- Decision owner: repository owner
- Scope: narrow successor to the selection clause of
  [one eval runner](2026-09-03-one-eval-runner.md); other clauses remain in force

## Context

[verified] The native runner previously selected one exact scenario ID or every scenario. Maintainers
now need repeatable groups across hundreds of cases, while tests and benchmark adapters retain their
existing execution paths. [sourced] The owner chose discovery and selection first and directed that
organization precede hashing finalized definitions.

## Decision

Add a read-only catalog and explicit named suites. Keep suites as mutable workflow groupings; export
an exact native selection with case IDs, finalized case hashes, and a fixed total trial count before
an authorized measurement. Admit that file through the existing native runner's `run` and `validate`
subcommands. Keep one-ID/all commands, grading semantics, and saved-run interfaces.

Do not restore split-based scheduling or introduce a generic runner for other engines. Link benchmark
manifests and their admission guides instead. Selection exports are not run approvals. Preserve old
result identities; earlier hashes do not constrain useful organizational changes.

## Consequences

Suite changes cannot silently expand a frozen campaign. The existing campaign reporter can use the
same task list and total trials, including missing slots. The new input requires strict admission,
trial-window validation, and retention of exact selected bytes. The retained file hash is explicitly
distinct from the reporter's logical JSON hash.

Existing commands remain the rollback path. Retain selections and evidence if the new interface is
withdrawn; never relabel results as produced by another case or runner. The
[design](../fleet-evaluation/discovery-and-selection-design.md) defines verification and boundaries.
