# ADR: Parked machinery lives under `archive/`

- **Date:** 2026-09-04
- **Status:** Accepted 2026-09-04
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** fleet weight review — repository layout
- **Supersedes:** the path clause of
  [`2026-08-22-incident-navigation-archive.md`](2026-08-22-incident-navigation-archive.md)
  ("Keep the existing evidence in place", and its link to
  `docs/reviews/2026-08-12-incident-navigation-preservation/`) — that clause only, and only as to
  where the bundle lives.
- **Does not supersede:** anything else in that ADR. Its rejection of `incident-navigation` as a
  fleet feature stands, and so does its prohibition: the branch and packet are not to be deleted,
  rebased, merged, published, rerun, or repaired. The remote branch pointer
  (`feat/incident-navigation` at `9a545123e440dec474d13d13f9e1cf460d692fe9`) is unchanged.

## Context

`docs/reviews/` holds evidence *for* live decisions — review packets a reader reaches for while
working on the current tree. Parked machinery is a different thing: byte-exact copies of components
removed from the live tree, kept so a later owner can read or restore them, with no bearing on how
the fleet behaves today. Mixing the two made `docs/reviews/` a place where a reader could not tell
which documents described something shipping.

The maintainer set the convention on 2026-09-03 while parking the incident-autonomy machinery:
`archive/<name>/` at the repository root, holding copies, patches, and a README that says what the
bundle is and why it is parked. [`archive/incident-autonomy/`](../../archive/incident-autonomy) was
its first occupant.

## Decision

We will keep parked machinery under `archive/<name>/` at the repository root — copies, patches, and
a README — and not under `docs/reviews/`.

On 2026-09-04 the 2026-08-12 incident-navigation preservation packet moved there, unchanged, as
[`archive/incident-navigation-preservation/`](../../archive/incident-navigation-preservation). The
2026-08-22 ADR still names the old path, by design: an accepted ADR is immutable, and this record is
the sanctioned way to change where the bundle lives.

The maintainer's merge of PR #232, which performed the move, is the acceptance of this decision.

## Consequences

- `docs/reviews/` again holds only evidence about the live tree; `archive/` holds what is parked.
- Links into the old path are dead. The archived README carries a two-line note pointing forward to
  this ADR, and the decision index marks the 2026-08-22 row's status accordingly.
- Nothing about the candidate's disposition changed. A future owner who wants to revive
  `incident-navigation` still needs a new accepted decision; this ADR moved bytes, not authority.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>". -->
