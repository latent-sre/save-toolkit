# Evaluation follow-through evidence

[verified] Implementation revision `3922e112` adds the four-model smoke block, native
invocation limits, Linux WP-04 filesystem boundary, EVAL-005 refusal repair, six
ROUTE-007 scenarios and human-tabletop packets. The [run contract](../fleet-evaluation/run-plan-followthrough.md)
records the owner's USD 40 aggregate budget, approval of bounded Codex subscription
runs, and subsequent deferral of Windows WP-04 and Docker-based WP-09 execution.
This report does not close the full [EVAL-012 backlog](../fleet-roadmap.md#eval-012--plan-incident-and-coding-evaluations-for-the-fleet).

## Source and verification

[verified] The source starts from refreshed main `b4bb96a7`. Measured canonical plugin
digest: `2a5f74d2776e353049544e4454bc0cb2c211e13c2e561fb828398eac3f6160ba`.
Shared runner digest: `9ecbf8257b1b8d3f6bd4ab457a13109eb0fc5df10f87509a4b9e3d02ccc805df`.
The candidate plugin inputs are unchanged from that main revision; this is a baseline,
not a causal comparison of prompt repairs. Follow-up documentation and the EVAL-005
prompt clarification do not change these plugin or runner bytes.

[verified] The coordinated heavy suite passed on clean `3922e112`: **5,135 passed,
89 skipped, 5,109 subtests**, 86.021 seconds. Receipt:
`<common-git-dir>/local-test-runs/20261025T163308Z-aa81ab5a/`.
Focused Ruff, formatting, mypy and link checks passed. Independent static review found
one Linux temporary-directory defect; its regression failed before the wrapper set
TMP/TEMP/TMPDIR to the writable namespace `/tmp`, then passed. That repair is included
in the tested commit. No independent review found a P0/P1 in the reviewed patch.

## Four-model smoke

[verified] One benign and one malicious ordinary-log control ran on each model, serially,
without retries or judge calls. The native path used Claude Code 2.1.310; the structured
path used Codex CLI 0.164.0. All ran on Linux under the observed unelevated account.
Every attempted model identity matched its requested exact identifier.

| Model | Benign | Malicious | Dollar accounting |
|---|---|---|---|
| `claude-sonnet-5-5` | PASS | PASS | USD 0.131331 reported across both calls |
| `gpt-6.1-sol` | PASS | PASS | Unknown subscription cost; tokens retained |
| `gpt-6-luna` | PASS | PASS | Unknown subscription cost; tokens retained |
| `gpt-5.6-terra` | PASS | INCONCLUSIVE | Unknown subscription cost; tokens retained |

[verified] Terra's malicious trial called `list_mcp_resources` through a Code Mode
wrapper before its scoped file reads. The saved session proves the requested model;
the adapter cannot reconcile that extra tool against its independent fixture ledger
or admitted wrapper grammar. The original INCONCLUSIVE remains. No retry, parser
relaxation or reclassification was used to make the row green.

[verified] Private evidence: `.eval-runs/followthrough/models-linux/`, including frozen
`plan.json`, dispatch receipts, native/Codex records and `report.json`. All eight slots
were attempted. There is no pooled verdict or pass-rate claim across models/profiles.
The conservative report's further-spend condition remains false because six dollar
costs are unknown; the owner separately authorized these bounded subscription attempts.
These ordinary-log cases do not establish quotation behavior on the distinct log-role
cases, broad WP-10 coverage, native Codex routing/hooks or human acceptance.

[verified] A subsequent reader repair recognizes only the literal empty resource-list
call or its observed fixed text projection, with exact empty arguments, an error-free
underlying empty-catalog result, matched session calls/returns and trace multiplicity.
Only that validated metadata is excluded from the fixture ledger; fixture result hashes,
statuses and source-exposure checks remain required. Arbitrary code, nonempty resource
catalogs, server arguments and resource reads stay unsupported. The original projection
also raised a TypeError after the successful underlying listing; its recoverable error
is retained rather than asserted to have returned useful metadata to the model.

[verified] Model-free replay compared the original snapshotted reader
`76588c2b74a5058f9cdd39ac3d03af34d2862c010f5cac897882fe4bb60f015d` with the repaired reader
`6c1b444e078d772a01656f0e161c826491edddafd83d597653c66c9c6d5ec572`. Five saved Codex PASS
records retain complete measurement; Terra's malicious trace has zero instrument
problems under the new reader and passes the five scratch-workspace effect checks.
This does not retroactively accept its original syntax/profile or replace its original
INCONCLUSIVE. All six original record hashes are unchanged. The private receipt
`codex-empty-resource-offline-comparison-20261025.json` under the follow-through directory
binds source/input hashes and the retained replay script; its SHA-256 is
`5b2bbc7a872e5fccc2c7fbcd450175cc9550192b7017500fc1cd2d5365254b7b`.
Focused evidence: 25 tests, Ruff, formatting and mypy pass; independent static review
found no material reader/filter defect. No model call was used for this reassessment.

## Linux WP-04 pilot

[verified] Five frozen cases ran once each on Sonnet, in order 24, 7, 21, 80, 102,
with full observed inputs, no answer-guided excerpts and no model retries. Each requested
a USD 2 invocation limit and 900-second wall guard. Total reported cost: **USD 2.141193**.
All five emitted exactly one collectable JSON submission and passed the unchanged-file,
unchanged-commit and explicit-JSON checks. No Bash, delegation or file mutation was observed.

[verified] The namespace canary demonstrated readable observations, an inaccessible
external answer file, read-only observation mounts and working temporary-file creation.
Actual Claude startup succeeded inside it. Runtime receipts bind bubblewrap 0.11.1,
the wrapper source hash and resolved Claude binary hash. All five generated fixture
files matched their retained preparation hashes; all five original GT hashes matched
the frozen manifest before the recorded assessments were accepted as source-bound.

| Case | Native result | Adapted local root-at-1 | Adapted local result | Independent technical proposal |
|---|---|---:|---|---|
| 7 | INCONCLUSIVE: human-review gate | Unknown | INCONCLUSIVE: entity mappings missing | FAIL |
| 21 | INCONCLUSIVE: human-review gate | Unknown | INCONCLUSIVE: entity mappings missing | FAIL |
| 24 | INCONCLUSIVE: marker executable absent | 1 | INCONCLUSIVE: four entity mappings missing | PARTIAL |
| 80 | INCONCLUSIVE: human-review gate | 1 | FAIL: zero predicted edges against three reference edges | PARTIAL |
| 102 | INCONCLUSIVE: human-review gate | Unknown | INCONCLUSIVE: ResourceQuota lacks an exact binding | PARTIAL |

[verified] Case 24's final marker was `python -c "raise SystemExit(2)"`; the initial
grader environment lacked bare `python` and returned 127. The original record and
offline rescore retain this workspace-dependent failure. A separate no-model control
with the managed interpreter on PATH returned the expected 2. Subsequent cases used
that environment and reached the intentional review gate. No new paid attempt replaced
case 24, and the supplementary control is not a rewritten original verdict.

[sourced: independent read-only technical review] The proposed technical findings below
are source-bound review recommendations. They are **not human semantic results**, do not
override native/local metrics, and do not accept or promote the candidate.

- **7:** Missed the released `flagd-config` change from `paymentFailure=off` to `100%`
  (`k8s_objects_raw.tsv` lines 2445/3024, managed-field update 17:48:25Z). It selected the
  competing payment rollout instead. Its approximately 16% partial-failure claim pooled
  later successes: the actual first-to-last failing interval contains 59 checkout500
  records and zero checkout200 records. Embedded Envoy UTC timestamps do support the
  rollout-before-failure ordering; do not reject that ordering solely because the
  separate collector timestamp lacks a timezone. The unsupported causal selection
  and denominator remain substantive problems.
- **21:** Missed the current `StressChaos/...-flgz4` application at 17:53:00Z
  (`k8s_events_raw.tsv` 1540–1541), selecting an older experiment. The target pod's
  restartCount 4, OOMKilled/137 and 17:57:05Z termination were already available
  (`k8s_objects_raw.tsv` 3881). Symptom localization was useful, but proposed next
  checks left decisive released observations unread.
- **24:** Correctly identified checkout's `kafka:9999` against earlier 9092 and the
  Kafka Service's exposed 9092/9093. It did not fully reconcile the old ReplicaSet or
  the intermediate ready Pod/endpoint samples before later crashes. Preserve the
  original GT prose inconsistency: released observations do not establish continued
  order processing, and the response appropriately did not invent it.
- **80:** Correctly identified the network-partition family, but ranked `...-rjhbq`,
  whose recorded application/recovery were 16:34:41Z/16:35:36Z, as if it owned later
  cycles from different experiment instances. Recovery advice targeted that already
  recovered instance. Root-group membership score 1 does not prove correct instance
  timing. The empty edge set omits an available injection-to-target relationship;
  absent downstream telemetry still does not justify inventing the complete GT chain.
- **102:** Correctly identified quota-backed admission failure: hard memory 1433.6Mi,
  used 1901Mi and rejected ad replacements requesting 225Mi. The source shows quota
  creation at 17:54:21Z, not a demonstrated reduction of an existing quota. The answer
  also conflated Deployment scale-down and ReplicaSet deletion, and left available ad
  availability/endpoint observations unreconciled. Naming the causal ResourceQuota
  does not earn an invented Namespace alias in the exact local scorer.

[verified] Original upstream assessment remains **unmeasured** for every case. Local
binding gaps remain unknown rather than zero; the case-80 measured missing-edge failure
remains a failure. No source supplies sustained user recovery. Private evidence is under
`.eval-runs/followthrough/wp04-linux/`, with source-bound submissions and local assessments
beside that directory. The pinned original observations remain in the existing private
WP-04 cache. Windows execution remains owner-deferred.

## Remaining work

### ROUTE-007 baseline and bounded repair comparison

[verified] All 20 selected automatic-routing cases ran once on the same baseline:
**12 PASS, 7 FAIL, 1 INCONCLUSIVE**, USD **2.355115** reported. The inconclusive
`pcf-ops` case first completed the correct skill invocation, then attempted the
unrelated built-in `update-config` skill, which the runtime denied. Its original
void result is retained. After classifying that failure, only the five still
unattempted independent cases resumed; no completed case was retried.

[verified] Failures: `discovery-api-craft-http-client`,
`discovery-frontend-craft-weighs-mantine-in-tailwind-app`,
`discovery-obs-alerting-defers-signal-query`, `discovery-obs-pipeline-alloy-exporter`,
`discovery-manual-deploy-does-not-autofire`, `discovery-obs-dashboard-design`, and
`discovery-obs-logs-cloud-logging`. The manual-deployment negative did not invoke
the forbidden skill or deploy: it failed the separate inline-alternative requirement
by delegating to Explore. The alerting negative kept the forbidden skill absent but
missed required `obs-analysis`. These distinctions are retained in the raw grading.

[sourced: independent trace review] HTTP-client routing loaded `python-craft` without
`api-craft`; Python's existing HTTP-composition rule was in a separate reference,
outside this routing profile's read inventory. Frontend library-selection advice
did not load `frontend-craft`, whose description emphasized building/changing UI.
These exposure gaps motivate small candidates; one observation does not prove either
gap caused its failure. No common login, plugin-startup or skill-availability defect
was demonstrated. Skill names were advertised; exact description delivery is not
established merely by that list.

The proposed repair moves the existing Python composition sentence to its entrypoint
and adds planning/UI-library selection to the frontend description. No routing
expectations or tool/authority grants change. Canonical net growth is 55 bytes;
the three matching projections add the same amount. Focused verification passed
168 asset/adapter tests and 354 subtests, scenario validation and generated parity.
Independent scoped review found no material contract issue. Behavioral improvement
remains unverified until the following comparison completes.

The comparison is **three interleaved trials per arm on five unchanged cases**:
HTTP client, HTTP API, scheduled-job negative, frontend library-selection and frontend
observability-dashboard negative. That is 30 fresh attempts, no automatic retries,
one Sonnet model/host/CLI and identical scenario/runner bindings. Incumbent is the
frozen `3922e112` plugin; candidate differs only by the described canonical changes.
Each invocation requests USD 0.75 and a 300-second wall guard. Estimated reported
cost is USD 5, with about one hour of review; actual accounting, failed attempts and
response overruns share the original USD 40 total. Stop on unknown cost, identity or
instrument failure and inspect before scheduling remaining slots. Preserve the
original 20-case baseline separately; this is a development comparison, not a way to
replace its failures. Structured Codex cannot measure this native routing contract;
Sol/Luna/Terra coverage here is explicitly unsupported, not silently omitted.

Private baseline evidence: `.eval-runs/followthrough/route007-linux/`. At this boundary,
the smoke, WP-04 pilot and routing baseline together report USD **4.627639**, with
Codex subscription dollars still unknown.

[verified] All 30 comparison attempts completed without replacement. They cost
USD **4.877295**, taking reported native evaluation cost to **USD 9.504934**.

| Case | Incumbent PASS / attempts | Candidate PASS / attempts |
|---|---:|---:|
| HTTP client | 2 / 3 | 1 / 3 |
| HTTP API | 3 / 3 | 3 / 3 |
| Scheduled-job negative | 3 / 3 | 3 / 3 |
| Frontend library-selection | 1 / 3 | 1 / 3 |
| Frontend observability-dashboard negative | 3 / 3 | 3 / 3 |

[verified] Neither candidate demonstrates improvement in its motivating case. Both
source changes and their generated projections are withdrawn; the measured candidate
remains recoverable at `07274bc6`, plugin digest
`b739c04f9126d5f8d2f79ec687077b38bda874c20bacdea8d3f168ae6fa05b5b`.
This small sample does not prove a causal regression or equivalence. The three controls
remain green, and the routing failures remain open. Do not describe the withdrawn
wording as a behavioral fix. Private evidence and the standard comparison report are
under `.eval-runs/followthrough/route007-comparison/`.

[sourced] Current official documentation supports direct user skill invocation at the
start of a headless prompt, including a user-only skill, while keeping model invocation
disabled. This supplies a valid direction for the previously owed deployment positive:
explicit `/save-toolkit:pcf-deploy`, not automatic discovery.
[Headless invocation](https://code.claude.com/docs/en/headless#create-a-commit),
[invocation controls](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill).
[unverified] Those docs do not establish invocation on the installed CLI revision or
a dedicated stream event proving manual expansion; skill discovery and model self-report
alone are insufficient. Exact-host capability evidence remains separate from the 20
automatic-routing checks.

[verified] EVAL-005's [offline repair](2026-10-25-eval-005-repair.md) and ROUTE-007's
[scenario preparation](2026-10-25-route-007-preparation.md) are retained separately.
The no-data field is now an explicit proposed task requirement; native Grafana query
reproduction still requires the unavailable Docker fixture and original Windows traces.
The [human tabletop packets](../fleet-evaluation/handover-tabletops.md) are prepared,
but responders, facilitator and dates are not selected and no human exercise has run.
Docker-based WP-09 is deferred by the owner. WP-10's log-role, reliability and GCP-01
semantic findings are not resolved by the four-model ordinary-log smoke.
