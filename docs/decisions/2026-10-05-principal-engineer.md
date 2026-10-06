# Principal engineering and system architecture in one design lane

Status: proposed. The user authorized creating a needed role; acceptance of the exact candidate
and installation remain separate. This decision uses only the fresh `origin/main` checkout at
`8d7ecda1ebc6fc37016c5e3063fc26e215cd9a64` and changes made on its new branch.

## Problem and evidence

[verified] The base has nine canonical agents and no general system architecture owner.
[`eng-ladder`](../../skills/eng-ladder/SKILL.md) supplies principal and distinguished reasoning,
but its base routing sends general architecture decisions back to the caller or a human senior
engineer. [`software-engineer`](../../agents/software-engineer.md) returns unresolved design forks;
[`reliability-engineer`](../../agents/reliability-engineer.md) owns service resilience and toil,
not general system architecture. The gap is ownership of a design proposal, not missing seniority
advice. These are source findings, not a measured runtime routing failure.

## Decision

Add [`principal-engineer`](../../agents/principal-engineer.md) as the combined principal engineering
and system architecture lane. It owns shared contracts, cross-service and new-system design,
migrations, and build/buy or technical direction proposals. It reuses the existing ladder and
relevant domain skills rather than duplicating their methods.

The role can read local evidence and write requested design documents or proposed ADRs. Its only
delegates gather local facts, protected operational observations, or sanitized public evidence.
It has no direct execution, external access, implementation delegation, or approval authority.
The caller arranges implementation and independent review; human owners accept decisions.

Document-path restrictions are cooperative because Write/Edit can reach other paths. Tool absence
and validator checks establish the authored posture; target-host enforcement requires its own probe.

## Alternatives

| Option | Tradeoff |
|---|---|
| Keep architecture in the caller with `eng-ladder` | Lowest listing cost, but leaves the requested dedicated design ownership absent |
| Broaden `reliability-engineer` | Reuses the same evidence tools, but dilutes a service reliability lane with general product and system design |
| Separate principal and architect agents | No distinct authority or durable ownership split is established here; adds overlapping descriptions and another handoff |
| One combined design lane | Gives architecture a callable owner while preserving implementation, reliability, review, and acceptance boundaries |

Seniority remains a skill-level choice. This is not a second builder or a coordinator. Revisit a
split only when actual tasks establish different authority, context, or ownership requirements.

## Verification and recovery

Acceptance cases are the `discovery-principal-*` routing specs and the
[`migration design fixture`](../../evals/build-scenarios/build-principal-engineer-migration-design.yaml).
The fixture includes a strict old reader, an unknown external consumer, accepted durable-storage
constraints, and hostile instructions to change code and fabricate results. It checks document-only
writes mechanically; design quality needs assessment of its explicit success criteria and trace.

The validator pins the role's tools and delegation. Mutation tests reject execution, direct web
access, and implementation delegation; platform tests cover generated model-call edges. Existing
human-selected handoff graphs are unchanged. Canonical changes regenerate into both host copies.

Structural checks do not accept the agent or prove live discovery, design quality, helper behavior,
or host containment. A maintainer can revert this additive change and regenerate adapters to
return architecture consultation to the caller; it changes no production system or accepted ADR.

## Candidate evidence and remaining acceptance

[verified] The new agent is 8,146 UTF-8 bytes, including a 679-byte discovery description. The
growth buys one architecture owner, its document/evidence authority, conditional method loads,
and a bounded return contract; it adds no second architect role or new skill.

[verified] The initial integrated candidate passed 1,710 tests and 3,229 subtests, with 40
platform/opt-in skips, using Python 3.14.7. A static independent review of the working-tree
candidate reported no findings; it is not an immutable-commit merge verdict.

One native fixture ran on Claude Code 2.1.290 / `claude-sonnet-5-5` on Windows, with a one-call,
180-second limit. Its source digest was
`cc151624e1b7245c6065bad67439b32056d34311994dc2c1cd902da8a2690d2e`; its original scenario digest was
`abfa7bb7f92801a1ad6c8425811f77c17e381ba5d588204cd45c015faacb3d28`.
The private trace is under `.eval-runs/principal-architect-20261005/`, label `candidate-native`.

[verified] That trial passed its original 6/6 file/trace checks in 61.7 seconds. It wrote only the
requested proposed ADR, with no shell, helper or commit, and loaded `stack-profile`, `eng-ladder`
and the principal reference. Manual content review found the strict-reader break, alternatives,
stage-specific recovery preserving orders, unknown external-consumer prerequisites, proposed
verification, and explicit human acceptance. This is one supplied fixture, not general acceptance.

[verified] It also omitted the required `database-reliability` load while proposing persistence,
backfill and recovery. The original six checks did not grade that requirement. The source now
makes this an explicit prerequisite, and the fixture requires all three skills before writes and
the principal reference read. The original structural PASS is retained, not relabelled as a pass
of the changed scenario. [unverified] The corrected final prompt has not had another native run;
live discovery and helper behavior are also unmeasured.

[verified] After that correction, final source digest
`fa673d13554eb24da491efb0ab50545986eb9f08e696be49074aecd0c47de668` passed the focused fleet checks
(120 tests, 507 subtests, two symlink skips), skill/reference harness checks (21 tests, 56 subtests),
all 202 scenario specifications / 759 expectations, adapter regeneration, and Gate A (2/2).
Replaying the existing skill-load checker over the original saved trace confirms stack and ladder
loads passed before writes and the data-recovery load failed. That diagnostic made no model call
and does not constitute a rerun of the corrected prompt.

[`ARCH-001`](../fleet-roadmap.md#arch-001--accept-the-principal-and-architecture-lane)
owns the remaining acceptance decision; this ADR is evidence, not a separate work queue.
