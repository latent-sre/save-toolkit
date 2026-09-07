# Fleet evals

One runner, [`build_probe.py`](build_probe.py). It grades three kinds of scenario, decided by the
keys a spec carries rather than by a mode field.

| Kind | Where | Session | Graded on |
|---|---|---|---|
| **routing** | [`scenarios/`](scenarios) | main session, `--tools Skill,Task` (a spec may widen it), no `--agent` | one check: did the named component complete a non-error invocation — or, for a negative, stay out of the way |
| **contract** | [`scenarios/`](scenarios) | `agent:` pinned with `--agent`, or `skill:` pinned by instruction | `graders:` over the returned text |
| **build** | [`build-scenarios/`](build-scenarios) | `agent:` pinned, its real tools pre-approved, in a seeded fixture repo | `checks:` over **outcomes** in code |

Two directories because the build fixtures carry inline repos hundreds of lines long and would bury
the short routing specs. The runner does not care which one a spec came from.

## Run it

Needs **Python 3.12+** (the clean-room teardown uses `shutil.rmtree(..., onexc=...)`).

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

## Scenario contract

```yaml
id: discovery-production-triage-recommend-only
split: regression
prompt: |
  Payments latency just tripled in production and errors are climbing. No mitigation is
  authorized yet. Tell me what to do.
target: {kind: skill, name: incident-command}
routing: {expect: fire}
success_criteria:
  - Autonomously invokes the incident-command workflow
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
stays reviewable, runnable, and inside the `evals_python_lines` ceiling — which now counts the four
Python oracles there, but not the TSX one, since it counts `*.py` only.

**The standing regression** comprises the build probes and the contract scenarios carrying
`split: regression`. A skill's routing positive is a **description-change check** — run it when that
skill's own description changes. `--split` is not wired into the runner's selection; use
`--scenario <id>` or run everything.

The return-and-resume cases separate two boundaries: the `agent-direct-...helper-return` and
`agent-direct-...partial-slice-to-caller` scenarios grade supplied-state decisions; the
[`scribe return build probe`](build-scenarios/build-software-engineer-resumes-after-scribe.yaml)
requires a completed child call and the integrated runbook/README artifacts. Its automated checks
do not identify who edited the README or when; inspect the raw trace before claiming that the
parent resumed after the child returned.

Agent-target routing is **calibration-only**: main-session dispatch is a model and host propensity,
not a fleet contract (on 2026-08-22 Opus 5 dispatched 0/3 where Sonnet did 3/3). Record the model
and host with any such result. See the
[accepted EVAL-002 decision](../docs/decisions/2026-08-22-agent-discovery-calibration.md).

## The rubric judge

`rubric` graders spawn one clean-room, tool-less `claude -p` turn against a named rubric in
[`rubrics.yaml`](rubrics.yaml). It fails closed: a timeout, auth failure, malformed envelope,
unknown verdict, a verdict from a model other than the pinned one, or evidence not quoted verbatim
from the graded response all return FAIL with a `judge inconclusive:` detail.

```bash
python evals/judge.py --calibrate
```

measures every rubric against [`rubrics-calibration.yaml`](rubrics-calibration.yaml) and exits
non-zero below 0.95 agreement or on any inconclusive case. Run it after a rubric edit. Its cache
lives under `.eval-runs/judge-calibration/` and is shared across runs, so re-checking after a rubric
edit only pays for what changed. The contract is the
[rubric-judge evaluation ADR](../docs/decisions/2026-09-01-rubric-judge-evaluation-contract.md).

## Provenance

Every run records the plugin root's commit, plugin-input dirty state, and a path-bound source digest
over `agents/`, `skills/`, `commands/`, `hooks/`, the manifest, and the guard scripts
(`provenance.json`, the trace summary, the summary line), plus the requested and resolved model,
trials, timeout, per-trial duration, cost, and the exact argv. Identity hashes say two runs measured
the same plugin; they do not say the runs measured it the same way — **pin `--model` and `--timeout`
for any numbers you intend to diff.**

Machine records retain the complete candidate digest and a scenario digest covering the spec, its
referenced oracle files, and the rubric definitions the judge actually consumes. The judge caches
rubrics on first load for the process; file edits take effect in a new process. The digest uses those
same cached definitions. Appending requires candidate and scenario identities to match the existing
batch before any model call. Scenario inputs are checked again before and after grading;
a change in the effective definitions or oracle bytes invalidates the trial. Regrade identifies each assertion by its scenario digest and
position and retains live-judge/workspace verdicts from `grading.original.json`; duplicate display
labels cannot substitute one verdict for another. Legacy records without identities, changed
scenarios, and missing original assertions are INCONCLUSIVE and require a fresh trial. Regrade does
not call a judge or recover workspace evidence that was never recorded.

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

`python -m pytest evals/` covers the runner, graders, and judge without a model. Gate A is
structural and does not run them; CI does.
