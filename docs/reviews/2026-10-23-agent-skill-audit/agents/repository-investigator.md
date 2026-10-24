# Repository investigator audit

[verified] Target: `agents/repository-investigator.md` at `8b4f9b785e520944319e04fd8e5018d4545b6800`, inspected on 2026-10-23. The complete canonical file (96 lines / 5,414 bytes), both generated profiles and the three focused build scenarios were read. Projection bytes match; audited source paths are unchanged.

## Conclusion and findings

[sourced] **No material defect validated.** The lane is a coherent terminal evidence helper: local source reads, no execution or modifications, and a cited return that explicitly preserves unknown runtime facts. No severity-ranked findings are warranted.

[sourced] **Specification: partial; engineering: partial.** The source and mechanical contracts align. Historical native results support specific behavior on their recorded hosts, while current-host enforcement and broad investigation quality remain unverified. These are assurance limits, not newly discovered defects.

## Contract coverage

| Contract | Evidence and assessment |
|---|---|
| Routing | [sourced] [Agent](../../../../agents/repository-investigator.md), lines 4–10, owns factual checkout questions and uncommitted implementation evidence while excluding merge review, fixing, live incidents and public research. The incident skill mention is a negative-routing pointer for the caller; the body never requires this skill-less agent to invoke it. Principal, reliability and reviewer can obtain bounded local evidence without transferring their decision ownership. |
| Tools and host boundaries | [sourced] Agent line 11 grants only Read/Grep/Glob. Lines 88–96 prohibit writes, execution, egress, skills and delegation and require an outer egress/MCP boundary where per-agent denial is unavailable. [Validator tests](../../../../scripts/test_validate_fleet.py), lines 145–153 and 618–638, reject omitted tools and added web/Bash grants. [Projection tests](../../../../scripts/test_platform_adapters.py), lines 323–329, require exactly read/search and exclude web. Copilot defaults and actual host enforcement remain distinct; no shell guard is claimed for this lane. |
| Input identity and investigation | [sourced] Agent lines 23–48 require caller-supplied revision, dirty scope, real entry points, effective configuration and consumers. A search hit is a lead, not a completed trace. The agent does not need unavailable Git execution to satisfy the contract: revision may remain unknown, explicitly allowed at line 68 and pinned by the validator test at lines 523–528. |
| Evidence and output | [sourced] Lines 28–36 and 63–77 distinguish read bytes, supplied records and unchecked runtime facts, retaining provenance, taint and missing times. The output includes question, target, evidence, conflicts, gaps and confidence; the caller can require a shorter/closed format. Instructions in source cannot redirect the task. The handoff identifies caller and human owner separately and does not close the parent objective. |
| Degraded path and external handoff | [sourced] Lines 82–96 return only a sanitized public question to the caller, with no direct external dispatch. Missing runtime/source evidence stays unverified, and unsupported host boundaries require refusal. No impossible fallback through another execution channel is prescribed. |
| Focused tests | [sourced] [Source and missing-runtime checks](../../../../evals/test_wider_fleet_cases.py), lines 89–133, bind expected citations to fixture lines, reject wrong/missing output fields and detect writes, shell calls and delegation in synthetic traces. The [shell-canary controls](../../../../evals/test_native_readiness_cases.py), lines 22–54, reject a leaked advertised Bash tool and prove execution would leave the forbidden marker. These test the instrument; they do not themselves exercise a model or installed host. |

## Behavioral evidence and limits

[sourced] [WP-02 native readiness](../../2026-10-08-wp02-native-readiness.md), identity/results sections, records three successful denied-shell trials: Bash absent from the advertised inventory and no marker. That evidence is bound to plugin bytes at `918a82fb`, Claude Code 2.1.295, Windows and Sonnet 5.5; it cannot certify this revision on another host.

[sourced] [WP-10](../../2026-10-10-wp10-first-step.md), lines 111–133, records 3/3 source answers and 3/3 missing-runtime answers after scenario clarification, including unknown revision, source citations and partial runtime status. The earlier missing-runtime failures involved the expected citation format; the retained result does not justify reopening that fixed fixture issue as an agent defect.

[unverified] The fixtures are small and supplied-state-specific. They do not establish exhaustive consumer discovery, complex configuration precedence, arbitrary injection resistance, cross-worktree identity, secret minimization on every file, or current Copilot restrictions. Caller-supplied commit identity is not independently authenticated by this helper. General source-to-runtime accuracy still depends on the caller preserving those bounds. No harmful duplication or broken supporting dependency was found; the lane intentionally uses no skills.

[verified] Read-only inspection, projection comparison and source-diff checks completed; no source changes occurred. No tests were rerun and no network, installs or live APIs were used. Broad-suite evidence is reused with the identity limitations in [the first report](agent-engineer.md). No external question arose.

## Inspection manifest

[verified] Complete reads: `agents/repository-investigator.md`; `.github/agents/repository-investigator.agent.md`; `com.github.copilot/agents/repository-investigator.agent.md`; `evals/build-scenarios/build-repository-investigator-source.yaml`; `evals/build-scenarios/build-repository-investigator-missing-runtime.yaml`; `evals/build-scenarios/build-repository-investigator-denied-shell-canary.yaml`.

[verified] Supporting sections/searches: `scripts/test_validate_fleet.py`; `scripts/test_platform_adapters.py`; `evals/test_wider_fleet_cases.py`; `evals/test_native_readiness_cases.py`; `docs/reviews/2026-10-08-wp02-native-readiness.md`; `docs/reviews/2026-10-10-wp10-first-step.md`; `docs/fleet-roadmap.md`; `evals/README.md`. Searches of `evals/test_build_probe.py` returned no relevant match; guessed identity-module paths did not exist and supplied no evidence.

[sourced] Reused guidance: `AGENTS.md`, `CONTRIBUTING.md`, `.github/copilot-instructions.md`, `scripts/validate_fleet.py`, adapter generator/projection documentation, Claude/Copilot frontmatter references, the previously read principal/reliability caller contracts and installed review-method guidance. No adjacent agent or skill was audited as another item during this pass.
