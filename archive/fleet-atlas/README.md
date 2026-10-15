# Fleet Atlas — retired

Retired at the human owner's request on 2026-10-15. GRAPH-004 and GRAPH-006 are retired,
not pending adoption. This archive preserves historical material; it is not active guidance,
an installed skill, a supported runtime, or part of normal CI and test discovery.

The 36 archived files preserve their original repository-relative layout and bytes from
`3db39edc34dc41dcb54e26ff0f74b17b7f6d0f56`. [MANIFEST.sha256](MANIFEST.sha256) records each
original path and SHA-256. Generated adapters are reproducible consequences and are not copied.

## Contents

- [Skill](skills/fleet-atlas/SKILL.md) and [schema](schemas/fleet-atlas-v2.schema.json).
- [Implementation, browser source, tests, and test support](scripts/).
- [Routing scenarios](evals/scenarios/).
- [Dashboard guide](docs/fleet-atlas-dashboard.md).
- [GRAPH-004/GRAPH-006 implementation and compatibility evidence](docs/reviews/2026-09-30-backlog-four/graph-004.md).
- [Fleet audit](docs/reviews/2026-10-02-fleet-audit/group-03-fleet-atlas.md).

## Reading and recovery

Commands, relative links, and completion or adoption statements inside the preserved files
describe their original tree and time. In particular, earlier pending-acceptance statements do
not reopen the retired work. Historical links may point outside this partial snapshot.

For the complete original environment, inspect the source revision above in a separate checkout.
The archived scripts retain their original root assumptions and shared dependencies; do not run
them in place. Existing private `.eval-runs/` evidence and exported dashboards are left untouched
in their original locations and are not included or published by this archive.

Normal repository search excludes `archive/`; use `rg --no-ignore` to inspect it explicitly.
Restoration to the active toolkit requires a new owner decision, integration work, and fresh
verification. Tests and live evaluations were not run for this retirement, at the owner's request.
