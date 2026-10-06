# ADR: Add one principal engineering lane for system design and architecture

- **Date:** 2026-10-05
- **Status:** proposed; implementation authorized by the owner on 2026-10-05, exact-candidate
  acceptance pending
- **Decision owner:** Save Toolkit maintainers

## Context

The owner asked for the principal engineer back and for a system architect in the roster. This
repository has carried seniority as ladder skills, not agents, since its first content commit
(`b7ce7480`, as `sde-ladder-*` skills), consolidated into `eng-ladder` tiers on 2026-07-14
(`7d4270a6`) [verified]. The owner's sibling fleet `latent-sre/homelab-agents` runs the role as an
agent. In commit `07facd8c` (2026-09-08 UTC) it merged a separate `distinguished-architect` into
`principal-engineer`, because both had the same tools, document-only mandate and handoffs and
differed only in reasoning depth [sourced] that repository's decision record.

No lane here owns general design. `software-engineer` returns an unresolved fork to its caller
(`agents/software-engineer.md:93`) [verified], `reliability-engineer` leaves general architecture
with its existing owner (`agents/reliability-engineer.md:25`) [verified], and on Copilot a returned
fork had no agent to select before this change [verified]. The 2026-09-21 reliability decision
declined a general architect as the answer to a reliability request
(`docs/decisions/2026-09-21-reliability-engineer.md:75`) [verified]; it did not settle the general
question.

## Decision

Add one agent, `principal-engineer`, for system design and architecture: changes across existing
boundaries, the architecture of a new system, and tool or platform selection or multi-year
direction, in one engagement. Do not add a second architect agent. It would share this lane's tools and output, and a
split by size or by new-versus-existing mis-sorts mixed requests, such as a migration that also
shapes its target system.

Import the homelab body's judgment into `eng-ladder`, not the agent file, so the author and any
assessor at the bar read one standard. `references/principal.md` gains the default habits, a
new-system method, the design record with a worked example, and the review checks;
`references/distinguished.md` gains the strategic analysis. The agent body keeps posture, method
order, evidence labels and the return contract. Five defects of the homelab body are fixed on
import:

1. The worked example carries every design-record slot and all three evidence labels; a test fails
   when the record and its example diverge.
2. The record adds contracts and consumers, verification, and operational cost.
3. The lane advises: every owner decision is a `Decision needed` line, and drafted ADRs stay
   `proposed`.
4. Evidence labels use this fleet's definitions.
5. The lane holds `Skill` and loads `stack-profile` and `eng-ladder` before drafting.

Bash, web tools and the homelab guard text are not imported. The posture matches
`reliability-engineer`: local reads, document-only Write/Edit, Skill, and three evidence helpers —
`repository-investigator`, `sre-assistant` for history, consumers in other repositories and runtime
evidence, and `researcher` for sanitized public questions. The document-only limit is cooperative.
The guard's fleet-name inventory includes the lane for the credential tripwire, and the validator
requires that inventory to match the roster. Copilot gains two
human-selected handoffs: `software-engineer` to `principal-engineer` for a returned fork, and
`principal-engineer` to `software-engineer` for an accepted design. `/adr` admits
`principal-engineer` under the same fail-closed preflight as `software-engineer`, and writes the
status of an ADR drafted with that lane selected as `proposed`. Whether
Copilot's file tools provide the exclusive create the command requires is unverified, so on
Copilot it may correctly refuse for either agent.

## Evidence and acceptance

Offline checks pin the authority and delegation, reject added execution, egress and implementation
delegation by mutation, pin the projected Copilot tools and handoff graph, and bind the worked
example to the record. They establish structure, not model competence.

Native evaluations are recorded under `PRINCIPAL-001` in the live roadmap; acceptance remains
pending. The homelab merger's routing comparison has not run: that repository's roadmap still lists
it as a next action [sourced]. Neither fleet has measured one design lane against two.

## Alternatives and rollback

- **Status quo, or a stronger `eng-ladder` alone:** no owner for design-only work and no Copilot
  entry point.
- **Two agents:** identical posture, a routing predicate that mis-sorts mixed requests, and twice
  the maintenance.
- **Broadening `reliability-engineer`:** reverses its scoped decision and disturbs the
  `RELIABILITY-001` baseline.

If evaluation does not justify the lane, remove its profile, validator pins, guard name, handoffs,
routing lines and tests as one reviewed change, then regenerate adapters. The `eng-ladder` content
stands on its own and can stay.
