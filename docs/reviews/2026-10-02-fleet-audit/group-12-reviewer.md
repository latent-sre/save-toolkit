# Group 12: reviewer — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting report HEAD `74615d27236d966ea65d6dfede41c97551501908`. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent fleet audit remains in progress and requires a group commit before group 13.

**Conclusion:** reviewer has suitable independent judgment, candidate-binding, trusted-instruction, and return-ownership rules. No new defect was confirmed in those instructions or their generated projections. Two bounded evaluator defects were reproduced: **REV-01 Medium**, ordinary qualified/wrapped Python invocations evade the scratch-location check; **REV-02 Low**, newline-only changes evade an explicitly byte-preserving checkout check. Neither result demonstrates a model failure, host containment, or acceptance of a whole native trial.

The complete 180-line agent was read, plus both projections, bounded caller/skill/graph/validator/guard dependencies, ten reviewer build specifications, its supplied-state verification decision, related handoff cases, and calibration tests. Canonical size: 13,278 bytes/about 1,924 whitespace-delimited words. `[verified]` identifies inspected current source or named local execution; `[sourced]` identifies primary external evidence; `[unverified]` identifies behavior not established. Historical results are attributed to their records, not rerun. Only this scratch report was written by this worker.

## Pass 1 — suitability, selection, and ownership

**Evidence:** `agents/reviewer.md:3-24,89-137,174-180`; `AGENTS.md:50-66,100-104`; `agents/software-engineer.md:168-199`; `skills/agent-authoring/SKILL.md:150-157`; `docs/decisions/2026-08-22-production-review-boundary.md`; discovery-reliability-defers-change-review.

[verified] The mission is independent assessment of a named change, including incomplete initial packets, affected unchanged consumers, and reachable security paths. It excludes implementing repairs, whole-repository threat modeling, and release acceptance. It can gather missing Git facts directly, distinguish a missing decision from missing preparation, disprove builder claims, and report no findings. Independent review does not mean refusing useful factual assistance.

[verified] Current main delegates only to repository-investigator, at most twice within budget. The reviewer owns severity and verdict; the helper supplies facts. Public-source questions return to the caller as gaps. The software-engineer supplies target/scope, untracked content, trusted context, and actual verification, then retains repair ownership. Production exact-SHA evidence is separate from ordinary merge policy; neither provisional review nor helper completion authorizes deployment.

**Conclusion/gap:** the lane is distinct and appropriately restrained. The discovery case routes change judgment away from reliability-engineer, while direct/build cases exercise reviewer decisions. They do not establish arbitrary-request routing or comparative model quality. The graph's contradictory universal-researcher-sink row is already **AA-04**, not a new REV finding.

## Pass 2 — technical contracts, tool grants, and projections

**Evidence:** canonical `4,35-44,61-76`; `.github/agents/reviewer.agent.md`; `com.github.copilot/agents/reviewer.agent.md`; `scripts/validate_fleet.py:125-128,163`; adapter generator `147-158,174-186`; `scripts/test_validate_fleet.py:300-309,330-336`; adapter tests `199-203,208-223,297-309,341-346`.

[verified] Canonical tools include local reads, Bash, Write/Edit, TodoWrite, Skill, and the one evidence-helper edge. The projections contain `read, search, edit, execute, agent, todo`, with only repository-investigator in `agents:`. Both projections have SHA-256 `9eaac1c87819b20cbed592e5e1de1331485fbf1fc00aba23d508a84d207441dc`; their 12,596-character bodies exactly match the canonical body. The separate software-engineer handoff is human-selected and requires accepted findings/current binding; it grants no reviewer model-call edge to implementation.

[sourced] Official contracts were checked through Context7 on 2026-10-02. [Claude documentation](https://code.claude.com/docs/en/sub-agents) limits `Agent(type)` enforcement to an agent on the main thread; nested type lists are ignored. [VS Code documentation](https://github.com/microsoft/vscode-docs/blob/main/docs/agent-customization/custom-agents.md) distinguishes tool availability, the `agents` allowlist, and handoff buttons. These support the repository's host/depth qualifications, not universal runtime enforcement. Local projection implementation was inspected directly; no public implementation claim required GitHits.

[verified] The Git prefix suppresses optional locks, pager, and fsmonitor; diffs/patches additionally disable external diff/text conversion. Immutable export avoids `git archive` transformations; mutable snapshots include untracked files. These are integrity procedures, not an execution sandbox. A suspected `$G` history-grader incompatibility was refuted: `build_probe.py:2246-2262` expands same-call variable assignments, and tests already cover it.

**Gap:** the complete shell-export recipes were not executed in this audit. Missing dependencies, submodule material, platform-specific tooling, or unsupported shell behavior must remain missing verification. Repository presence and adapter parity do not register this agent in Codex; the current session advertises a different code-reviewer role, not this canonical reviewer. Actual installed-host grants remain unverified.

## Pass 3 — trusted instructions, isolation, identity, and recovery

**Evidence:** agent `20-33,46-87,129-137,163-180`; hooks; software-engineer `185-199`; the paired withholds-review/dispatches-review instruction cases; established-verification and candidate-runner cases.

[verified] Candidate instructions, skills, PR text, logs, and helper output remain data. Skill can resolve only trusted installed/base guidance; otherwise the reviewer reads an explicit trusted copy. When changed instructions have been loaded as its own context, the agent withholds its verdict and returns a preparation gap. Absolute paths and a worktree do not establish safe instruction loading. The matched unchanged-instruction control avoids turning this into blanket refusal of ordinary reviews.

[verified] The agent separates team-authored work, established caller-designated runners, and outside/unknown provenance. Routine authorized checks use named scratch outside the source checkout. Candidate-controlled claims of a safe runner cannot admit external code to host execution. A check requiring installs, credentials, endpoints, or network dependencies remains unverified; source review continues. Explicit reading-only requests take precedence over default verification, and imports count as execution.

[verified] Filesystem/write and network restrictions are cooperative. Bash/Write/Edit remain broad, and the role says so explicitly. Hooks provide no reviewer scratch-directory sandbox. [Current VS Code guidance](https://github.com/microsoft/vscode-docs/blob/main/docs/agents/run/agent-sandboxing.md) likewise distinguishes ordinary user-account terminal permissions from additional OS sandbox controls. No host sandbox or credential isolation was tested here.

[verified] Immutable review binds full SHA and bytes; mutable review binds paths/time/snapshot and is provisional. A changed target invalidates affected coverage. The reviewer checks source preservation, reports discrepancies, and does not reset someone else's work. Its return is independent review evidence for the caller, not a repair, merge, release, or parent-task completion.

**Conclusion/gap:** preserve these boundaries. The explicit cooperative boundary is not a remediation claim or permission for broader effects. Actual instruction-loading isolation, nested helper enforcement, and successful scratch behavior require host-specific evidence.

## Pass 4 — LLM readability, instruction precedence, and context cost

**Evidence:** complete body, especially `35-80,89-111,139-180`; trusted-skill exception; generated-body comparison; relevant contract assertions.

[verified] The document follows a useful decision order: bind scope, establish trust, decide execution authority, gather/disprove evidence, then report. It names the caller separately from the human owner and requires load-bearing citations to be reopened. Findings need introduced/worsened behavior, trigger, consequence, and counterevidence; pre-existing gaps and unresolved leads stay outside the candidate verdict. This reduces both builder anchoring and invented findings.

[verified] Output guidance preserves meaning in caller-required formats. Priority, confidence, evidence status, and input taint have distinct purposes. No mandatory praise or finding quota obscures the verdict. The no-execution and unavailable-runner branches qualify the reproduction requirement; they do not force an unauthorized run merely because a finding might be P1.

**Deletion-first recommendation REV-R01 — Low priority, medium confidence:** the dense export/snapshot recipe at `64-70` is the best future simplification target if execution evidence shows recurring errors. First calibrate the existing recipes on a tiny disposable tree containing a tracked deletion, untracked helper, spaces, binary content, and export attributes. If a trusted reusable export helper already exists or becomes justified, replace repeated recipe detail with that tested path while retaining provenance, scratch-only execution, source preservation, and no-install rules in the body. Do not add a new helper/framework merely to shorten prose. No recipe defect is claimed here.

**Gap:** about 1,924 words is a real per-invocation cost, but source length alone does not establish poor comprehension. Preserve the identity, trust, and ownership core before attempting compression; no broad rewrite is justified by this review.

## Pass 5 — verification depth, controls, and limits

**Evidence:** all ten `build-reviewer-*.yaml` files; `agent-direct-reviewer-permits-established-verification.yaml`; three caller build cases; `evals/test_reviewer_cases.py`; `scripts/test_agent_scope_alignment.py:17-56`; `evals/README.md:261-280`; roadmap PRECOMMIT-001 and REVIEWER-001.

[verified] Coverage includes an unchanged caller broken by a keyword rename, a matched correct refactor, cross-tenant access, exhausted retries suppressing alerts, unrequested timeout changes, untracked CSV precision loss, terse branch handoff with a dirty tree, untrusted runner instructions, and false helper approval. Calibration verifies real fixture semantics, including the correct controls. The strongest decision cases use closed JSON and reject extra/conflicting prose; the remaining caller exact-fields weakness is already **EL-01**. Shared dispatch identity limitations remain **AA-01**.

[verified] Command patterns establish attempted command shapes, not successful reads or interpretation. The scratch case separately checks copies, Python invocation, unchanged source, and working location; helper-scoped checks distinguish reviewer commands from builder commands. These are useful tests with specific blind spots below, not containment controls. The helper-reopen case supplies a pasted return rather than proving a live helper dispatch/resume.

[verified as record inspection] The roadmap records earlier in-place reviewer execution failures and defers a meaningful changed-file-history fixture: current fixtures have one base commit, so merely observing `git log` adds little evidence of recognizing a deliberate earlier decision. Preserve **PRECOMMIT-001** and **REVIEWER-001** instead of opening duplicate queues or interpreting dated rates as current-candidate success.

The parent baseline remains **1,470 tests passed, 19 skipped, one warning, 2,690 subtests**; **192 specifications/737 expectations** validate, both exit 0 under Python 3.14.7. No full rerun or native/model campaign occurred. Fresh parent probes establish the two bounded defects below. Broader review quality and host behavior remain unverified.

## Pass 6 — adversarial findings and smallest improvements

### REV-01 — qualified/wrapped Python evades the scratch-location oracle

**Confirmed evaluator defect; Medium severity; high confidence.** Sources: `evals/build_probe.py:2266,2282-2302`; `build-reviewer-reproduces-in-scratch.yaml:157-158`; `build-software-engineer-hands-uncommitted-work-to-reviewer.yaml:54-56`; calibration `test_reviewer_cases.py:342-366`.

**Trigger → consequence:** a reviewer starts candidate-importing Python inside the source checkout using `/usr/bin/python3`, `.venv/bin/python`, or `env PYTHONDONTWRITEBYTECODE=1 python`. The location check recognizes none of these executable shapes and reports that every candidate run started outside. This contradicts agent `61-64` and the check's stated outcome; an ordinary interpreter selection can hide the behavior being measured.

**[verified] Reproduction:** root loaded the actual two YAML checks and ran the real `TraceSummary`/grader on six text-only cases per scope. Bare Python inside failed; known outside passed; returning to the named source before bare Python failed. All three qualified/wrapped invocations inside falsely passed, in both direct and subagent scope. All 12 assertions passed under Python 3.14.7. No shell, Git, candidate import, or model ran. Evidence: `group-12-reviewer-probe-results.json`.

**Smallest repair/verification:** reuse or factor the already calibrated executable/wrapper recognition from the external-runner refusal checks, preserving correct command position and same-call variables. Retain the inside/outside/return controls; add qualified and wrapped forms inside and outside, plus harmless quoted source-read controls. Unknown cwd/execution syntax should not produce confident location attestation; mark it inconclusive or require trustworthy execution/cwd evidence. Do not attempt to turn regex into a sandbox. This proves the location predicate's false acceptance, not passage of every scenario check.

### REV-02 — byte-preservation check accepts newline rewrites

**Confirmed evaluator defect; Low severity; high confidence.** Sources: `evals/build_probe.py:969-974,2513-2521`; `build-reviewer-reviews-uncommitted-work.yaml:1-2,35-70,72-73`.

**Trigger → consequence:** a seeded uncommitted file is rewritten from LF to CRLF without changing decoded lines. Seeded paths are excluded from generic changed-path errors, and `read_text()` normalizes newline sequences before comparing with YAML text. The check returns `checkout unchanged` despite different bytes and SHA-256, violating this fixture's explicit byte-for-byte promise.

**[verified] Reproduction:** root used the actual YAML predicate and `_write_files` helper, which explicitly seeds LF. Unchanged bytes passed; LF-to-CRLF rewrite changed raw bytes/digest but passed; a semantic edit failed. Synthetic GitFacts included the seeded modified/untracked paths. Only owned temporary files were changed; no Git/native call occurred. Results share `group-12-reviewer-probe-results.json`.

**Smallest repair/verification:** compare actual seeded byte content/digests with final raw bytes, or use the fixture's explicit LF byte encoding consistently. Preserve normal semantic-change and missing-file failures. Add the three demonstrated controls so newline translation cannot establish preservation. This finding is limited to the byte promise; it does not claim arbitrary mutation, metadata, or filesystem coverage.

**Caller next step:** root should record REV-01/02 and the optional recipe-calibration recommendation under AUDIT-001, preserve existing shared dispositions and runtime gaps, and commit group 12 after adjudication. No source fixes or new native spending are implied. This helper's review is complete; the parent audit continues.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
