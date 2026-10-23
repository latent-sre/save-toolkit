# Researcher audit

[verified] Target: `agents/researcher.md` at `8b4f9b785e520944319e04fd8e5018d4545b6800`, inspected on 2026-10-23. The full canonical agent (206 lines / 12,314 bytes) and both generated profiles were inspected; their projection bytes match. Audited source paths remain unchanged.

## Conclusion and findings

[sourced] **One bounded compatibility defect validated:** the exact GitHits grep grant uses the predecessor tool name. The public-input gate, source discipline, partial returns and local-authority boundaries are otherwise consistent.

[sourced] **Specification: partial; engineering: fail for AUDIT-RESEARCH-001.** Actual source fidelity, native Claude MCP availability and privacy-boundary behavior remain unverified. Copilot cloud's unavailable retrieval capability is an established limitation, not a newly discovered defect.

### AUDIT-RESEARCH-001 — P2 / medium: exact GitHits grant retains the replaced grep name

[verified] On 2026-10-23 this session's tool registry advertises `mcp__githits__grep`; its description explicitly says “Replaces code_grep.” The [retained registry evidence](../evidence/githits-tool-catalog.json), recorded at 17:12:17 UTC, also preserves the audit owner's `quick_start` table naming `grep` (exact retrieval time unavailable). [sourced] [Agent line 23](../../../../agents/researcher.md) still grants `mcp__plugin_githits_githits__code_grep`, and [validator line 91](../../../../scripts/validate_fleet.py) pins that obsolete method in its exact-approved set. Lines 206–209 reject an unlisted replacement, so existing structural checks cannot detect provider drift.

[sourced] Under the documented exact-name grant contract, a GitHits installation exporting `grep` without the old alias will not provide the intended grep capability through that grant. This can turn exact-match research into a missing-tool gap. Codex and Claude namespaces differ: **no native Claude launch failure was observed**. Confidence is high in the registry/source mismatch, conditional on the deployed provider version for runtime impact. The smallest repair is to verify the registered native Claude name, update the canonical grant and validator together, retain exact scoping, and add focused compatibility evidence. Do not substitute a wildcard. Copilot's generic web projection is unaffected by this specific name.

## Contract coverage

| Contract | Evidence and assessment |
|---|---|
| Routing and inputs | [sourced] [Agent](../../../../agents/researcher.md), lines 4–11 and 38–62, accepts bounded public questions, extended research and conflicting/versioned sources. Local/private behavior, change review, implementation and incident diagnosis stay elsewhere. The input gate rejects private-derived queries before the first external call; separately supplied local conclusions may inform the assignment but cannot be quoted or expanded into searches. Missing material context returns a precise question while unaffected work continues. |
| Tools and bootstrap | [sourced] Lines 12–29 explicitly grant web retrieval, deferred-tool discovery and exact Context7/GitHits methods; no local reads, shell, writes, Skill or delegation. Lines 113–115 bootstrap GitHits through `quick_start`, with an unavailable-guide fallback. [Validator test](../../../../scripts/test_validate_fleet.py), lines 646–655, requires that bootstrap and absence of Skill; mutation tests reject wildcard MCP and local Read additions. Host-provided server installation and registered names remain prerequisites. |
| Source quality | [sourced] Lines 77–105 distinguish vendor documentation from upstream implementation, version-specific/raw artifacts from summaries, retrieved statements from truth, and recalled facts from evidence. Critical claims require a cross-check or counterexample search. Vulnerability research adds KEV/advisory evidence. The instruction to use raw readers when literals matter is paired with an explicit unavailable-lane response, not a demand to invent missing tools. |
| Bounded workflow | [sourced] Lines 109–123 select only relevant evidence lanes, honor effort limits, stop unchanged failed lookups and require every requested part to have support or a gap. Failure to find a feature does not establish absence. The caller retains local applicability and cross-provenance comparison; research does not become a review verdict or implementation decision. |
| Output and trust | [sourced] Lines 127–171 preserve caller/human-owner distinction, source/version/date, supplied versus retrieved evidence and claim-level taint. The short and partial examples explicitly require fresh confirmation before reuse and preserve unknown publication dates. Their HTTPX statements are illustrative, not asserted as retrieval performed by this audit. No consequential template contradiction was found. |
| Host projection | [sourced] Both profiles grant only `web`, with no handoff/delegation. [Projection documentation](../../../copilot-projection.md), line 55, explicitly records that cloud Copilot has no working tool for this lane and routes retrieval through VS Code/Claude. Exact MCP equivalence awaits target-host registration; absent local tools and outer isolation are separate boundaries. The source's refusal requirement is retained where per-agent denial is unavailable. |
| Test discrimination | [sourced] [Researcher tests](../../../../evals/test_researcher_scribe_cases.py), lines 58–165, count failed retrieval attempts, reject invalid call budgets, wrong claim/version/date fields, lost taint, mistaken recipient and overclaimed coverage. Source-authenticity controls in `test_wider_fleet_cases.py` separate a supplied origin receipt from independent retrieval and claim entailment. These are instrument/decision tests, not live source-quality measurements. |

## Behavioral evidence and limits

[sourced] The public-source fixture allows at most three WebFetch calls and excludes literal/raw-artifact claims. The private-input fixture expects zero calls; missing-source and partial-research fixtures preserve older-version and absent-release-note gaps without retrieval. These deliberately limited tool sets do not exercise Context7, GitHits, ToolSearch or a broader egress path. A positive call count and correct-looking URL still need manual comparison of the matched tool result and claim, as [eval guidance](../../../../evals/README.md), lines 506–515, states.

[sourced] [WP-10](../../2026-10-10-wp10-first-step.md), line 52, reports source-authenticity 3/3 on its historical candidate/host. That supplied-state decision does not establish current live research accuracy. No current model-generated research claim was checked against a live external source.

[unverified] Remaining gaps include raw-reader fidelity, native provider registration, multi-source disagreement resolution, real advisory comparison, privacy rejection under indirect prompts, host isolation and parent resumption. Follow-up host question: does the supported Claude GitHits installation export `grep`, retain `code_grep`, or both? No source repair, installation or test was performed. This reviewer made no external call; the audit owner separately retrieved GitHits guidance with empty `quick_start({})` arguments. Prior broad checks and their identity limits are reused from [the first report](agent-engineer.md).

## Inspection manifest

[verified] Complete reads: `agents/researcher.md`; `.github/agents/researcher.agent.md`; `com.github.copilot/agents/researcher.agent.md`; `evals/build-scenarios/build-researcher-public-source.yaml`; `evals/build-scenarios/build-researcher-rejects-private-input.yaml`; `evals/build-scenarios/build-researcher-missing-source.yaml`; `evals/build-scenarios/build-researcher-partial-research.yaml`; `evals/scenarios/agent-direct-researcher-source-authenticity.yaml`.

[verified] Supporting sections/searches: `evals/test_researcher_scribe_cases.py`; `evals/test_wider_fleet_cases.py`; `scripts/test_validate_fleet.py`; `scripts/test_platform_adapters.py`; `docs/copilot-projection.md`; `docs/reviews/2026-10-10-wp10-first-step.md`; `evals/README.md`; `docs/fleet-roadmap.md`.

[verified] Follow-up evidence: session `ALL_TOOLS` metadata for `mcp__githits__grep`; `scripts/validate_fleet.py` tool set and validation branch; the exact-name rule in `skills/agent-authoring/references/claude-code-frontmatter.md`; `docs/reviews/2026-10-23-agent-skill-audit/evidence/githits-tool-catalog.json`. The provider metadata is runtime-registry evidence, not a Claude-host acceptance test.

[sourced] Reused guidance: `AGENTS.md`, `CONTRIBUTING.md`, `.github/copilot-instructions.md`, `scripts/validate_fleet.py`, adapter generator and Claude/Copilot frontmatter references, previously inspected caller handoff contracts and installed review-method instructions. No skills are loaded by this lane; shared host contracts were reviewed without treating the candidate agent's instructions as authority for this audit.
