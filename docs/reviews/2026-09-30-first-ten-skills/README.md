# First ten skills correctness and prose review

This is the historical review baseline. The owner's subsequent selected repair batch and current
dispositions are recorded in [remediation evidence](remediation.md).

Reviewed on 2026-09-30 for the repository owner. This is a review of the first ten skills alphabetically, as confirmed by the owner, with each bundle inspected individually. It records findings for a later decision; it does not authorize or implement repairs.

The skills contain substantial useful, accurate guidance. The most consequential corrections concern SPA fallback behavior, Cloud Run traffic and HTTP/2 semantics, and incident causal reasoning. Duplication is concentrated in agent-authoring, Grafana, and incident-investigation. Removing all repeated safeguards would be a mistake: independently loaded references still need a short authority and evidence boundary.

## Reviewed state and evidence limits

- [verified] Baseline: `f505da5cacc4679a6eebe9ceebfd07108ecb226f`, with an existing working-tree modification to `CONTRIBUTING.md`. That file was read and preserved.
- [verified] Read all 70 tracked files in the ten bundles: entrypoints, bundled references, starter assets, and helper scripts. Generated projections were checked by Gate A, not counted as separate skills. Ignored Python bytecode was excluded.
- [verified] [Snapshot](snapshot.json) records the exact reviewed file paths, SHA-256 hashes, byte counts, and line counts. Locations below refer to these bytes. Supporting inspection included the fleet guide, stack-profile, selected agent bodies, validators, guard code, and relevant tests.
- [sourced] Current public documentation was checked through Context7, upstream source through GitHits, and primary vendor pages through web retrieval. Sources support only the named claims below. Context7 retrieval was sometimes broader than the question; direct vendor pages were used to settle those details.
- [unverified] No live cloud, database, Grafana, browser, deployment, notification, host-enforcement, or model-behavior campaign ran. Historical target observations and owner statements in the skills were checked for appropriate qualification, not re-observed. This is not certification of every vendor claim or target configuration.
- Earlier review notes were used only to identify questions to recheck. Prior fixes were not presumed present or merged; findings below come from the current tree.

**Disposition:** 30 numbered items: **10 confirmed defects or contract gaps**, and **20 recommendations** covering completeness, duplication, prose, or policy clarity. Confirmed items are six Medium and four Low; none is a demonstrated live outage or exploit. Every item is open for owner review. Recommendations are not prerequisites to accepting unrelated work.

| Order | Skill | Tracked files | Bundle bytes | Entrypoint lines | Confirmed | Recommendations |
|---|---|---:|---:|---:|---|---|
| 1 | agent-authoring | 10 | 79,224 | 157 | AA-01 | AA-02, AA-03 |
| 2 | akamai-edge | 4 | 27,088 | 79 | None identified | AK-01, AK-02 |
| 3 | backend-craft | 9 | 54,071 | 85 | BE-01 | BE-02 |
| 4 | ci-actions | 6 | 42,557 | 107 | None identified | CI-01 |
| 5 | database-reliability | 6 | 20,286 | 83 | None identified | DB-01 |
| 6 | eng-ladder | 4 | 13,695 | 74 | None identified | EL-01 |
| 7 | frontend-craft | 3 | 13,686 | 71 | FE-01 | FE-02, FE-03, FE-04, FE-05 |
| 8 | gcp-ops | 3 | 19,951 | 166 | GC-02, GC-03, GC-05 | GC-01, GC-04, GC-06 |
| 9 | grafana | 18 | 123,499 | 85 | GF-01 | GF-02, GF-03, GF-04 |
| 10 | incident-investigation | 7 | 57,244 | 290 | II-01, II-02, II-03 | II-04, II-05 |

## 1 Agent authoring

Read the entrypoint and all nine references. The method now correctly distinguishes repairing an observed failure from creating a new capability. It also preserves source trust, evidence labels, bounded evaluation, and human promotion.

**AA-01 — New evaluation work still requires a measured prior failure in one reference. Confirmed; Low; high confidence.**

Location: [artifact.md](../../../skills/agent-authoring/references/artifact.md), lines 43–45; compare [SKILL.md](../../../skills/agent-authoring/SKILL.md), lines 35–46. The entrypoint allows explicit new behavior without inventing a failing baseline. The reference nevertheless says every new grader, validator, scenario, or script names the measured failure it prevents. A scenario for a genuinely new capability cannot always meet that rule. This can cause unnecessary baseline work or invented evidence. Smallest fix: make the reference accept either an observed failure or a requested new contract and its acceptance cases. Verification: review a new-capability example and a repair example against the combined instructions; only the repair should require a reproduced incumbent failure.

**AA-02 — State which artifact the validation rules describe. Recommendation; Low; high confidence in the ambiguity.**

Location: [artifact.md](../../../skills/agent-authoring/references/artifact.md), lines 81–84. Directory matching, a character limit, and quoted trigger phrases describe skills. Agent frontmatter instead uses a UTF-8 byte limit and does not require the skill trigger syntax. [check_links.py](../../../scripts/check_links.py), lines 307–324, and [validate_fleet.py](../../../scripts/validate_fleet.py), lines 201–205, implement that distinction. The reference is used for both agents and skills. Label the bullet “Skill frontmatter” and link to the existing agent table; do not add another copy of both contracts. This is a clarity issue, not proof that the validators are wrong.

**AA-03 — Consolidate repeated evaluation rules. Recommendation; Low; high confidence.**

Location: [artifact.md](../../../skills/agent-authoring/references/artifact.md), lines 18–49 and 53–67. Exact candidate identity, comparable conditions, evidence retention, independent review, and human promotion appear in the loop table and again immediately below. Keep the table as the contract; keep only the unique details about held-out cases, independent review, and instruction-removal evidence in the following sections. Preserve failure evidence and promotion boundaries. Verification: map every unique rule before deleting text; report the byte delta. Reduced length alone would not prove improved agent behavior.

**Checks and correct information:** [sourced] Current [Claude subagent documentation](https://code.claude.com/docs/en/sub-agents) supports the distinction between tool grants, settings permissions, plugin restrictions, and host behavior. The [portable Agent Skills specification](https://agentskills.io/specification) supports the six-field metadata list, 1,024-character description limit, conditional resources, and implementation-dependent `allowed-tools`. [verified] Local validators distinguish skill characters from agent bytes. [unverified] Exact installed-host filtering, historical probes, discovery-budget measurements, and Copilot enforcement were not rerun. Those limits should remain explicit.

## 2 Akamai edge

Read all four files. No material factual defect was established in the technical claims checked. The separation between edge symptoms, origin evidence, WAF ownership, and change authority is useful.

**AK-01 — Keep the offload diagnostic differential open. Recommendation; Low; medium confidence in operational benefit.**

Location: [edge-triage.md](../../../skills/akamai-edge/references/edge-triage.md), lines 129–130. Calling an offload drop with rising origin traffic a cache-key or TTL question is a useful lead, but too narrow as the whole next-step rule. Traffic/object mix, purges, cacheability changes in origin responses, and cache warmth can change the result without a property activation. Change the sentence into candidate checks and compare like populations. Do not label any one cause established from the aggregate. Verification: a cold-cache or changed-request-mix example should remain open after the property activation history is clean.

**AK-02 — Replace abbreviated citations and repeated historical headers with usable source links. Recommendation; Low; high confidence.**

Locations: [edge-triage.md](../../../skills/akamai-edge/references/edge-triage.md), lines 3–5, 17–29 and 110–116; [property-config.md](../../../skills/akamai-edge/references/property-config.md), lines 3–5. Strings such as `…/docs/faq` and broad August retrieval headers make it harder to refresh an individual claim; later paragraphs already carry newer checks. Use direct links near decision-changing facts, with one scoped freshness statement where needed. Preserve the documented retry-budget disagreement and target-account uncertainty rather than deleting them as clutter.

**Checks and correct information:** [sourced] [Pragma/cache statuses](https://techdocs.akamai.com/edge-diagnostics/docs/pragma-headers), [Enhanced Debug](https://techdocs.akamai.com/property-mgr/docs/enhanced-debug), [DataStream fields](https://techdocs.akamai.com/datastream2/docs/data-set-parameters), [activation behavior](https://techdocs.akamai.com/property-mgr/docs/how-activation-works), and [mPulse timers](https://techdocs.akamai.com/mpulse/docs/use-metrics) support the checked descriptions: authenticated debug requests, parent/child cache distinctions, cache presence not proving offload, turnaround not isolating origin latency, and conditional Fast Fallback. Enhanced Debug's page failed direct retrieval once; Context7 supplied its official contract. [unverified] Actual account features, stream delivery/retry behavior, RUM populations, and recovery timings were not exercised.

## 3 Backend craft

Read the entrypoint, four references, and four assets. The code handles request correlation, protocol headers, malformed JSON, and unhandled exceptions deliberately. The write/background references correctly separate atomic local state from uncertain remote effects.

**BE-01 — The collection limit assertion can pass when the implementation ignores the limit. Confirmed coverage gap; Low; high confidence.**

Location: [test_http_contract.py](../../../skills/backend-craft/assets/test_http_contract.py), lines 90–106. The test asserts at most one item after `limit=1`, but requires no fixture containing more than one visible item. An empty or one-item collection passes even if the application ignores `limit`. A fresh controlled counterexample called the shipped test with a client that ignores all parameters and always returns its one existing item: the assertion passed. The header warns about sparse data for the maximum-cap check, but the same issue applies to this basic limit assertion. Smallest fix: require at least two visible fixtures before asserting limit behavior, or explicitly separate a response-shape check from a populated pagination test. Verification: an implementation that deliberately ignores the parameter must fail the adapted test. No application pagination defect was demonstrated here.

**BE-02 — Make conditional crash-testing guidance read consistently. Recommendation; Low; high confidence.**

Location: [api-writes.md](../../../skills/backend-craft/references/api-writes.md), lines 39–43. One sentence says a naturally idempotent upsert or PUT needs only a duplicate-request check; the next unqualified sentence requires both commit-boundary crashes. Make the latter explicitly apply to the effectful/replay-ledger branch. Preserve stronger testing when an apparently idempotent write also emits a notification or other non-idempotent effect. This removes ambiguity without adding a new test framework.

**Checks and correct information:** [verified] `test_backend_craft_assets.py` and `test_api_write_contract.py`: **93 passed**. The latter tests the acceptance predicates with controlled adapters, not a real database or killed production worker. [sourced] [FastAPI async-testing guidance](https://fastapi.tiangolo.com/advanced/async-tests/) confirms that ASGITransport does not run lifespan automatically. GitHits source inspection of [Starlette ServerErrorMiddleware](https://github.com/encode/starlette/blob/63c5760d8a672cee96e1e523d84bfa1c77d9ee4c/starlette/middleware/errors.py#L180) confirms re-raising after the handler, supporting the starter's warning that server logging needs separate redaction. [unverified] Provider-specific auth flows, real persistence races, server logging configuration, and deployment shutdown behavior were not exercised.

## 4 CI actions

Read all six files. No material correctness defect was established in the reviewed workflow advice or executed local deployment fixtures. In particular, newer syntax was checked rather than rejected from older recollection.

**CI-01 — Trim repeated summaries while retaining the separate execution-authorization reference. Recommendation; Low; medium confidence in benefit.**

Locations: [SKILL.md](../../../skills/ci-actions/SKILL.md), lines 36–58 and 71–105; [execution-and-runners.md](../../../skills/ci-actions/references/execution-and-runners.md), lines 38–80; [security-and-provenance.md](../../../skills/ci-actions/references/security-and-provenance.md), lines 26–41. Pinning, cache-versus-artifact identity, credential protection, and failure visibility recur in the entrypoint and references. Keep the entrypoint's short decisions and put implementation caveats in their existing references. Do not merge `validation-runs.md` into a generic security paragraph: downstream workflows, rerun ref resolution, and unknown submissions are distinct hazards. No new abstraction is needed.

**Checks and correct information:** [verified] `test_pcf_deploy_example.py` and `test_validate_workflow.py`: **43 passed, 21 subtests passed**. The CF commands ran against local fixtures; health checks used local test responses. [sourced] Current [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) supports `queue: max`, its 100-pending limit, incompatibility with cancellation, and scoped `cache-mode`. [Reusable workflow documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations) distinguishes all-job reruns from failed/specific-job reruns. GitHits returned checkout's [reviewed action metadata](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/action.yml); it reported a fallback under the release tag but the served commit matched the requested SHA. [unverified] No remote workflow, environment approval, actual runner isolation, foundation access, or recovery was tested. The repository's intentional latest-version canary is a policy choice, not incidental pin drift.

## 5 Database reliability

Read the entrypoint and all five references. No material factual defect was established in the version-sensitive migration claims checked. The references are already comparatively compact and well separated by task.

**DB-01 — Make engine-specific source pointers complete and versioned. Recommendation; Low; high confidence.**

Locations: [postgres-migrations.md](../../../skills/database-reliability/references/postgres-migrations.md), lines 20–22 and 49–51; [sql-server-migrations.md](../../../skills/database-reliability/references/sql-server-migrations.md), lines 22–24 and 38–41. Some load-bearing claims point only to a document title or release-note name. Add direct version-specific links where the edition, lock behavior, or syntax changes the migration plan. Keep the target-version precondition. No broad prose rewrite or extra runbook is justified by this review.

**Checks and correct information:** [sourced] PostgreSQL 18's [ALTER TABLE contract](https://www.postgresql.org/docs/18/sql-altertable.html) supports named `NOT NULL ... NOT VALID`, enforcement on new writes, and lower-lock validation. Its [generated-column documentation](https://www.postgresql.org/docs/18/ddl-generated-columns.html) confirms virtual-by-default behavior. Microsoft [ALTER TABLE](https://learn.microsoft.com/en-us/sql/t-sql/statements/alter-table-transact-sql?view=sql-server-ver17) and [CREATE INDEX](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql?view=sql-server-ver17) support the checked online-operation qualifications, excluded types, maximum possible row-size condition, and operation-specific low-priority waits. [verified] Restore-drill guidance separates observed recovery time/freshness from objectives and permits an inconclusive verdict. [unverified] No SQL, scale rehearsal, lock contention test, backup restore, or edition check ran.

## 6 Engineering ladder

Read all four files. The ladder is a house routing and assessment policy, not an externally standardized career ladder. Its ownership distinctions are consistent with the current fleet: an accepted cross-service design can remain builder-owned; a consultation does not silently transfer implementation or grant a delegation edge.

**EL-01 — Mark fixed time horizons as illustrative. Recommendation; Low; medium confidence in benefit.**

Location: [SKILL.md](../../../skills/eng-ladder/SKILL.md), lines 18–33. The table's 6–18-month and 3–5-year horizons read like routing tests, while the actual routing rule uses the unresolved decision and reversibility. Say these are typical horizons, or remove that row if it never changes a routing decision. Retain the scope row as authoritative. A small build/buy decision should not need a three-year project to receive the appropriate analysis.

**Checks and correct information:** [verified] The builder's three-failed-fixes escalation matches `root-cause`; references distinguish design completion from implementation verification and reserve human deployment authority. [sourced] [Hyrum's Law](https://www.hyrumslaw.com/) supports the warning about observable behavior becoming a dependency; it does not mandate preserving every accidental behavior forever. [unverified] Routing usefulness and organizational career expectations were not behaviorally tested.

## 7 Frontend craft

Read all three current files. Several useful improvements described in older notes are absent from this snapshot, so this review assesses the current guidance directly.

**FE-01 — SPA fallback also swallows missing asset requests. Confirmed guidance defect; Medium; high confidence.**

Location: [stack.md](../../../skills/frontend-craft/references/stack.md), lines 32–41. The instruction rewrites unknown paths to `index.html` and excludes API paths only when co-serving. It does not exclude a missing hashed JavaScript/CSS file, so a broken release can return HTML/200 for an asset. [sourced] GitHits inspection of the Staticfile buildpack at `22b502fd325f5725e0a1d5972f9b59ca9ec6d8c2` found the unconditional nonexistent-path rewrite in [data.go](https://github.com/cloudfoundry/staticfile-buildpack/blob/22b502fd325f5725e0a1d5972f9b59ca9ec6d8c2/src/staticfile/finalize/data.go#L123). Smallest fix: distinguish document-navigation fallback from asset lookup; require missing assets to return 404 and preserve API/health responses. Verification: deep-link navigation succeeds, missing JS/CSS stays 404, and co-served API misses retain their contract. This review did not run NGINX or claim a deployed application is affected.

**FE-02 — Add identity and scope rules for cached server data. Recommendation; Medium; high confidence in the gap.**

Location: [SKILL.md](../../../skills/frontend-craft/SKILL.md), lines 40–49. The query-cache recommendation lacks a rule for tenant/account/environment changes, logout, or late in-flight responses. [sourced] [TanStack query keys](https://github.com/TanStack/query/blob/main/docs/framework/react/guides/query-keys.md) must identify changing inputs to the returned data. Add one concise rule to include the relevant non-secret scope in query identity and prevent prior-session data from surviving a switch. Verification should use delayed responses during a user/tenant change. This is an incomplete safety recipe, not a demonstrated data leak.

**FE-03 — Specify different cache treatment for HTML and hashed assets. Recommendation; Medium; high confidence in the omission.**

Location: [stack.md](../../../skills/frontend-craft/references/stack.md), lines 32–42. “Cache-bust on hashed filenames” does not establish HTML freshness or how an old page loads its old chunks during a release. Document a revalidated entry document, long-lived immutable caching only for content-hashed assets, and the project's old-asset retention/recovery strategy. Test an old loaded page across a release. Preserve existing serving policy where already established; do not invent cache durations for every application.

**FE-04 — Include dynamic status and reflow in accessibility verification. Recommendation; Medium; high confidence in the omission.**

Location: [SKILL.md](../../../skills/frontend-craft/SKILL.md), lines 26–32 and 53–60. Labels, focus, keyboard access, contrast, and chart alternatives are useful but do not cover asynchronous success/error messages or zoom/reflow. [sourced] W3C's [status-message guidance](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) and [reflow guidance](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) describe those separate concerns. Add task-scoped checks for status announcements without unnecessary focus movement and usable reflow/zoom. An actual UI's conformance remains unverified.

**FE-05 — Replace arbitrary thresholds and aesthetic prohibitions with task-based choices. Recommendation; Low; high confidence in the prose issue.**

Locations: [SKILL.md](../../../skills/frontend-craft/SKILL.md), line 45; [design-language.md](../../../skills/frontend-craft/references/design-language.md), lines 17–24 and 48–57. “A few hundred rows,” five destinations, typography counts, and lists of forbidden visual styles mix heuristics with mandatory wording. Base virtualization on measured rendering cost, navigation on the information structure and viewport, and styling on the agreed design plan. Keep real house decisions such as the Mantine policy explicit. Delete repeated aesthetic self-critique before adding more guidance. There is no evidence here that every current design choice is wrong.

**Checks and correct information:** [verified] Auth guidance distinguishes cookie/BFF CSRF from bearer-token use; SSE guidance accounts for native EventSource's header limitations and unsafe retry effects. Backend checks are currently tied to co-serving in the reference. [unverified] No UI, browser lifecycle, accessibility audit, or tenant-switch test ran in this review.

## 8 GCP operations

Read all three files and compared command advice with the current SRE agent's protected-output contract. The pending runtime decision and placeholder inventory are correctly labelled; neither should be “fixed” by inventing current project data.

**GC-01 — Put output protection before broad service and log reads. Recommendation; Medium; high confidence.**

Location: [SKILL.md](../../../skills/gcp-ops/SKILL.md), lines 15–18, 31–44 and 65–67. These commands can expose literal environment values or sensitive log content. Sanitizing the excerpt returned afterward is too late if raw output already reached the model. [sourced] Google's [environment-variable documentation](https://docs.cloud.google.com/run/docs/configuring/services/environment-variables) shows environment values in exported service configuration. The parent [SRE agent](../../../agents/sre-assistant.md), lines 175–181, already requires protected output, so this is a local guidance gap rather than proof of an authorized bypass. Add a short pre-read requirement and a sanitized-console fallback. Verify with synthetic canaries at the result boundary; do not retrieve real secrets to test it.

**GC-02 — Zero percentage traffic does not make a tagged revision unreachable. Confirmed factual overstatement; Medium; high confidence.**

Location: [SKILL.md](../../../skills/gcp-ops/SKILL.md), lines 55–63. `--no-traffic` is described as keeping a revision “unrouted until traffic is explicitly assigned.” A revision with a tag can still receive direct requests at its tagged URL while receiving zero service percentage traffic. [sourced] Google's [tagged-revision procedure](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration#tags) explicitly combines `--no-traffic` with a testable tag. Change “unrouted” to the precise percentage-traffic statement and inspect tags, ingress, and IAM before making reachability claims. Verification: reason through a zero-percent tagged revision without classifying it as isolated.

**GC-03 — HTTP/2 is recommended without its required application protocol check. Confirmed incomplete operational instruction; Medium; high confidence.**

Location: [SKILL.md](../../../skills/gcp-ops/SKILL.md), line 105. The 503 row ends with “turn on HTTP/2.” [sourced] [Cloud Run HTTP/2](https://docs.cloud.google.com/run/docs/configuring/http2) requires the container to accept cleartext HTTP/2 (`h2c`); it is not a safe switch for every HTTP/1-only server. Make it conditional on observed connection pressure and verified h2c support, with a tested rollout/backout. The row's throughput threshold is a troubleshooting lead, not proof that every service above that rate has exhausted sockets.

**GC-04 — Distinguish migration-guide assumptions from platform limits and singleton guarantees. Recommendation; Medium; high confidence.**

Location: [cf-to-cloud-run.md](../../../skills/gcp-ops/references/cf-to-cloud-run.md), lines 8–20 and 50. The eligibility list accurately attributes a specific migration overview, but can be read as Cloud Run's entire capability envelope. Label it as that migration path's assumptions, with separate routing/workload redesign assessment where needed. Likewise, moving singleton work to a job or worker pool does not itself establish one business effect under duplicate launches or retries. Reference the existing idempotency/coordination contract rather than inventing another one. Verification: a duplicate task and a path-routed application must receive bounded assessment, not automatic safety or rejection.

**GC-05 — Multi-container services do not automatically share a memory volume. Confirmed factual ambiguity requiring correction; Medium; high confidence.**

Location: [cf-to-cloud-run.md](../../../skills/gcp-ops/references/cf-to-cloud-run.md), line 51. The row groups the shared network namespace with “a shared in-memory volume” as if both are inherent. [sourced] [Deployment documentation](https://docs.cloud.google.com/run/docs/deploying#sidecars) says containers can share files through such a volume; [volume configuration](https://docs.cloud.google.com/run/docs/configuring/services/in-memory-volume-mounts) requires explicit mounts. State “optional, explicitly configured shared volume.” The same row should note that collectors needing CPU between requests require the appropriate billing/CPU allocation; startup ordering alone does not keep a collector running. Verify both mounts and idle-time collection in the chosen deployment before claiming coverage.

**GC-06 — Explain that a 504 can leave application work running. Recommendation; Medium; high confidence.**

Location: [SKILL.md](../../../skills/gcp-ops/SKILL.md), line 106. Comparing request timeouts with downstream latency is correct, but omits the retry consequence. [sourced] [Cloud Run timeout documentation](https://docs.cloud.google.com/run/docs/configuring/request-timeout) says the container is not terminated and code may continue after the client receives 504. Add this fact and direct effectful retries to reconciliation/idempotency. Verification: a timed-out write must not be treated as a proven failed operation that can be blindly repeated.

**Checks and correct information:** [verified] The existing guard tests cover selected noncredential config properties. [sourced] Explicit project/region binding, revision-versus-traffic distinctions, and HTTP2 cleartext requirements were checked against Google documentation. [unverified] No actual project, revision, output filter, sidecar, traffic change, or Cloud Run retry was tested. Not every networking limit or regional feature in the migration table was independently refreshed.

## 9 Grafana

Read all 18 files, including the three scripts. The strongest parts are ownership checks, optimistic concurrency, UNKNOWN outcomes, per-query error inspection, and separation of read, render, and delivery evidence.

**GF-01 — Uncheckable dashboard structures violate the helper's exit-code contract. Confirmed and reproduced; Low; high confidence.**

Location: [dashboard_hygiene.py](../../../skills/grafana/scripts/dashboard_hygiene.py), lines 78–96 and 184–201; compare [json-model.md](../../../skills/grafana/references/json-model.md), lines 130–140. The helper promises exit 2 for an input it cannot check. Valid JSON `null`, `{"panels":[1]}`, and `{"panels":{"id":1}}` instead raise uncaught TypeError/AttributeError, print a traceback, and exit 1. That conflates an unreadable structure with a checked dashboard containing violations. Smallest fix: validate the top-level/wrapper and panel collection types before walking, and return the documented uncheckable result. Verification: those three inputs return 2 without traceback, while a genuine rule violation remains 1 and a valid clean model remains 0. The original files were not modified for this reproduction.

**GF-02 — Reproduce the actual rate interval when comparing query and image evidence. Recommendation; Medium; high confidence.**

Location: [http-api.md](../../../skills/grafana/references/http-api.md), lines 137–144; compare [visual-verification.md](../../../skills/grafana/references/visual-verification.md), lines 106–132. A replacement interval “at least four scrape intervals” is a safe floor, but does not necessarily match the panel. [sourced] Grafana defines [the macro](https://grafana.com/docs/grafana/latest/datasources/prometheus/template-variables/) as `max($__interval + scrape_interval, 4 * scrape_interval)`. Record the real resolution/Min step or label the query as an approximation. For example, a one-hour display interval with a 15-second scrape is not reproduced by a one-minute rate window. This is an evidence-fidelity improvement, not proof that existing panels are wrong.

**GF-03 — Delete the misleading idempotency label. Recommendation; Low; high confidence.**

Location: [dashboard-operations.md](../../../skills/grafana/references/dashboard-operations.md), lines 64–70; [http-api.md](../../../skills/grafana/references/http-api.md), lines 96–100. “Idempotent-by-target” is immediately qualified by correct reconciliation rules, while the API reference warns identical content can create another history entry. Keep the latter precise statement: stable UID identifies desired state; it does not prove retry safety or execution attribution. No additional mechanism is needed, and the existing UNKNOWN handling should remain.

**GF-04 — Give version facts and operation rules one owner each. Recommendation; Low; high confidence.**

Locations: [dashboard-operations.md](../../../skills/grafana/references/dashboard-operations.md), lines 13–21 and 32–90; [http-api.md](../../../skills/grafana/references/http-api.md), lines 7–12 and 37–47; [json-model.md](../../../skills/grafana/references/json-model.md), lines 5–47; [read-only-review.md](../../../skills/grafana/references/read-only-review.md), lines 46–59. Version history and 13.2 target observations are repeated across four files, and the dashboard operation loop repeats substantial API procedure. Keep the loop as decisions, the API reference as endpoint/concurrency mechanics, and JSON model as schema rules. Keep a short read-only limitation at each entry point. Two consecutive `stack-profile` loads in dashboard operations can become one. Preserve distinct folder, alert, silence, and dashboard recovery rules.

**Checks and correct information:** [verified] Grafana helper, hygiene, guard/config and skill-asset checks are included in the **322-test** group below. Inspection confirms organization binding, redirect rejection, bounded reads, known-auth-value masking, explicit query coverage limits, and refusal of V2 by the hygiene checker. [sourced] Current [folder API documentation](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/folder/) supports the reference's documented 412 mismatch handling; do not replace it with a blanket dashboard rule. [unverified] Current target rights, stored schema, import/write fidelity, notification delivery, and historical 13.2 target observations were not revalidated. GitHits began indexing the pinned Grafana 13.2 source for a parser spot-check; its status must not be mistaken for fetched source evidence.

## 10 Incident investigation

Read the entrypoint, all five references, and closeout asset. The advisor/helper/ITO split, human recovery decision, UNKNOWN-effect reconciliation, and source-versus-current-state distinction are sound and worth preserving.

**II-01 — A timing difference does not prove time was spent outside the container. Confirmed diagnostic overclaim; Medium; high confidence.**

Location: [signal-patterns.md](../../../skills/incident-investigation/references/signal-patterns.md), lines 46–47. A load balancer reporting seconds while an application log reports milliseconds only establishes different measured intervals until their boundaries are known. A request can queue inside the application process before a handler timer starts, or spend time streaming after that timer stops. Thus the sentence can incorrectly clear the app and send the investigation to a network owner. Smallest fix: identify the same request and timer boundaries, then separate admission/queueing, handler, downstream, and transfer time. [sourced] [Cloud Foundry timing documentation](https://docs.cloudfoundry.org/adminguide/troubleshooting_slow_requests.html) explicitly distinguishes request-flow intervals. The queue example is a reasoning counterexample, not a measured incident.

**II-02 — Dependency transport errors do not clear client code or configuration. Confirmed diagnostic overclaim; Medium; high confidence.**

Location: [signal-patterns.md](../../../skills/incident-investigation/references/signal-patterns.md), lines 23–25. It puts 429, refused/reset connections, and certificate errors on the dependency side “rather than the app's code,” except for increased call volume. Client trust-store changes, SNI/hostname mistakes, stale pooled connections, or wrong endpoint configuration are additional local candidates without increased volume. The preceding dependency rule already correctly includes the app's client. Smallest fix: preserve both sides of the boundary and compare failing client versions/configuration and requests. Verification: a client-only certificate/configuration change must remain in the differential. This is not a claim that a current dependency or application is faulty.

**II-03 — Alert fire time is not universally the closing time of a window. Confirmed factual overstatement; Low; high confidence.**

Location: [SKILL.md](../../../skills/incident-investigation/SKILL.md), lines 69–73. Sliding evaluations, pending durations, and notification delays break the stated explanation. [sourced] [Prometheus alert rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) distinguish evaluation, pending, and firing; a page can arrive later still. The intended action—read back to observed onset—is correct. Replace the parenthetical with “evaluation, pending and notification timing may delay the page; establish impact onset from evidence.” Also keep alert-condition onset separate from user-impact onset.

**II-04 — Remove the fixed candidate count. Recommendation; Low; high confidence.**

Location: [SKILL.md](../../../skills/incident-investigation/SKILL.md), lines 74–80. “Two or three” and “Never one story” conflict in practice with “Do not pad the list” when only one supported candidate exists or the cause is established. Ask for supported alternatives and an explicit uncertainty statement, without a quota. Preserve counter-evidence and a discriminator. A smaller list is not permission to jump to certainty.

**II-05 — Reduce repeated turn instructions while retaining the board and examples. Recommendation; Low; high confidence.**

Locations: [SKILL.md](../../../skills/incident-investigation/SKILL.md), lines 25–37, 63–137, 140–179 and 215–240; [helper-exchange.md](../../../skills/incident-investigation/references/helper-exchange.md), lines 41–56. Intake, five questions, phase questions, mandatory turn sections, board fields, and pressure examples restate several obligations. Make the first-turn intake and normal-turn sequence the authoritative procedures; retain only unique exceptions and discriminating examples elsewhere. The 290-line entrypoint's line count alone is not a defect, but these overlaps are concrete deletion candidates. Preserve open actions, timestamps, owners, evidence labels, and the no-incident/closeout exceptions. Any claim of improved incident behavior would still need a separately chosen behavioral check.

**Checks and correct information:** [verified] The fictional helper example's September UTC-to-EDT conversion is correct; closeout retains dated UTC fields while conversation display uses Eastern time. Mitigation readback distinguishes a new rollback revision from its historical target and retains operator ownership. These CF-specific command claims were inspected for consistency with the local procedures; not every one was re-fetched from upstream in this review. [unverified] No live incident, helper-return/resume campaign, platform mitigation, or recovery window was observed. The existing roadmap's incident behavioral gate remains open.

## Verification record

All commands used the existing `.venv/Scripts/python.exe`, observed as **Python 3.14.7**, with `-B`. No packages were installed and no candidate source, test, agent, skill, or generated adapter was changed.

| Command or check | Fresh result | What it establishes |
|---|---|---|
| `-m pytest -q scripts/test_backend_craft_assets.py scripts/test_api_write_contract.py` | Exit 0; 93 passed | HTTP starter behavior and controlled acceptance assertions |
| `-m pytest -q scripts/test_pcf_deploy_example.py scripts/test_validate_workflow.py` | Exit 0; 43 passed, 21 subtests passed | Local deploy/health/recovery examples and workflow contracts |
| `-m pytest -q scripts/test_grafana_read.py scripts/test_dashboard_hygiene.py scripts/test_grafana_helper_guard.py scripts/test_gcloud_config_guard.py scripts/test_skill_assets.py` | Exit 0; 322 passed, 77 subtests passed | Helper, guard and asset behavior covered by those tests |
| `scripts/gate_a.py` | Exit 0; 2/2 structural steps green before and after report creation | Canonical links, frontmatter/fleet contracts and generated parity |
| Three malformed dashboard inputs passed to the unmodified helper in a temporary directory | Each exit 1 with traceback | Reproduces GF-01; expected uncheckable contract is exit 2 |
| Shipped collection test called with a controlled client that ignores `limit` | Assertion passes on its one-item collection | Reproduces BE-01's false-negative condition; no application behavior inferred |
| Snapshot hash comparison, report link/ID checks, and `git diff --check` | No source hash changes, broken local links, duplicate finding IDs, or diff whitespace errors | Reviewed bundle/support bytes preserved; report has 10 confirmed items and 20 recommendations |

Total existing checks: **458 tests passed and 98 subtests passed**. Backend tests emitted one dependency deprecation warning concerning AnyIO's `BlockingPortal` alias; it did not fail a check. Green structural and unit checks did not detect all prose defects and do not establish live correctness. No new tests were committed or added to the product tree.

## Suggested review order and retention

First consider FE-01, GC-02, GC-03, GC-05, II-01, and II-02: they change an operational recommendation or interpretation. Then handle the Low confirmed items AA-01, BE-01, GF-01, and II-03. Choose completeness improvements separately, especially FE-02 and GC-01. Prose consolidation should follow the accepted correctness decisions, with unique-rule preservation and byte deltas.

Each accepted repair should refresh the cited current lines, change the canonical source, regenerate projections when applicable, and run the smallest relevant verification. An optional recommendation may be declined with a reason. Do not report any item closed from this report alone.

This packet is retained by `SKILL-REVIEW-010` in the live roadmap until the owner dispositions its findings. It is evidence, not a second backlog. No fix, commit, push, remote run, or deployment was performed as part of this review.
