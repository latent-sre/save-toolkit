# Fleet evals

The native fleet runner, [`build_probe.py`](build_probe.py), grades three kinds of scenario, decided by the
keys a spec carries rather than by a mode field.

| Kind | Where | Session | Graded on |
|---|---|---|---|
| **routing** | [`scenarios/`](scenarios) | main session, `--tools Skill,Task` (a spec may widen it), no `--agent` | one check: did the named component complete a non-error invocation — or, for a negative, stay out of the way |
| **contract** | [`scenarios/`](scenarios) | `agent:` pinned with `--agent`, or `skill:` pinned by instruction | `graders:` over the returned text |
| **build** | [`build-scenarios/`](build-scenarios) | `agent:` pinned, its real tools pre-approved, in a seeded fixture repo | `checks:` over **outcomes** in code |

Two directories because the build fixtures carry inline repos hundreds of lines long and would bury
the short routing specs. The runner does not care which one a spec came from.

## Run it

Use the latest **Python 3.14** patch for development and CI. The native runner's existing
compatibility floor is Python 3.12; installed hooks retain their separate Python 3.11 floor.

```bash
python -m pip install -r requirements-dev.txt
python evals/build_probe.py --validate                      # offline schema/grader/target check
python evals/build_probe.py --scenario all --label baseline --model sonnet --trials 3 \
  --out .eval-runs/<iteration>
python evals/build_probe.py --scenario discovery-runbook-incident-update --label desc-change \
  --model sonnet --trials 3 --out .eval-runs/<iteration>
```

`--validate` is the CI-safe check and the one to run on any scenario edit. `--run` equivalents need
a Claude-enabled runner and start a fresh non-persistent process per trial.

**Pin `--model` on every run.** The fleet's measurement default is the `sonnet` alias unless the
roadmap item names another tier: it is the tier the existing routing evidence was taken on. A run on
a different tier is a different baseline — record it and never average it with a Sonnet run.

Compare an incumbent with `--plugin-root <worktree> --label incumbent`; `--expect-plugin-digest`
refuses any other bytes. `--overwrite` replaces the selected run slots; use a new label when changing
the candidate or scenario. `--regrade` re-grades saved traces offline only when the original scenario
identity matches, and `--container IMAGE@sha256:…` runs every shell call inside a pinned, network-less
container for a candidate that is not team-authored.

## Inspect AI + Inspect SWE pilot

[`inspect_pilot.py`](inspect_pilot.py) runs the existing word-frequency fixture through Inspect
SWE's sandboxed Claude Code agent, with Inspect AI owning scheduling, logs, limits, and scoring.
It reuses seven artifact checks and records the other nine as omitted. It does not load the
Save Toolkit plugin or pin its software-engineer agent: this is an **artifact-only integration
pilot**, not native fleet acceptance. The existing runner remains authoritative for plugin
identity, routing, hooks, delegation, calibrated judging, and conversation continuity.

Install `requirements-test.txt` for offline tests, or `requirements-dev.txt` for all tooling.
Both include Inspect AI, Inspect SWE, and the Anthropic SDK required by the Claude bridge.
Docker must be available for sandboxed runs. The sandbox uses a reviewed image digest, resource
limits, all capabilities dropped, and a read-only system filesystem. Only workspace, home, and temporary
directories are writable. Grading uses system executables, a fixed PATH, and disables Python's
user-site and unsafe startup paths so agent-written configuration cannot replace the grader.
Inspect's root helper and agent retain the image's root user, but cannot modify the read-only
system executables. There are no host mounts or operator credential files. Network access remains available for
agent installation and the model proxy; it is not an offline sandbox.

```powershell
inspect eval evals/inspect_pilot.py@wordfreq --model <provider/model> --log-dir .eval-runs/inspect
inspect view --log-dir .eval-runs/inspect
```

Select the model explicitly and configure the provider credential through its normal local
environment. This differs from native Claude subscription authentication. The task requests
the latest Claude CLI, one attempt, no refusal/crash retries, 20,000 tokens, 300 seconds, and
a $1 cost limit. Inspect checks limits between operations; an in-flight call can overshoot.
Models without pricing metadata require explicit pricing before a cost-limited run can start.
`-T claude_version=<version>` selects a repeatable CLI version for comparisons.

Run the bridge smoke tests without a paid model (downloads Claude and starts Docker):

```powershell
$env:RUN_INSPECT_DOCKER_SMOKE = '1'
python -m pytest evals/test_inspect_pilot.py -k real_swe -q
Remove-Item Env:RUN_INSPECT_DOCKER_SMOKE
```

These scripted pass/fail cases verify the bridge and scorers, not model capability. Ordinary
CI runs the offline tests; Docker smoke cases are explicit opt-ins. Details and remaining
modernization work are in [Python and eval modernization](../docs/python-eval-modernization.md).

## Scenario contract

```yaml
id: discovery-production-triage-recommend-only
split: regression
prompt: |
  Payments latency just tripled in production and errors are climbing. No mitigation is
  authorized yet. Tell me what to do.
target: {kind: skill, name: incident-investigation}
routing: {expect: fire}
success_criteria:
  - Invokes incident-investigation for technical advice while the human incident lead owns coordination
```

A routing prompt is byte-for-byte unhinted — `--validate` rejects one that names its own target.
For `expect: not_fire`, set `expected_alternative: inline` or name the component expected instead:
a negative does not pass merely because the forbidden target stayed absent. Negatives are
zero-tolerance, so their threshold is always clamped to 1.0 and `--validate` rejects a declared
threshold below it; `threshold` on a positive is the fraction of trials that must pass.

A contract scenario pins `agent:` or `skill:` and lists `graders:` from the registry in
[`graders.py`](graders.py): `rubric`, `exact_json`, `exact_fields`, `regex`,
`not_regex`, `contains_all`, `contains_any`, `not_contains`. Structure is checked deterministically;
natural-language policy questions go to `rubric`. New scenarios use a `rubric` or a structural
grader, never a new keyword list. `--agent` runs the session AS the agent, so the pin is itself the
invocation; a `skill:` instruction can be ignored, so a skill-pinned trial additionally asserts the
skill completed.

A build check that grades with a probe-owned oracle stages the oracle into the workspace before it
runs the command: `writes:` carries a line or two of data inline, while `writes_from:` maps the
workspace filename to a file under [`oracles/`](oracles) so an oracle long enough to be a program
stays reviewable, runnable, and inside the `evals_python_lines` ceiling, which counts Python
oracles there, but not TSX, since it counts `*.py` only.

The CLI, API, UI, and deployment-pressure builder probes use `verification_completed` to check
the agent's own verification separately from probe-run artifact tests. It requires a standalone
foreground unittest, pytest, or Vitest invocation, a matching non-error Bash/PowerShell result,
and a nonzero passing test summary. `echo pytest`, failed tests, and a `Verified` heading do not
establish this. Missing/unsupported receipts, overlapping effects, or a later potentially mutating
tool call leave verification INCONCLUSIVE. The latter includes later shell commands even when a
human can recognize a read-only `git diff`; the checker does not interpret arbitrary shell effects.
This is ordered trace evidence, not exact-byte or detached-process attestation. The default build
tool set stays portable; PowerShell is available to an explicitly configured scenario only when
the native host supplies it. Offline parser tests do not establish live host provisioning.

[`build-software-engineer-root-cause-reassessment`](build-scenarios/build-software-engineer-root-cause-reassessment.yaml)
adds a tool-bearing bug repair after a failed retry-budget change. The optional
`skill_loaded: {before_effects: true}` check requires a successful main-thread Skill result before
any shell, edit, write, or delegation call. This scenario explicitly asks for guidance before shell
execution and permits initial Read/Grep/Glob inspection. It is intentionally stricter than the
general agent rule (load before permanent remediation); other scenarios retain ordinary
`skill_loaded` behavior. Ordered regrading requires the raw trace. The independent retry oracle
rejects another budget increase, suppressed exceptions, and disabling all retries; final foreground
verification remains separate from the probe's own artifact test.

**Native acceptance also requires manual trace review** against the scenario's `success_criteria`:
a completed failing reproduction of the prior repair, an actual discriminating comparison before
remediation, and a returned mechanism explanation grounded in those results. A skipped comparison,
an edit before investigating the contradictory result, weakened tests, or unsupported claims fail
that review even if automated checks pass. A good final artifact or the words "root cause" do not
prove reassessment. [`test_root_cause_probe.py`](test_root_cause_probe.py) calibrates skill ordering
and positive/negative artifacts offline; it does not grade hidden reasoning or prove native model
behavior. This scenario has not itself established native acceptance; agree host/model, exact
candidate, trial count, and budget before a model run.

The deployment-pressure probe also checks the maintenance banner's enabled, unset, empty, and
escaped-text behavior with an [independent oracle](oracles/maintenance-banner/probe_banner.py).
Its [positive and negative fixtures](test_maintenance_banner_oracle.py) reject a comment-only
implementation despite a green original suite. This proves HTML structure and literal text,
not browser/CSS appearance; the deployment and credential boundaries remain separate checks.

**The standing regression** comprises the build probes and the contract scenarios carrying
`split: regression`. The seven `build-python-...` probes cover refactoring effects, generator
consumption/lifetime, module moves, stdlib migration contracts, leaving correct code unchanged,
a shared calculation boundary usable without files, and a medium-sized policy unification across
three drifted intake entrypoints with a registry, a configured dotted lookup, a legacy re-export,
and a unit suite that encodes the drift. That oracle checks specification parity over a bounded
domain for every entrypoint, single ownership through the `policy.normalize_order` patch seam
(a record the old rules reject must pass once the shared policy accepts it), exception identity,
input immutability, six fresh-process import orders, and that the fixture suite stays green
without losing assertions; eleven named partial-ownership and lost-consumer artifacts are
rejected. It does not grade how the work was staged. Their shared
[outcome oracle](oracles/python-craft/check_contracts.py) is calibrated by
[positive/negative artifact tests](test_python_craft_oracle.py): correct implementations pass and
named behavioral and structural counterexamples fail, including eager reads, adjacent duplicate loss, broken
legacy imports, circular imports, and bypassed public patch points. The effect oracle adds 936
generated comparisons over a bounded integer/None domain, with independent output, mutation, error,
and effect expectations; this is not arbitrary-input coverage and needs no additional dependency.
The module-move oracle runs both import orders in fresh processes and exercises an unchanged alias
registry and configured dotted lookup. The generator oracle observes unbounded read/readlines and
uses the source position to detect logical EOF before first yield, allowing bounded chunks and
readline iteration. These common API
paths are covered; this is not a memory benchmark or proof against every possible read mechanism.
Migration checks exercise a stdlib adapter, not package discovery. The oracle and tests count
toward the eval ceiling; their outcome-level evidence does not establish live model performance.
Run `python -m pytest evals/test_python_craft_oracle.py` for offline calibration.

The calculation probe verifies a specified maintenance outcome: the in-memory boundary works
without ordinary Python file opens, and a policy replacement there reaches the existing file
entrypoint, including input rejected by the old parsing policy. It checks that actual helper parse
exceptions propagate by identity and rejects duplicated parsing before or after delegation.
These checks and their positive/negative calibration account for the 33-line review-fix eval increase.
It is not an arbitrary-I/O sandbox or a general design-quality score. The original
effect probe checks compatibility plus a source edit, not whether that edit improves design.
`python-refactoring-judgment` checks supplied-state choices about shared policy, independent rules,
internal callers, supported plugin imports, no-change restraint, coherent stages for large work,
authorized library adoption, established versus uncertain defects, explanation-only scope, and
justified whole-codebase rewrites in scope that preserve required contracts. It loads both the Python
refactoring reference and the builder bar so their abstraction guidance is assessed together.
It does not prove execution or consumer discovery. `discovery-python-improvement` checks routing
for an outcome-driven request; it does not grade implementation quality. These focused oracles
and calibration tests justify the accompanying eval
line-ceiling increase; no new grader, dependency, or evaluation framework is introduced.

For a live Python-skill comparison, agree the native host/model, exact candidate, cases, repetitions,
and cost cap first. Use matched disposable fixtures and the same builder, tools, prompt, and checks,
varying only skill availability and its necessary load instructions. Verify completed skill loads
in the skill arm and absence in the control; preflight one pair before spending the remaining budget.
Compare compatibility, the named maintenance outcome, restraint, and cost separately. Keep invalid
or mixed-model trials inconclusive: the resolved identity is the model that carried the main
thread (the init model and every top-level assistant turn), while the CLI's internal helper calls
in its usage table, such as a Haiku side call of a few tokens, are recorded as `usage_models` and
do not make a batch mixed. Offline oracle calibration does not establish model uplift;
the new cases have no live with/without-skill result until that comparison is actually run.

The reviewer cases cover explicit reading-only scope, Git investigation of a broken unchanged
caller and a matched compatible refactor, candidate-controlled runner/instruction rejection, and
the supplied-state decision to use an established verification environment. Their
[calibration tests](test_reviewer_cases.py) check real fixture branches, caller behavior, decision
graders, and command matching. Git trace matches establish attempted commands, not successful
interpretation; final workspace checks do not enforce a filesystem sandbox. The verification
decision case is not an execution trial. These bounded probes do not establish general free-form
review quality, host containment, or live helper behavior.

A skill's routing positive is a **description-change check** — run it when that skill's own
description changes. `--split` is not wired into the runner's selection; use `--scenario <id>` or
run everything.

The return-and-resume cases separate two boundaries: the `agent-direct-...helper-return` and
`agent-direct-...partial-slice-to-caller` scenarios grade supplied-state decisions; the
[`scribe return build probe`](build-scenarios/build-software-engineer-resumes-after-scribe.yaml)
requires a completed child call and the integrated runbook/README artifacts. Its automated checks
do not identify who edited the README or when; inspect the raw trace before claiming that the
parent resumed after the child returned.

The researcher/scribe cases add a bounded public-page lookup, private-input rejection with
zero attempted web calls, a missing-current-version source decision, extended/quick research
routing, and command provenance classification. The [partial-research case](build-scenarios/build-researcher-partial-research.yaml)
uses a fictional public packet and zero remaining retrieval attempts to check useful per-question
coverage, citations, and gaps without promoting an older default or incomplete release highlights.
Its literal fields allow the normal return header; explanation quality still needs manual review.
`tool_call_count` counts attempted calls from
the trace, including failures: a positive WebFetch count and cited answer still need manual
inspection of the matched retrieval result before claiming successful or accurate research.
The strict-empty MCP runner does not test Context7/GitHits provisioning or raw-reader behavior.
The postmortem artifact probe checks draft status, impact versus resolution-confirmation times,
retained follow-up ownership and evidence gaps. The contact-closeout probe checks the actual
card/index edit after a completed scribe dispatch; inspect the trace to establish who wrote it
and whether the caller supplied the correct checkout binding. These are bounded artifact checks,
not general document-quality judgments. `python -m pytest evals/test_researcher_scribe_cases.py`
calibrates their checks offline, including rejection of newly verified execution in the runbook
fixture, which supplies no incoming verified execution claims. New scenario definitions and
offline passes do not establish live model behavior, routing reliability, or host acceptance.

Agent-target routing probes remain **calibration-only** evidence of model/host propensity
(on 2026-08-22 Opus 5 dispatched 0/3 where Sonnet did 3/3). Record the model
and host with any such result. See the historical
[accepted EVAL-002 decision](../docs/decisions/2026-08-22-agent-discovery-calibration.md).
The expanded SRE workflow now requires an actual unhinted incident/runbook dispatch, helper return
and caller continuation as a product acceptance case on each claimed host. A routing probe or a
supplied-state JSON decision alone does not satisfy that requirement; one success does not establish
general dispatch reliability. The pending cases live in
[host acceptance](../docs/vscode-plugin-acceptance.md#expanded-investigation-acceptance-pending).

### Native incident conversation

[`native-incident-helper-return-and-resume`](scenarios/native-incident-helper-return-and-resume.yaml)
extends the same runner with exactly one `followups:` prompt. It runs the initial parent unpinned,
keeps its clean environment and fixture workspace, then passes the actual session ID to `--resume`.
There are at most two CLI invocations, each capped at `$0.75` and the selected `--timeout` (use
`--timeout 240` for the frozen incident comparison: up to 240 seconds per invocation). Prompt
suggestions are disabled; there is no automatic retry. This path grants only `Skill,Read,Task`,
accepts fixture files only, and checks each invocation's plugin, advertised inventory, actual tool
use (including child calls), read paths, and session identity before continuing. Optional
`expected_model:` pins the concrete parent/init model identity on every invocation; the committed
incident scenario requires `claude-sonnet-5`. Each turn retains expected and observed identities.
Credential markers or missing, invalid, or over-`$0.75` cost records stop this path before a follow-up.
`references:` are assertions only here: they do not add instructions to the prompt. The initial
parent must finish reading the measured plugin's exact reference before its first helper dispatch;
a helper read, a later parent read, or a reference first loaded on resume does not count. The summary
retains the qualifying initial-parent read's tool ID and start/completion trace lines.
The initial parent's advisor Skill invocation must also complete before helper dispatch; late or
helper-only selection does not count.

The parser distinguishes an asynchronous submission receipt from a matched completed task
notification. The `helper:` assertion requires exactly one completed child and parent text after
that return. A successful synchronous child result remains valid. Follow-up traces, responses, and
invocation metadata live under `followup/`; the initial response is also retained as `response.md`.
Regrade checks both original traces against each invocation's saved workspace, exit status, session,
and model binding, applying the same runtime and credential boundaries after the fixture is gone.
Missing or partial boundary evidence is INCONCLUSIVE. Timing totals count each invocation once even
when its runtime emits repeated cumulative terminal results.

**A native PASS is structural only.** Its grading and summary records explicitly carry
`assessment_scope: structural_only` and `semantic_assessment: UNVERIFIED`. Read the initial dispatch,
child response, parent continuation, and resumed response to judge the scenario's manual criteria:
caller/owner preservation, evidence quality, feasible advice, corrected recovery, and causal/timing
limits. Successfully reading the helper's supplied evidence file is also a manual check: a completed
child alone does not establish that read. Parent text after a return proves continuation, not good synthesis. This scenario has not
been behaviorally accepted merely because its schema or parser tests pass.

## The rubric judge

`rubric` graders spawn one clean-room, tool-less `claude -p` turn against a named rubric in
[`rubrics.yaml`](rubrics.yaml). It fails closed: a timeout, auth failure, malformed envelope,
unknown verdict, a verdict from a model other than the pinned one, or evidence not quoted verbatim
from the graded response all fail closed with a `judge inconclusive:` detail; the runner marks the
trial INCONCLUSIVE. Normal build and contract rubric graders require one explicit completed
calibration receipt before starting the evaluated agent:

```bash
python evals/build_probe.py --scenario <id> --label <label> --out <dir> --judge-calibration .eval-runs/judge-calibration/<run>/identity.json
```

The receipt must cover the current canonical corpus (every rubric has PASS and FAIL cases),
match the loaded judge code, configuration, and rubric definitions, and
meet the repository's 0.95 agreement threshold with no inconclusive cases. The loader recomputes
agreement from `results.json`; a legacy, partial, custom-subset, or stale receipt cannot certify a
normal trial. Both grader forms and direct `run_trial` calls enforce the same preflight. Scenario
kwargs cannot supply the binding. `--validate`, empty-response spec validation, and direct judge
spot checks stay offline or retain their explicit bootstrap behavior.

```bash
python evals/judge.py --calibrate
```

measures every rubric against [`rubrics-calibration.yaml`](rubrics-calibration.yaml) and exits
non-zero below 0.95 agreement or on any inconclusive case. Calibration remains owner-triggered;
the runner never starts it automatically. New judge code/configuration or rubric definitions need
an applicable calibration before normal rubric trials. Its cache lives under
`.eval-runs/judge-calibration/`; entries bind judge/clean-room source, Python/PyYAML, effective CLI
arguments and timeout, prompt template, rendered rubric, response, and observed model. A rubric
edit invalidates that rubric's entries; a judge source/configuration edit invalidates the affected
execution cache. Label-only edits reuse judgments but recompute agreement, and cache-only
calibration remains visibly marked. Cache eligibility does not depend on a calibration receipt,
so bootstrap calibration has no circular dependency. The contract is the
[rubric-judge evaluation ADR](../docs/decisions/2026-09-01-rubric-judge-evaluation-contract.md).

The normal runner derives the concrete judge model from the receipt and freezes its executable,
arguments, timeout, and optional `EVAL_JUDGE_CACHE` location. Later ambient `EVAL_JUDGE_MODEL`,
`EVAL_JUDGE_CACHE`, or `CLAUDE_BIN` changes cannot redirect that binding. Every live judgment and
cache hit checks the pinned model. Complete binding metadata is retained in provenance and grading;
`timing.json` retains each call's response/rubric identities, full verdict detail, observed model,
cache status, cost, and duration, including inconclusive calls. The 600-character display limit does
not truncate those records. These are trusted local evidence records, not signed runtime attestation.

## Provenance

Every run records the plugin root's commit, plugin-input dirty state, and a path-bound source digest
over `agents/`, `skills/`, `commands/`, `hooks/`, the manifest, and the guard scripts
(`provenance.json`, the trace summary, the summary line), plus the requested and resolved model,
trials, timeout, per-trial duration, cost, and the exact argv. Identity hashes say two runs measured
the same plugin; they do not say the runs measured it the same way — **pin `--model` and `--timeout`
for any numbers you intend to diff.**

Machine records retain the complete candidate digest and a scenario digest covering the spec, its
referenced oracle files, the explicit judge binding when used, and the rubric definitions the judge actually consumes. The judge caches
rubrics on first load for the process; file edits take effect in a new process. The digest uses those
same cached definitions. Appending requires candidate and scenario identities to match the existing
batch before any model call. Scenario inputs are checked again before and after grading;
a change in the effective definitions or oracle bytes invalidates the trial. Regrade identifies each assertion by its scenario digest and
position and retains live-judge/workspace verdicts from `grading.original.json`; duplicate display
labels cannot substitute one verdict for another. Legacy records without identities, changed
scenarios, and missing original assertions are INCONCLUSIVE and require a fresh trial. Regrade does
not call a judge or recover workspace evidence that was never recorded. Rubric regrades use the
immutable binding embedded in the original live grade, without reopening a current receipt or
recalibrating. Missing binding evidence or a changed judged response makes the regrade INCONCLUSIVE.

The scenario digest also binds the evaluator implementation: `build_probe.py`, `graders.py`,
`judge.py`, and `clean_room.py`, plus Python and PyYAML versions. Start the runner in a fresh process
from a stable checkout with the pinned dependencies. All four modules are loaded before the source
identity is captured; subsequent source edits abort grading/regrade and require a new process rather
than assigning changed disk bytes to already-imported code. The digest is conservative: even an
unrelated evaluator edit invalidates prior scenario identities. In-process code replacement is
unsupported; this is provenance for the trusted runner, not attestation of its Python environment.

Run slots are shared across models under each label. Regrade copies a verdict into a summary only
when its full candidate digest, scenario identity, and resolved model identity match the saved run.
An overwritten slot or missing identity makes the conflicting summary row INCONCLUSIVE; it never
acquires the replacement run's PASS. Prefer separate labels for separate model/candidate comparisons.

`--overwrite` prepares a complete replacement in a hidden sibling attempt directory. The previous
run remains intact through execution, grading, artifact writes, and workspace cleanup. Publication
renames the previous slot to a backup and restores it if the replacement rename fails; only a
published attempt reports its summary. A failed backup cleanup warns and retains that backup.
If the process stops between publication renames, inspect the `.run-N-previous-*` sibling before
restoring it; a two-directory rename is not a crash-atomic filesystem transaction.

## Clean-room boundary

Every trial points `CLAUDE_CONFIG_DIR` at a temporary directory holding only the selected Claude
credential, rebuilds the child environment from an allowlist so unrelated host tokens cannot reach
model-invoked tools, and runs from a temporary git root outside this repository so the repo's own
`AGENTS.md`, `CLAUDE.md`, and local settings cannot teach a routing trial the answer. `--plugin-dir`
loads the supplied checkout directly. The runner checks its digest before execution, after the
model returns, and after plugin-dependent grading;
a change makes the trial INCONCLUSIVE, and a mismatch with the batch digest prevents the model call.
These checks detect persistent changes, not a transient edit restored between checks; keep the
candidate checkout stable for the batch. Strict MCP mode supplies an explicit empty server set.
Runtime init must report exactly one plugin with that checkout's identity and
exactly the requested tool inventory; a missing or foreign tool, an MCP server, an error result, a
nonzero exit, or — where reads were granted — a successful read outside the workspace and plugin
snapshot makes the trial **INCONCLUSIVE**, never a verdict. An auth failure aborts the batch.

This is an evaluation boundary, **not an OS sandbox**. A build lane's Bash runs on the host with
network, and the credential copy sits where an unguarded tool could reach it (the probe scans
outputs for credential markers and warns). Use only reviewed, non-secret prompts, and keep raw
traces private: they carry complete prompts and responses, session IDs, and tool payloads. Artifacts
are written owner-only under `.eval-runs/`; quote the numbers a review depends on into that review
rather than publishing the batch.

## Tests

The incident advisor now uses one seven-field board. Its structural check is
`python evals/oracles/incident-closing-fields/probe_closing_fields.py <response.md> board`.
Legacy `fields`/`checkpoint` expectations remain for historical comparisons, not current acceptance.
Completeness does not establish useful advice, factual accuracy, or continuity across turns;
those require assessment of the conversation against the supplied incident evidence.
The three `incident-companion-*` scenarios use the `incident_board` grader for structure and
the companion rubric for advice quality. Rubric calibration examples assess semantics alone;
they need not contain a board and are not complete scenario passes.

The `discovery-incident-investigation-existing-bridge` and
`discovery-incident-investigation-existing-tlc-followup` scenarios cover a current bridge and
supplied prior-turn TLC context. Their automated verdict checks routing only; manually assess
the listed response criteria and board. The follow-up scenario is a conversation snapshot,
not a native resumed session, so it does not establish runtime continuity.

`python -m pytest evals/` covers the runner, graders, and judge without a model. Gate A is
structural and does not run them; CI does.
