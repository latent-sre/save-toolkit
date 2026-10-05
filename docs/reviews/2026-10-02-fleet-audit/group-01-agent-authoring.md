# Group 01 — agent-authoring

Review date: 2026-10-02. Frozen baseline: `a2d2e57d2de70125dbde002072853e73b788bd8d` in `F:\repos\sre-agents-audit-20261002`. Invoking caller: `/root`; human owner: the user. Assignment: six-pass, read-only review of `skills/agent-authoring`, including its direct consumers and verification. Canonical content was unchanged throughout this review. This report is findings evidence, not approval to implement or promote a candidate.

**Conclusion: suitable authoring method, partial verification.** [verified] The skill has useful routing, source-trust, bounded-evaluation, and human-promotion contracts. Four defects are supported: a reference-read identity weakness, a false containment assertion in a positive calibration example, and two smaller reference inconsistencies. Native activation, containment, and behavior were not tested. Recommendations below are separate from confirmed defects and repository policy.

## Scope and evidence inventory

[verified] Read all ten owned files in full: `SKILL.md` and `references/agent-security.md`, `artifact.md`, `claude-code-frontmatter.md`, `context.md`, `copilot-frontmatter.md`, `delegation-graph.md`, `roster.md`, `skill-portability.md`, and `tools.md`. There are no owned scripts, assets, or templates in this bundle. The entrypoint is 11,350 UTF-8/LF bytes over 157 lines; the whole bundle is 79,861 bytes over 1,082 lines. These are byte/line measurements, not tokenizer measurements or evidence of excess by themselves.

Bounded dependency inspection covered `agents/agent-engineer.md`; the roster and authority sections of `AGENTS.md`; `CONTRIBUTING.md`; `scripts/check_links.py`, `validate_fleet.py`, `generate_platform_adapters.py`, and `gate_a.py`; the corresponding `test_check_links.py`, `test_validate_fleet.py`, and `test_platform_adapters.py`; `evals/build_probe.py`, `test_build_probe.py`, `rubrics.yaml`, `rubrics-calibration.yaml`; the two direct authoring scenarios; and the consuming `agent-direct-agent-engineer-learning-loop.yaml`. The agent body was inspected only to resolve this skill's ownership and handoff dependencies.

## Six passes

| Pass | Evidence and result | Remaining gap |
|---|---|---|
| 1. Suitability and routing | [verified] `SKILL.md:4-19,85-130`, `roster.md:18-48`, and `agents/agent-engineer.md:24-59` distinguish a quick inline task, sustained artifact work, roster work, and executable graph design. The capability serves both a human author and the fleet authoring lane. Source-code graphs and runtime implementation are explicitly excluded. | [unverified] The direct discovery scenario covers a positive Loop Engineering request; it does not establish ordinary prompt/skill requests, neighboring-lane negatives, or current host discovery. |
| 2. Technical correctness | [verified] All nine references were checked against applicable local validators, generator paths, and tests. [sourced] Current Claude documentation supports the main-thread-only `Agent(...)` target restriction, ignored plugin-agent fields, skill invocation versus compaction budgets, model precedence, and MCP output behavior. The portable six fields agree with the current specification. AA-03 and AA-04 identify local inconsistencies. | Historical installed-host assertions retain their original version/date bounds. They were not re-probed. The VS Code source evidence is a pinned indexed snapshot, not proof of installed behavior. |
| 3. Workflow, authority, trust, recovery | [verified] `SKILL.md:23-50,150-157`, `artifact.md:14-68`, `agent-security.md:38-84`, `context.md:14-29`, `roster.md:71-102`, and `tools.md:28-41` distinguish imported text from executable code, preserve taint and evidence, retain the incumbent on inconclusive results, and require effect reconciliation before retry. Agent-engineer returns unavailable implementation/review dispatches to its caller (`agents/agent-engineer.md:105-111`). | [unverified] Prompt compliance with these rules, actual no-egress harness containment, and native callback/tool denial. AA-02 weakens the verification of one security claim. |
| 4. LLM readability and context cost | [verified] The task-to-reference table directly exposes every reference, reducing chained retrieval. Tables make routing, failure form, and loop decisions inspectable. Duplication remains between platform summaries and their owning references; the Claude `tools` row alone contains 1,250 characters (`claude-code-frontmatter.md:23`). | No measured LLM comparison supports a particular compression target. `agent-security.md` has 103 lines without the opening Contents list recommended by `claude-code-frontmatter.md:83`; this is a minor readability recommendation, not an enforced gate failure. |
| 5. Verification and negative oracles | [verified] Metadata, exact authority, generated parity, handoff graph, and boundary mutation tests inspect meaningful structural behavior. `test_build_probe.py:2749-2813` rejects missing/denied reference reads. AA-01 exposes a missing wrong-root negative; AA-02 concerns semantic quality of a calibration example. `discovery-agent-authoring-loop-engineering.yaml:8-17` has behavioral prose criteria but only a routing assertion in the runner (`build_probe.py:2688-2702`). | Routing success does not prove loop execution. The consuming learning-loop case is a constrained knowledge answer, not evidence of applying budget/termination rules during real authoring. Root owns the suite execution record; no duplicate suite was run here. |
| 6. Adversarial challenge and simplification | [verified] Counterexamples considered: imported instructions demanding execution; a same-suffix reference under a different root; retained Bash after WebFetch removal; an agent description within 1,024 characters but above 1,024 UTF-8 bytes; and reviewer research dispatch inferred from “universal sink.” The first is addressed in the written trust gate; the other four support the findings below. | No adversarial model trial was purchased or run. Simplification should remove contradictory copies first; adding more prose is not required to repair these cases. |

## Confirmed defects

### AA-01 — Required reference reads are not bound to the canonical file

**Medium; high confidence; [verified] offline reproduction by the invoking caller.** Location: `evals/build_probe.py:2663-2675,2695-2699`; affected direct consumer: `evals/scenarios/skill-direct-agent-authoring-security-review.yaml:24-32`.

An ordinary contract/build read is accepted when its path merely ends with the requested reference string. The runner passes the exact `plugin_root` only for follow-up conversations. Consequently a successful read of `.github/skills/agent-authoring/references/agent-security.md` satisfies the assertion for `skills/agent-authoring/references/agent-security.md`. It also passes the allowed-root check, because both paths lie inside the plugin checkout.

Root reproduced this with Python 3.14.7, exit 0: the generated projection exists; the unbound `reference_read` returns true; the same call bound to `ROOT` returns false; `read_boundary_problem` returns no problem; the ordinary `scenario_expectations` reference thunk returns true. This demonstrates wrong-file provenance, not an observed model failure. The generated mirror can be semantically equivalent at this revision; a divergent projection or workspace suffix makes the missing identity check material.

**Smallest correction:** bind all reference expectations to the measured canonical plugin root, resolving allowed relative paths against the known workspace when necessary. **Verification:** a focused regression must reject a successful same-suffix read under the generated/workspace root while accepting the exact canonical path and continuing to reject denied/missing reads. Re-run affected contract/build and regrade tests; a paid model trial is unnecessary for this deterministic defect.

### AA-02 — A positive security calibration example contains a false containment assertion

**Medium; high confidence; [verified] source contradiction, [sourced] platform behavior.** Location: `evals/rubrics-calibration.yaml:728-732`; compare `skills/agent-authoring/references/agent-security.md:77-80` and scenario `skill-direct-agent-authoring-security-review.yaml:8-15`.

The positive example retains Bash while claiming that removing WebFetch makes posting to the payload-selected callback impossible. Bash still provides an outbound path. This contradicts the reference's explicit warning and current Claude administration documentation. A human gate over promotion does not establish that the unrelated callback path cannot run.

The finding is the false fact in accepted calibration evidence. It is **not** a demonstrated judge failure: the current rubric also permits a human gate over the sensitive step (`evals/rubrics.yaml:230-235`), so its coarse acceptance rule can label the response positive for that separate reason. The corpus therefore mixes a valid remediation direction with an invalid guarantee.

**Smallest correction:** rewrite the example to describe actual egress enforcement, removal of all outbound capability, or a credential-free proposal-only role without claiming WebFetch removal blocks Bash. **Verification:** independently review every positive example against the complete supplied tool set; if this semantic distinction becomes a required grading criterion, add a negative example that merely removes WebFetch while retaining unrestricted Bash. Recalibration is needed before relying on a changed rubric/corpus for behavioral acceptance; it was not run in this audit.

### AA-03 — General artifact guidance states skill-only validation rules as universal

**Low; high confidence; [verified].** Location: `skills/agent-authoring/references/artifact.md:84-85`.

The artifact reference covers prompts, agent bodies, skill bodies, descriptions, and graders (`SKILL.md:122`), but states without a skill qualifier that names match their directory, descriptions allow 1,024 characters, and canonical validation requires two to four quoted triggers. In fact, `check_links.py:293-324` applies these rules to skills; agents match their filename and have a 1,024 UTF-8-byte limit (`validate_fleet.py:200-204,315-317`). Agents do not require the quoted trigger list.

**Trigger → consequence:** an author follows this general reference while writing an agent, admits a multibyte description within the stated character limit, then fails the actual gate; it also encourages unnecessary skill metadata conventions on agent definitions. **Smallest correction:** prefix the statement “For skills” and refer agent authors to the already-linked frontmatter reference. **Verification:** compare the corrected scope against both existing validators and their boundary tests; no new model campaign or prose-matching test is needed.

### AA-04 — Delegation guidance still calls researcher universally reachable

**Low; high confidence; [verified].** Location: `skills/agent-authoring/references/delegation-graph.md:35`.

The “Universal sink” row says every orchestrating lane reaches researcher. The same table correctly states that reviewer has no public-research dispatch (`:32`), and `validate_fleet.py:161-170` grants reviewer only repository-investigator.

**Trigger → consequence:** a reader using the summary as a graph rule attempts or designs a reviewer→researcher edge that the canonical graph rejects on a main-thread Claude agent; depth-specific limitations can also make the contradictory prose matter. **Smallest correction:** delete the universal row. The complete graph and reviewer exception already exist. **Verification:** inspect the surviving text against the exact graph; existing graph and adapter tests cover the controlled edges.

## Recommendations and policy choices

**AA-R1 — Reduce duplicate context before adding guidance.** [verified] `SKILL.md:132-141` repeats facts owned by the Claude/Copilot references; `artifact.md:27,48-63` repeats promotion distinctions already in the method. Consolidate only repeated facts, retain the entrypoint's trust gate and decision table, and split the 1,250-character tools cell into scoped rows. Measure the entrypoint and reference deltas separately. `docs/fleet-roadmap.md:157-181` already queues agent-authoring under SKILL-001; this report does not create a competing backlog or authorize compression. The 11,350-byte body is not over the portable 500-line recommendation, and bytes alone do not establish worse task behavior.

**AA-R2 — Make the evidence catalog say what is actually checked.** [verified] Label the Loop Engineering discovery scenario's extra prose criteria as ungraded, or use an explicitly authorized behavior check when such evidence is needed. The consuming `agent-direct-agent-engineer-learning-loop.yaml:23,47` still expects `non_author_exact_candidate_revision`; current `artifact.md:27,57-63` requires human acceptance and makes independent review conditional. The choice schema conflates author identity with revision identity and omits human identity. Retain this as an adjacent verification gap for the later agent-engineer review; assess its body there. Prefer a small closed-object case that separates human authority and exact revision before considering an expensive behavioral campaign.

**AA-R3 — Keep host and field scope precise.** [sourced] `skill-portability.md:42` mentions VS Code `disallowedTools` in a skill-field map, while the inspected upstream source places it in `claudeAgentAttributes`; its `skillAttributes` table lacks it. Narrow the wording to agent-file support rather than implying a skill alternative. The existing “runtime effect unconfirmed” label should remain. The same reference's claim that host differences appear in every adapter (`:68-71`) should follow the generator's actual policy: no generated preface; relevant limitations live in affected canonical lane bodies (`generate_platform_adapters.py:382-385`). These are clarity improvements, not evidence that a restricted skill is currently shipped unsafely.

Repository choices worth retaining as **policy**, not universal facts: explicit tool grants; no model pins by default; two-to-four quoted skill triggers; main-session orchestration; source-only canonical edits; exact-revision human promotion; conditional independent review; and no automatic live-eval campaign for wording changes.

## External evidence and verification limits

All external retrieval below occurred on 2026-10-02 after local inspection. Context7 supplied official contract evidence; GitHits supplied upstream source evidence. Neither establishes the installed runtime.

- [Claude subagents](https://code.claude.com/docs/en/sub-agents): scoped delegation, ignored plugin fields, forks, and model precedence support the principal local cautions.
- [Claude skill lifecycle and permissions](https://code.claude.com/docs/en/slash-commands): descriptions, invocation versus compaction, and per-turn tool effects match the distinctions in the references.
- [Claude administration](https://code.claude.com/docs/en/admin-setup): restricting WebFetch does not prevent Bash networking; supports AA-02. Context7 and a direct official-page read agree.
- [Claude MCP limits](https://code.claude.com/docs/en/mcp): the default 25,000-token limit and text-result persistence support `tools.md:12-17`.
- [Agent Skills specification](https://agentskills.io/specification): six portable fields, naming, metadata limits, and progressive disclosure support the portability baseline.
- [VS Code attribute definitions at `afedf379`](https://github.com/microsoft/vscode/blob/afedf379/src/vs/workbench/contrib/chat/common/promptSyntax/languageProviders/promptFileAttributes.ts): GitHits read `skillAttributes` at lines 182-223 and `claudeAgentAttributes` at 343-363. A separate latest-head search remained indexing; conclusions use the pinned snapshot only.

[verified] Local inspection commands and the coordinator's synthetic reproduction ran without changing canonical files. The coordinator owns the fresh offline suite and structural gate results; incorporate those exact results in the group report. [unverified] No native Claude/Copilot discovery, behavioral trials, judge recalibration, credential access, cloud change, dependency installation, or publication occurred in this bounded review. Full six-pass static completion establishes review coverage, not universal runtime readiness.

## Central verification

[verified] The caller completed the full offline baseline (1,470 tests and 2,690 subtests passed; 19 skipped) and validated 192 scenario specifications. See [shared verification and reproduced counterexamples](verification.md) for commands, environment, exact outcomes and limits. These results do not close the runtime gaps above.
