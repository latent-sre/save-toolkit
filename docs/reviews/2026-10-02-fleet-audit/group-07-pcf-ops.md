# Group 07: pcf-ops — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting audit HEAD `593f13aaff951a0db3b3ba617278ad48a5ae3839` contains preceding reports. Initial tree clean; the bundle matched the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. Parent objective remains the six-pass review of skills before agents, three per group, with findings committed before continuing.

**Conclusion:** this is a useful, carefully bounded application-operations skill. Apps Manager and command users receive parallel first checks; target binding, protected output, incomplete history, platform ownership, and human execution are explicit. One confirmed Medium defect remains: JVM sizing guidance categorically excludes correcting an excessive pinned heap, although its own cited calculator rejects that configuration. The appropriate repair is a small diagnostic distinction, not a new platform workflow.

`[verified]` denotes inspected current source or identified local execution; `[sourced]` denotes primary external documentation/upstream evidence; `[unverified]` denotes target/model/runtime facts not established. All five bundle files were read completely: `SKILL.md` and references `application-crashes-and-health-checks.md`, `router-errors.md`, `state-changing-effects.md`, and `foundations.md`. They total 22,948 bytes and approximately 3,205 whitespace-delimited words; the entrypoint accounts for 10,117 bytes and 1,469 words. There are no executable bundle assets. Only this scratch report was written. No target CF/cloud calls, credentials, installations, platform writes, source repairs, or paid/native evaluations occurred.

## Pass 1 — suitability, discovery, and adjacent lanes

**Sources:** complete entrypoint; `references/foundations.md`; `skills/stack-profile/SKILL.md:27-32,45-47,100-104`; `agents/sre-assistant.md:52-64,169-175`; `evals/scenarios/discovery-gcp-ops-defers-pcf.yaml:1-17`.

[verified] The lane matches the team's current operating model: app-side PCF/TAS investigation, with Apps Manager before optional `cf` commands. It does not assume the SRE has a CLI. The ordered target, instance-state, events, and recent-log views answer useful initial questions without pretending to establish the whole incident history. Conditional reference loading covers crashes, health checks, routing, and proposed mutations; the foundation inventory is explicitly a placeholder requiring real target confirmation.

[verified] Foundation components remain platform-team work. One-app versus cross-app impact is a triage clue, not a proof of component ownership or cause (`SKILL.md:59-80`). Incident mitigation choice stays with incident investigation and the human responder; deployment planning routes to the human-invoked PCF deployment workflow (`141-150`). The GCP negative discovery fixture explicitly selects PCF as its alternative. No new routing contradiction was found.

**Gap:** the negative discovery specification and caller references establish intended routing, not current native-host selection or correct behavior across all PCF symptoms. Installed host registrations, real inventory values, CLI access, and target versions remain `[unverified]`.

## Pass 2 — technical correctness and dependencies

**Sources:** all four references; `SKILL.md:48-55,102-137`; current official documentation retrieved through Context7; upstream Java buildpack, its pinned memory calculator, CLI v8.18.4, and Gorouter files retrieved through GitHits.

[sourced] Current Cloud Foundry documentation supports the liveness/readiness distinction: HTTP checks require a successful 200 response; liveness failure restarts an unhealthy instance, while readiness affects route eligibility. Spring Boot documentation supports exposing probe paths on the application port and configuring graceful shutdown per phase. The local warnings against dependency-sensitive liveness and a separate management port masking application-port failure are useful. See [Cloud Foundry health checks](https://docs.cloudfoundry.org/devguide/deploy-apps/healthchecks.html), [Spring Boot actuator endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html), and [graceful shutdown](https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html), checked 2026-10-02.

[sourced] CLI implementation confirms that memory, disk, or log-rate flags trigger application stop/start, including when a process selector is supplied; instance-only scaling avoids that restart branch. Restart stages the newest package when it is unstaged. This validates the unusually important distinctions in `state-changing-effects.md:11-17`: [scale_command.go:129-168,208-209](https://github.com/cloudfoundry/cli/blob/v8.18.4/command/v7/scale_command.go#L129) and [restart_command.go:72-116](https://github.com/cloudfoundry/cli/blob/v8.18.4/command/v7/restart_command.go#L72). GitHits resolved this tag to `3fcd823a`; files remain under `command/v7` despite the v8 module. Official [rolling-deployment guidance](https://docs.cloudfoundry.org/devguide/deploy-apps/rolling-deploy.html) corroborates the distinction between rolling web replacement and bulk non-web restart.

[sourced] Gorouter source supports the named route/no-endpoint/connection-limit discriminators and the 90-second backend idle-connection default: [lookup.go](https://github.com/cloudfoundry/gorouter/blob/a602bb6a/handlers/lookup.go#L163), [proxy.go](https://github.com/cloudfoundry/gorouter/blob/a602bb6a/proxy/proxy.go#L87). The skill correctly treats endpoint failure as insufficient proof that application code received the request. It does not repeat the cross-boundary timing-localization defect recorded as II-01.

[verified/sourced] PCF-01 below is the material contradiction. A separate suspected defect was refuted: upstream buildpack documentation really does describe calculator inputs being logged at staging even though memory sizing runs at startup. Preserve that distinction. The exact target foundation's configuration, Apps Manager restart behavior, buildpack/JDK version, CAPI resize support, and actual rollback binding remain `[unverified]`; current upstream behavior does not establish them.

## Pass 3 — authority, trust, failure, and recovery

**Sources:** `SKILL.md:27-55,68-80,131-157`; `foundations.md`; `state-changing-effects.md:3-5,20-33`; `scripts/readonly-guard.py:546-553,791-806,896-908,1078-1083,1238-1257`; `agents/sre-assistant.md:171-175,209-223`.

[verified] The entrypoint correctly separates command-shape permission from runtime target binding, output masking, and assignment scope. It prohibits raw `cf target` as a way to discover whether masking works. Missing authenticated access leads to Apps Manager or caller-sanitized observations, not credential retrieval or a false platform diagnosis. Revision-list metadata is not promoted into evidence of an earlier droplet/environment; rollback requires a separate authoritative, credential-free record. Singular `cf revision`, credential-bearing commands, SSH, and mutation verbs are outside the five selected SRE reads.

[verified] The parser implements the stated selected forms and rejects target setters, inventory expansion, tails, and unrecognized options for the guarded lane. The fleet credential tripwire is a separate named-path control, not a general command sandbox. This skill accurately describes that scope; do not import the broader wording defect found previously in GP-01.

[verified] Capture-before-restart, escalation without waiting for root cause, and explicit missing evidence protect recovery quality. The mutation reference names whole-app and non-web effects, quota requirements, and deployment locks; all application changes retain the human owner and existing production-change packet. Its source-level examples are planning data, not execution grants.

**Gap:** neither the parser nor these examples prove safe output, correct target, browser enforcement, a functioning installed wrapper, or recoverability on a real foundation. Those dependencies are clearly exposed, so missing deployment evidence is a runtime gap rather than a new defect.

## Pass 4 — LLM readability, contradictions, and context cost

**Sources:** complete bundle, particularly entrypoint first-look table, reference-selection section, access rules, and mutation handoff; crash reference `59-92`.

[verified] The order is operationally useful: orient, establish evidence coverage, gather only permitted observations, identify the relevant failure branch, and escalate with observations and limits. Tables keep console/CLI correspondence and JVM failure categories scannable. The reference split permits symptom-specific reading rather than loading all 3,205 words. The inventory template explicitly keeps repository text from becoming authority.

[verified] PCF-01 shows why a short categorical imperative can override otherwise careful diagnosis: the reader is told to exclude the heap flag immediately after being told that the heap contributes to the failed total. Correct that local contradiction before adding more explanation.

**Deletion-first recommendation PCF-R01 — Low, high confidence:** keep the state-changing-effects table as the detailed effects source. When next editing, shorten repeated explanatory restart prose in the JVM section (`61-70`) to the necessary sizing consequence plus that link. Preserve the entrypoint's execution boundary and whole-app warning because each skill must remain usable on its own. Verify the reduced text still distinguishes instance scaling, resource resizing, rolling web replacement, non-web restart, and restaging. There is no evidence that wholesale restructuring or more mandatory context would improve this asset.

## Pass 5 — verification coverage and oracle quality

**Sources:** `scripts/test_readonly_guard.py:668-712,976-1083,1147-1167`; complete build scenarios `build-sre-assistant-active-incident-guarded-triage.yaml`, `build-sre-assistant-handles-partial-research.yaml`, and `build-sre-assistant-suspected-compromise-preserves-evidence.yaml`; the negative discovery scenario above.

[verified] Guard tests exercise Bash and PowerShell selected CF forms, malformed/expanded reads, credential-path denials, and compatible host grammar. Their subprocess helper checks both the exit code and output contract. These are meaningful positive and negative controls for syntax enforcement, with no claim of authenticated platform coverage.

[verified] The active-incident build fixture checks both the synthetic CF shim's received verbs and attempted mutation commands in the trace (`159-176`). It supplies masked target evidence and uses a rubric for rollback/retry-policy reasoning rather than claiming keywords prove mitigation quality. The partial-research case supplies an injected unverified restart instruction and requires preserved taint plus continued bounded observations (`62-71`). The suspected-compromise case intentionally has no protected CF path and requires no raw CF access, Apps Manager fallback, preservation of state, and human security ownership (`91-110`). These exercise materially different failure paths.

The parent reports a fresh frozen-source offline baseline under Python 3.14.7: **1,470 tests passed, 19 skipped, one warning, 2,690 subtests**, and specification validation of **192 scenarios with 737 expectations**, both exit 0. These results establish executable structural checks and specification validity. They do not show that the native scenarios ran, that a model diagnosed PCF incidents correctly, or that real output was masked. No additional execution was necessary for the source-proven PCF-01.

**Recommendation PCF-R02 — Medium, high confidence:** add small semantic counterexample pairs to the existing scenario family rather than another broad campaign. Require an appropriate evidence gap for bare exit 137; distinguish it from a captured Garden OOM reason; prevent a recent-events window from excluding earlier changes; distinguish generic 502 from `endpoint_failure`; and test both calculator overflow branches. Inspect conclusions and proposed action, not just mentions of 137/OOM or required slot labels. Shared AA-01/EL-01 findings remain separate; no duplicated claim of a new generic grader defect is made here.

## Pass 6 — adversarial challenge and prioritized disposition

The review challenged target confusion, incomplete history, permission failure, untrusted runbook mutation pressure, bare exit 137, readiness/liveness conflation, unstaged-package restart, whole-app resource scaling, non-web rolling effects, and explicit-heap sizing. Existing text provides appropriate boundaries for all except the final categorical exclusion. No live incident, platform canary, or JVM workload was run.

### PCF-01 — guidance excludes correcting an excessive pinned heap

**Confirmed documentation defect; Medium severity; high confidence.** Local evidence: `skills/pcf-ops/references/application-crashes-and-health-checks.md:66-68`, with diagnostic context at `72-84`. Upstream evidence: the exact [pinned calculator implementation](https://github.com/cloudfoundry/java-buildpack-memory-calculator/blob/3d845d8695ed03f1315c5a66582a441c754e3870/calculator/calculator.go#L72), retrieved through GitHits on 2026-10-02, and [Java buildpack JVM sizing documentation](https://github.com/cloudfoundry/java-buildpack/blob/e6ac5c32/docs/jre-open_jdk_jre.md#L122).

**Trigger → consequence:** an application pins a heap that makes total requested JVM memory exceed available container memory. The guidance tells the responder to adjust thread count or container size and explicitly excludes the heap flag. It can therefore steer a recommendation toward needless quota growth or a thread-sizing change while overlooking the actual excessive heap setting. It does not authorize an automated live change; the consequence is a wrong diagnostic/remediation recommendation within a human-owned process.

**Violated contract:** the cited calculator has two relevant branches. Lines 75-78 reject non-heap overhead alone exceeding available memory. Lines 80-89 obtain an explicit maximum heap, or calculate a default, and then reject overhead plus heap exceeding available memory. Reducing heap cannot fix the first branch; correcting an excessive explicit heap can fix the second. The local categorical instruction conflates them.

A constructed arithmetic illustration, **not an executed calculator or JVM test**, makes the distinction visible: with 512 MiB available, 300 MiB non-heap overhead and a pinned 256 MiB heap total 556 MiB and fail the fit check. A 128 MiB heap totals 428 MiB and passes that arithmetic check. Neither this illustration nor upstream source establishes that 128 MiB can serve the actual workload.

**Smallest fix:** replace the exclusion with branch-specific diagnosis. Determine whether fixed non-heap overhead alone exceeds the limit or whether an explicit heap makes the total too large; adjust the responsible estimate/pool/container limit using measured demand and headroom. State that reducing or removing an excessive explicit `-Xmx` is valid only in the latter case. Retain the warning that pinning heap does not bypass the calculator and retain human change authority.

**Verification:** a focused review/evaluation should accept correction of an excessive pinned heap when overhead fits, reject lowering heap as a remedy for overhead-only overflow, and require workload/headroom verification before calling either sizing plan sufficient. Include a valid default-calculated-heap control. Source inspection proves the bounded contradiction; target-specific remediation success remains `[unverified]`.

**Recommendation PCF-R03 — Low, high confidence:** when an actual platform question makes it necessary, record the target's CLI/CAPI/buildpack versions, protected-output path, log coverage, and applicable API capability alongside the existing foundation inventory and handoff. Verify through permitted sanitized evidence. Do not fill placeholders from assumptions or expand the read allowlist. This is an applicability improvement, not a claim that repository documentation can certify a live foundation.

**Disposition/caller next step:** accept or refine PCF-01 within the existing AUDIT-001 findings disposition; no separate live-backlog queue was created. Preserve the positive controls and qualified runtime gaps, assemble this report with the two peer reviews, and commit group 07 before beginning the next group. Product repair and any later native evaluation remain separate from this findings-only audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
