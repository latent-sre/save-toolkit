# 2026-08-24 host context-budget audit

## Conclusion

The three numbers in scope govern different surfaces:

| Number | Contract | Consequence here |
|---|---|---|
| 8,000 characters | Claude's default aggregate model-visible skill-listing budget on a 200k-token context | Description discovery can degrade to name-only; it is not a `SKILL.md` body cap |
| 5,000 tokens per skill / 25,000 total | Claude's post-compaction reattachment budget for invoked skills | Conditional references reduce retained invoked context; they do not reduce discovery metadata |
| 30,000 characters | GitHub Copilot custom-agent Markdown prompt below frontmatter, per `.agent.md` profile | Validate the fully generated agent prompt; this is not an Agent Skill or aggregate-fleet limit |

The owner-approved **5,000 immutable-byte** SKILL-001 Phase 2 screen is deliberately a fourth,
repository-local number. It is a conservative candidate-selection rule, not a vendor limit and not a
claim that every selected skill must shrink below 5,000 bytes.

## Evidence bases

### Claude Code

- `[sourced]` The current [Claude skills documentation](https://code.claude.com/docs/en/skills)
  says the aggregate names-and-descriptions listing uses 1% of context, retains names when
  descriptions are cut, supports `skillListingBudgetFraction` and
  `SLASH_COMMAND_TOOL_CHAR_BUDGET`, and caps combined `description` plus `when_to_use` at 1,536
  characters by default.
- `[sourced]` The same page says an invoked rendered body persists as one conversation message;
  identical reinvocation adds an already-loaded note, changed content appends again, and compaction
  reattaches the newest invocation of each skill up to 5,000 tokens per skill and 25,000 total.
  It recommends a `SKILL.md` under 500 lines with directly linked supporting files.
- `[verified]` `claude --version` reported `2.1.241 (Claude Code)` and resolved to
  `C:\Users\hawkins\.local\bin\claude.exe`. Read-only binary inspection found the implemented
  defaults `skillListingBudgetFraction = 0.01`, `bytesPerToken = 4`, context fallback `200000`, and
  per-description cap `1536`, with `SLASH_COMMAND_TOOL_CHAR_BUDGET` checked first. The fallback
  calculation is therefore `200000 * 4 * 0.01 = 8000` characters; a one-million-token context would
  yield 40,000 characters under the same fraction.

### GitHub Copilot and Agent Skills

- `[sourced]` GitHub's
  [custom-agent configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
  limits the Markdown below YAML frontmatter to 30,000 characters. Its surrounding table applies to
  GitHub.com, Copilot CLI, and supported IDEs unless a property says otherwise, so the limit is per
  custom-agent profile rather than an aggregate fleet number.
- `[sourced]` The open
  [Agent Skills specification](https://agentskills.io/specification) caps `description` at 1,024
  characters and recommends fewer than 5,000 tokens and 500 lines for an activated `SKILL.md`, with
  resources loaded only when needed.
- `[sourced]` GitHits inspection of `github/docs` commit `4f8c3170`,
  `agentskills/agentskills` commit `69ef37e`, and `microsoft/vscode` commit `40f27cc` confirmed those
  documented limits. The public VS Code prompt-body validator checks references and enabled tools but
  showed no length check in the inspected path.
- `[unverified]` Public sources do not establish where every Copilot surface enforces the 30,000
  limit or whether “character” means Unicode code point, grapheme cluster, or UTF-16 code unit. The
  repository guard uses Python decoded-string length and reports that assumption; current margins are
  large enough that the ambiguity does not change any result below.

## Exact repository measurement

All immutable-byte measurements use exact base
`b9b274f237caf8ce6068812e151f8543f608c7e7` (`origin/main` on 2026-08-24), not checkout line
endings. The nine completed Phase 1 skills are excluded by owner decision:
`incident-command`, `ops-tooling`, `agent-security`, `ci-actions`, `pcf-deploy`, `pcf-ops`,
`production-change-gate`, `database-reliability`, and `stack-profile`.

### SKILL-001 Phase 2 candidates

| Candidate | Entrypoint bytes | Reference bytes | Initial recommendation |
|---|---:|---:|---|
| `frontend-craft` | 13,827 | 37,078 | Assess first; largest entrypoint and substantial routable depth |
| `backend-craft` | 10,814 | 28,628 | Assess after the frontend pattern is reviewed |
| `obs-dashboards` | 10,724 | 81,867 | Strong router candidate |
| `agent-authoring` | 9,420 | 63,277 | Strong router candidate; preserve always-loaded authority rules |
| `obs-alerting` | 7,656 | 29,640 | Likely router candidate |
| `runbook` | 7,385 | 8,185 | Assess semantic split before changing |
| `gcp-ops` | 7,384 | 6,786 | Assess semantic split before changing |
| `operational-learning` | 6,078 | 4,958 | Likely retain unless a clean conditional boundary exists |
| `eng-ladder` | 5,873 | 20,248 | Likely router candidate; keep its owed routing eval separate |
| `obs-pipeline` | 5,835 | 14,664 | Likely router candidate |
| `root-cause` | 5,048 | 0 | Retain unless obsolete text is found; size alone is not a finding |
| `obs-traces` | 5,024 | 18,821 | Near-threshold; assess cohesion before changing |

The selected set is 12 entrypoints totaling 95,068 bytes. Selection means “inspect,” not “rewrite.”
Each skill remains its own evidence/recommendation checkpoint, and a cohesive near-threshold body may
receive `not_applicable` rather than a forced split.

### Claude discovery listing

- `[verified]` The 30-skill fleet has 28 model-invocable skills and two manual-only skills
  (`pcf-deploy`, `service-onboarding`).
- `[verified]` Rendering the 28 model-visible entries as
  `- save-toolkit:<name>: <description>` plus separators uses 13,239 characters, 5,239 above the
  default 8,000-character fallback. Names alone plus separators use 803 characters.
- `[verified]` No individual fleet description reaches Claude's 1,536-character cap, and every
  `SKILL.md` entrypoint is under 500 lines.
- `[unverified]` The exact descriptions removed in a real session depend on host priority, usage,
  bundled skills, selected model context, and local overrides. Body compaction cannot repair this
  separate discovery risk. Measure it with `/doctor` or `/context` on a declared 200k session before
  changing routing descriptions.

### Generated Copilot agent prompts

Counted as decoded characters in the generated Markdown body after YAML frontmatter, including the
generated host contract:

| Agent | Prompt-body characters | Headroom to 30,000 |
|---|---:|---:|
| `sde` | 21,584 | 8,416 |
| `reviewer` | 19,428 | 10,572 |
| `observability-engineer` | 17,596 | 12,404 |
| `sre` | 17,309 | 12,691 |
| `scribe` | 14,667 | 15,333 |
| `prompt-engineer` | 9,140 | 20,860 |
| `researcher` | 7,511 | 22,489 |
| `repository-investigator` | 3,491 | 26,509 |

No current profile violates the host contract. The preventive gap was that adapter generation did
not reject a future over-limit prompt.

## Agent inspection findings and disposition

1. `[verified]` `agents/scribe.md` contained the malformed sentence “Copilot receives no execute or
   On a host...”, omitting “web tool.” The candidate restores the intended host boundary sentence.
2. `[verified]` `scribe` and `reviewer` handoff templates claimed `[trusted] code/CI you ran` even
   though both roles intentionally lack execution. The candidate limits `[trusted]` to trusted-base
   code read and keeps CI output `[UNTRUSTED]` even when its provenance is authenticated; it does not
   widen tools or authority.
3. `[verified]` A focused over-limit fixture failed before the generator guard because no exception
   was raised, then passed after the guard rejected a generated prompt above 30,000 characters.

Recommendation: commit the agent wording corrections and the hard Copilot projection guard as one
bounded host-contract slice. Treat agent-body compaction as separate follow-up work: start with
`scribe` only after a fresh-context mode-selection packet is agreed, and do not move conditional
procedure out of `reviewer`, `repository-investigator`, or `researcher`, which intentionally cannot
load skills.

## What this audit does not prove

- It does not prove which fleet descriptions a particular Claude session will truncate.
- It does not prove runtime activation, reference selection, or answer quality for any Phase 2 skill.
- It does not prove every Copilot client counts Unicode characters identically.
- It does not authorize description rewrites, paid model trials, or multi-skill implementation.
