# Evaluation contracts

These are proposed logical contracts for adapters and reports. They do not introduce a deployed API
or require a new generic envelope. Map native fields first and retain original framework records.
Version any implemented mapping and test it with known passing, failing and unavailable measurements.

## Case definition

| Field group | Required meaning |
|---|---|
| Identity | Local case ID, source benchmark and task ID, source revision, content digest, license/source reference |
| Purpose | Evaluation mode, target role, task question and applicability to the team's stack |
| Inputs | Candidate-visible files/messages, declared tools, environment/fixture references and limits |
| Hidden material | Ground truth, reference patches, verifier tests and human labels kept outside candidate access |
| Expected behavior | Required outcomes, valid alternatives, prohibited behavior and unavailable-evidence handling |
| Assessment | Native checks, upstream verifier/version, calibrated rubric references and manual-review needs |
| Partition | Development, held-out evaluation, or published benchmark; related variants grouped together |
| Adaptations | Every change from the source, rationale and a new local identity when behavior changes |

No task ID, filename or prompt should reveal a hidden fault accidentally. Check input assets for
answer-bearing names and copied solution text. Public benchmark familiarity cannot be eliminated by
local isolation; report that limitation and retain private/synthetic held-out variants separately.

Turn-based cases additionally identify the starting observations, each release condition, the exact
new observation, supported requested checks and the human/lab actions reported. Time is part of the
evidence: retain source time, timezone, observation window and freshness, with unknown values explicit.

## Run plan

A run plan selects the case manifest, incumbent/candidate, execution profile, requested model and
expected identity where available, judge configuration, trial count, budget, timeout, retry policy,
concurrency, output destination and run owner. The owner selects credentials through the protected
host mechanism; the plan contains a reference or authentication class, never a credential value.

Pin the candidate by content and revision. Record dirty inputs if measuring them; do not describe a
dirty candidate using only its commit. Record runner source/revision, mapping version, package and
CLI versions, host/architecture, image digests, input digests and declared versus observed tools.
Changing any load-bearing input starts a new run identity. Preflight catches incompatibility before
a model call or fault injection.

Compare arms under matched task, model, tools, limits and reset conditions. If changing a host,
framework or authentication path is the experiment, identify it as the variable and avoid attributing
the resulting difference solely to prompt quality.

## Execution and assessment

Execution status and agent assessment are separate. The executor can finish normally while the
verifier cannot measure; conversely a completed verifier can show an agent failure.

| Event | Execution record | Assessment treatment |
|---|---|---|
| Valid task and verifier complete | Completed | PASS or FAIL from applicable checks |
| Target model/authentication unavailable | Failed or not started, with reason | INCONCLUSIVE; no candidate verdict |
| Candidate exhausts a declared task budget in a functioning environment | Budget exhausted, with execution evidence | FAIL for the unmet deadline/completion requirement; retain completed checks |
| Candidate finishes without a required patch, submission or other task artifact | Record actual completion and verified absence | FAIL for the unmet requirement |
| Infrastructure timeout, external cancellation or unresolved cause of missing output | Preserve interruption and attribution evidence | INCONCLUSIVE for affected measurements; retain supported completed checks |
| Agent demonstrably violates a measured requirement | Record actual execution outcome | FAIL for that requirement, with evidence |
| Verifier/collector fails or loses evidence needed to assess the task | Preserve original error | INCONCLUSIVE for the affected assessment |
| Case not selected or unsupported before running | Excluded, with reason in manifest/report | Outside the measured denominator; visible in selection accounting |
| Selected case silently skipped | Incomplete coverage | Never omitted from expected-run accounting or treated as passing |
| Lab cleanup fails after a valid assessment | Separate cleanup failure | Retain assessment, mark lab unavailable and block reuse until reconciled |

Each profile declares its task deadline, required submissions and instrument health evidence before
execution. Apply this precedence per requirement: valid evidence of a violation is FAIL and valid
evidence of satisfaction is PASS; otherwise an instrument failure or unresolved attribution is
INCONCLUSIVE. A later unrelated instrument failure does not erase a supported result, but changed
artifacts or other invalidated evidence require reassessment. A timeout code or absent file alone
does not identify the cause. Confirm that the candidate had the declared opportunity to complete
and that artifact collection worked before attributing a missing submission to it.

Do not remove genuine budget-exhaustion or missing-submission failures from the task denominator.
AC-24 contrasts a nonterminating candidate and an omitted patch with provider/runner outage and lost
artifacts. Imports preserve original native statuses; new mappings and any rescoring are separate
assessment revisions, with differences explained rather than silently rewriting historical results.

Timeout semantics can differ upstream. Keep upstream verdicts unchanged and report how the fleet
assessment maps them. An upstream zero reward must not conceal an infrastructure error; a local
INCONCLUSIVE must not silently rewrite an official benchmark metric.

Per-assertion records retain identity, scope, method, verdict, evidence references, reason and
measurement gaps. Semantic outputs also retain judge model, rubric, calibration binding and any
supporting quotes. Validate quotes against the assessed source. A score without usable evidence
does not satisfy a requirement that explicitly needs evidence.

## Report records

The report must expose, either directly or through stable source references:

- Run, case, arm, trial and attempt IDs; exact candidate and measurement identities.
- Profile and claim scope: artifact, semantic, native host, diagnostic or live recovery.
- Execution status, per-check assessments, manual assessment state and upstream results.
- Original response, patch/artifact, trace, verifier output and evidence release history.
- Requested/observed model, tools, session continuity and helper relationships where measured.
- Original task latency, judge latency and report-generation latency separately.
- Known spend, unknown spend, cached calls and any reference to the provider's billing evidence.
- Setup, fault, reset and cleanup results for lab profiles.

Historical imports preserve their original identity and omissions. The importer must not fill missing
CLI/host facts from the computer importing the run. It can render incomplete historical evidence
while marking it unsuitable for claims requiring those facts. A replay timestamp is not a new trial.

## Fresh trials and caching

1. A fresh behavioral trial invokes the candidate under its declared conditions. Disable any cache
   that would substitute a prior candidate response. Record trial and attempt independently.
2. A replay reads a saved output and existing assessments. Its new model spend is zero; original
   task/judge spend remains attributed to the original run, not billed again in the replay total.
3. Rescoring applies a selected scorer to frozen outputs. It may spend on a judge without invoking
   the candidate. It creates a new assessment revision and retains the earlier assessment.
4. A deterministic scorer cache keys all consumed inputs and scorer version. A model-judge cache
   also binds the actual judge identity, rendered rubric, configuration and assessed response.
5. When resolved model identity is unavailable, state that limitation. Cached aliases cannot prove
   what the provider would resolve today. Do not merge results whose required identity is unknown.

Judge-stability experiments require fresh independent judge inferences on the same frozen inputs.
Disable verdict/result reuse in every participating adapter and judge library; record a distinct call
receipt and cache state for every planned repetition. A replayed verdict is not a repetition. If
independent-call evidence is unavailable, stability remains INCONCLUSIVE. Failed fresh attempts stay
visible and do not count as completed judgments; any retry follows the declared attempt policy.
Prefix/token caching that still performs a new inference is not verdict reuse, but its effect on
cost/latency must be recorded. Compare fresh-call stability, cost and latency separately from cached
replay performance. Ordinary deterministic replay and explicitly cached rescoring remain available.

Retries are new attempts attached to the original trial; preserve the unsuccessful attempts and
their cost. Default native acceptance comparisons use no automatic retry. A benchmark's different
published retry policy is a separate profile. Never rerun failures until the report becomes green.

## Aggregation and comparison

First report selected, started, completed, failed-to-measure and excluded counts. Then report
per-case and per-dimension outcomes. Preserve the native scenario threshold when displaying native
results. Do not replace its aggregation with promptfoo's average or a framework's default threshold.

Critical authority violations and fabricated evidence have an explicit blocking disposition that
cannot be offset by unrelated quality scores. The experiment declares which checks are blocking
before execution. Do not retroactively turn a disappointing result into a nonblocking check.

Report agreement/accuracy over its stated denominator and inconclusive coverage separately. For
example, 8 correct diagnoses, 1 wrong and 1 unavailable are 8/9 among measured cases and 9/10
measurement coverage; the unavailable case remains visible. The same run's official benchmark
score may use another denominator and must retain its own label.

Comparisons join by case revision, assessment identity and matched trial policy, never display name
alone. Show gains, regressions, unchanged cases and missing pairs. Aggregate only comparable arms;
multi-host, multi-model and differently adapted suites stay separate.

## Storage and compatibility

Use private ignored run storage under `.eval-runs/` for this repository. Preserve original traces and
framework outputs; a bounded display excerpt links to the full evidence and states truncation.
Portable references should resolve within the run bundle after relocation, without depending on a
deleted temporary workspace. Apply the project's documented retention policy, with owner disposition
for evidence supporting unresolved decisions.

No signing, distributed writer coordination or exact-once effect guarantee is proposed. One writer
owns a run directory. A failed import writes no replacement over the last complete report. Partial
publication remains visibly incomplete. Freeze format/mapping versions and reject unsupported major
versions before interpreting verdicts; preserve unknown optional source fields in the original data.
