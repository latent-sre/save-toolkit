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
(`agents/software-engineer.md:93`) [verified], `reliability-engineer` left general architecture
with an unnamed existing owner (`agents/reliability-engineer.md:25`) [verified], and on Copilot a returned
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
requires that inventory to match the roster. `reliability-engineer` names this lane as the owner of
general system architecture. Copilot gains two
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

On 2026-10-07 the owner selected demonstrably better design judgment, plus consistent usable
records, as the acceptance bar and approved preparation of the alerting prerequisite repair and
semantic comparison. The [acceptance candidate](../reviews/2026-10-07-principal-judgment-acceptance.md)
keeps record consistency separate from judgment, with matched principal/builder cases and proposed
calibration examples. Source and offline evidence do not accept this ADR or establish superiority;
live calibration and each further campaign retain their own owner-triggered budget.

The later owner-approved twelve-attempt diagnostic recorded USD 2.351204, eleven completed trials
and one authentication interruption. The revised lane loaded alert guidance 3/3 and passed its six
structural trials. Author-aware document review nevertheless found retired-endpoint paging,
unestablished database-outage notification, unverified recovery dependencies and a false verified
claim that a supplied CSV was absent. The linked packet preserves those findings and the masked
documents for owner/teammate review. This evidence does not meet the stronger acceptance bar;
the ADR remains proposed.

On 2026-10-08 the owner approved the bounded source repair. It strengthens input-grounding in the
agent, lifecycle and preservation reasoning in the shared principal method, and query-error
notification in `obs-alerting`, with paired proposed calibration controls. The packet records the
new source digest and offline checks. The earlier live trial results remain bound to their old
digest and do not establish the repaired candidate's behavior.

The owner then approved twelve new trials of repaired digest `fb2fba9ac780` under the same USD 10
ceiling. All completed for USD 2.306003 with no interruptions or retries. Principal passed six
structural trials; author-aware review found all three tracker designs addressed the four repair
targets, with material gaps still present in the builder outputs. Contract migration was broadly
comparable, and residual reasoning errors remain. The packet retains complete author-hidden
records and trace evidence. This supports targeted improvement, not broad superiority: independent
human review, a fresh held-out case and exact-candidate acceptance remain open. The ADR stays proposed.

The separate AI review's blind ratings and trace reconciliation now support a material tracker
advantage with no detected contract-case regression. Both passes are preserved verbatim through
the linked acceptance packet. This is independent AI evidence, not independent human review.
The owner approved evidence reconciliation and preparation of one fresh live-store cutover case,
with uniformly masked author metadata in the next packet. Lane sources remain frozen; the next
campaign's budget and exact-candidate acceptance are not approved by that preparation decision.

The owner subsequently approved the six held-out trials under a USD 10 ceiling. All completed
for USD 1.905009. Principal passed the structural checks, but coordinating review found a material
fence/abort contradiction in one principal plan and replay-cursor concerns across the arms. Builder
boundary/reporting failures also remain. The completed independent AI first pass, prompted
addendum and trace/unmasking review are now preserved through the
[held-out reconciliation](../reviews/2026-10-08-principal-heldout-cutover.md#independent-ai-review-and-final-reconciliation-2026-10-08).
They find a design tie on the unfamiliar case with material findings in both arms, alongside
consistent principal method use and no shell execution. Shell absence partly explains the latter.
Across the three cases the evidence shows one targeted design advantage and two ties, not broad
superiority or a general non-regression proof. The owner authorized evidence publication and a PR;
the original acceptance bar is unchanged, no further run is authorized, and the ADR remains proposed.

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
