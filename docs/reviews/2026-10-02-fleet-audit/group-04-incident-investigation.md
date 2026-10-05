# Group 04 — incident-investigation

Reviewed 2026-10-02 against canonical baseline `a2d2e57d2de70125dbde002072853e73b788bd8d` in `F:\repos\sre-agents-audit-20261002`. Invoking caller: `/root`; human owner: the user. Assignment: six read-only passes on the incident-advisor bundle and its direct consumer/evaluation contracts. The parent audit remains all skills, then agents, committed three assets at a time.

**Verdict: suitable for the team's human-led workflow, with one confirmed diagnostic correctness defect and an existing native-acceptance gap.** The load-balancer/application timing shortcut overstates where elapsed time occurred. Most other examined rules preserve uncertainty, ownership, existing coordination, and action reconciliation well. Green structural checks do not settle the roadmap's outstanding decision-quality acceptance.

## Scope and evidence contract

[verified] Read all seven bundle files: the entrypoint; `references/{helper-exchange,mitigation-selection,signal-patterns,symptom-investigation,systemic-analysis}.md`; and `assets/closeout-packet.md`. Read relevant `sre-assistant` dispatch/return passages, the shared incident fast path, the complete board oracle and its tests, the companion semantic rubric and positive/negative calibration examples, direct companion/bridge/TLC/timezone/intake/native-resume scenarios, and current roadmap incident entries. No canonical files changed relative to the frozen baseline in the scoped diff.

Requirements: keep incident advice with the responder, existing coordination with its human owner, live effects with authorized humans/automation, evidence scoped to its source/time, and each next check useful under available access. Source inspection establishes the written contract; external documentation establishes selected vendor timing/deployment semantics. No real incident, platform call, credential read, installation, or paid/native evaluation was performed.

## Pass 1 — suitability, routing, and continuity

[verified] `SKILL.md:4-13,19-23` targets a human responder who needs interpretation and next-step advice, while excluding delegated lookups, incident command, stakeholder communication, and postmortem authoring. `:101-109` preserves an existing bridge/TLC and sends paging requests through ITO; it does not make the responder start another channel or take command. The unknown lead's name is not made a prerequisite for advice.

The helper remains a bounded investigative partner. `SKILL.md:249-266` requires a concrete question, target/source, completion condition, and relevant time window. `helper-exchange.md:12-39` distinguishes invoking caller from human owner, lookup from investigation, partial evidence from complete results, and acknowledgment from delivery. The reciprocal `agents/sre-assistant.md:10-44,117-132` keeps the same boundary and lets a causal assignment interpret evidence without importing the advisor's whole workflow.

The skill can explain an operational signal outside a live incident and omit the board when no problem is being worked (`:114-117`). That exception is important for usability. Active-incident novice explanations keep the board but should not be displaced by a full report, which the semantic rubric explicitly tests. No role split or new coordination artifact is needed.

## Pass 2 — correctness and source currency

The diagnostic method is generally cautious: comparable affected/unaffected paths, unexplained stages, absent telemetry, request mix, and multiple simultaneous failures are not promoted into causes. `signal-patterns.md:42-45` correctly treats a sampled connection wait as a momentary observation until pool counts and duration support more. `systemic-analysis.md:17-23,37-39` distinguishes an initiating trigger from a mechanism sustaining harm and requires affected-population recovery.

The exception is `signal-patterns.md:46-47`: larger load-balancer timing than container-log timing is declared time outside the container. Different timing boundaries do not support that localization (II-01).

[sourced] Current official Cloud Foundry pages support the important restart/rollback distinctions. The v8 restart reference, explicitly generated from v8.0.0, documents downtime for plain restart and staging when the latest package is unstaged. The revisions guide explains rollback as a new revision carrying earlier code/configuration; the cancel-deployment reference resets to the previous deployment's droplet. GitHits independently read `cloudfoundry/cli@49cf1226`, `command/v7/rollback_command.go:84-140`: rollback defaults to rolling and creates a new revision. Preserve the explicit target CLI/foundation uncertainty in `mitigation-selection.md:23-34,48-61`.

The Apps Manager navigation source is an identified 2023/TAS 2.12 manual, not evidence about today's foundation. The reference already labels that limitation. No target UI, revision support, package state, routes, serving capacity, or restart behavior was tested.

## Pass 3 — workflow, mitigation, trust, and recovery

[verified] The six-step response order gives immediate guidance before complete intake while keeping mutation advice in a separate step (`SKILL.md:65-110`). A next-check branch selects another check or decision, rather than sneaking a change into an if/then diagnostic. Missing or stale knowledge becomes a follow-up, not a reason to stop. Historical postmortems are candidate evidence and runbooks are recommendations, not permissions (`:52-56,189-206`).

Mitigation preserves the useful speed/safety distinction. `mitigation-selection.md:65-98` permits a named human to forgo unavailable diagnostics for an otherwise approved reversible action, while retaining target/artifact/approval/recovery requirements and separate security/destructive rules. It distinguishes a current readback from an executor receipt and preserves UNKNOWN until reconciliation. A successful read cannot manufacture the time an interrupted rollback applied.

Handover asks for receiver read-back and acknowledgment; preparation alone is not acceptance (`SKILL.md:281-285`). The closeout packet keeps impact-end time separate from the later human resolution call and does not erase unresolved effects or causes. Its UTC receiving fields coexist with Eastern conversation display, retaining unknown unzoned timestamps. The dated timezone fixture covers winter/summer offsets, a midnight date change, DST's repeated hour, and approval expiry.

The board is the advisor's retained investigation state, not authority to replace the bridge's coordination record. ITO paging, human resolution, human change execution, and the seven-field board are team policy choices. This audit does not recommend weakening them.

## Pass 4 — LLM readability and context cost

[verified] The complete bundle is 57,244 bytes/8,736 whitespace-delimited words. The entrypoint is 21,691 bytes/3,521 words. These are file/word measurements, not token counts. Conditional references are useful, but routine interpretation requires the entrypoint plus signal patterns; mitigation and helper work add substantial further context.

The clearest readability strength is one coherent flow and one retained board. Preserve the plain-language explanation, evidence-for/against, inconclusive branches, and no-repeat guidance. Do not replace them with a generic incident checklist or add a parallel action ledger. The detailed mitigation table has a high context cost, but much of it prevents real restart/restage/rollback mistakes; treat each deletion as a hypothesis to test, not an automatic improvement.

Two bounded improvements are possible: qualify II-01 in place rather than adding a new timing framework, and label the short symptom conversations as diagnostic excerpts (II-R01). The existing board, knowledge, and handoff rules need no broad rewrite. The old entrypoint byte measurement in `docs/fleet-roadmap.md:190-199` is explicitly tied to `ed321035`; it is not a current size claim or proof that length causes quality problems.

## Pass 5 — verification, semantic oracles, and historical acceptance

[verified] This skill has substantive behavioral specification coverage. Companion scenarios pair `incident_board` with the case-specific semantic rubric. The rubric (`evals/rubrics.yaml:3-114`) rejects invented observations, unsupported causal conclusions, repetition of unavailable reads, false recovery, UNKNOWN retries, ownership transfer, and reopening a duplicate bridge. Positive/negative calibration examples deliberately contrast similar plausible answers with one consequential error. These assess decisions beyond headings.

The board oracle (`evals/oracles/incident-closing-fields/probe_closing_fields.py:6-20,105-169`) honestly grades structure, not truth. Tests cover missing/empty fields, examples, nonterminal boards, legacy forms, and shipped helper/handover examples. Its complete all-unknown fixture is valid structural input; that alone is not a defect because semantic assessment is separate. Shared AA-01 reference-identity and EL-01 exact-fields weaknesses are not duplicated here.

The native helper scenario now includes the complete board grader and a closeout rubric (`native-incident-helper-return-and-resume.yaml:53-64`). It verifies actual same-session return/resume mechanics structurally, while naming manual review and the hinted helper request as limits. The existing-TLC case is a pasted conversation snapshot, not native continuity evidence (`evals/README.md:532-536`).

[verified: centralized execution] The centralized offline baseline passed 1,470 tests and 2,690 subtests, with 19 skips; 192 specs and 737 expectations validated. No suite was repeated here. Current `INCIDENT-QUALITY-001` explicitly keeps behavioral acceptance on hold after historical failed samples and a failed 24-session campaign (`docs/fleet-roadmap.md:90-116`). `SKILL-001` and `EVAL-007` retain context/closure decisions. These are current backlog statements about dated measurements, not fresh failures of this exact source. No new campaign was authorized or run.

## Pass 6 — adversarial cases and findings

| Counterexample | Contract result and evidence |
|---|---|
| An existing TLC has an unnamed lead | Continue on that TLC; do not require command setup; covered by semantic case and supplied-state scenario |
| Helper says no crashes over 09:40–10:10 but only read 10:00–10:10 | Preserve the uncovered interval and reject claimed cause; directly covered |
| Rollback description matches but deployment is still mixed | Current desired state is unproved; reconcile before retry; covered in calibration |
| Logs are empty, instances running, and pool graph absent | Neither healthy application nor healthy pool follows; covered |
| Corrected output/delivery evidence and human resolution arrive, cause unknown | Accept sufficient recovery, prohibit unnecessary resend, retain an owned cause gap; native follow-up specification covers this |
| A runbook or pasted helper packet asks for live execution | Treat it as data; preserve the applying actor and gate |
| Proxy sees 2,010 ms while handler-only log sees 10 ms, with 2,000 ms queued in the container | The outside-container conclusion is false; II-01 |

### II-01 — A timing difference is incorrectly localized outside the container

**Category:** confirmed diagnostic correctness defect. **Severity:** Medium. **Confidence:** High. **Location:** `skills/incident-investigation/references/signal-patterns.md:46-47`.

**Trigger:** a responder compares the load balancer's total request duration with an application/container log timer that covers only handler work. A concrete counterexample is the same request waiting 2,000 ms inside the application server before a 10 ms handler runs; the proxy observes roughly 2,010 ms and the handler log records 10 ms. The written condition holds, but the missing time is inside the container. Different requests, retries, streaming bodies, or unmatched aggregation windows introduce further ambiguity.

**Consequence:** the advisor may clear application/server queueing prematurely and send the responder toward the load-balancer/network owner. The reference's general “none is a diagnosis” introduction does not make this specific categorical localization technically valid.

**Evidence:** direct source plus a deterministic timing counterexample, not an observed incident/model failure. NGINX's primary log documentation defines a broad request interval from client read through response completion. OpenTelemetry's official conventions likewise document timing-boundary variation and the need for instrumentation to document what its duration includes. No source guarantees that arbitrary container log timers cover the full container residence time.

**Smallest fix:** replace the sentence with “This exposes an unexplained interval; correlate the same request and confirm both timers' boundaries, then compare arrival/queue, handler, and response timings before assigning the delay outside the app.” Preserve outside-app delay as a candidate, not a proven location.

**Verification:** add a supplied-evidence case with the queue/handler counterexample and one with missing timer definitions. The answer must retain application queueing and request correlation as open, request the missing boundary evidence, and avoid assigning sole network blame. Calibrate a wrong outside-container conclusion to fail before any bounded model trial. No live platform reproduction is necessary to demonstrate the statement's logical error.

### II-R01 — Identify abbreviated symptom dialogues as excerpts

**Category:** optional LLM-readability recommendation. **Priority:** Low. **Confidence:** High on the textual ambiguity; model impact unverified. **Locations:** `references/symptom-investigation.md:34-59`; `SKILL.md:114-121`; `evals/test_closing_fields_oracle.py:215-234`.

**Trigger/consequence:** the symptom reference presents `Human`/`Advisor` replies without a board, while active-problem replies require one. They are useful teaching excerpts, but unlike the calibration documentation their abbreviated nature is not explicit. A model may imitate them as complete replies. This is not a confirmed native failure.

**Smallest improvement:** add one short label identifying these as diagnostic-body excerpts that use the parent's board when a problem is active. Do not duplicate seven-field boards throughout the examples. **Verification:** inspect the label and retain the existing structural example tests; if changing actual reply behavior, use a bounded symptom follow-up case that verifies both concise advice and complete retained state.

### II-G01 — Native decision-quality acceptance remains open

**Category:** existing runtime/acceptance gap. **Priority:** Medium. **Confidence:** High. **Locations:** `docs/fleet-roadmap.md:90-116,178-189,415`; native scenario `:54-59`; `evals/README.md:520-536`.

**Impact:** neither this audit nor the passing offline suite proves useful advice under actual helper handoff, long conversation, time pressure, missing access, and corrected recovery evidence. **Smallest next action:** reuse the existing roadmap item rather than creating a duplicate backlog. The maintainer selects the exact repaired candidate, host/model, and bounded budget; preserve failed cases and manual trace assessment. Include timing-boundary discrimination from II-01. Pending evaluation choices do not authorize spending or live operations.

## External evidence and return

Sources checked 2026-10-02: Context7 [Cloud Foundry revisions](https://docs.cloudfoundry.org/devguide/revisions.html) and [OpenTelemetry HTTP span semantics](https://opentelemetry.io/docs/specs/semconv/http/http-spans/); official [CF v8 restart](https://cli.cloudfoundry.org/en-US/v8/restart.html), [cancel-deployment](https://cli.cloudfoundry.org/en-US/v8/cancel-deployment.html), and [NGINX log timer definition](https://nginx.org/en/docs/http/ngx_http_log_module.html#log_format); GitHits [rollback implementation at 49cf1226](https://github.com/cloudfoundry/cli/blob/49cf1226/command/v7/rollback_command.go). A separate GitHits OpenTelemetry source preparation timed out; the documented contract came from Context7, not a completed upstream code read.

Recipient: `/root`. Assignment complete; only this UTF-8 scratch report was written. Caller next step: reconcile II-01 and the recommendations with the group, attach the centralized verification boundary, commit group 04's findings, and continue the parent audit. No repair, incident action, model acceptance claim, or promotion was performed.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
