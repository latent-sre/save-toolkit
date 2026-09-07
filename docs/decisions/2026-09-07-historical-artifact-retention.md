# ADR: Keep retired artifacts in Git history

- **Date:** 2026-09-07
- **Status:** proposed; takes effect when Save Toolkit maintainers merge PR #238
- **Decision owner:** Save Toolkit maintainers
- **Scope:** the owner-requested documentation and eval-history cleanup in
  [PR #238](https://github.com/latent-sre/save-toolkit/pull/238); merge this decision and its removals together.

## Context

The owner requested removal of obsolete documents, evals, and history, then specifically selected
PR #219's historical review for removal. Earlier accepted decisions still require working-tree
copies of retired incident prototypes. This successor records the changed retention decision;
deleting a file alone does not supersede its preservation rule.

## Decision

We will remove the incident-navigation preservation bundle (including its manifest and eleven
patches) and the incident-autonomy bundle (including copied agents, skills, evals, and restore
patches) from the working tree. This supersedes only these retention clauses:

- The packet-preservation requirement and prohibition on deleting the packet in the
  [2026-08-22 incident-navigation decision](https://github.com/latent-sre/save-toolkit/blob/e6702ee04ca03f87e71595fb4dbf89a722df9fe9/docs/decisions/2026-08-22-incident-navigation-archive.md).
- The requirement to keep those bundles under `archive/` and the repeated packet-deletion
  prohibition in the [2026-09-04 archive decision](https://github.com/latent-sre/save-toolkit/blob/e6702ee04ca03f87e71595fb4dbf89a722df9fe9/docs/decisions/2026-09-04-parked-machinery-lives-in-archive.md).
- The requirement to keep incident-autonomy copies and restore patches in the
  [2026-09-03 incident-lane decision](2026-09-03-incident-lane-advisor-and-hands.md).

We will also remove completed review reports and completed or superseded decision files selected
in PR #238. Their original accepted bytes remain in Git; retained accepted ADRs stay byte-for-byte
unchanged, including historical citations. The decision index records supersession and recovery
locations rather than rewriting those records. Current contracts and unresolved-decision evidence
remain in the working tree.

The incident-navigation rejection and branch-preservation restrictions still stand. This decision
does not authorize branch deletion, rewriting Git history, restoring a prototype to the fleet,
rerunning its evals, or accepting any held behavioral candidate.

## Consequences

- Git becomes the recovery source for removed files. The
  [pre-cleanup snapshot](https://github.com/latent-sre/save-toolkit/tree/e6702ee04ca03f87e71595fb4dbf89a722df9fe9)
  contains both bundles, their manifests/patches, and the predecessor ADRs. The navigation
  manifest's eleven patch hashes have been checked against that snapshot.
- Historical links inside immutable ADRs describe the accepted tree and can name removed paths.
  For files removed by PR #238, use the snapshot above or
  `git show e6702ee0:<repository-relative-path>`; earlier removals require their own historical
  revision. Recovery for inspection does not revive a feature.
- The changelog summarizes recent changes; it is not a permanent closure register. Closed items
  remain traceable through their removal commits and historical changelog under the
  [roadmap item contract](../fleet-roadmap.md#item-contract). No item is reopened by this cleanup.
- Maintainer merge accepts this retention change; structural checks or an automated review do not.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>". -->
