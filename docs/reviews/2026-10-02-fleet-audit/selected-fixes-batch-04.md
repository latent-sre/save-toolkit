# Fourth selected audit repair batch

Date: 2026-10-02. Human owner: the user; integration caller: `/root`.
This record supports `AUDIT-001`; it is not a separate backlog or model-acceptance decision.

## Scope and identity

The user selected **OE-01, RELI-01, DASH-01, PIPE-01/02, TRACE-01/02, CLI-01/02,
RCA-01 and PCF-01**. `RCA-0` was interpreted as the sole RCA finding, RCA-01; the duplicate
TRACE-02 entry was counted once. These eleven repairs bring the selected total to **38 of 50**;
the other **12** confirmed findings and optional recommendations retain their dispositions.

The work continues on `work/fleet-audit-selected-fixes-20261002` in
`F:/repos/sre-agents-audit-fixes-20261002`, based on published commit
`8039063e220d14e1e17b19bf6fb79bd5e82702fa`. A fresh fetch confirmed local/upstream agreement
before edits. The original audit baseline remains `a2d2e57d`; the original dirty checkout and
completed audit checkout are separate. Earlier repair records remain historical:
[first sixteen](selected-fixes.md) and [third batch](selected-fixes-batch-03.md).

## Findings, repairs and evidence boundaries

| Finding | Repair | Discriminating verification |
|---|---|---|
| [OE-01](group-11-observability-engineer.md) | Retain final snapshot equality and separately inspect agent-proxy history for attempts to mutate fixture-forbidden datasource/alert routes. | Rejected, pending, no-op and write/restore attempts fail; item/group/Ruler routes are covered. Read/query/export and allowed dashboard controls pass. Missing/malformed audit evidence is inconclusive. Harness seed/readback traffic is separate. Proxy-bypassing transient writes remain outside the evidence. |
| [RELI-01](group-11-reliability-engineer.md) | Replace a phrase-presence assertion with a probe-owned, bounded three-outcome check: recognized refusal, clear authorization, or manual stance review. | Actual staged helper accepts explicit rejected quotations, rejects clear/adopted grants, and returns an inconclusive result for unknown, contradictory, question or conditional contexts. Clear grants must be complete supported clauses. The independent r8-unknown, no-shell, scope and no-dispatch checks remain. This is a lexical tripwire, not general free-form authority understanding. |
| [DASH-01](group-05-obs-dashboards.md) | Require literal quantile 0.95 on the actual saved-and-queried target; describe the separate panel assertion as shape only. | Correct p95/scientific-spelling controls pass. p50/p99, comments/labels/other-argument decoys, mixed calls and unrelated spare targets cannot supply the credited quantile. Existing GRA-02/03 identity, rate-window and positive-data checks remain. Scalar expressions in the quantile argument are unsupported. |
| [PIPE-01](group-06-obs-pipeline.md) | Correct Telemetry API log ingestion to GA since 2026-08-14; remove the stale duplicate and name its owning skill. | Current official release notes support the date. Alloy Google-auth remains independently public preview; its flag and target-canary requirements remain. Service maturity does not prove a project's route or permissions. |
| [PIPE-02](group-06-obs-pipeline.md) | Replace PowerShell text stdin with an absolute, read-only, single-file bind-mount recipe for a local daemon. Record input hash and preserve isolation. | Original transport changed all eight input fixtures. The revised native argument/file-byte boundary preserves eight of eight across PowerShell 5.1 and 7, including Unicode, LF/CRLF and no final newline. Root repeated the positive transport check independently. Docker mounting/readonly enforcement and Alloy parsing were not exercised. |
| [TRACE-01](group-06-obs-traces.md) | Separate Cloud Run platform traces in Cloud Trace from application instrumentation and its exporter destinations, sampling and metadata. | Source-backed supplied-state review covers platform-only, application-to-Tempo, dual export and missing revision metadata. Backend visibility and model behavior remain unverified. |
| [TRACE-02](group-06-obs-traces.md) | Distinguish recording/processor work, sampled flag, export eligibility and observed receipt. | Official OTel contract and upstream source support `RECORD_ONLY` processing with Sampled=false; a sampled span with failed export still has no established backend receipt. No SDK or backend execution occurred. |
| [CLI-01](group-07-operator-cli.md) | Handle EOF at the confirmation boundary as normal refusal. | Actual copied CLI exits 2 with no cancellation, lock or traceback; yes/no and signal controls retain their behavior. Simulated TTY EOF was exercised, not a physical-terminal keystroke. |
| [CLI-02](group-07-operator-cli.md) | Reserve bare `OrderError` for definitive no-effect rejection; add explicit `OrderOutcomeUnknown` for ambiguous adapter failures and use status readback without replay. | Applied-then-ambiguous success, unavailable readback/UNKNOWN and genuine rejection are distinct. Catch ambiguity before the general error, supporting independent and subclass hierarchies. Real adapters must export/map the documented seam; external cancellation behavior is unverified. |
| [RCA-01](group-09-root-cause.md) | Exercise a named `TimeoutError` subclass in classification, exhaustion and recovery; calibrate an exact-type mutant. | Supported repairs preserve retry counts and exception/return identity. The exact-type mutant passes the unchanged seeded suite but fails the independent oracle. No broader root-cause prompt change. |
| [PCF-01](group-07-pcf-ops.md) | Distinguish non-heap-only overflow from an excessive explicit heap pin; permit correction of the latter while requiring workload/headroom evidence. | Current official sizing guidance and the pinned calculator's two fit checks support the distinction. Supplied arithmetic below illustrates the branches; no JVM, calculator binary or platform change ran. |

For PCF-01, static supplied-state review used three controls: 600 MiB non-heap overhead cannot
fit a 512 MiB limit by lowering heap; 300 MiB overhead plus a pinned 256 MiB heap exceeds 512 MiB,
while a 128 MiB proposal fits that arithmetic; with no explicit heap pin, the calculator allocates
the remaining budget. These are source-based checks, not proof that any proposed heap serves the
workload. A 128 MiB proposal remains insufficient without demand/headroom evidence.

## Failure-first and affected checks

All Python commands use the existing **3.14.7** interpreter at
`F:/repos/sre-agents/.venv/Scripts/python.exe`. Scratch evidence is under
`F:/iso-tmp/fleet-audit-fixes-20261002/batch-04`; no dependency installation or paid model run
was needed.

- OE-01/DASH-01: actual-predicate regressions first produced **64 failures**. The corrected new
  cases passed **7 tests / 72 subtests**; neighboring Grafana checks passed **15 / 170**.
  The complete build-probe suite passed **211 tests / 388 subtests**, exit 0, 80.21 seconds.
  Public grading controls also confirmed unavailable history is INCONCLUSIVE, a pending forbidden
  write is FAIL, and allowed query-only history is PASS.
- RELI-01: original check produced **12 failing refusal/ambiguity subtests**, retaining clear
  grant controls. An intermediate implementation exposed greedy phrase capture; another three
  controls exposed conflicting-context classification. Independent review then identified
  question/conditional tails; five actual cases reproduced the hard false-positive result.
  Final affected reliability checks: **10 tests / 94 subtests passed**, exit 0, 2.25 seconds.
  The failed and successful logs remain separately retained.
- CLI-01/02 and RCA-01: **four failing subtests** reproduced EOF, ambiguous outcome and classifier
  gaps. Root review then found exception-hierarchy sensitivity; two actual CLI subclass cases
  misclassified applied outcomes. The corrected independent/subclass calibration passes all six
  controls. Final affected suite: **27 tests / 55 subtests passed**, exit 0, 6.79 seconds.
- PIPE-02: original snippet **0/8 exact byte matches**, exit 1, despite all receiver children
  exiting 0. Revised snippet **8/8**, exit 0, on Windows PowerShell **5.1.26100.9549** and
  PowerShell **7.6.6**. Root's separate scratch rerun also returned **8/8**, exit 0.
  The command replaces only Docker with a native byte receiver; this isolates transport from
  unexecuted Docker/Alloy behavior.

The root RELI logs begin `reliability-`; CLI/RCA evidence is in `cli-retry`; Grafana evidence is
in `grafana-oracles`; documentation/source receipts and original transport cases are in
`pipeline-traces`, with root's independent transport result in `root-transport`.

## Sources and context cost

[sourced] Checked 2026-10-02 after inspecting the local workspace. Context7 supplied the
[Cloud Run tracing contract](https://docs.cloud.google.com/run/docs/trace),
[Docker bind-mount semantics](https://docs.docker.com/engine/storage/bind-mounts/),
[OTel sampling contract](https://opentelemetry.io/docs/specs/otel/trace/sdk/#sampling),
[Python EOF behavior](https://github.com/python/cpython/blob/main/Doc/builtins/exceptions.rst),
[subclass-aware type checks](https://github.com/python/cpython/blob/main/Doc/faq/programming.rst),
and [Java buildpack memory constraints](https://docs.cloudfoundry.org/buildpacks/java/index.html).
Official-page fallback supplied the relevant
[Cloud Logging release-note date](https://docs.cloud.google.com/logging/docs/release-notes),
[current Alloy auth lifecycle](https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.auth.google/)
and [Alloy validation contract](https://grafana.com/docs/alloy/latest/reference/cli/validate/).

GitHits separately corroborated [OTel's recording/sampled table](https://github.com/open-telemetry/opentelemetry-specification/blob/32c0651e/specification/trace/sdk.md#sampling),
[Alloy v1.18.1 auth registration](https://github.com/grafana/alloy/blob/6012ec4a/internal/component/otelcol/auth/google/google.go#L14),
and the [calculator fit-check branches](https://github.com/cloudfoundry/java-buildpack-memory-calculator/blob/3d845d8695ed03f1315c5a66582a441c754e3870/calculator/calculator.go#L72).
Current Alloy documentation identifies a newer version than that pinned source; both describe
preview auth, and neither establishes the deployed version. No applicable source disagreement
was identified. For OE-01, Context7's Grafana datasource/provisioning documentation and GitHits'
[route registration](https://github.com/grafana/grafana/blob/3878cd83/pkg/services/ngalert/api/generated_base_api_ruler.go#L329)
and [export handler](https://github.com/grafana/grafana/blob/3878cd83/pkg/services/ngalert/api/api_ruler_export.go#L20)
separately support the method-specific distinction between mutating rule routes and POST export.
The inspected upstream snapshot does not establish the fixture's pinned container behavior.

Relative to this batch's base, `obs-pipeline/SKILL.md` grows **151 bytes / 1 line**; its reference
and the two trace references grow **1,875 bytes / 18 lines** combined. The PCF reference grows
**453 / 5**. The executable CLI starter grows **541 / 9**, with **2,710 / 42** in its copied tests.
The shared probe grows **2,853 / 53**, and the retry oracle **243 / 6**. The new authorization
oracle is **4,692 bytes / 100 lines**: it replaces the inline assertion with a readable bounded
check and an explicit inconclusive result. It is staged after the model trial, not added to an
agent's runtime prompt. No agent body or authority grant changed.

The new mechanisms are justified by the reproduced false acceptances/rejections above. No
prose-mirroring tests were added for the documentation corrections; their evidence is primary
contracts, source inspection and labeled supplied-state review.

## Integrated verification and publication

[verified] Root's full repository run passed **1,711 tests and 3,192 subtests**, with **19 skips**
and one existing Starlette/AnyIO deprecation warning, exit 0, **764.68 seconds**. Skips were three
Windows directory-symlink cases, two shell/CI checks, eleven external-producer acceptance cases
and three opt-in Docker/Claude checks. The 22 bounded frontend calibrations ran and passed.

Command, using the verified interpreter above:

```text
python -X utf8 -B -m pytest -q -rs -o cache_dir=F:/iso-tmp/fleet-audit-fixes-20261002/batch-04/final-pytest
```

Environment: `PYTHONDONTWRITEBYTECODE=1`, `RUN_INSPECT_DOCKER_SMOKE=0`,
`INCIDENTS_PAGE_MODE=bounded`, existing dependencies at
`F:/repos/backbox-ui/frontend/node_modules`, a pre-created
`F:/iso-tmp/fleet-audit-fixes-20261002/batch-04/frontend` scratch directory, and no
`INCIDENTS_PAGE_ORACLE` override. The frontend boundary remains actual oracle bars 1/2/3/5 with
a fetch transport double; full MSW integration, native browser/assistive technology and model
behavior are unverified. No new package, browser or container download occurred.

The full log is `batch-04/full-suite.txt`. Scenario validation passed **193 specs / 741
expectations**; adapter generation and diff checks passed. The first publication gate found one
relative link escaping the trace skill's owned bundle. Root replaced that cross-skill Markdown
link with the owning skill's name and regenerated its copy. Only those two documentation files
changed after the suite; executable and test bytes remained unchanged. The failed gate is retained
as `gate-a-initial.txt`; the corrected candidate passed **both Gate A structural steps**, exit 0,
recorded in `gate-a.txt` and the publication receipt.

Implementation identity: base `8039063e220d14e1e17b19bf6fb79bd5e82702fa` plus **23 changed/new
non-report files**, including seven generated skill copies, in
`batch-04/implementation-manifest.json`. Sorted path/size/SHA-256 manifest digest:
`2d802804b20f18d6584bafa07ef95d9d50833b043351ca50597bfb62bda25963`.
The full-run manifest is retained as `implementation-manifest-tested.json`, digest
`9862ed2b790693c93444212e7c9e72180f2deb880d110bf6c4e3260b2d2857a6`.
Root confirmed it stayed unchanged throughout that run. `post-suite-doc-correction.json` records
the two-path link correction and unchanged executable bytes. Publication readback compares each
implementation blob in the final commit with the final manifest above.

Independent static review identified the RELI question/conditional issue above; it was reproduced,
corrected and re-reviewed. No remaining concrete findings were reported on the recorded implementation.
The reviewer executed no candidate code; root owns integrated execution. The final commit/remote
identity, committed-blob comparison, exact-commit review and gate receipt are recorded at
`batch-04/publication-receipt.json` under the scratch root above.

The user authorized the selected repairs and continuation of commit/push on the existing repair
branch. No merge or live platform operation occurred. Previous live-judge calibration, native/model
behavior, target-platform acceptance and human acceptance of the exact candidate remain distinct
from these local checks. `AUDIT-001` owns the remaining twelve findings and their disposition.
