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
refuses any other bytes. `--overwrite` replaces a label's runs, `--regrade` re-grades saved traces
offline, and `--container IMAGE@sha256:…` runs every shell call inside a pinned, network-less
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
[`graders.py`](graders.py): `rubric`, `exact_json`, `embedded_exact_json`, `exact_fields`, `regex`,
`not_regex`, `contains_all`, `contains_any`, `not_contains`. Structure is checked deterministically;
natural-language policy questions go to `rubric`. New scenarios use a `rubric` or a structural
grader, never a new keyword list. `--agent` runs the session AS the agent, so the pin is itself the
invocation; a `skill:` instruction can be ignored, so a skill-pinned trial additionally asserts the
skill completed.

**The standing regression** is the ten build probes plus the eleven contract scenarios carrying
`split: regression`. A skill's routing positive is a **description-change check** — run it when that
skill's own description changes. `--split` is not wired into the runner's selection; use
`--scenario <id>` or run everything.

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

## Clean-room boundary

Every trial points `CLAUDE_CONFIG_DIR` at a temporary directory holding only the selected Claude
credential, rebuilds the child environment from an allowlist so unrelated host tokens cannot reach
model-invoked tools, and runs from a temporary git root outside this repository so the repo's own
`AGENTS.md`, `CLAUDE.md`, and local settings cannot teach a routing trial the answer. `--plugin-dir`
loads a stable copy of the plugin created once per batch, and strict MCP mode supplies an explicit
empty server set. Runtime init must report exactly one plugin with the snapshot's identity and
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
