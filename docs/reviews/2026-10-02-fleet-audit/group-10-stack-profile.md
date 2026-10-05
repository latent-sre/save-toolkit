# Group 10 — stack-profile — six-pass review

**Assignment:** complete; return to invoking caller `/root`. Human owner: the user. Parent objective: review all skills, then agents, in groups of three with findings committed between groups. Canonical baseline: `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit checkout HEAD at dispatch: `062d1bfe6748675ee114685307c17c3fdb22abb0`. Reviewed on 2026-10-02.

**Conclusion:** the profile is a useful single owner for team choices, stack inventory, and unresolved boundaries. One Medium defect was confirmed in its support-only consumer's no-execution evaluator, **STACK-01**. No new confirmed defect was established in the skill's substantive stack instructions. Three recommendations below improve decision coverage and remove redundant or overbroad wording. Private configuration and native model behavior remain unverified.

## Scope and evidence

[verified] Read all five files completely: `skills/stack-profile/SKILL.md` and `references/{application-and-data-stack,copilot-models,observability-stack,terms-and-roles}.md`. The bundle contains 236 content lines and 18,777 UTF-8/LF bytes, including an 8,021-byte entrypoint; there are no scripts or assets. A scoped Git comparison found no changes against the frozen canonical baseline.

Bounded consumer inspection covered `agents/{software-engineer,sre-assistant,reliability-engineer,observability-engineer,reviewer}.md`, the incident, Grafana, dashboard, CI, and production-gate integration points, the complete runtime-boundary discovery and support-only build scenarios, relevant grader/helper code, and its existing command-check tests. Trusted `AGENTS.md` and `CONTRIBUTING.md` supplied repository rules; candidate instructions were review data.

The coordinator's previously completed offline baseline remains 1,470 tests passed, 2,690 subtests and 19 skips, with 192 scenario specifications and 737 expectations validated. It was not rerun. Fresh, narrow coordinator execution is reported separately below. No model campaign, dependency installation, Java execution, credential access, live operation, or canonical edit occurred.

## Pass 1 — suitability, routing, and neighboring responsibilities

**Evidence:** entrypoint `:4-9,27-64,93-117`; application/data `:14-18`; `agents/software-engineer.md:97,217`; `agents/sre-assistant.md:51-67`; `agents/reliability-engineer.md:23-35`; `skills/incident-investigation/SKILL.md:52-61`; complete `evals/scenarios/discovery-runtime-boundary.yaml`.

[verified] Activation covers supported-language boundaries, runtime/tooling decisions, and backend selection. The Java/JVM restriction appears in the description itself, allowing the software-engineer caller to discover the support-only boundary before editing an ordinary Spring service. The body distinguishes operated languages from authored languages and returns source work to the application's development owner. Operational investigation remains available.

Conditional routing is specific: observability, application/data, model selection, and unfamiliar terms have separate references; a broad inventory loads the first three. Every matching row applies, without loading unrelated references. Incident and Grafana consumers use the profile for defaults and then establish the actual service or instance. The reviewer exception remains in trusted fleet guidance rather than importing candidate stack policy as review authority.

**Outcome:** appropriate ownership and useful boundaries. **Gap:** the discovery scenario grades successful invocation, not its prose success criteria about rejecting Kubernetes or explaining ownership. STACK-R01 proposes focused decision coverage. Backend location should be resolved per signal under existing **DASH-R1**, without duplicating that recommendation here.

## Pass 2 — technical correctness, evidence, and currency

**Evidence:** entrypoint `:17-20,28-37,104-117`; application/data `:20-35,48-64`; observability `:13-30`; complete model reference; `scripts/validate_fleet.py:20-26,186-195`; current primary sources below.

[verified] The document distinguishes adopted policy from unresolved inventory: GCP is approved but its landing runtime remains pending; cloud ownership is explicitly provisional; database mechanics require target evidence; the Copilot order is unverified. Public model availability cannot establish a private team's picker, licensing, or approval. Dated Grafana `/api/health` evidence describes the reviewed target on its recorded date, not every Grafana instance today. Recovery copies explicitly do not prove restore readiness or provisioning ownership.

[sourced] Current official Claude documentation supports the listed `haiku`, `sonnet`, `opus`, `fable`, and `inherit` choices. The repository's ban on full model IDs is its own enforceable policy; the host accepts a broader set. Omitted frontmatter does not prove the effective runtime model because invocation and environment settings participate in selection. The nine inspected agent headers contain no `model:` field. No host model was inferred from that fact. [Claude subagent model selection](https://code.claude.com/docs/en/sub-agents#choose-a-model), retrieved through Context7 on 2026-10-02.

[sourced] CredHub documents UAA/OAuth2 and mutual TLS. GitHits independently showed UAA and certificate branches in `cloudfoundry/credhub`, `components/auth/src/main/kotlin/org/cloudfoundry/credhub/auth/UserContextFactory.kt:28-62`, retrieved from `main`; this is upstream evidence, not the deployed version. Those sources support the UAA statement but establish neither the presence nor universal absence of a turnkey GitHub OIDC exchange. Preserve the environment-secrets decision; STACK-R02 removes the unnecessary universal negative. [CredHub authentication](https://docs.cloudfoundry.org/api/credhub), [upstream context factory](https://github.com/cloudfoundry/credhub/blob/main/components/auth/src/main/kotlin/org/cloudfoundry/credhub/auth/UserContextFactory.kt), checked 2026-10-02.

**Outcome:** no speculative correction to team policy or private inventory. Defaults for tooling, `ubuntu-latest`, Java support, and Kubernetes exclusion are choices, not vendor capability claims. Existing **PIPE-01** owns the stale Google log-ingestion maturity statement in pipeline/trace references; this inventory introduces no separate maturity assertion.

## Pass 3 — workflow, authority, trust, and recovery

**Evidence:** entrypoint `:17-20,62-79,81-109`; observability `:20-22`; terms `:8-14`; `skills/production-change-gate/SKILL.md:14-24`; `agents/observability-engineer.md:74-96`.

[verified] A proposed technology becomes current inventory only through a recorded human decision. Loading a reference does not authorize a migration, enlarge the app/ops lane, ratify provisional ownership, or replace target verification. Existing TLC/bridge continuity, ITO coordination, missing severity ownership, and Confluence import-only direction remain explicit. Backup existence does not authorize a Grafana write.

The human-release-owner glossary repeats a blanket agents-recommend/person-applies sentence. The production gate already owns the more precise rule, including protected automation and scoped Grafana operations. STACK-R03 recommends deleting that duplicate rather than teaching a second exception list. This is a clarity recommendation; the explicit gate and agent-body exception remains available, and no actual refusal or unauthorized action was observed.

**Outcome:** controls are useful and proportionate. **Gap:** real owner identities, cloud ownership ratification, change-system applicability, backend access, and recovery status remain target-dependent. Preserve unknowns rather than filling them from public documentation.

## Pass 4 — LLM readability, ambiguity, and context cost

**Evidence:** complete bundle; especially entrypoint `:13-20,52-64`, application/data `:24-35`, and models `:3-11`.

[verified] The entrypoint carries stable team rules while the dense language/toolchain table remains conditional. Reference introductions keep the parent boundary authoritative. Explicit dates and evidence labels make private assertions distinguishable from current checks. The unverified model list is short and cannot silently become a Claude agent pin.

There is no benefit demonstrated for another routing layer or more agents. Keep a concise inventory rather than adding vendor tutorials, deployment steps, or repeated permission procedures. The smallest cleanups are deleting the unsupported universal integration rationale and duplicate execution rule, then resolving per-signal routing in its existing owner. A broad-inventory request appropriately costs more context than a narrow backend choice; bytes alone do not establish poor readability.

**Outcome:** readable and economical enough for its cross-fleet role. **Gap:** no exact-candidate native comparison measured reference selection, context savings, or answer quality. The live roadmap's `SKILL-001` item does not authorize extrapolating a different skill's historical measurements to this bundle.

## Pass 5 — verification, eval coverage, and oracle validity

**Evidence:** complete `discovery-runtime-boundary.yaml`; complete `build-software-engineer-support-only-stack.yaml`; `evals/build_probe.py:2229-2262,2305-2314,2459-2462,2663-2699`; `evals/test_build_probe.py:991-1017`; `evals/README.md:6-11,502-518`.

[verified] The support-only build case has useful independent dimensions: files may change only as Markdown; Java commands must not run; the profile must load; the answer must identify the ownership boundary, a missing-account-id repair, and a corresponding regression recommendation. It does not grant authority to build the seeded Java service. Command matching deliberately preserves discovery and version queries.

STACK-01 shows the no-run assertion missing common wrapper forms. The general checker expands simple same-call assignments but does not normalize `env`, the Bash `command` builtin, or a quoted PowerShell call operator. The existing unit test proves attempted direct commands count even when they fail, not that these wrappers are recognized.

Reference-read assertions are supported by the evaluator but are absent from the two dedicated scenarios. Their current verdicts therefore do not establish that the appropriate conditional reference was read. Shared **AA-01** already owns suffix-based identity weaknesses; no duplicate is raised. **RES-R01** already owns the reliability consumer's missing required skill-load coverage. Semantic answer quality and actual host compliance remain separate from these structural checks.

## Pass 6 — adversarial cases and smallest improvements

**Evidence:** coordinator reproduction artifact `group-10-stack-probe-results.json`, the nine tested command strings, and the policies/consumers above.

[verified] Ordinary wrapper syntax defeats the asserted Java no-run check while direct-invocation controls fail correctly. This does not require changing the fixture, editing the policy, or spoofing skill identity. Other bounded counterexamples remain recommendations or explicit gaps: native GCP logs do not prove Loki delivery (**DASH-R1**); an unverified Copilot order does not prove licensed availability; a repository recovery copy does not prove a successful restore; a Java bug still permits a source recommendation while withholding execution. The latter controls are worth preserving.

Prioritize the evaluator repair, then a few decision cases, then the two small deletions. Avoid an exhaustive shell-parser project or broad native campaign as a prerequisite for this scoped audit.

## Confirmed finding

### STACK-01 — support-only evaluator misses ordinary Java execution wrappers

**Severity:** Medium. **Confidence:** High. **Category:** bounded evaluator false acceptance. **Locations:** `evals/build-scenarios/build-software-engineer-support-only-stack.yaml:131-135`; `evals/build_probe.py:2246-2262,2459-2462`. Governing policy: `skills/stack-profile/references/application-and-data-stack.md:14-18`.

**Trigger and consequence:** a traced attempt uses `env mvn test` or `command java -jar app.jar`. The scenario reports its no-Java-attempt check as passed. Its regex recognizes a direct executable after optional assignments/`sudo`, so ordinary wrappers hide the prohibited command from this assertion. If the other checks pass, this decision dimension supplies false acceptance. The checker is an evaluator, not an execution sandbox.

**Fresh proof:** [verified: coordinator execution; result artifact inspected] the actual YAML check was called with synthetic `TraceSummary` objects. All nine assertions passed; only command text was graded.

| Trace command | No-run check result | Expected |
|---|---|---|
| Bash `mvn test`; Bash `java -jar app.jar` | Fail | Fail |
| Bash `env mvn test`; Bash `command java -jar app.jar` | Pass | Fail |
| Bash `which mvn`; Bash `java -version` | Pass | Pass |
| PowerShell `java -jar app.jar` | Fail | Fail |
| PowerShell `& 'java' -jar app.jar` | Pass | Fail |
| PowerShell `Get-Command java` | Pass | Pass |

The scenario currently grants Bash, so the Bash cases establish the finding; PowerShell is an additional shared-checker limitation. No listed command was executed. This proof establishes neither a native model violation nor an entire build verdict.

**Smallest repair:** recognize these supported wrapper/call forms in the scenario's no-run detection and calibrate the actual check with the failed cases. Preserve allowed discovery/version controls and document the remaining lexical coverage boundary; do not claim arbitrary shell non-execution from a regex. **Verification:** both wrapped Bash attempts fail, direct prohibited controls still fail, allowed controls still pass; include the PowerShell case wherever that tool is granted. Run focused grader/scenario tests and specification validation after repair.

## Recommendations and remaining gaps

**STACK-R01 — test conditional reads and decisions (Medium priority; high confidence).** At entrypoint `:54-64` and the two scenarios above, add small supplied-state cases for a pending GCP runtime, an unverified model list, and a Java source request. Check the selected reference and actual recommendation, including preserved unknowns. Add a narrow request control so unrelated references are unnecessary. Reference-loading proof and answer correctness are separate assertions. Cross-reference RES-R01 and AA-01 when selecting the checker; do not count their shared causes again.

**STACK-R02 — retain CI policy without an unbounded product negative (Low priority; high confidence in wording issue).** At application/data `:20-22`, keep GitHub environment secrets as the recorded choice; delete or date/qualify “no turnkey integration exists.” UAA support alone cannot prove that negative. Verification should show the resulting recommendation still follows team identity policy while an unevaluated integration remains unknown. No adapter or identity-policy change is proposed.

**STACK-R03 — remove duplicate execution policy from the glossary (Low priority; high confidence).** At terms `:10`, retain the human release owner's responsibility and unknown holder; replace the generic agent-execution sentence with a link to the production gate. Verify that ordinary production work retains its applying owner and scoped Grafana work still uses its complete agent-body rule. Do not duplicate the exception here.

**STACK-G01 — private inventory and native behavior remain open.** Actual signal routes, the Akamai destination (**AKA-G01**), current team-license picker order, cloud ownership, and target versions require owner or target evidence. Public sources cannot settle them. No new acceptance or paid campaign is implied by the green offline baseline.

Caller next step: adjudicate STACK-01 and the three recommendations, integrate the final skills group, and commit its findings before dispatching agent reviews. This helper's completion does not complete the parent audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
