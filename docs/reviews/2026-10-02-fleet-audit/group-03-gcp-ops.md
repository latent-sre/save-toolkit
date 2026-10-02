# Group 03: gcp-ops — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit HEAD `299c409615578c6616027707f60ca83eb307987f` contains earlier findings reports. Initial worktree was clean and the skill had no diff from the canonical baseline. Invoking caller/recipient: `/root`; human owner: the user. Assignment: complete. Parent objective: review skills before agents, three assets per group, with findings committed before advancing.

**Conclusion:** `gcp-ops` is suitable for bounded application-side Cloud Run investigation and gives useful paired console/CLI paths. Its output-protection requirement and unknown-state handling are strengths. One confirmed documentation defect overstates the scope of two guard restrictions. Current provider evidence also supports adding optional readiness-probe guidance; rollback compatibility and targeted behavioral coverage are recommendations, not observed service failures.

`[verified]` means inspected current source or the named local execution; `[sourced]` means fetched provider evidence; `[unverified]` means behavior or deployment facts not established. All three bundle files were read in full. No cloud command, project lookup, secret read, installation, model campaign, or candidate edit was performed.

## Pass 1 — suitability, routing, and human usability

**Sources:** complete `skills/gcp-ops/SKILL.md`, `references/cf-to-cloud-run.md`, and `references/projects.md`; `agents/sre-assistant.md:52-58,171-181,208-223`; `agents/observability-engineer.md:228`; `skills/stack-profile/SKILL.md:27-37,100-109`; both `discovery-gcp-ops-*.yaml` scenarios.

[verified] The description targets application-side GCP symptoms, revision correlation, and read-only investigation. The console-first table maps service details, revision history, metrics, and logs to CLI equivalents; it does not invent a metrics CLI where the workflow uses Cloud Monitoring. The skill distinguishes ambient CLI defaults from the caller's explicit project/service/region and binds those targets in its operational examples.

[verified] Missing tools have a console fallback. Missing or denied observations remain unknown, and a placeholder inventory leads to a question instead of an invented environment. The project inventory is deliberately incomplete and human-maintained; that is an operational gap, not a broken lookup implementation. Cloud Run remains a migration candidate rather than a silently accepted team runtime. The migration reference qualifies Google's recipe assumptions instead of treating every recipe restriction as a platform impossibility.

**Conclusion:** a useful application/operations lane for the team's coexistence period. The GCP and PCF routing scenarios provide opposing cases. Broad incident advice still belongs to the responder workflow; an agent's dispatch remains a bounded investigation.

**Gap:** [unverified] actual project ownership, supported regions, target IAM, console access, and a configured output-protected execution path. The artifact correctly refuses to infer those from installed CLI syntax or an empty view.

## Pass 2 — current technical contracts and provenance

**Sources:** `SKILL.md:25-115`; `references/cf-to-cloud-run.md:8-52`; Context7 official Cloud Run documentation and direct Google documentation, checked 2026-10-02. No claim here substitutes public documentation for target configuration.

[sourced] The service-log command supports the skill's region, freshness, and count controls; the documented default limit is unlimited, so explicit bounds are valuable. Traffic tags address revisions independently of percentage allocation, and `--to-latest` assigns traffic to current/future latest revisions. Sources: [service logs read](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/logs/read), [traffic commands](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/update-traffic), [rollouts and tags](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration).

[sourced] The troubleshooting sequence for the named 503 message remains supported, including the conditional high-throughput TCP-socket issue. HTTP/2 requires container `h2c` support. A 504 does not prove application work stopped, supporting the instruction to reconcile effects before retrying. Sources: [Cloud Run troubleshooting](https://docs.cloud.google.com/run/docs/troubleshooting), [HTTP/2 prerequisite](https://docs.cloud.google.com/run/docs/configuring/http2#before_you_configure), [request timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout).

[sourced] Direct VPC documentation retains the `/26` minimum, steady-state 2X address use plus a rollout buffer, potential startup connection delay, and the Cloud NAT connector recommendation for startup performance. Scale-from-zero for an instance-billed service still needs a request, supporting the worker-lifecycle qualification. Domain mappings remain preview and not recommended for production. Sources: [Direct VPC](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc), [autoscaling](https://docs.cloud.google.com/run/docs/about-instance-autoscaling), [domain mapping](https://docs.cloud.google.com/run/docs/mapping-custom-domains).

[sourced] A potentially misleading retrieval was resolved rather than reported as a defect: Context7 returned a 240-second maximum from the **individual-instance** health-check page. The exact **service** page documents the 240-second default TCP probe and a 600-second startup threshold×period maximum for the non-GPU service case. The skill's service mapping is supported. The same current page also documents readiness probes, motivating GP-R01. Source: [service health checks](https://docs.cloud.google.com/run/docs/configuring/healthchecks).

**Conclusion:** no contradiction found in the refreshed provider claims above. Context7 established documented contracts; direct provider pages resolved resource-specific details. This managed-service review did not obtain or claim access to Google's control-plane implementation/tests through GitHits.

**Gaps:** [unverified] actual configured probe values, availability/capacity, request paths, observed bottlenecks, and deployed client/server versions. Public limits do not prove a particular target is correctly configured.

## Pass 3 — authority, protected output, and recovery

**Sources:** `SKILL.md:16-21,45-54,117-153`; `references/projects.md:3-4`; `scripts/readonly-guard.py:555-585,809-824,1120-1136,1238-1318`; `hooks/hooks.json`; bounded `production-change-gate/SKILL.md:38-58,75-90` consumer contract.

[verified] The entrypoint explicitly requires credentials to be removed before stdout, errors, or log/configuration content reach the model. It recognizes that syntax admission does not mask output, and preserves human-sanitized observation as the fallback. This is especially important for service descriptions containing environment configuration and migrated `VCAP_SERVICES` values. The skill never supplies an output masker or claims that filtering rows makes credentials safe.

[verified] Traffic rollback is recommend-only, with a human release owner, explicit revision identity, pre-onset health evidence, metric verification, and a restoration command for the intended allocation/tracking policy. Revision proximity is a hypothesis, creation order is insufficient, and in-flight/transition effects remain visible. During an incident, the existing TLC/ITO change path is preserved.

[verified] Guard implementation distinguishes the SRE command allowlist from the fleet-wide credential tripwire. The skill's wording conflates those scopes for impersonation/flags-file restrictions; GP-01 documents the reproduced difference. Neither a hook allow result nor a credential already present grants operational authority.

**Conclusion:** the behavioral boundary is clear, but its enforcement description needs the small scope correction below. The gate's UNKNOWN-outcome reconciliation remains applicable after a human's interrupted traffic change; a recommendation should not imply that a missing receipt means nothing happened.

**Gap:** [unverified] host hook identity, protected output at every return path, actual applying actor, and post-change reconciliation. No privileged or live execution was used to validate these properties.

## Pass 4 — LLM readability and context cost

**Sources:** all three bundle files; `skills/obs-logs/references/gcp-logging.md:86-114` for the reason behind the filter form.

[verified] Sizes are 11,465 bytes/1,462 whitespace-delimited words for the entrypoint, 8,077/1,066 for the migration map, and 888/153 for the inventory: 20,430 bytes/2,681 words total. These are byte/word measurements, not token estimates. The migration and local-inventory references are conditional, which keeps much of the translation detail outside a simple triage read.

[verified] The task flow is understandable: establish protected access and target, inspect symptoms/revisions, interpret evidence, recommend bounded mitigation, identify the receiving owner. The explicit return fields are usable by a human and agent. The long severity exclusion chain is purposeful: the shared log reference explains why the PowerShell guard rejects comparisons/parentheses even inside quotes. Replacing it with a shorter but denied expression would be a regression.

The densest material is the concept-map table, especially networking and health checks. A future simplification should keep the decision-changing traps and link the exact resource-specific provider section, rather than repeat long numeric guidance in more files. GP-01 can be fixed by narrowing existing text; it needs no new generic authority section.

**Conclusion:** moderately large but relevant content, with useful conditional loading. Preserve the output-protection, tagged-revision, timeout-effects, and provisional-owner qualifications during any compression.

**Gap:** [unverified] improved native task completion or context savings from moving further material. Byte reduction alone does not establish better LLM behavior.

## Pass 5 — verification coverage and what green results establish

**Sources:** `scripts/test_skill_assets.py:158-203`; full `scripts/test_gcloud_config_guard.py`; gcloud and fleet credential cases in `scripts/test_readonly_guard.py:177-221,449-480,991-1055`; both GCP discovery scenarios; bounded SRE protected-output scenario `agent-direct-sre-assistant-dispatch-coverage.yaml`.

[verified] Asset tests require project/region bindings in entrypoint Cloud Run examples, require service/location/project in log filters, and feed fenced command examples into the guard under Bash and PowerShell. Read examples are admitted and traffic updates denied for `sre-assistant`. Configuration tests cover exact allowed target properties and reject broad/password/account reads, including the fleet credential context. These checks validate command policy, not Google API behavior or output redaction.

[verified] The discovery scenarios test GCP selection and PCF deferral. The positive routing scenario lists log/revision reading among success criteria, but its routing assertion does not prove retrieval, causal reasoning, or sanitized results. The protected-output SRE scenario is a supplied-record exercise for CF; it is useful shared evidence, not a GCP runtime proof. Existing shared findings AA-01/EL-01 remain cross-cutting harness limitations where their mechanisms apply; they are not duplicated here. BC-02's HTTP oracles are outside this skill's execution path.

[verified] Root's common baseline under Python 3.14.7 remains applicable to unchanged source: full offline suite 1,470 passed, 19 skipped, 1 warning, 2,690 subtests; specification validation 192 scenarios/737 expectations, both exit 0. GP-01 additionally has a fresh targeted synthetic-hook reproduction.

**Conclusion:** substantial structural/command-policy evidence, with no fresh GCP service, console, IAM, masked-output, or native-model verification. No historical canary scores were promoted to evidence for these bytes.

## Pass 6 — adversarial cases, finding, and recommendations

### GP-01 — two SRE-only flag restrictions are described too broadly

**Confirmed documentation defect; Medium severity; high confidence; [verified] source and root reproduction.**

**Locations:** `SKILL.md:139-143`; `scripts/readonly-guard.py:809-816,1120-1136,1246-1257,1309`; `agents/observability-engineer.md:228`.

**Trigger → consequence:** `observability-engineer` loads this skill for a GCP observation. The text says Claude's guard denies `--impersonate-service-account` and `--flags-file` on every command, but those tests run in the SRE allowlist. An operator or agent can incorrectly treat that stated control as protection in an unguarded lane. This is an enforcement-description error; no leaked credential or unauthorized cloud operation was observed.

**Fresh controls:** root sent synthetic hook JSON to `readonly-guard.py` with Python 3.14.7 `-I -S`. For both Bash and PowerShell, `sre-assistant` denied the two flag forms (43), while `observability-engineer` allowed them (42). A direct access-token-print command was denied for both (43). Denial JSON and empty allow output were asserted. No `gcloud` command or flags file was opened or executed.

**Smallest fix:** state that the SRE command allowlist denies these two flags; describe named credential-output prohibitions separately as the fleet tripwire. Retain protected-output and actor authority requirements. Do not broaden the guard or another lane's permissions merely to make the documentation true.

**Verify:** retain the two-lane/two-shell matrix and credential negative control, then check the revised wording against the hook dispatch path. Host acceptance remains a separate check.

### GP-R01 — include optional readiness in the CF-to-Run health mapping

**Recommendation; Medium priority; [sourced] current capability, [unverified] target applicability.** `references/cf-to-cloud-run.md:48` maps health to startup plus liveness. Current [service health-check documentation](https://docs.cloud.google.com/run/docs/configuring/healthchecks#configure_readiness_probes) also describes readiness: failed checks withdraw new routing without killing the instance, and passing checks restore routing. It documents a session-affinity exception and an older API-v1 configuration caveat. Add a short conditional pointer; distinguish startup completion, ongoing readiness, and liveness. Verify with a supplied-state case where an instance is alive but unready. Do not mandate deployment of a new probe.

### GP-R02 — qualify rollback suitability with current compatibility

**Recommendation; Medium priority; high confidence in the missing explicit check, [unverified] service risk.** `SKILL.md:126-132` requires evidence that the previous revision served healthy before onset. A previously healthy revision may be incompatible with a subsequently changed schema, shared secret/configuration, or upstream contract. Add one bounded preflight condition: confirm the candidate still fits current shared state, or retain the compatibility gap and seek a safe recovery option under the existing change gate. Verify a compatible positive and an accepted-write/schema-change counterexample. Prior health alone should not settle present rollback suitability.

### GP-R03 — add a focused protected-investigation contract case

**Verification recommendation; Medium priority; [unverified] runtime gap.** Cover missing project/region, an unavailable output-protected path, denied/empty logs, and a supplied zero-percent revision that still has a tag URL. The expected result should retain unknowns, avoid raw credential-bearing reads, and choose a bounded next observation. Pair with sanitized positive evidence sufficient to identify a candidate rollback while leaving application with the human. Use synthetic records/guard receipts first; live host validation needs a separately established protected target. No new paid campaign is proposed here.

**Strengths to preserve:** console/CLI parity, exact target flags, bounded logs, immutable revision versus actual-serving distinction, tagged revision reachability, `h2c` prerequisites, post-504 effect reconciliation, human rollback ownership, and honest inventory/platform unknowns.

**Handoff:** `/root` should reconcile GP-01 with its recorded reproduction, commit the group-03 findings, and continue the parent audit. This reviewer wrote only this scratch report and did not modify canonical content, tests, configuration, or repository history.

## Central verification

The caller adjudicated this report against its cited source and [group 03 verification](verification.md). Static findings, executed counterexamples, the frozen-baseline atlas contract and unavailable UI execution remain explicitly distinguished.
