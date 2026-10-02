# Group 13: sre-assistant — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting report HEAD `a0a4fa12648257a62e8fcf34e0ade355c77b60af`. Invoking caller/recipient: `/root`; human owner: the user. Assignment complete. Root owns final group integration, rollup, checks, and commit; this helper's completion does not complete those steps.

**Conclusion:** the agent provides a suitable bounded investigation role, with clear human incident ownership and honest limits on credentials, browsers, and host enforcement. One **Medium confirmed guard defect, SRE-01**, allows two nominal Git reads to create or overwrite a file. No new agent-body authority defect was confirmed. Existing access/behavior acceptance gates stay open; source guidance and green offline checks are not complete operational readiness.

Scope included the complete 315-line agent, planning README, complete 1,322-line guard and its launchers/preflight, hooks, both projections and generator rules, bounded method/caller references, four SRE build cases, six supplied-state decisions, the ownership-handoff case, two discovery cases, and the native incident exchange's SRE contract. Relevant guard/adapter/evaluator tests and recorded acceptance limits were inspected. `[verified]` means current source inspection or identified local execution; `[sourced]` means primary external evidence; `[unverified]` means behavior not established. This worker wrote only this report; root performed the separately described disposable reproduction. No live platform, credential, browser, install, source repair, or model campaign was used.

## Pass 1 — suitability, bounded investigation, and incident ownership

**Evidence:** `agents/sre-assistant.md:8-67,91-143,225-239,249-315`; `agents/README.txt`; `skills/incident-investigation/SKILL.md:249-277` and `references/helper-exchange.md:8-38`; root-cause entrypoint and symptom/systemic references.

[verified] The role distinguishes exact extraction from investigation. A lookup returns requested numbers/statements and their limits without an invented diagnosis; a causal assignment can select discriminating reads and follow connected evidence within the named target/window. An unrelated tenant, environment, service, or materially wider window needs a scope decision. The role stops at completion, a meaningful checkpoint, or lack of a permitted useful read, while one blocked source does not erase independent evidence.

[verified] The caller retains the overall investigation and resumes from the packet. Supplied severity/scale, impact and ownership are preserved; the helper neither assigns command nor closes an incident. Findings return through the existing bridge/TLC. The advisor owns human coaching and coordination advice, while ITO/the human incident process retains paging and approval. Mitigation can be recommended before cause is established, with release-owner execution and recovery evidence. Suspected compromise routes preservation and containment decisions to the human security owner through the caller.

[verified] Neighbor lanes remain distinct: implementation, observability writes, durable documents, and broad resilience/toil design are caller-relayed recommendations. Researcher is the only direct delegate. Human-selected ownership transitions are separately described, with no automatic parent-resume claim.

**Conclusion/gap:** preserve this scope and the useful partial-return fallback. Supplied-state and routing fixtures exercise intended distinctions, not automatic dispatch quality or diagnostic usefulness on a real incident. The prior **II-01** timing/localization finding remains relevant where symptom guidance is loaded; it is not reissued here.

## Pass 2 — tools, methods, projections, and current contracts

**Evidence:** canonical `4,46-67,145-206`; `scripts/generate_platform_adapters.py:73-116,374-414`; both generated SRE profiles; adapter tests `100-149`; Grafana command-access/visual-verification and planning README.

[verified] Claude grants exact local reads, Bash/PowerShell, Skill, researcher delegation, and nine named Playwright tools. There is no general interpreter/analysis grant; the installed Grafana helper is a narrowly validated exception. Methods load conditionally before their source procedure, and skills cannot grant another lane's write authority. Apps Manager is the first CF path; selected CLI reads require a protected, target-bound output path. Helix/BigQuery and an isolated analysis runner remain unavailable, rather than assumed integrations.

[verified] Standard Copilot removes terminal execution and adds only the mapped native/MCP viewing tools. Its command preview is a separate export with agent-scoped hooks, not an enabled standard capability. Both projection hashes are `f194f3d8c6cbdfa4d095160d9d14befbc0aad2bed2066fcc3bd71ef9f9e95471`; their bodies exactly match canonical text at 21,136 characters. Canonical size is 22,278 bytes/about 3,001 words, below the local 25,000-character SRE projection ceiling. Neither parity nor a repository file establishes current Codex registration or callable tools.

[sourced] Current official documentation was checked through Context7 on 2026-10-02. [Claude plugin components](https://code.claude.com/docs/en/plugins/components) still distinguish ignored plugin-agent hooks/permissionMode/MCP-server fields from plugin-level configuration. [Hook denial output](https://code.claude.com/docs/en/hooks-guide) uses permissionDecision JSON with exit 0; the repository launchers translate the internal 42/43/44 protocol accordingly. These are documented contracts, not a fresh host invocation.

[sourced] Current [Playwright capture schemas](https://github.com/microsoft/playwright-mcp/blob/main/_autodocs/api-reference/tools-core-execution.md) confirm that screenshots save files, while [snapshot schemas](https://github.com/microsoft/playwright-mcp/blob/main/_autodocs/api-reference/tools-core-introspection.md) permit inline output or a workspace-relative filename. The role therefore correctly describes authority rather than falsely claiming it has no writing capability.

**Gap:** current host registration, MCP schemas, viewing permissions, protected sessions and returned image delivery were not exercised. Exact installed versions and configuration must be bound before applying documentation to runtime claims.

## Pass 3 — enforced versus cooperative boundaries and failure recovery

**Evidence:** complete `scripts/readonly-guard.py`; `hooks/hooks.json`; Bash/PowerShell/Copilot launchers and SessionStart preflight; agent `147-223,241-266`; `docs/vscode-plugin-acceptance.md:39-113,115-172`.

[verified] The command allowlist selects sre-assistant by agent identity. Known renamed namespace/key shapes fail closed; the main loop is deliberately outside that scope. The separate fleet credential scanner is a named-path tripwire, not universal secret isolation. **GP-01** already owns the misleading broader scope in GCP guidance. Payload parsing, isolated interpreter startup, distinctive exits, and nonempty denial output address documented silent-failure modes. Those exit values are a protocol, not authentication against a hostile executable or proof that a host blocks hook launch failures/timeouts.

[verified] Bash and PowerShell have different parsing paths but reuse Git/CF/GCP checks. Exact selected CF grammar rejects target changes, extra targets, inventory expansion and unbounded log streaming. PowerShell rejects script expressions/interpolation and requires approved scalar projection before JSON process output. The historical `uniq INPUT OUTPUT` overwrite is now denied, including quoted-operator/Unicode variants; it is not a current finding. SRE-01 below is a distinct unguarded flag path.

[verified] The Grafana helper gate binds fixed installed paths, compares projected/canonical helper bytes, validates arguments using the reviewed parser, and refuses arbitrary scripts, URLs, methods, or unprotected expression transport. Existing **GRA** findings/limits cover the helper and query oracles; they are not duplicated here.

[verified] No hook guards Read/Grep/browser actions. Browser navigation, typing and captures require a trusted origin/org, effective read-only session and protected results; file credential reads remain prohibited by instruction. Authentication identity/secrets must be removed before model-visible stdout/stderr/errors/images, and final-answer redaction is explicitly insufficient. A failed helper yields a safe error, repair proposal and independent continuation, not edits, credential discovery, or a substitute access path.

**Conclusion/gap:** OS identity, PATH/installation integrity, effective service permissions and host controls remain essential. No current host sandbox, pre-model masking, or browser mutation boundary was proven. Existing **SRE-CF-001** and **RELEASE-001** correctly retain these acceptance tasks.

## Pass 4 — evidence identity, LLM readability, and simplification

**Evidence:** agent `69-89,103-143,208-223,276-315`; helper-exchange; visual-verification `74-94`; generated-body comparison.

[verified] Evidence rules bind target, source, method, observation time, actual covered interval and pagination/retention/sampling limits. Aggregates do not establish onset, crash counts do not establish current instance state, and reading an old export verifies its contents rather than today's service. Causal conclusions require mechanisms and contradictory evidence, while user recovery is distinct from knowing the cause. Evidence labels and taint survive handoffs; human owner is separate from return recipient, including omitted caller identities.

[verified] The body scales exact lookup versus causal output and separates complete collection from a complete diagnosis. Interim findings use only a channel that actually delivers to the caller; a final-only host requires a useful partial return and caller-directed continuation. This avoids promises of background work or fabricated progress delivery.

**Existing wording recommendation GRA-R2 remains applicable, Low priority:** agent `158-162` permits time-range viewing but says never “apply,” while visual-verification explicitly allows unsaved time-picker Apply. Narrow the wording to saved/mutating actions, preserving opposite controls for harmless view selection and an actual mutation dialog. This is not a generic browser-click grant or a second SRE finding.

**Deletion-first recommendation SRE-R1 — Low priority, high confidence:** shorten the guard's long historical narrative before adding more policy text. Its introductory comments still use generic “reviewer” terminology and describe sentinel codes as authentication (`readonly-guard.py:36-59,107-115`), whereas current role scoping and the roadmap explicitly distinguish these concepts. Keep the compact current scope, trust assumptions, parser invariants and links to regression tests; move obsolete rationale to existing history only if it still supports a live decision. This improves maintenance clarity without changing command authority or weakening tested failures. Retain the agent's existing conditional skill references rather than copying procedures back into its 3,001-word body.

**Gap:** no prompt-compression or comprehension experiment ran. Do not use the size reduction alone as evidence of improved adherence.

## Pass 5 — decisive verification and remaining oracle limits

**Evidence:** guard tests, hook-wiring tests `70-219,232-351`, GCP/helper guards, adapter tests; four SRE build cases; six supplied-record cases and calibration `evals/test_graders.py:999-1098`; native incident helper/return scenario; live roadmap `90-141`.

[verified] Meaningful negative coverage includes denied writes/code execution, protocol stubs and malformed payloads, renamed identity, quoted/escaped shell structure, exact CF arguments, secret-printing paths, workspace helper impostors, expression transport, and conflicting field claims. Positive controls retain ordinary reads and known protected helper forms. Hook tests distinguish declaration from actual launcher execution; platform-dependent checks are not interchangeable with CI or installed-host evidence.

[verified] Supplied-state SRE cases test wrong-window evidence, unknown capture/onset/current state, separate human/caller identities, exact extraction, absent credentials, and useful partial results. Closed JSON rejects conflicting extra fields. The build cases add a protected CF shim, unavailable protection under suspected compromise, injected restart in a partial research return, and a matched sequential-redelivery comparison. Supplied research is not a live helper exchange. The native incident case explicitly needs manual examination of child reads, claim quality, parent synthesis and corrected recovery; its hinted dispatch is not unhinted host acceptance.

**Verification recommendation SRE-R2 — Medium priority, high confidence:** when next calibrating active guarded triage, require successful protected-read receipts bound to the expected operation/target/window. `build-sre-assistant-active-incident-guarded-triage.yaml:159-176` positively checks attempted `cf` syntax and negatively checks shim verbs; those alone do not establish a successful observation. Retain the rubric/manual evaluation of mechanism and mitigation. Also calibrate permitted direct-human prose against the agent's flexible output contract rather than treating required headings as semantic quality. These are bounded coverage improvements, not evidence that a whole native trial falsely passed.

Shared **AA-01**, **EL-01**, **II-01**, **GRA** and **REV** oracle limitations remain cross-references. The parent baseline is **1,470 passed, 19 skipped, one warning, 2,690 subtests**, with **192 specifications/737 expectations** valid, both exit 0 under Python 3.14.7. No suite repetition occurred. Recorded earlier incident campaigns failed semantic acceptance; later source changes do not retrospectively repair those results. **INCIDENT-QUALITY-001** stays open.

## Pass 6 — adversarial finding and smallest repair

### SRE-01 — nested Git read verbs bypass the output-file restriction

**Confirmed guard defect; Medium severity; high confidence.** Primary local evidence: `scripts/readonly-guard.py:436-440,460-470,728-754`; PowerShell reuses that decision at `384-393`; tests currently cover direct diff/log/show output flags at `scripts/test_readonly_guard.py:305-318`.

**Trigger → consequence:** an SRE command uses `git stash show -p --output=<path>` or `git reflog show -p --output=<path>`. Direct Git read subcommands reject write/output flags, but the nested-read branch checks only its first positional verb. Both commands receive allow even though Git creates the requested file or truncates an existing one. A nominal observation can therefore overwrite a user-writable evidence, source or configuration file without a shell redirect. This violates the command-level read-only contract; it is separate from documented on-disk Git driver/configuration residual risks.

**[verified] Controlled reproduction:** root ran the real guard with synthetic sre-assistant Bash and PowerShell envelopes. Plain stash/reflog reads returned 42; direct `git diff --output=...` returned 43 with denial JSON; both nested output forms incorrectly returned 42 with empty output. With **Git 2.53.0.windows.2**, the two commands then ran in a new owned disposable repository containing synthetic commits/stash, isolated Git configuration and disabled hooks/signing. They exited 0 and created 186/492-byte patches. Repeating after placing an owned sentinel in each target replaced both sentinels, again exit 0. Temporary targets were contained and removed. Evidence: `group-13-git-guard-probe-results.json`. No source checkout, credential, external endpoint or native agent was used.

**[sourced] Contract/implementation, checked 2026-10-02:** Context7's official [stash documentation](https://git-scm.com/docs/git-stash) exposes diff options; [reflog documentation](https://git-scm.com/docs/git-reflog) passes log options. GitHits resolved upstream `git/git@a0189536`: [stash.c:1056-1088](https://github.com/git/git/blob/a0189536/builtin/stash.c#L1056) forwards unknown options into revision parsing, [reflog.c:150-154](https://github.com/git/git/blob/a0189536/builtin/reflog.c#L150) delegates to log handling, and [diff.c:5800-5814](https://github.com/git/git/blob/a0189536/diff.c#L5800) opens the output path with `xfopen(path, "w")`. Documentation, upstream implementation and local installed-binary reproduction are separate evidence layers.

**Smallest repair:** apply the existing output/write-flag rejection to allowed nested read forms before accepting the verb. Alternatively remove unnecessary nested forms after deciding their actual operational need; no agent/skill/command call site found here requires stash/reflog reads. Avoid a larger shell-parser rewrite or a broader grant. Keep intentional main-loop/other-lane scoping unchanged.

**Verification:** add Bash/PowerShell guard negatives for both reproduced attached-output forms and other supported output spellings; preserve plain-read allows and direct-output denies. In owned scratch, retain creation and sentinel-overwrite controls against the selected Git version. Check the actual hook transport after repair within existing host acceptance. The current reproduction proves parser admission and Git's effect, not a live host event or complete containment.

**Caller next step:** root records SRE-01 and the qualified recommendations, retains all existing access/semantic gates and shared findings, then integrates and commits group 13. This completes the assigned six-pass review; final fleet reconciliation and completion remain with root.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
