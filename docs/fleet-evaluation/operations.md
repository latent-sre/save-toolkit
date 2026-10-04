# Proposed operations guide

This guide specifies the workflow the implementation must support. New CLI names and commands have
not been selected or implemented. Existing native commands remain documented in the
[eval README](../../evals/README.md). No lab, package installation or model call occurred while
authoring this package.

## Operator workflow

1. **Select:** choose task suite, case revisions, candidate/incumbent, host/model, scorer and claim
   scope. State whether this is replay, rescoring, a fresh trial or a lab exercise.
2. **Preflight:** confirm manifests, installed versions, plugin identity, protected credentials,
   task compatibility, output directory, resource limits and budget. Validate local inputs before
   opening a provider connection or creating a lab. For external coding tasks, require DEC-13's
   admitted command-execution actor and receipt path; stop if either is missing.
3. **Prepare:** create the isolated task workspace or lab; stage candidate-visible inputs only;
   record a healthy baseline and fault injection when applicable.
4. **Execute:** run the selected agent profile with bounded tools, session limits and attempts.
   Preserve raw output and infrastructure errors as they occur.
5. **Assess:** run independent checks and selected calibrated semantic judgments. Retain original
   framework results and all manual-review requirements. Label CI-supplied execution evidence by
   its actor; do not report it as a test run performed by the evaluated agent.
6. **Restore:** reconcile any unknown lab action, reset/destroy the exercise resources and verify
   cleanup. A stopped process does not establish that a remote action stopped.
7. **Compare:** review case-level differences, coverage, native parity, cost and limitations.
8. **Disposition:** human owner accepts, requests revision, retains the incumbent or requests a
   separately scoped follow-up. Summarize supporting evidence in the appropriate review/roadmap.

The implementation should expose these stages through existing tool commands and thin wrappers
where needed. A single local report entrypoint is useful; a new permanent service is not required.
WP-01's report/import acceptance requires the same bundle on Windows and Linux (AC-23), including
relocation and paths with spaces. Different host path rendering is expected; verdicts, counts and
provenance must agree, and evidence links must open on both hosts.

## Resource planning

Record host OS/architecture, container engine, CPU, memory, disk, image cache and network access.
Separate orchestration capacity from per-task limits. Live faults may affect cluster-wide components;
namespace separation alone must not be assumed to isolate simultaneous exercises. Serial runs are
the default until the selected fault domains and reset procedure support more concurrency.

Linux containers/labs are the proposed execution target. Windows report/import compatibility and a
Docker command succeeding on Windows do not establish all benchmark tasks work there. Confirm the
chosen SREGym problems, cluster/runtime versions and storage against their pinned instructions. Record
which terminal/coding tasks need additional resources before selecting the pilot set.

## Spend and time

Estimate separately: candidate calls, helper calls, semantic judges, attack generation, retries and
lab compute/storage. Known zero, unknown and unavailable cost are different states. Provider-reported
token cost is not necessarily the subscription invoice or total lab cost.

Use a small representative preflight to measure costs before a campaign. For example, 12 incident
cases with two arms and three repetitions yield 72 conversations. Two invocations per conversation
would yield 144 parent invocations, with helper/judge calls additional. Ten coding cases with the
same arms/repetitions yield 60 task attempts. These are sizing examples, not approved run counts.

A run budget includes wall time, number of attempts, model spend, resources and cleanup allowance.
Check limits before scheduling the next operation. An in-flight model request can exceed a soft
budget; record this risk and the enforcement granularity. Unknown pricing prevents claiming a dollar
cap; choose a supported model/pricing configuration or record an explicitly accepted alternate cap.
Do not silently select another model when a configured one fails.

## Data and credentials

Keep raw transcripts, prompts, patches and screenshots private under the run's ignored storage.
An export may contain source code, identifiers or credential-shaped text even when the final answer
does not. Review/redact derived summaries before sharing; keep the original evidence under its
intended access controls. An evidence omission/redaction must remain visible to the reviewer.

Configure model authentication through the selected protected host path. Do not read or print
credential values to diagnose setup. Benchmark containers receive only what the approved provider
path requires, with no production account files or arbitrary host mounts. External research uses
public descriptions, never raw private cases. Provider calls, telemetry, remote generation, result
sharing and cloud synchronization require separate destination/configuration verification.

Review framework opt-outs for the pinned release and confirm them using controlled fixtures or
observed permitted network behavior. A telemetry opt-out is not a promise of zero egress. Do not
enable hosted dashboards merely to obtain a local comparison report.

## Failure handling

| Symptom | Operator response |
|---|---|
| Dataset/image cannot be obtained | Record setup failure and source revision; do not grade the agent |
| Host advertises unexpected tools or wrong plugin | Stop that trial before accepting behavioral evidence |
| Model/judge unavailable | Preserve diagnostics without secrets; record INCONCLUSIVE, no implicit fallback |
| Invalid or missing scorer output | Keep raw output and scorer error; do not coerce to zero/false as an agent verdict |
| Candidate exhausts its task budget or omits a required submission | Retain execution/collection evidence; apply AC-24 task FAIL when the environment worked and the declared completion requirement was unmet |
| Infrastructure timeout, lost artifacts or external cancellation | Retain diagnostics/partial trace, reconcile remaining processes/actions and use INCONCLUSIVE for affected measurements; preserve already supported results |
| Stability repetition returns a cached judge verdict | Mark it as replay, exclude it from independent repetitions and retain the incomplete call count; any replacement call needs remaining declared budget |
| Reset or cleanup fails | Mark resources unavailable and hand off exact resource identities to the lab operator |
| Import interrupted | Retain original data and last complete report; publish no incomplete result as current |
| Source inputs changed mid-run | Stop comparison, retain the affected run and start a new identity after reconciliation |
| Good aggregate hides a critical failure | Review the specific case and blocking check; do not average it away |

Do not automatically retry an action with unknown outcome. Retry infrastructure only under a
declared policy, with a separate attempt, original failure and cost. Cancel future scheduling when
an essential boundary or identity check fails.
Apply the per-requirement precedence in [contracts](contracts.md#execution-and-assessment). A missing
file is an agent failure only when valid execution and working artifact collection establish the
omission; missing collector evidence is a measurement gap.

## Maintenance and upgrades

Pin framework/runtime/dataset versions at adoption. Upgrade one integration at a time, replay known
good/bad/unavailable controls and rerun its native compatibility canaries when tool/session behavior
can change. Recalibrate whenever load-bearing judge inputs change. Preserve original evidence and
record verdict changes instead of rewriting old runs under a new scorer name.

Refresh task licenses, image availability and host requirements at selection time. Upstream README
examples can move ahead of released packages. Record documentation/source discrepancies and test
against the installed version. Reject a new dependency if the existing tool provides the same
capability with less integration work and equivalent evidence.

## Operator documentation required at each delivery

Each adapter ships a short tested guide: prerequisites and supported hosts, installation into the
selected isolated environment, task selection, model/credential configuration without values, a
bounded run, replay/regrade behavior, evidence locations, cancellation/reset, failure interpretation,
known limitations and removal/rollback. Commands are published only after actual validation.
The guide states whether the run measures artifacts, semantics, native behavior or live outcomes.
