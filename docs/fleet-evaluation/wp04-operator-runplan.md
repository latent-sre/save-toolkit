# WP04 offline preparation and gated native plan

The owner's 2026-10-25 follow-through request selects **both Linux and Windows**
execution. The [follow-through plan](run-plan-followthrough.md) adds a separately
measured Linux read-only namespace profile and a shared USD 40 testing budget.
The Windows commands below remain the Windows arm; their results are not pooled
with Linux. The earlier pending-budget statements below are superseded only for
this requested campaign; source, runtime, hidden-answer boundaries and independent
assessment still need their actual evidence. The later
[Linux pilot](../reviews/2026-10-25-followthrough.md#linux-wp-04-pilot) records five attempts;
the [Windows preparation audit](../reviews/2026-10-27-eval012-windows-preparation.md) records
restored fixtures and remaining host/test gates. The Windows execution template below
does not represent an executed or accepted Windows campaign.

[verified] [The adapter](../../evals/itbench_pilot.py) validates, fetches exact pinned public files,
stages observed-only workspaces, prepares native fixtures, collects explicit submissions, exports
upstream input and performs separately labelled local assessment. It never invokes a candidate,
model, judge, container or service. Outputs are new files/directories; existing evidence is refused.
The [case review](wp04-case-review.md) and [proposed run plan](../../evals/manifests/wp04-run-plan.json)
are the admission packet. Selection revision 2 proposes cases 7/21/24/80/102; human admission remains pending.

[verified] Offline preparation produced five observed-only directories and validated native specs.
The raw observation total is 441,911,602 bytes; serialized YAML has a separate 512 MiB aggregate
limit. Native fixtures carry all selected source observations, without GT-guided projections.
Per-source and generated digests are evaluator-side receipt data. Large generated fixtures belong
only to ignored storage and disposable runner checkouts, never Git or candidate plugin sources.

## Preparation commands

Run these with the verified managed interpreter. On the approved Windows host, activate its
managed environment first so grader subprocesses resolving `python` use that same interpreter.
The commands perform repository/local-file preparation and pinned public downloads only.

```powershell
$Python = (Resolve-Path .venv\Scripts\python.exe).Path
$Cache = Join-Path $PWD '.eval-runs\complex-campaigns\wp04-source'
$Prepared = Join-Path $PWD '.eval-runs\complex-campaigns\wp04-native-fixtures-selection2'
$Receipt = Join-Path $PWD '.eval-runs\complex-campaigns\wp04-native-preparation-selection2.json'
& $Python -c 'import sys; print(sys.executable); print(sys.version)'
& $Python evals/itbench_pilot.py validate
& $Python evals/itbench_pilot.py fetch --source $Cache --include-hidden
& $Python evals/itbench_pilot.py rebuild-bindings --source $Cache --output .eval-runs\complex-campaigns\wp04-rebuilt-bindings.json
& $Python evals/itbench_pilot.py prepare-native --source $Cache --destination $Prepared --receipt $Receipt --max-prepared-bytes 536870912
& $Python evals/itbench_pilot.py prepare-judge-input --source $Cache --output .eval-runs\complex-campaigns\wp04-upstream-ground-truths-v2.json --receipt .eval-runs\complex-campaigns\wp04-upstream-ground-truths-receipt-v2.json
```

[verified] `fetch` constructs only immutable dataset URLs from validated manifest identities,
reads no more than the declared size plus one byte, and verifies each digest before publishing.
`--include-hidden` is for the evaluator cache, which must be outside candidate access. `stage` is
available for a standalone evidence workspace and writes its receipt separately:

```powershell
& $Python evals/itbench_pilot.py stage --case wp04-24 --source $Cache --destination .eval-runs\complex-campaigns\wp04-observed-24 --receipt .eval-runs\complex-campaigns\wp04-stage-24.json
```

[unverified] Before any model call, the owner must admit the exact source-supported cases, then bind exact incumbent/candidate and runner revisions/digests, the native CLI version,
observed concrete model, host/account/elevation, authentication class, output path, spend exposure
and runtime boundary evidence. The Windows arm preserves DEC-23's everyday **unelevated Windows account**;
the separately authorized Linux arm uses the follow-through plan's measured namespace boundary.
Preserve DEC-17's `sonnet` default and
record actual resolved model identity. No credentials are provisioned or printed by this adapter.

[verified] The prepared profile pins `sre-assistant`, declares only Read/Grep/Glob/Skill, prohibits
helper dispatch in the task, and validates each spec with the existing runner before publication.
No Bash, Write, external MCP server or live platform interface is granted. The ordinary native
runner records actual tools, identity and read-boundary evidence. [unverified] Staging and tool
selection are **not an OS sandbox**: host paths remain a load-bearing boundary. Human admission
must verify that the candidate's effective host/tool configuration cannot expose the evaluator
cache, GT/bindings, reviewer packet or unapproved source. Logical candidate-relative missing-file
controls do not establish hostile-process containment. Stop live admission if that cannot be shown.

## Exact commands after admission and run approval

The owner supplies the four approval bindings below from the accepted receipt; values are not
inferred from the reporting/preparation host. A disposable runner checkout holds generated specs;
the measured plugin root stays the approved incumbent/candidate. Existing observations are the
only fixture files. These commands are provided for review and have not run a model.

```powershell
param(
  [Parameter(Mandatory)][string]$ApprovedRunnerRevision,
  [Parameter(Mandatory)][string]$ApprovedPluginRoot,
  [Parameter(Mandatory)][string]$ApprovedPluginDigest,
  [Parameter(Mandatory)][ValidateSet('incumbent','candidate')][string]$Arm
)
$Python = (Resolve-Path .venv\Scripts\python.exe).Path
$Prepared = Join-Path $PWD '.eval-runs\complex-campaigns\wp04-native-fixtures-selection2'
$Runner = Join-Path $PWD ".eval-runs\complex-campaigns\wp04-runner-$Arm"
$Out = Join-Path $PWD '.eval-runs\complex-campaigns\wp04-native-runs'
git worktree add --detach $Runner $ApprovedRunnerRevision
Copy-Item (Join-Path $Prepared '*.yaml') (Join-Path $Runner 'evals\build-scenarios')
& $Python (Join-Path $Runner 'evals\build_probe.py') validate
& $Python (Join-Path $Runner 'evals\build_probe.py') run --scenario wp04-itbench-24 --plugin-root $ApprovedPluginRoot --expect-plugin-digest $ApprovedPluginDigest --label "wp04-smoke-$Arm" --model sonnet --trials 1 --timeout 900 --max-batch-usd 3 --out $Out
```

[unverified] The smoke must establish actual source reads, usable structured output, supported
Windows shell/manual-review behavior, complete runtime identity and expected boundary evidence
before proceeding. Thirty-six CLI turns are an offline provisional task limit; 900 seconds is a
wall-clock instrumentation guard. Neither establishes measured completion. `--max-batch-usd`
stops further scheduling after known spend reaches its limit or cost becomes unknown; it is not a
hard cap on a running build trial. The persistent-conversation spend guard does not apply to these
single-invocation build cases. The owner must accept that exposure before execution.

After reviewing smoke evidence and reconciling the full campaign spend authorization, use matched
arms, serial execution, two fresh trials per case, no automatic retries:

```powershell
foreach ($Id in @('7','21','24','80','102')) {
  & $Python (Join-Path $Runner 'evals\build_probe.py') run --scenario "wp04-itbench-$Id" --plugin-root $ApprovedPluginRoot --expect-plugin-digest $ApprovedPluginDigest --label "wp04-$Arm" --model sonnet --trials 2 --timeout 900 --max-batch-usd 5 --out $Out
  if ($LASTEXITCODE -ne 0) { break }
}
```

[verified] The terminal semantic check intentionally leaves mechanically successful trials
INCONCLUSIVE. The batch exits nonzero for that supported pending state, so this conservative loop
stops for review after its first case; the owner schedules each subsequent case explicitly after
classifying that outcome. A real measured failure also remains visible. Do not weaken the manual
check or rerun failed attempts to get a green batch. A no-model `validate` exit is not a trial.
[unverified] All twenty planned trials remain selected coverage until they are actually measured;
a stopped schedule is incomplete coverage, not a reduced denominator.

## Collection and assessment

Preserve the response and raw native v1 record/trace first. Substitute the actual saved response
path for `$Response` and use new output paths per attempt. Collection accepts exactly one explicit
JSON block with the selected case ID and valid entity/edge claims; it does not infer a graph from prose.

```powershell
& $Python evals/itbench_pilot.py collect --response $Response --case wp04-24 --output .eval-runs\complex-campaigns\wp04-submission-24.json
& $Python evals/itbench_pilot.py export --submission .eval-runs\complex-campaigns\wp04-submission-24.json --output .eval-runs\complex-campaigns\wp04-upstream\24\1\outputs\agent_output.json
& $Python evals/itbench_pilot.py assess --submission .eval-runs\complex-campaigns\wp04-submission-24.json --bindings evals/manifests/wp04-bindings.json --ground-truth (Join-Path $Cache 'Scenario-24\ground_truth.yaml') --output .eval-runs\complex-campaigns\wp04-assessment-24.json
```

[verified] `rebuild-bindings` regenerates all mappings from manifest-bound event/object names and
original GT metadata using the same anchored matching policy as the scorer. Compare its parsed
JSON with the frozen binding file and retain the file digest selected for the run. Ground-truth
IDs existing in a supplied binding are insufficient: assessment rechecks kind, namespace and
whole-name or anchored-prefix eligibility before resolving any entity.

[verified] Assessment verifies the GT digest against the selected case, keeping root and edge
measurement gaps distinct. Supply `--upstream-result` only for the original result object emitted
by the approved pinned evaluator; its entire JSON object is retained unchanged, including errors
and unknown fields. This does not verify that an imported object came from a real judge: preserve
its original file, judge identity/configuration and call receipt as supporting evidence.

[sourced] An eventual original upstream assessment uses the pinned evaluator's documented
`python -m itbench_evaluations --domain sre --ground-truth <consolidated.json> --outputs <exports>`
interface. [verified] `prepare-judge-input` emits its array contract and canonical numeric IDs, retaining
all original groups, aliases, faults and propagation values. Current selected sources need no
container unwrapping; the helper's wrapper support is exercised separately by a synthetic control.
The five raw source GT files stay unchanged, including their stated limitations. [unverified] Installing/running that third-party evaluator and approving
its judge are separate gates. Validate the prepared view on that approved evaluator before consuming
any score. Original upstream score
currently remains unknown; this adapter neither installs nor invokes the evaluator.

[verified] Keep supported assessments when later collection, billing or cleanup fails. Missing or
ambiguous mapping is unavailable measurement; an invalid submission after demonstrated opportunity
and healthy collection is a candidate requirement failure. Keep original v1 evidence separate from
local and human assessments. No result promotes the candidate; exact-revision human acceptance
remains required. Cleanup removes only the named disposable worktree after evidence retention has
been checked, and records any failure separately.
