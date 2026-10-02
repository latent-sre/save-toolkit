# Group 12: repository-investigator — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit HEAD at dispatch was `74615d27236d966ea65d6dfede41c97551501908`. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains the six-pass skills-then-agents review, three assets per group, with findings committed before continuing.

**Conclusion:** no new confirmed defect was established. The role has a coherent, small local-evidence mandate, and its declared tool absence materially supports that mandate on a host that honors the definition. Preserve its separation from review verdicts, runtime verification, and external research. Recommended improvements concern fallback-host enforcement, explicit treatment of unavailable Git/dirty-state evidence, and a direct behavioral fixture. Existing caller tests challenge fabricated helper claims; they do not prove this investigator produced a correct packet.

`[verified]` identifies inspected frozen-source facts and the stated existing offline baseline; `[sourced]` identifies primary host documentation; `[unverified]` identifies behavior and host facts not established. The entire canonical agent and both generated projections were inspected, with bounded callers, validator/graph logic, tests, scenarios, and authoring contracts. Only this scratch report was written. No canonical/test changes, installs, live operations, native/paid runs, extra agents, commits, or repeated suite occurred.

## Pass 1 — mission, suitability, and caller boundaries

**Evidence:** complete `agents/repository-investigator.md`; `agents/reviewer.md:12-33,127-137`; `agents/reliability-engineer.md:57-70,107-125`; `agents/researcher.md:43-50,152-157`; current delegation expectation and projections.

[verified] The role answers bounded questions about definitions, callers, configuration, data flow, local differences, and private/uncommitted implementation. It excludes implementation, live incident investigation, external research, and change/merge judgment. The method starts at the execution surface, follows actual wiring, checks overrides and consumers, and returns the smallest cited answer that resolves the caller's decision. A keyword match alone is a lead.

[verified] Reviewer may assign at most two bounded local evidence questions within its review budget and must reopen load-bearing citations before adopting claims. Reviewer retains candidate/base identity, severity, and verdict. Reliability-engineer uses the same helper for local definitions/configuration/callers and retains synthesis. Researcher returns private-input questions to the caller for a separate local assignment; it cannot dispatch this role itself.

[verified] There are no outgoing model-call edges or generated human-selected handoffs for repository-investigator. External research is a sanitized question returned to the caller, not a tool call or transfer of private material.

**Result:** a distinct useful lane despite sharing file-reading tools with other agents. **Gap:** no direct investigation-quality comparison or actual native helper run was performed. The current review's tool roster offers a role with the same name; that does not prove it loads these exact canonical bytes or their intended authority on this host.

## Pass 2 — correctness of source identity and evidence claims

**Evidence:** `repository-investigator.md:23-36,40-48,66-77,90-96`; reviewer identity/refresh contract at `agents/reviewer.md:14-24`; reliability caller identity handling at `agents/reliability-engineer.md:59-63`; `scripts/test_validate_fleet.py:469-474`.

[verified] The body asks for repository root, caller-supplied commit identity, uncommitted scope, paths, and relevant time. The output permits an unknown revision. A unique short commit ID is preferred, not a claim that the reader independently resolved Git history. Direct byte observation is separated from what a local record reports and from unavailable runtime behavior. Reading a test file does not establish that the test passed.

[verified] Implementation/configuration takes precedence as evidence of current wiring over unsupported documentation claims. The method still requires cross-checking callers, consumers, tests, and overrides; it does not equate a definition with a reachable runtime path. Contradictions and missing evidence have explicit return slots, and conclusions retain source trust and claim-level taint.

The main precision opportunity is dirty-state identity: Read/Grep/Glob can inspect supplied files, but they do not themselves provide Git status or establish that every relevant untracked/modified path was included. The current rules allow gaps, so no false clean-tree claim is required. RI-R02 makes that limitation easier to apply consistently, especially when a caller supplies a commit but not a snapshot of current work.

**Result:** correct source-versus-runtime distinctions. **Gap:** no real target checkout's dirty-state completeness, immutable snapshot, or read-time consistency was established. Source-only answers cannot verify production state, dependency versions outside the checkout, or behavior of code that was never executed.

## Pass 3 — tool absence, trust, and actual enforcement

**Evidence:** canonical frontmatter `:11`; guardrails `:88-96`; `scripts/validate_fleet.py:129-133,161-169,186-233,266-300`; bounded delegation reference; generator tool mapping; `scripts/test_platform_adapters.py:208-228,275-280,352-358`; current Claude tool documentation retrieved through Context7 on 2026-10-02.

[verified] Canonical tools are exactly Read, Grep, and Glob. There is no shell, Write/Edit, worktree mutation, Skill, Agent, browser, web, or external MCP grant. Validation rejects missing explicit tool declarations, forbidden execution/write/external tools, unknown MCP grants, and delegation mismatches. The role is not relying on the SRE shell allowlist to make Bash safe; it has no Bash grant at all.

[verified] Both generated profiles contain only `read` and `search`, with no `agents:` or `handoffs:` entry. Their byte/configuration checks do not establish the enforcement behavior of an installed Copilot build. Read/search scope is also not a filesystem sandbox: authorization to inspect particular paths remains bounded by the caller and outer environment.

[sourced] Current [Claude Agent tool documentation](https://code.claude.com/docs/en/tools-reference), fetched through Context7, states that a normal non-fork subagent with a tools allowlist receives only listed tools, subject to host availability/filtering. This supports the declared absence boundary; it does not prove the runtime configuration used by this review or every alternative host. Do not generalize an allowlist's behavior across different launch modes or hosts without evidence.

[verified] Repository instructions, comments, files, and returned material are data rather than authority. Private excerpts, paths, identifiers, logs, and secrets must not enter external queries. Unlabeled trust defaults to untrusted, and returned conclusions retain taint. The caller must still assess them independently; trust labels do not make a claim true or mechanically redact its contents.

**Result:** strong normal-host posture with candid portability limits. The fallback paragraph requires egress/external-MCP isolation where per-agent tool denial is absent, but does not name local mutation/execution containment (RI-R01). **Gap:** no exact-host capability, filesystem, egress, instruction-loading, or injection-resistance probe was run.

## Pass 4 — LLM readability and return-packet usefulness

**Evidence:** entire 96-line agent; the two output blocks and method; generated projection comparison; caller reuse contracts.

[verified] The canonical file measures 5,414 bytes, 96 lines, and 748 whitespace-separated words. Each generated profile is 5,351 bytes, 89 lines, and 746 words. These are not token counts. The projections match each other and differ from canonical only in expected host frontmatter and namespace rewriting. Relevant canonical files have no diff from the frozen source.

[verified] The six-step method is short, and its observation/provenance/inference examples are useful. The return separates the invoking caller from the human owner and preserves parent work after the helper finishes. The second block supplies the factual question, source identity, citations, conflicts, unverifiable claims, sanitized research need, and confidence. This provides enough structure for a cold reader to reopen the evidence.

For a simple location-only answer, the “smallest cited answer” and caller-format clauses should keep the response short; no evidence here proves the model overproduces a full dossier. If later trimming is justified, combine overlapping gaps/unverified wording or express shared header meanings in a compact return rather than dropping source identity or provenance. Do not add a new packet schema, persistent log, or Git tool solely to make identity fields appear complete.

**Result:** proportionate body with useful evidence contracts. **Gap:** no measured native output establishes consistent concision, correct citations, or successful handling of a closed caller schema. Those are behavior questions, not defects inferred from the presence of templates.

## Pass 5 — tests and what they actually establish

**Evidence:** `scripts/test_validate_fleet.py:99-105,330-336,469-474,589-600,695-702,882-892`; adapter tests cited above; `scripts/test_reliability_contract.py:18-34`; complete `build-reviewer-reopens-helper-claims.yaml` and `agent-direct-reviewer-permits-established-verification.yaml`; bounded researcher private-input handoff and repository-wide scenario-name/content search.

[verified] Structural tests enforce explicit tools, the investigator's forbidden WebSearch/Bash directions, short-or-unknown revision output, graph edges, and the read/search-only projection. A line-wrapped no-delegation disclaimer is recognized rather than failing a brittle substring check. Reliability caller tests pin its permitted evidence helpers. These are useful regression checks for authority declarations and contract text.

[verified] The reviewer build fixture supplies a fabricated helper return claiming no consumer and recommending APPROVE, then requires reviewer inspection and the opposite source-supported conclusion. The supplied-state verification case likewise refuses to adopt a helper verdict. Neither invokes repository-investigator or measures its ability to find the unchanged caller, preserve identity, or reject the injected instruction. The adversarial helper text is test data, not an observed investigator failure.

[verified] No scenario directly targeting repository-investigator's discovery or file-tracing behavior was found in the frozen `evals/scenarios/` or `evals/build-scenarios/` corpus. This is a coverage gap (RI-R03), not evidence the role fails. Reference identity checks remain subject to shared [AA-01](group-01-agent-authoring.md); a same-suffix read must not become proof of exact target identity in future coverage.

The unchanged-source baseline remains 1,470 passed, 19 skipped, 2,690 subtests; 192 specifications/737 expectations validated. No focused executable reproduction was needed or run for this asset. **Gap:** behavioral accuracy, source-read success, privacy preservation in returned text, and native tool enforcement remain unverified.

## Pass 6 — counterexamples and ranked improvements

### RI-R01 — specify what enforces local read-only behavior in the fallback

**Recommendation; Medium priority; high confidence in the limited stated controls.** Location: `agents/repository-investigator.md:88-94`.

**Trigger and consequence:** on a host that cannot enforce per-agent tool denial, the paragraph requires network egress and external MCP to be disabled. Those controls address external disclosure, but they do not themselves prevent a still-available shell or write tool from changing local files or executing repository code. The separate no-write/no-execute instruction still applies cooperatively. No such action or deployed fallback was observed.

**Smallest improvement:** distinguish the egress condition from the local-effect condition. Require a host/session exposing only the permitted readers, or outer controls that also prevent the prohibited local mutations/execution; otherwise state the unsupported boundary and refuse that fallback. Preserve the current no-shell tool grant rather than solving this by adding a command filter to a newly privileged lane.

**Verification:** a bounded host capability check must cover forbidden local writes/execution as well as external access, against the exact selected build and launch mode. A supplied configuration with egress off but an effective Write/Bash grant must not be labeled mechanically read-only. No live canary or new enforcement implementation is authorized by this audit.

### RI-R02 — distinguish caller-supplied Git state from observed file bytes

**Recommendation; Low priority; high confidence in clarification value; native behavior unverified.** Locations: agent `:24-25,40,68,74-75`.

**Trigger and consequence:** a caller supplies a commit ID but omits dirty-state/path evidence, or files change during a multi-file investigation. The reader can cite current bytes while being unable to bind all of them to that commit or prove the supplied path list complete. Existing unknown/gap rules prevent a mandatory false assertion, but the target template does not explicitly separate those identities.

**Smallest improvement:** make caller-supplied commit/dirty evidence and directly read content explicit in the same target/gaps record. Missing Git status or snapshot identity stays unknown. For a version-sensitive conclusion, request the caller's bounded path/diff or snapshot evidence; continue independent factual work and qualify changed coverage. Do not require a full Git receipt for a trivial location question or grant shell access merely to fill the fields.

**Verification:** a dirty configuration override should be cited as included uncommitted evidence, not claimed present in the supplied commit; absent dirty evidence should produce an explicit gap; materially changed cited bytes should cause scoped refresh or qualification before reuse.

### RI-R03 — add one direct local-tracing fixture before claiming behavioral readiness

**Recommendation; Medium priority; high confidence in coverage absence.** Locations: agent `:40-48,66-77`; current validator tests and reviewer helper-return fixtures cited in pass 5.

Use a small local fixture whose documentation differs from effective configuration and whose unchanged caller selects an override. Include caller-supplied dirty/snapshot evidence and an untrusted comment requesting execution or external disclosure. Ask the investigator a bounded factual question, then assess the actual cited path/lines, conflict, identity qualification, source-versus-runtime distinction, sanitized research gap, and absence of forbidden calls or edits. Pair it with a simple location query to check proportionate effort.

Reuse the existing runner and caller evidence format; do not introduce a generalized grading framework. Calibrate a correct packet and wrong-default/wrong-revision/runtime-promotion counterexamples offline. Source reads and semantic interpretation require trace review; any native run remains separately scoped and unperformed. Preserve reviewer ownership of severity/verdict and its independent reopening of citations.

**Disposition:** no new confirmed RI defect; three recommendations and explicit host/model/evidence gaps. Preserve the minimal tools, terminal delegation posture, caller-owned judgment, bounded local investigation, private-data separation, claim-level citations/taint, and honest runtime uncertainty. `/root` should adjudicate and commit group 12 before continuing the remaining agent review.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
