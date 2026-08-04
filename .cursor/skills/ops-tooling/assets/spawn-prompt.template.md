<!-- Spawn-prompt handoff — the shape of every builder/reviewer spawn in Phase 2/3. Agents do not
     inherit this conversation: an underspecified handoff is the #1 multi-agent bug, and what you
     omit here the agent will improvise. Every slot: fill it, or write "n/a — <why>". Prose in the
     spawn never grants authority the agent's own definition (tools, tiers) doesn't already carry. -->

**Objective**: <!-- required: one sentence — what done looks like, not how -->

**Scope in**: <!-- required: the components/files this agent owns (disjoint from every parallel builder) -->

**Scope out / non-goals**: <!-- required: what it must NOT touch or attempt, incl. tempting adjacencies -->

**Acceptance criteria**: <!-- required: checkable statements the agent self-verifies before returning -->

**Boundary**: <!-- required: run to here, then return once — never mid-batch status; return early only on a material fork -->

**Inputs**:
- Environment card / mission block: <!-- required: path (usually the repo's CLAUDE.md) -->
- Contract artifact: <!-- multi-component only: path + version being built against -->
- Focus files / prior packets: <!-- reviewer spawns: "Check first" entries and nothing more — never your diagnosis or fix -->

**Leash**: reversible decisions are yours — make them and log them in your packet. A material fork
(changes what gets built and isn't inferable) comes back as the question plus your recommended
default. <!-- add lab-work tier constraints or other authority notes here, citing the approval, not restating it -->

**Return contract**: end with your agent file's packet. Name partial work explicitly — partial never
reads as complete. If you built against a contract version that changed while you ran, say so; the
result is stale until reconciled.
