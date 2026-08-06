# ADR: Rename the plugin namespace from `sre-agents` to `save-toolkit`

- Date: 2026-08-05
- Status: Accepted
- Decision owners: save-toolkit maintainers
- Evidence: [`../reviews/2026-08-05-naming-audit-and-graph-engineering.md`](../reviews/2026-08-05-naming-audit-and-graph-engineering.md)

## Context

The plugin and repository were named `sre-agents`. That identifier contained the incident-lane agent
name `sre` as a strict substring. The fleet's own tooling and eval graders match by substring:

- Graders asserting the bare token `"sre"` were satisfied by any answer that named any component
  under the `sre-agents:` plugin namespace — unfixable by renaming agents alone.
- The observability-engineer rename ADR already recorded that the `sre-agents` prefix collision
  survived any agent rename; closing that defect required renaming the plugin itself.

The same audit closed two sibling substring collisions (`sre` ⊂ `sre-steward`,
`craft` ⊂ `backend-craft`/`frontend-craft`) under separate ADRs. This record governs the plugin/id
rename so later decisions can cite a decision, not only the naming-audit review.

## Decision

1. Rename the plugin namespace and published identity to `save-toolkit`. Claude components address as
   `save-toolkit:<name>`; generated Codex custom agents use the `save-toolkit-<role>` filename
   mirror of that namespace.
2. Update manifests, generator `PLUGIN_NAME`, guard namespace handling, installer markers, docs, and
   eval graders that depended on the old prefix in the same change set; regenerate host adapters.
3. Leave dated plans, specs, reviews, and recorded eval baselines that still say `sre-agents` as
   historical evidence. Do not rewrite recorded results to match current vocabulary.
4. Treat component names as node identifiers: pairwise substring-free across agents, skills,
   commands, and the plugin id. Future renames that reintroduce a substring collision are defects.

## Alternatives considered

- **Keep `sre-agents` and harden every grader:** rejected. Word-boundary matching everywhere would
  paper over one grader class while leaving the plugin prefix as a permanent false-friend for any
  bare-`sre` assertion and for human routing prose.
- **Rename only the Claude marketplace id:** rejected. Host projections, installer markers, and
  guard scoping all consume the same namespace string; a partial rename would reintroduce fail-open
  and orphaned-install failure modes already observed in the audit.

## Consequences

- Bare `"sre"` graders can mean the incident lane again; dependent graders were tightened to
  boundary regexes as part of the rename landing.
- The readonly guard must fail closed on an unknown namespace whose bare agent name is guarded —
  a renamed plugin without that fix fail-opened (`rm -rf` allowed under the new namespace before the
  fix; recorded in the naming-audit review).
- The Codex installer claims legacy markers while writing only the current one, so marker-text
  changes do not orphan previously installed files.
- Component addressing lengthens in prose (`save-toolkit:observability-engineer`) and shortens the
  class of false matches.

## Rollback

Revert manifests, generator `PLUGIN_NAME`, guard namespace handling, installer markers, docs, and
evals together, then regenerate adapters. Never restore the old plugin id while leaving generated
roots or guard scoping on `save-toolkit`; `validate_fleet.py` treats that drift as a failure. Keep
the fail-closed unknown-namespace guard behavior even if the display name rolls back.
