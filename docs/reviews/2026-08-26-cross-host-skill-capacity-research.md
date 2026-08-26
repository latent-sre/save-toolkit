# Cross-host skill-capacity research — Claude Code, Codex, and Copilot/VS Code

- **Date:** 2026-08-26
- **Repository baseline:** `f9534a3e8de456b56260b5b212f709f0d677a081`
- **Scope:** the 33 canonical skills and their generated host projections
- **Method:** three independent GPT-5.6 Terra research runs, one per host, followed by a
  repository-level cross-check against first-party documentation
- **Verification boundary:** static repository measurement and public-source review; no skill evals
  or runtime host trials were run

This note records research evidence and recommendations only. It creates no backlog item, changes no
fleet authority, and does not authorize implementation. Only `docs/fleet-roadmap.md` can import
unfinished work from this review.

## Conclusion

Thirty-three skills are not inherently too many for any of the three hosts. The current problem is
the size and overlap of routing metadata, not the number or total size of progressively loaded skill
bodies.

| Host | Finding | Disposition |
|---|---|---|
| Claude Code | The model-visible catalog is larger than the current default discovery budget | Keep the skills; shorten and differentiate model-invocable descriptions |
| Codex | This repository deliberately does not distribute these skills to Codex; a hypothetical restored catalog would be near the resolved-model metadata cap and above the unknown-model fallback | Do not restore distribution to solve a count problem; optimize metadata if distribution is reconsidered for independent reasons |
| Copilot/VS Code | The host uses progressive disclosure and no first-party aggregate skill-count limit was found | Keep the skills; reduce routing overlap and picker clutter |

## Exact repository measurement

`[verified]` The following values were recomputed from the clean PR #180 head named above. Character
counts use decoded repository text; byte counts use UTF-8 encoding.

| Surface | Measurement |
|---|---:|
| Canonical skills | 33 |
| Model-invocable skills | 30 |
| Manual-only skills | 3 (`incident-drill`, `pcf-deploy`, `service-onboarding`) |
| All canonical description characters | 14,795 |
| Model-invocable description characters | 13,575 |
| Claude-qualified model-invocable name characters | 794 |
| Claude raw name-plus-description lower bound | 14,369 |
| Hypothetical Codex name-plus-description-plus-path characters | 16,215 |
| Generated Copilot description characters | 14,769 |
| Canonical `SKILL.md` characters / UTF-8 bytes / lines | 223,870 / 224,923 / 3,261 |
| Largest canonical skill entrypoint | 155 lines |
| Largest individual description | 589 characters |
| Generated Copilot skill characters / largest entrypoint | 231,738 / 160 lines |

`[verified]` Eighteen descriptions contain an `Ownership map` tail, totaling 2,491 characters, and
the `Triggers:` portions across descriptions total 7,313 characters. Some of that language is useful
for routing, but its current repetition consumes the scarce always-visible surface. The descriptions
also contain several routing-adjacent families that need sharper boundaries rather than merged
bodies:

- `operational-learning`, `postmortem`, and `runbook`
- `merge-gate`, `release-gate`, and `production-change-gate`
- `obs-logs`, `obs-metrics`, `obs-traces`, and `obs-pipeline`
- `backend-craft`, `frontend-craft`, and `language-idiom`
- `gcp-ops` and `pcf-ops`
- `incident-command` and `incident-investigation`

## Claude Code

`[sourced]` Claude Code's current
[skills documentation](https://code.claude.com/docs/en/skills) says model-invocable skill names and
descriptions occupy the discovery catalog while a full `SKILL.md` body loads only after selection.
When that catalog exceeds its budget, Claude retains names and removes lower-priority descriptions.
The same documentation sets a 1,536-character per-entry metadata limit, recommends entrypoints below
500 lines, and says `skillOverrides` do not apply to plugin skills. The
[model configuration documentation](https://code.claude.com/docs/en/model-config) distinguishes
200K- and 1M-context configurations, so the available discovery budget is host/model dependent.

`[verified]` Every individual skill meets the documented per-entry and line-count guidance. The
30 model-invocable descriptions plus their `save-toolkit:`-qualified names already require at least
14,369 characters before Claude's formatting or any other installed skills. That exceeds the
current default 10,000-character ceiling applicable to a 1M-context catalog and leaves still less
room on smaller configurations.

`[sourced]` Claude Code
[v2.1.246](https://github.com/anthropics/claude-code/releases/tag/v2.1.246), released 2026-08-25,
fixed doubled plugin prefixes and a reload case that could report zero skills. Those fixes improve
correctness but do not remove the catalog-budget constraint.

**Finding:** Claude is the only current distribution target where the repository has a demonstrated
aggregate metadata-capacity problem. It is a discovery problem, not evidence that any skill body is
too large or that 33 skill lanes should be collapsed.

## Codex

`[verified]` The accepted
[Codex distribution retirement](../decisions/2026-08-23-retire-codex-distribution-target.md) removes
the fleet's Codex projection. Codex working in this checkout receives `AGENTS.md`, but it receives
zero of these 33 fleet skills unless a user separately installs them. The retirement addressed
authority and enforcement parity, not skill count.

`[sourced]` The current official OpenAI
[Build skills documentation](https://learn.chatgpt.com/docs/build-skills) says Codex initially loads
each skill's name, description, and file path, then loads the full body only on selection. The
initial list uses at most 2% of the resolved model context, uses an 8,000-character fallback when
the context is unknown, shortens descriptions before omitting entries, and warns when entries are
omitted. It also recommends concise, front-loaded descriptions because shortening can affect
implicit matching.

`[sourced]` The current implementation introduced by OpenAI's
[skill metadata budgeting change](https://github.com/openai/codex/pull/34626) caps a
resolved-model catalog at 4,000 tokens; the 8,000-character value is the fallback, not the normal
large-context allowance. `[unverified]` The exact token count of a hypothetical installed fleet
cannot be established from raw character count because host serialization, tokenizer choice,
resolved paths, and other installed skills are not captured here.

`[verified]` A simple raw rendering of all canonical names, descriptions, and canonical relative
paths is 16,215 characters. It is therefore over the fallback and close enough to the 4,000-token
resolved-model cap to require host measurement rather than an assumption that a large model window
makes the catalog unlimited.

**Finding:** there is no present Codex fleet-capacity problem because there is no Codex fleet
distribution. If that decision is ever reopened, metadata size and authority parity both need to be
re-evaluated; capacity alone is not a reason to restore the projection.

## GitHub Copilot and VS Code

`[sourced]` VS Code's current
[Agent Skills documentation](https://code.visualstudio.com/docs/agent-customization/agent-skills)
describes three-stage progressive disclosure: name and description for discovery, `SKILL.md` after
selection, and supporting resources only when needed. It explicitly says many skills can be
installed without placing every full body in context and caps each description at 1,024 characters.
No first-party aggregate count or catalog-size limit was found.

`[verified]` All 33 generated Copilot descriptions are below 1,024 characters. This repository's
`.vscode/settings.json` adds `platforms/copilot/skills` as a skill location, and `plugin.json`
publishes the same generated projection. The full generated corpus is not an always-loaded prompt,
so its 231,738 characters do not demonstrate context pressure.

`[sourced]` GitHub announced
[Agent Plugins 1.0](https://github.blog/changelog/2026-08-12-agent-plugins-1-0-in-vs-code-copilot-cli-and-the-copilot-app/)
across VS Code, Copilot CLI, the SDK, and the Copilot app while preserving existing formats. That
could simplify future packaging, but it does not itself resolve description overlap or establish
Claude-equivalent authority controls. GitHub's
[custom-agent configuration limit](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
of 30,000 characters applies to each `.agent.md` prompt body, not to the aggregate Agent Skills
catalog.

`[sourced]` GitHub.com's code-review support for skills expects repository skills under
[`.github/skills`](https://github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available/).
`[unverified]` Nothing reviewed proves that this repository's VS Code-only custom location also
exposes the projection to GitHub.com code review.

**Finding:** Copilot/VS Code can retain all 33 skills. The material risks are ambiguous implicit
routing and an unwieldy manual picker, not aggregate prompt-body loading.

## Recommended improvement

1. Keep the 33 current lanes unless a separate ownership review finds two skills semantically
   identical. Do not merge workflows merely to reduce a count.
2. Run one cross-host description pass. Target roughly 200–250 characters for each model-invocable
   description: owner/job first, high-signal triggers second, and the closest exclusion last. Move
   procedural detail and repeated ownership maps into the body or a linked reference.
3. Preserve the three manual-only skills. Their metadata does not need to compete for implicit
   routing merely to make the catalog look uniform.
4. Add a static generated-catalog measurement with a declared Claude threshold. At 250 characters
   per model-invocable description, the current 30 descriptions plus qualified names would total
   about 8,294 characters before host formatting, a nominal 1,706-character margin below a
   10,000-character ceiling. Host formatting and other installed skills consume part of that margin.
5. Treat host diagnostics as the final capacity evidence: Claude `/doctor` or `/context`, Codex's
   omission warning if distribution is ever restored, and the VS Code skill picker plus routing
   traces. Static character counts do not prove which description a live host will shorten or omit.
6. Consider host-specific packs or a smaller default set only if supporting Claude's tighter
   contexts is an explicit requirement after the description pass. Do not make `context: fork` a
   fleet-wide default because it changes execution context and may conflict with the fleet's explicit
   ownership graph.

## Limits of this research

- `[unverified]` No live Claude session established the exact descriptions currently removed.
- `[unverified]` No installed Codex fleet established the exact tokenized catalog size, because this
  repository intentionally has no Codex distribution target.
- `[unverified]` No Copilot/VS Code runtime trial measured ambiguous activation or picker usability.
- The research did not run evals, edit skill descriptions, regenerate adapters, or assess answer
  quality. Any future candidate remains subject to exact-revision human acceptance.
