# Three-pass sister-lab import review

- Date: 2026-07-31
- Target baseline: `sre-agents@e2eef274d21ef2df16f92c77543be83a396cec83`
- Sister baseline: `sde-agents@d50eda62c4fec083f5a5b0b3980f845d7ae0d8a1`
- Scope: plugin packaging, agents, skills, progressive-disclosure bundles, validation, and eval method
- Status: implementation and three-pass review complete; no unresolved P0/P1 findings

## Pass 1 — packaging and platform contracts

Conclusion: adopt the sister repo's canonical-source/generated-adapter architecture, but implement a
target-specific generator rather than transplanting its roster-hardcoded code.

Adopted:

- Claude, Copilot/VS Code, and Codex manifests/marketplaces with one identity/version.
- Root `agents/` + `skills/` canonical source and committed host-native projections.
- Session-wide Claude hook rooted at `${CLAUDE_PLUGIN_ROOT}`; plugin-inert agent hooks removed.
- Narrower Copilot authority for guarded roles; standalone Codex agent TOML and conflict-safe installer.
- Transactional generation, link/reparse traversal refusal, exact drift checks, and host-specific
  invocation policies with Claude's cooperative limit documented rather than overstated.

Not copied:

- The sister generator verbatim: its roster names, special cases, and text rewrites are donor-specific.
- Raw Claude frontmatter on other hosts, symlinked sources, or four independently authored copies.
- Runtime publication claims not proven in this repository.

## Pass 2 — agent, skill, reference, and eval patterns

Conclusion: import targeted methods that close observed gaps; do not replace this fleet's PCF/TAS and
split-observability domain model.

Adopted or adapted:

- Reviewer identity binding: immutable full SHA versus provisional mutable-worktree verdicts,
  categorical confidence, false-positive/pre-existing gates, and concrete source-to-sink paths.
- Researcher exact read-only Context7 and GitHits grants with local/official/upstream provenance kept
  separate and no external-write tool.
- SDE stale-finding/reproduction protocol and prompt-engineer paired old/new reps, held-out cases, and
  wrapper bisection.
- Native fleet validator plus mutation tests, hook-wiring tests, adapter tests, and installer tests.
- Progressive-disclosure references for API design, TypeScript, multi-component contracts/batches,
  frontend design language, interaction accessibility, UX writing, and database restore drills.
- Postmortem asset template and a corrected top-level RFC 9457 interface-contract example.

Deferred:

- New verification and application-security agents. Their proposed value is real, but adding lanes
  before routing/isolation evidence would widen the roster and authority without a proven boundary.
- FastAPI- and framework-specific references until this PCF fleet has a repository/version predicate
  that makes them load only when relevant.

Rejected for this fleet:

- Homelab/platform agents and skills, a monolithic observability skill, Kubernetes/cloud defaults, and
  wholesale donor replacement. They conflict with `stack-profile` and current lane ownership.

## Pass 3 — integrated adversarial review

Conclusion: the first independent diff review found four P1 integration defects and no P0. Each P1
was fixed, covered by a targeted regression, and returned to the independent reviewer. The scoped
re-review approved all four fixes and found no residual P0/P1 introduced by them.

Findings and dispositions:

1. **P1 — guarded-Bash hook had a raw-JSON prefilter bypass.** Whitespace/key-shape drift could skip
   the Python identity canary. Fixed by sending every Bash payload to `readonly-guard.py`; an
   unavailable interpreter now denies all Bash rather than silently allowing it. Runtime tests cover
   guarded allow/deny, unguarded main-thread input, whitespace drift, renamed identity, and missing
   interpreters.
2. **P1 — generated agent descriptions leaked Claude's `sre-agents:` namespace.** Fixed by adapting
   both Copilot and Codex descriptions before serialization. The regression iterates all six agents.
3. **P1 — a generator stage-swap failure could strand the current root's backup.** Fixed by restoring
   that iteration immediately before the outer rollback. An injected second-stage failure proves all
   four prior generated roots survive byte-for-byte.
4. **P1 — the Codex installer had a preflight/apply race.** A concurrent replacement could be
   overwritten or removed after planning. Fixed with expected-byte plans, atomic claim-and-verify for
   existing targets, and create-if-absent publication. Tests cover concurrent fresh creation,
   concurrent managed replacement, and concurrent stale-file replacement.

## Verification evidence

Verified on the working tree after all remediations:

- `[verified]` `py -3 scripts/gate_a.py` — **PASS, 11/11 structural steps**. Included 4 validator
  mutation tests, 11 adapter tests, 7 installer tests, 4 hook-wiring tests, 15 read-only guard tests,
  56/56 grader checks, 19/19 clean-room checks, and parsing of all 12 shipped eval scenarios.
- `[verified]` `claude plugin validate . --strict` on Claude Code 2.1.220 — marketplace validation
  passed.
- `[verified]` the Codex plugin-creator validator passed `plugins/sre-agents`.
- `[verified]` an isolated clean-config Claude invocation with `--plugin-dir` and
  `--agent sre-agents:reviewer` returned exactly `PLUGIN_AGENT_LOADED` with exit code 0.
- `[verified]` `git diff --check` passed; generated outputs were regenerated and byte-checked.
- `[verified]` the independent Pass 3 fix re-review approved all four remediations with no residual
  P0/P1 directly introduced by them.

Limits and remaining release checks:

- `[verified]` direct non-marketplace validation of `.claude-plugin/plugin.json` passes with one
  warning: root `CLAUDE.md` is repository/project guidance and is not loaded as plugin context.
  `--strict` promotes that warning to failure. The distributable marketplace manifest passes strict
  validation; no plugin behavior relies on root `CLAUDE.md` being shipped as context.
- `[unverified]` Copilot/VS Code runtime loading was not probed because the Copilot CLI is not
  installed. Its manifest, generated tools, namespace rewrites, and guarded-role narrowing are
  structurally tested only.
- `[unverified]` Codex custom-agent runtime discovery was not probed. The plugin schema, generated
  TOML syntax, sandbox selection, collision-safe installer, and skill policies are structurally
  validated.
- `[unverified]` behavioral evals were not executed. Gate A proves scenario/target/grader integrity,
  not answer quality. Run the clean-room behavioral suite from a throwaway worktree before a public
  release when authenticated model calls are authorized.
