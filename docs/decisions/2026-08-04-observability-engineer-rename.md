# ADR: Rename `sre-steward` to `observability-engineer`

- Date: 2026-08-04
- Status: Accepted
- Decision owners: sre-agents maintainers

## Context

The steady-state observability role was named `sre-steward`. Two problems followed from that name,
one mechanical and one about routing.

The mechanical problem is that `sre` is a strict prefix of `sre-steward`, and the fleet's own tooling
matches component names by substring:

- `scripts/generate_platform_adapters.py` rewrites backticked sibling names into the prefixed Codex
  identity with `str.replace`. It carried an explicit longest-first sort whose only stated purpose was
  keeping `sre` from rewriting inside `sre-steward`. A future contributor reordering that loop would
  have silently corrupted every generated adapter.
- `evals/graders.py:contains_any` tests `needle.lower() in response.lower()`. The two scenarios that
  guard the incident-versus-steady-state boundary asserted the bare string `"sre"`, which a response
  routing to `sre-steward` satisfies. The evals protecting that lane split could pass on the wrong
  lane.
- `scripts/check_stale_names.py` needs hyphen-aware lookaround boundaries because retired names nest
  inside live ones.

The routing problem is that "steward" names a stance, not a lane. Every other agent is a job (`sde`,
`reviewer`, `scribe`, `researcher`) or a lane (`repository-investigator`), so the description carried
the entire disambiguation load and `AGENTS.md`, both agent bodies, `incident-command`, `postmortem`,
and `scribe` each spent a sentence restating which of the two `sre*` names to pick. The role also owns
the whole `obs-*` skill namespace and its name connected to none of it.

## Decision

1. Rename the agent to `observability-engineer`. The name leads with the lane, is a unique token that
   is neither a prefix nor a substring of any other agent name, and matches the existing hyphenated
   `prompt-engineer` convention.
2. Add `sre-steward` to the `STALE` tuple in `scripts/check_stale_names.py`, as `observer` was when it
   retired into `sre-steward`.
3. Tighten the two evals that asserted a bare `"sre"` substring into name-boundary `regex` graders, so
   the `sre-agents` plugin prefix cannot stand in for naming the incident lane. This is a real defect
   the rename exposed rather than fixed: the prefix collision with `sre-agents` survives any agent
   rename.
4. Keep the generator's longest-first ordering as a defensive measure and restate its comment, since
   no current name nests inside another.
5. Leave dated plans, specs, and recorded eval baselines under the old name. They are evidence of what
   ran, and rewriting a recorded result to match current vocabulary would falsify it.

## Alternatives considered

- **`observability`:** rejected. It is the shortest and maps one-to-one onto the `obs-*` skills, but
  it is also common prose in this repository, so it trades a prefix collision for a vocabulary
  collision in exactly the substring-matching tooling this ADR is fixing.
- **`obs-engineer`:** rejected. Short and namespace-aligned, but `obs-` is the *skill* prefix, so an
  agent sharing it blurs the agent/skill distinction.
- **`observability-steward`:** rejected. It ends the prefix collision but keeps a word that carries no
  routing signal, fixing the mechanical problem and not the naming one.
- **Keep the name and harden the tooling:** rejected. Word-boundary matching everywhere would fix the
  false-pass, but leaves two sibling lanes whose names imply seniority tiers of one role.

## Consequences

- The incident lane and the steady-state lane are lexically independent; no matcher can reach from one
  into the other.
- Any operator muscle memory, external bookmark, or prompt naming `sre-steward` breaks. The stale-name
  check turns that into a build failure inside `agents/`, `skills/`, and `commands/` rather than a
  silent miss.
- Component addressing is longer: `sre-agents:observability-engineer`.
- The rename does not change tool authority, the guard allowlist, or any delegation edge. `sre` still
  delegates to this role, and the role still delegates to `scribe` and `researcher`.

## Rollback

Revert the canonical `agents/observability-engineer.md`, the guard, validator, evals, and documentation
together, then regenerate adapters with `python scripts/generate_platform_adapters.py --write`. Never
revert the canonical agent while leaving generated roots on the new name; `scripts/validate_fleet.py`
treats that drift as a failure. The eval grader tightening in step 3 stands on its own and should be
kept on rollback.
