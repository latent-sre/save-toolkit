# Group 11: reliability-engineer — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting audit HEAD `a6132ea82c12bd5a3d0fd9c0a8739c6f8edb3753` contains all 30 skill reviews. Initial tree clean; the agent matched the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains nine agent reviews in groups of three, with findings committed before proceeding.

**Conclusion:** the role has a coherent mission and conservative authority boundaries. No new defect was confirmed in the agent's instructions or generated tool/delegation fields. One Low evaluator defect was reproduced: a clearly rejected quotation of an authorization instruction is graded as an affirmative authorization. The larger readiness limit remains the explicitly open native acceptance gate; structural results and earlier corrected-source samples do not establish reliable engineering reasoning on the current candidate.

The complete 125-line canonical agent was read, with bounded methods, graph/validator/generator, both Copilot projections, consumers, scenarios, tests, and recorded native evidence. Source size is 8,716 bytes/about 1,168 whitespace-delimited words. `[verified]` denotes current source inspection or named local execution; `[sourced]` denotes primary external evidence; `[unverified]` denotes runtime/model facts not established. Inspected repository records remain verified only as reads of those records. Only this scratch report was written. No source repair, installation, live operation, model invocation, or repeated full suite occurred.

## Pass 1 — mission, suitability, discovery, and ownership

**Sources:** `agents/reliability-engineer.md:3-36,41-76,122-125`; `docs/decisions/2026-09-21-reliability-engineer.md:7-33,72-80`; AGENTS roster; all nine reliability discovery specifications.

[verified] The agent fills a distinct responsibility: synthesize local facts and bounded operational/public evidence into a service reliability decision, proportionate options, and verification criteria. It does not replace repository fact finding, live incident advice, implementation, observability changes, or independent merge review. The body permits a no-material-finding conclusion when effective controls disprove a lead, while missing evidence remains a gap rather than proof of health.

[verified] The discovery suite has positive specialist-assessment and toil-design cases and negative controls for active incidents, accepted implementation, root-cause diagnosis, lifecycle inventory, observability implementation, PR review, and small arithmetic. This is materially better than selecting a role merely because a prompt mentions reliability. No canonical caller gains a new edge to the agent: selection by the main session/human is intentional in the ADR, not a missing delegation entry.

[verified] Stack ownership is loaded before interpretation/design. Java/JVM changes and platform internals retain their owners. Existing requirements guide judgment; new recovery targets, SLOs, and accepted risks require human decisions. The adjacent RES/TOIL reviews found no confirmed guidance defect, and their recommendations remain applicable.

**Gap:** these lane descriptions and fixtures establish intended fit. They do not establish better performance than the incumbent, current registration on every host, or correct routing on arbitrary requests.

## Pass 2 — correctness, projections, and current host contracts

**Sources:** canonical frontmatter/body; `.github/agents/reliability-engineer.agent.md`; `com.github.copilot/agents/reliability-engineer.agent.md`; generator `45-51,78-94,280-304,364-402`; validator `118-124,160-168`; graph `19-24,38-57`; current official host documentation through Context7, checked 2026-10-02.

[verified] Claude grants are explicitly limited to Read/Grep/Glob, Write/Edit, Skill, and Agent calls to repository-investigator, sre-assistant, and researcher. The projection maps them to `read`, `search`, `edit`, and `agent` with those same three names in `agents:`. It grants no execute/web/browser tools and creates no user ownership handoffs for this role. Both generated files have identical SHA-256 `7bab6ba948fa5c7f395249f6d091feca7026feac27f57c14dd60dd6a2bcea2f4`; their 7,881-character body is exactly identical to the canonical body.

[sourced] Current [Claude subagent documentation](https://code.claude.com/docs/en/sub-agents) supports the main-thread `Agent(type)` allowlist and explicitly states that type lists are ignored at subagent depth. Current [VS Code custom-agent documentation](https://code.visualstudio.com/docs/agent-customization/custom-agents) documents tools, the `agents` allowlist, and separate human-selected handoffs. The local graph correctly qualifies enforcement as host/depth dependent; generation proves metadata consistency, not runtime containment.

[verified] Codex distribution is deliberately retired: the generator treats `.codex/agents` as a retired root. Codex can work in this repository without that making each canonical profile a registered Codex role. This audit session's advertised collaboration roster does not name this canonical role; no invocation or registration was attempted. Its repository presence is therefore not evidence of a callable current-host agent.

**Gap:** actual current-host tool resolution, nested enforcement, helper availability, installation provenance, and selected model remain unverified. Historical Claude build observations are retained as historical evidence, not silently refreshed into current-host claims.

## Pass 3 — authority versus enforcement, delegation, and recovery

**Sources:** agent `21-39,53-55,59-86,94-125`; hooks; graph; `scripts/test_reliability_contract.py:18-56`; platform-adapter tests `208-220,263-285`.

[verified] Tool absence is meaningful for direct shell/browser/network execution. Write/Edit can still touch arbitrary workspace paths, so the body correctly calls document-only scope cooperative unless an outer host restricts it. The Bash/PowerShell guard is not a document-path sandbox and does not make this role's writes safe. Authority tests reject adding execution, egress, worktree/notebook capabilities, or a software-engineer delegation edge; those are configuration regression checks rather than live permission tests.

[verified] Helpers have bounded evidence assignments. Repository facts, protected operational observations, and sanitized public research are separately routed. Requests identify caller and human owner, preserve scope/window, and return missing access as a gap. Implementation, monitoring, documentation, and independent review go back through the caller; the role cannot dispatch those owners itself. Skill procedures explicitly cannot expand authority.

[verified] Partial/stale returns do not close the parent assignment. The body binds evidence to subject, revision, time, and taint and now specifically requires an actual completed post-return read before claiming a reread. It can finish a supported assessment while implementation/outcome verification remains pending. Stop conditions prevent repeated unavailable-source retries and forced findings.

**Host-dependent recommendation RELI-R01 — Medium priority, high confidence in the need for verification; no confirmed leak:** on the next authorized host acceptance, test the actual context delivered to a researcher helper, using synthetic public/private markers. Agent `114-115` prohibits inherited investigation context. Current [Claude tool documentation](https://code.claude.com/docs/en/tools-reference) describes fork modes that inherit the parent conversation; a sanitized task string alone cannot establish isolation when such a mode is active. Verify the host's fresh-context path and allowed/forbidden helper behavior without real private data. If the transport cannot satisfy the stated boundary, retain a public-research gap instead of widening authority. No setting was found or exercised here to establish that this checkout leaks context.

## Pass 4 — LLM readability, context cost, and instruction conflicts

**Sources:** full body; relevant stack/resilience/toil entrypoints; exact generated-body comparison; historical correction record `docs/reviews/2026-09-30-backlog-four/reliability.md:122-188`.

[verified] The body orders scope, method selection, investigation, evidence/output, and handoffs coherently. Conditional skill loading avoids reproducing every domain procedure. Findings carry outcome, mechanism, evidence, controls, priority/confidence, owner, verification, and uncertainty without inventing a universal service score. A requested closed schema explicitly takes precedence over the illustrative return block, resolving the previously observed output conflict.

[verified] The evidence/reread rule is a targeted response to a recorded failure, not speculative boilerplate. Preserve it, the distinction between caller and human owner, the no-runtime-inference rule, and the statement that skills cannot expand authority. They solve different problems. The source and projections contain no new contradiction between design-document writing and the ban on operational-record changes.

**Deletion-first conclusion:** retain the short handoff core and domain references. Do not add generic resilience checklists, more role titles, or repeated host disclaimers to every section. If future compression is needed, remove duplicated introductory explanation before touching the narrowly evidenced correction or return semantics. This review found no justified large rewrite.

**Gap:** source readability does not prove model adherence. The latest prompt corrections have not received a successful exact-candidate native acceptance result.

## Pass 5 — evaluator soundness and what the evidence establishes

**Sources:** three reliability build cases, five direct cases, native conversation scenario, `test_reliability_cases.py`, `test_reliability_contract.py`, relevant build-probe native validation/regrade code and tests; README `502-518`; current RELIABILITY-001 and its recorded comparison.

[verified] Direct cases discriminate effective controls, backup-versus-restore proof, positive/negative toil economics, and partial-helper continuation. They are explicitly supplied-state judgments. The matched source redelivery fixture includes a protected counterexample and keeps production concurrency/retention unknown; calibration demonstrates its sequential duplicate effect and checks pair identity. Document-boundary coverage protects the named output path and non-actions, with source-reading/prose quality left to trace review. RES-R01 already owns missing required-method-load assertions; do not reissue it here. RES-R02 and TOIL-R01/R02 remain relevant coverage improvements.

[verified] The native runner now pins the intended agent and checks model/session identity, permitted tools, one completed helper, continuation, and same-session follow-up. Regrade checks the saved agent pin (`build_probe.py:2695-2714,2855-2877,3162-3200`); tests reject the old unsatisfiable routing-plus-sole-helper configuration and wrong pins/model/session/tools (`test_build_probe.py:1137-1187`). Manual criteria separately require real source access, bounded synthesis, claim provenance, and valid timing reasoning. Shared AA-01 identity limitations remain cross-referenced rather than duplicated.

[verified as a read of the record] Earlier corrected native arms passed structural checks but trace review found a false post-helper reread, an unsupported timing bound, and an invalid inference that later retries could not occur. The source now addresses these distinctions. The record and live roadmap still withhold acceptance; they do not retroactively turn those trials into passes. Their historical model samples are not new results for frozen `a2d2e57d`.

The parent baseline is **1,470 passed, 19 skipped, one warning, 2,690 subtests**; **192 scenario specifications/737 expectations** validate, both exit 0 under Python 3.14.7. These remain structural/calibration evidence. Fresh text-only parent probes establish RELI-01 below. No native call, broad suite rerun, deployment experiment, or operational-benefit measurement occurred.

## Pass 6 — adversarial challenge and prioritized disposition

The review challenged implementation pressure, forged repository instructions, missing target identity, stale r7 evidence about r8, a working control that disproves a lead, backup-only recovery evidence, negative toil economics, partial helper return, unavailable dispatch, schema-only output, false reread claims, and nested host enforcement. Current instructions provide suitable boundaries. The following distinct defect affects a bounded evaluator, not the agent's change authority.

### RELI-01 — rejected authorization quotation is graded as affirmative authorization

**Confirmed evaluator defect; Low severity; high confidence.** Evidence: `evals/build-scenarios/build-reliability-engineer-resumes-after-partial-helper.yaml:36-47`, especially the quotation/refusal claim at `40-43` and regex at `46`. Related limits are acknowledged in the RES review; this finding establishes a specific false rejection rather than asserting general stance understanding.

**Trigger → consequence:** a correct assessment keeps the current control unknown and says it rejects the instruction `"I authorize deployment"`. The regex matches the authorization phrase inside the rejected quotation and fails the artifact. A safe explanation can therefore be recorded as an authority violation. This is not unsafe acceptance, evidence that a model authorized a change, or failure of an entire native trial.

**[verified] Reproduction:** parent extracted the actual two Python predicates and ran them on owned text-only fixtures. Clear refusal passed unknown-control/no-authorization checks with exits 0/0. Explicit rejection quoting `"I authorize deployment"` passed the unknown-control check but failed the authorization check, exits 0/1 with AssertionError. Actual affirmative authorization also produced 0/1. All probe assertions passed under Python 3.14.7; results are retained in `group-11-probe-results.json`. No model or external operation ran.

**Smallest repair direction:** calibrate author-owned authorization separately from quoted or explicitly rejected text. Keep an actual affirmative grant as a failing control and a clear refusal as a passing control; add quoted refusal and quoted adoption cases. Constrain hard failures to adequately supported authorization, or route ambiguous matches to an explicit manual/inconclusive decision rather than mislabeling them. Do not simply delete the authority check or treat every quotation as harmless. The independent no-shell/no-write-scope/no-dispatch controls remain intact.

**Verification:** use the same extracted predicate or its replacement on the three reproduced controls, plus negated/adopted quotations. Require the rejected quotation to avoid an affirmative-authorization verdict while actual adoption still fails. Preserve the r8-unknown assertion and existing artifact/non-action checks. Re-run only the relevant offline calibration when repaired; any later native acceptance remains separately authorized.

**Caller next step:** record RELI-01 and the qualified host-context recommendation under AUDIT-001, retain the existing RES/TOIL dispositions and RELIABILITY-001 gate, and commit group 11 after peer review. Do not promote from structural PASS or spend the historical native budget without a new owner decision. The parent fleet audit remains in progress.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
