# PCF operations skill audit

[verified] Target: `skills/pcf-ops/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. One P3 source/API finding is confirmed. Specification and engineering-quality verdicts: partial. The static triage contract is coherent; the resize recipe conflicts with the implementation at its advertised minimum, while live runtime adherence remains unverified.

## P3 — AUDIT-PCF-001: existing-droplet resize uses unsupported deployment options

[verified] `skills/pcf-ops/references/state-changing-effects.md`, lines 22–27, proposes an existing-droplet POST to `/v3/deployments` with `options.memory_in_mb` and `options.disk_in_mb`, claiming capi-release 1.205.0+ support. [verified] The coordinator read the public [1.205.0 gitlink metadata](https://api.github.com/repos/cloudfoundry/capi-release/contents/src/cloud_controller_ng?ref=1.205.0), binding its controller to `8d3cedf014719550e56bbf4ba1804d054d1df24b`. [sourced] That exact controller's [allowed options](https://github.com/cloudfoundry/cloud_controller_ng/blob/8d3cedf014719550e56bbf4ba1804d054d1df24b/app/messages/deployment_create_message.rb#L13-L17) contain only `canary`, `max_in_flight` and `web_instances`; [validation](https://github.com/cloudfoundry/cloud_controller_ng/blob/8d3cedf014719550e56bbf4ba1804d054d1df24b/app/messages/deployment_create_message.rb#L59-L68) rejects additional keys. The supplied resize payload would therefore fail validation at the stated minimum.

Trigger: following this recipe on that supported-by-guidance release. Impact: the promised resize cannot be performed through the supplied API body. Confidence is high in the bound source mismatch; no API request or production failure was observed. Counterevidence: the reference marks target behavior unconfirmed, and the gate requires human execution and verification; the failure occurs during validation rather than proving a disruptive partial resize. Correct or withdraw the payload/version claim until an actual supported existing-droplet procedure is established. Do not silently replace it with `cf push`, which may stage new bytes and has different authorization requirements.

[sourced] Other public checks support the qualified [health-check defaults](https://docs.cloudfoundry.org/devguide/deploy-apps/healthchecks.html), [Gorouter error behavior](https://docs.cloudfoundry.org/adminguide/troubleshooting-router-error-responses.html) and [Java memory accounting](https://github.com/cloudfoundry/java-buildpack/blob/v4.77.0/config/open_jdk_jre.yml#L27-L33). Startup 60/180 seconds and crash backoff are configurable defaults. Router idle-connection timeout is not a request deadline; 137 is not OOM proof. The calculator's 250 threads are an accounting assumption, not a JVM thread limit; `-Xss` remains a supported input. Deployed component revisions were not checked.

## Contract assessment

[verified] Apps Manager comes first, with bounded CLI equivalents. Foundation/org/space confirmation precedes app reads; protected output must exist before even raw `cf target`. Inventory placeholders cannot supply trusted target identity. Authentication/access gaps cannot become platform observations. The five allowed CF command forms match `_cf_allowed`; singular revision, inventory, streaming and state changes stay outside the SRE grant. Caller instructions independently retain masking and credential prohibitions.

[verified] Recent records require actual covered intervals and explicit history gaps. A bare 137 does not prove OOM, running instances do not prove successful requests, and broad impact does not by itself prove a platform defect. Router status requires header/context evidence; agents cannot turn an untrusted route into an egress request. Escalation asks for bounded evidence and open hypotheses without demanding cause certainty first.

[verified] Change effects and incident/deployment ownership agree with the already-reviewed PCF deploy/gate contracts: human execution, exact approval and existing-droplet classification are required; staging/new artifacts retain full gates; memory/disk/log-rate scaling may stop the whole app. JVM guidance distinguishes heap/native/pool/thread causes and avoids inferring the failed pool from a container OOM alone. Health-check examples remain proposals with target behavior unconfirmed.

## Evidence coverage

| Risk | Evidence | Result |
|---|---|---|
| Accidental credential output or wrong target | Entrypoint, foundations reference, SRE caller and guard | [verified] Explicit preconditions; syntax guard does not enforce masking/identity |
| Unsafe inference from exit/status/recent logs | Full crash/router references and entrypoint | [verified] Alternative causes and coverage limits retained |
| State-changing triage or platform overreach | Effect reference and caller/skill boundaries | [verified] Human execution, application scope and escalation preserved |
| Host/model adherence and current foundation behavior | No connected target or new live evaluation | [unverified] Not established by prose or existing component tests |

## Read manifest and checks

[verified] Full canonical reads: `SKILL.md`; `references/application-crashes-and-health-checks.md`, `router-errors.md`, `foundations.md`, `state-changing-effects.md` (five files, 372 lines). Full supporting read: `evals/scenarios/discovery-gcp-ops-defers-pcf.yaml`. Bounded supporting reads: `agents/sre-assistant.md` 160–225; `scripts/readonly-guard.py` 838–865 and 920–970; CF guard-test and scenario inventory searches. Shared PCF deploy, gate/fast-path and stack-profile source reads from earlier items are reused, not represented as fresh runtime evidence.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py pcf-ops` exited 0: bundle links resolve, four reference projections match byte for byte, source diff against target is empty. `diff -u` shows only the generated namespaced-to-bare PCF deploy invocation in the entrypoint. Existing unchanged-source test evidence is reused; no redundant broad test run occurred. Independent evaluation/public support is coordinated by the root reviewer and must be read with its stated scope.

[verified] Only this report changed for this item. No canonical/test/configuration changes, installs, live reads, model calls, deployments, commits, pushes or repairs occurred. Human acceptance and host-specific assurance remain separate.

[sourced] Root's independent evaluation pass fully read `discovery-sre-assistant-dispatched-read`, `agent-direct-sre-assistant-dispatch-coverage`, `discovery-gcp-ops-defers-pcf` and the restart/restage-classification build scenario; bounded reads covered guard tests 664–722 and roadmap SRE-CF-001 (80–105). Known-payload guard tests mechanically check accepted forms/negative flags. Supplied-record scenarios reject target changes, raw authentication output and overclaimed historical coverage without native execution. Six restart proposals distinguish existing staged droplet/headroom from new artifact, unknown state and plain restart. No new oracle defect confirmed. SRE-CF-001 host acceptance and ROUTE-007 direct PCF fire/not-fire routing remain known gaps.
