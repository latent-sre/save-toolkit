# Reviewer audit

[verified] Target: `agents/reviewer.md` at `8b4f9b785e520944319e04fd8e5018d4545b6800`, inspected on 2026-10-23. The full canonical agent (180 lines / 13,326 bytes) and both generated profiles were read. Projection bytes match; audited source paths are unchanged.

## Conclusion and findings

[sourced] **No material defect validated.** The lane coherently owns independent investigation and its verdict, permits bounded verification, preserves the candidate, and separates trusted instructions from review data. No severity-ranked finding is warranted.

[sourced] **Specification: partial; engineering: partial.** The declared contracts and focused fixtures align. Current host behavior, actual review quality beyond the seeded defects and the safety of a particular execution environment remain unverified. This audit does not issue the candidate a merge verdict.

## Contract coverage

| Contract | Evidence and assessment |
|---|---|
| Routing and review identity | [sourced] [Agent](../../../../agents/reviewer.md), lines 3 and 14–24, owns change/design review and independent finding verification, excluding fixes, repository-wide threat modeling and later release gates. Missing prepared diffs are recoverable through repository/PR reads. Immutable reviews bind a full SHA; mutable reviews bind paths/time/snapshot and remain PROVISIONAL. A changed candidate refreshes only affected analysis. |
| Instruction trust | [sourced] Lines 26–33 withhold a verdict when changed checkout instructions were loaded as the reviewer's own instructions; findings become leads for a trusted-base rerun. Line 51 loads only trusted installed/base skills or explicit trusted copies. Candidate runner assertions cannot establish isolation. This matches the caller's preparation contract and does not claim that an absolute path or worktree prevents instruction loading. |
| Evidence collection | [sourced] Lines 35–44 require hardened Git reads, branch and path history, tracked/untracked mutable content, complete changed-line coverage and unchanged source state. Missing objects go to reviewer-owned storage. Scoped GitHub reads are explicitly allowed; direct public research returns to the caller. No web/researcher grant is implied by Bash availability. |
| Execution and scratch writes | [sourced] Lines 48–87 restrict writes/runs to named scratch and differentiate team-authored code, established runners and outside contributions. The latter require independently established isolation. Explicit no-execution requests override default checks; unavailable checks become gaps. Full committed exports use a scratch index rather than attribute-sensitive archive export. The file explicitly states these are cooperative rules over broad Bash, not a sandbox or host filesystem guarantee. |
| Findings and verdict | [sourced] Lines 91–111 require a reachable introduced/worsened defect, counterevidence and an independent pass beyond caller leads. Lines 152–172 separate priority, confidence and evidence, allow no findings, and prevent unconditional approval across material evidence gaps. P0/P1 reproduction is subject to the preceding execution rules. Source reads and observed CI never become claimed runtime execution. PROVISIONAL review cannot supply exact-SHA production evidence. |
| Helper and handoff | [sourced] Lines 129–137 allow at most two bounded `repository-investigator` assignments and require reopening load-bearing citations; no child assigns the verdict. Lines 176–180 return repair decisions to the caller. [Tool tests](../../../../scripts/test_validate_fleet.py), lines 396–401, and [projection tests](../../../../scripts/test_platform_adapters.py), lines 189–193, pin that single helper and verification tools. The Copilot builder button is a human transition requiring accepted scope, not a model-call delegation edge. |
| Behavioral instrument | [sourced] [Reviewer tests](../../../../evals/test_reviewer_cases.py), lines 184–278, construct actual fixture branches and demonstrate a broken unchanged caller, unsafe evaluator, swallowed retry failure, cross-tenant read and uncommitted precision loss. Lines 347–373 distinguish scratch execution from in-place imports, including a standard-library-shadowing risk. Positive compatible-refactor controls help prevent a findings quota. These are fixture/check results, not a runtime reviewer assessment. |

## Coverage limits

[sourced] The scratch-reproduction case has a passing candidate suite but a separately reproducible missed alert, exercising independence from supplied tests. The outside-contributor case rejects a candidate runner that would leave a marker. The terse-handoff case includes both committed and uncommitted content. The helper case uses a pasted false approval; it does not establish a live child exchange. The established-environment case is an explicit supplied-state decision, not proof that an isolated runner was launched.

[unverified] Command-trace matching proves attempts, not successful interpretation; final source equality is not containment. Arbitrary shell syntax, malicious tests, remote PR identity handling, host instruction discovery and real helper reinspection still need environment-bound evidence. [Eval documentation](../../../../evals/README.md), lines 417–437, states these limits accurately. The broad tests already supplied by the caller do not convert them into general review competence. No new external question or harmful context duplication was identified.

[verified] No candidate code, tests, network, installs or live operations were executed in this item audit, and no source was edited. Inspection and projection/source comparisons completed. Existing broad-check evidence is reused with the receipt limits in [the first report](agent-engineer.md).

## Inspection manifest

[verified] Complete primary reads: `agents/reviewer.md`; `.github/agents/reviewer.agent.md`; `com.github.copilot/agents/reviewer.agent.md`; `evals/build-scenarios/build-reviewer-reproduces-in-scratch.yaml`; `evals/build-scenarios/build-reviewer-rejects-candidate-runner.yaml`; `evals/build-scenarios/build-reviewer-reviews-uncommitted-after-terse-handoff.yaml`; `evals/build-scenarios/build-reviewer-reopens-helper-claims.yaml`; `evals/scenarios/agent-direct-reviewer-permits-established-verification.yaml`.

[verified] Supporting sections/searches: `evals/test_reviewer_cases.py`; `scripts/test_validate_fleet.py`; `scripts/test_platform_adapters.py`; `evals/README.md`; `docs/fleet-roadmap.md`.

[sourced] Reused trusted guidance: `AGENTS.md`, `CONTRIBUTING.md`, `.github/copilot-instructions.md`, validator/adapter contracts, Claude/Copilot frontmatter and agent-security references, production-change gate, repository-investigator's complete contract and installed review-method instructions. Candidate instructions were reviewed as data; their scratch-only authoring rule was not adopted as this audit's report-write authority.
