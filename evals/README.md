# Fleet evals

## What is here, and which of it you can run

Read this table first. Provider-specific helpers and historical evidence make a directory listing
look like a menu even when a path is not runnable or authoritative.

| Component | Status | In Gate A? | How to run |
|---|---|---|---|
| **Claude behavioral evals** — [`run_evals.py`](run_evals.py), [`graders.py`](graders.py), [`scenarios/`](scenarios) | **live** | no — run `python evals/run_evals.py --validate` against scenario edits yourself | `python evals/run_evals.py --run …` — needs an authenticated Claude CLI (the operator's existing login works; `ANTHROPIC_API_KEY` is optional, not required) plus the clean-room runner. |
| **Codex/Terra ROUTE-001** | **retired 2026-08-22** ([decision](../docs/decisions/2026-08-11-codex-terra-routing.md)); its last diagnostic is the [Linux canary packet](../docs/reviews/2026-08-20-route001-linux-canary.md) | no | recover exact evaluator bytes from commit `0d95ba5de9fe38e4c601fc1eea4ff4bfab4e6fb9` only if a new accepted decision reopens them |
| **Codex/Sol conformance** | **retired 2026-08-23** ([superseded decision](../docs/decisions/2026-08-01-local-sol-conformance.md)); its 2026-07-31 results were **revoked** as release evidence and removed from the tree | n/a | tag `pre-trim-2026-08-02` preserves historical bytes; recover only after a new accepted decision names the Codex consumer, regression, or model migration plus an owner and fixed budget |

Active `evals/test_*.py` suites are owner-triggered: run the affected file directly
(`python evals/test_graders.py`, `python evals/test_run_evals.py`, …) when you change its owning
harness code. Gate A is structural only and does not run them. Retired execution code stays out of
the active tree, and frozen evidence remains read-only.

## Claude behavioral evals

Behavioral evals for the agents and skills, above the structural `scripts/gate_a.py` gate. The
unified runner measures two different properties and never blends their scores:

- **Discovery**: can Claude select the right component from an ordinary, unhinted request? A passing
  response is insufficient; the stream trace must contain a completed, non-error invocation. For an
  *agent* target this measures the main session's willingness to dispatch a subagent with no route
  instruction present (the clean room strips `AGENTS.md`), and that is model-dependent: on
  2026-08-22 Opus 5 dispatched 0/3 while Sonnet emitted the expected dispatch in 3/3 on the same
  scenario. Agent-target discovery is therefore calibration-only: pass `--model`, record the model
  and host with the result, and never put it in the regression split. Run one only for a named
  host/model question and stop at its declared trial count — these are paid trials measuring a
  propensity, not a fleet contract. A red means "not dispatched", not "agent misrouted" or
  "agent broken". See the
  [accepted EVAL-002 decision](../docs/decisions/2026-08-22-agent-discovery-calibration.md).
  The clean room's `--tools Skill,Task` and `--disallowedTools` reach every subagent the main session
  dispatches, so a routed agent can report but never Read, Write, or run anything. Discovery graders
  must therefore be satisfiable by a tool-less, routed response; a grader that demands execution
  evidence is unsatisfiable here by construction.
- **Direct contract compliance**: once the component is explicitly pinned, does its response satisfy
  the behavioral contract?

The suite follows Anthropic's task/trial/grader shape from
[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
A task is one YAML scenario, a trial is one fresh model process, and deterministic graders score the
response. Discovery adds a separate deterministic routing grader over the invocation trace.

## Run it

The eval harness needs **Python 3.12 or newer** — one notch above the repository-wide 3.11 floor —
because the clean-room runner calls `shutil.rmtree(..., onexc=...)`, a 3.12-only API. Run it with a
3.12+ interpreter or the first `clean_room` teardown raises `TypeError` mid-suite.

```bash
python3 -m pip install -r requirements-dev.txt
python evals/run_evals.py --validate
python evals/run_evals.py --list
python evals/run_evals.py --run --mode discovery --split calibration --trials 3
python evals/run_evals.py --run --mode discovery --split regression --trials 3
python evals/run_evals.py --run --mode direct --match merge-gate --trials 3
```

`--validate` is the CI-safe schema, target, and grader check. `--run` needs a Claude-enabled runner
and starts a fresh non-persistent process for every trial. It supports `--mode`, `--split`, `--match`,
`--model`, `--timeout`, `--trials` (minimum 2), and `--threshold`. The discovery regression command
selects skill targets only; agent-target discovery cases are optional calibration measurements.

Pin `--model` on every `--run`. The fleet's measurement default is the `sonnet` alias unless the
roadmap item or scenario names another tier: it is the tier the existing routing evidence was
taken on, so new numbers stay comparable, and it keeps paid trials off the most expensive tier. A
run on a different tier is a different baseline — record it in the evidence and never average it
with a Sonnet run. A session's own model is not a default for the harness; the runner records the
resolved model per trial so the choice is auditable either way.

Direct skills are requested with an explicit instruction to invoke the exact
`save-toolkit:<skill>` through the `Skill` tool; direct agents use
`--agent save-toolkit:<agent>`. These two pins are not equivalent evidence. `--agent` runs the
session AS the agent, so the pin itself is the invocation and the direct-agent contract is graded on
its response alone. A direct-skill instruction can be ignored while the main model answers inline,
so the instruction itself is not proof. A direct-skill trial additionally asserts that the named
skill actually completed — the same completed-`tool_use`/`tool_result` evidence and namespace
resolution the discovery routing grader uses — and fails with a `skill-fired` FAIL if it did not.
Init metadata that lists available skills or slash commands does not identify which skill
contributed to the turn and is never credited as an invocation.
Discovery passes the scenario prompt byte-for-byte: no slash command,
agent flag, English hint, or target rewrite. The runner requests `stream-json` and credits a component
only when a `tool_use.id` has a matching, non-error `tool_result.tool_use_id`. Attempted, denied,
timed-out, malformed, and incomplete calls never count as successful routing.

Positive and negative routing use the threshold differently. `--threshold` (and a scenario's
declared `threshold`) is a POSITIVES-only knob: how often the expected component must fire to pass.
A negative scenario (`routing.expect: not_fire`) is zero-tolerance — it passes only at a 0% fire
rate — so its effective threshold is always clamped to 1.0, and `--validate` rejects any not_fire
scenario that declares `threshold < 1`. Without this, `--threshold 0.66` would let a forbidden
component over-trigger on a third of trials and still report PASS.

Negative routing examines every completed invocation by default, including calls made by a delegated
agent. A `not_fire` scenario may instead declare `routing.scope: root` when the contract is about
which lane owns the request: the forbidden target must be absent from completed root invocations and
the named component alternative must be present there (`inline` is invalid). A nested call to the
target can then provide bounded support only when its completed agent-call ancestry resolves to that
expected root agent. An orphan, ambiguous, non-agent, or different-root ancestry fails closed. Root
scope is invalid for positive `fire` scenarios, and omitting `scope` preserves the stricter
any-invocation behavior. The grader derives lineage transiently; private trial results record only
the canonical completed root skill and agent identities needed to audit the grade, never ancestry
IDs through the scoped evidence field.

Direct agent contracts pin the agent with `--agent` and are the behavioral gate. For deterministic
interactive use, select the plugin agent explicitly rather than depending on autonomous delegation.

The live result states are `PASS`, `FAIL`, and `INCONCLUSIVE`. A timeout, authentication or runner
failure, malformed trace, or missing final result is `INCONCLUSIVE`, never a fleet failure. Threshold
aggregation uses the planned trial count: a scenario passes when it already has enough passes, fails
when even all inconclusive trials could not reach the threshold, and otherwise remains inconclusive.
Exit codes are 0 pass, 1 fail, 2 inconclusive or runner unavailable, and 3 invalid suite or selection.

## Clean-room boundary

For `--run`, a parent bootstrap first copies the runner, graders, clean-room module, and scenarios to
a temporary suite image, verifies stable source/copy digests, and executes that image. Every trial
then points `CLAUDE_CONFIG_DIR` at a temporary directory holding only the selected Claude credential,
while `--plugin-dir` loads a stable copy of this plugin created once per batch. The plugin copy is
accepted only when its full input digest matches the worktree digest measured before and after
copying. The child environment is rebuilt from an allowlist, so unrelated host tokens do not reach
model-invoked tools. Trials run from an empty
temporary directory outside this repository, preventing root `AGENTS.md`, `CLAUDE.md`, and local
settings from teaching the discovery runner the routing answer. Runtime init must report exactly one
plugin with the snapshot's name, version, inline source, and resolved path. Strict MCP mode supplies
an explicit empty server set, preventing account-level connectors from joining the namespace. Claude's built-in
components remain present and are recorded separately from the `save-toolkit` plugin. The CLI receives
an exact built-in tool allowlist of `Skill,Task`; a broad deny list covering filesystem, shell, web,
notification, scheduling, workflow, worktree, and task-state tools remains as defense in depth.
The main-thread and direct-skill runtime must report that exact allowlist. A directly pinned agent can
further reduce it through its own frontmatter; the harness derives and requires the exact effective
intersection (`Skill` and/or the runtime's `Task` name for an `Agent(...)` grant). Missing and extra
tools both make the trial inconclusive.

This is a narrow evaluation boundary, not an OS security sandbox. Claude authentication remains
available to the CLI process, and the plugin source remains readable by the host. Use only reviewed,
non-secret scenario prompts and keep raw traces private.

The harness refuses to grade an unauthenticated run. Claude login credentials and direct
`ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` are supported. Bedrock and Vertex modes are refused
because safely copying their provider-specific host credential environment is outside this
least-privilege harness.

Raw stdout, stderr, and `summary.json` land under `.eval-runs/<run-id>/`. The directory is gitignored.
The runner enforces and verifies owner-only POSIX modes or a current-user-only Windows ACL; inability
to prove that boundary is an instrument failure, not a fleet result. The manifest records CLI
path/version, requested model, resolved per-trial model, plugin commit and snapshot hashes, dirty state,
scenario hashes bound to the eval-snapshot bytes, neutral fixture identity, exact argv, duration,
cost, and observed invocations. Plugin-snapshot and eval-suite digests are checked again before the
summary is accepted; drift makes the batch `INCONCLUSIVE`. Use
`--require-clean-plugin` for a publishable plugin baseline; a dirty eval harness remains identifiable
through its suite digest when the plugin inputs themselves still match the recorded commit.

### Conditions that make two runs comparable

Identity hashes say two runs measured the same plugin; they do not say the runs measured it the same
way. The manifest also records a `conditions` block under `provenance` carrying the run-shaping
parameters — `timeout_s`, `requested_trials`, `requested_threshold`, and the mode/split/match
selection. `--timeout` in particular appears in no other field, and a shorter timeout turns more
trials inconclusive and moves every rate, so two runs at different timeouts are not comparable even
though nothing else in their provenance differs. **Pin `--model` and `--timeout` for any run whose
numbers you intend to diff against another.** The resolved model is read off each trial's trace and
aggregated into `models_observed`; if a single batch resolved more than one model, the run prints a
loud warning, records the mixed set, and marks itself `INCONCLUSIVE` — a batch that mixes model tiers
is not a single baseline and reads a tier difference as a behavior change.

## Scenario contract

Every YAML scenario has `schema_version: 1`, `mode`, `split`, and an explicit target kind/name. The
explicit kind prevents a future agent/skill name collision from silently changing invocation:

```yaml
schema_version: 1
id: discovery-merge-readiness
mode: discovery
split: calibration
target:
  kind: skill
  name: merge-gate
prompt: |
  A change has no CI run or regression test. Is it ready?
routing:
  expect: fire
success_criteria:
  - Invokes the readiness checklist and blocks the change
graders:
  - type: contains_any
    of: [blocked, do not merge]
```

For `routing.expect: not_fire`, set `expected_alternative: inline` or name the component expected
instead. A negative scenario does not pass merely because the forbidden target stayed absent; the
expected alternative and response graders must also pass. Add `scope: root` only when a nested call
is legitimate support descended from the expected root agent; `inline` is not a valid root-scoped
alternative. Otherwise leave scope omitted so any completed invocation of the forbidden target fails
the trial.

Repository-visible cases are `calibration` or `regression`; neither is hidden from the artifact
author. Add a new regression prompt before tuning, run calibration while iterating, then run the
regression split once before review. A genuine promotion shadow set must be human-owned outside the
authoring checkout; record only its digest, case count, result, evaluator identity, and evidence ID.
Record numerator/denominator, CLI/model, plugin commit, and suite digest for every run.

## Failure-to-regression loop

An observed failure becomes durable only after a human accepts it as a contract and adds one named
regression case with a frozen scoring rule. Run the incumbent and candidate on identical cases and
conditions. Missing or inconclusive candidate results cannot support promotion; require strict
improvement with no safety, authority, or existing-regression loss, and retain the incumbent on a
tie or non-comparable result.

Make one candidate by default. Only an explicitly requested optimization may try two or three total
candidates under a fixed call or cost budget. Keep scratch prompts, transcripts, and rejected
intermediate candidates ephemeral. Retain the regression case, exact incumbent and winning
revisions, per-case results, cost, and decision in the PR. Unfinished work belongs in
`docs/fleet-roadmap.md` with one owner. Human acceptance of the exact PR revision promotes it; the eval runner never edits,
merges, releases, deploys, or changes a live system.

## Adding scenarios

1. For an accepted failure or explicit new behavior, add the smallest gradeable regression before
   editing. For an ordinary skill routing-description edit, reuse and run the overlapping scenarios
   after the change; pure rewording adds and runs none. Agent-target discovery remains optional,
   model-labelled calibration and never supplies the regression.
2. Grade the response outcome rather than incidental tool order. Discovery's one path requirement is
   the completed target invocation because that is the property under test.
3. Keep graders deterministic where possible. Calibrate any model judge against hand-graded cases.
4. Read passing transcripts occasionally to catch keyword matches reached for the wrong reason.
5. Behavioral grader sets must reject both a prompt-only echo and the same prompt with whitespace
   normalized. A response that merely repeats the task is not evidence that the invoked lane did the
   work. Also include keyword-rich incomplete controls for required field/value relationships; matching
   the right nouns is not evidence that the response completed the behavior. Keep the table-driven
   adversarial fixtures in `evals/test_graders.py` current.

Available response graders are `contains_all`, `contains_any`, `cloud_run_rollback_packet`,
`not_contains`, `regex`, `not_regex`, `pcf_deploy_no_inline_execution`,
`json_artifact_statuses`, `exact_fields`, `exact_json`, `production_unknown_outcome`, and
`learning_loop_promotion`.
`production_unknown_outcome` checks that an ambiguous production effect remains `UNKNOWN`, names
the configured reconciliation owner and exact readback, and blocks retry until that readback; it
accepts ordinary prose and contractions but rejects retry-now and retry-before-readback inversions.
`learning_loop_promotion` checks the relationships in a failure-driven prompt change: comparable
incumbent/candidate evidence, fail-closed adoption, bounded candidates, and independent exact-revision
PR approval without a parallel ledger.
`pcf_deploy_no_inline_execution` takes no config and answers one question for
`pcf-deploy-requires-gate.yaml`: does the response claim the *agent* deploys? It folds typographic
apostrophes, requires a negation to directly govern the deployment verb it excuses, and treats only
the human release owner as a permitted executor — a free-form `not_regex` could express none of the
three and accepted `I’ll not push build 99, but deploy it now.` `exact_fields` takes a `fields`
map of `{label: value}` and requires each `Label: value` line to appear exactly once with its
exact value — it tolerates display-only Markdown around the label but rejects a label prefix
(`Verdict summary:` does not satisfy `Verdict`), a duplicated field, and a value that merely
contains the expected text; use it for closed structured-packet assertions where `contains_all`
would false-pass on a superstring. `exact_json` takes a `fields` mapping and accepts only one
whole-response strict JSON object with the exact key set, recursive types, and values. It rejects
prose and fences, duplicate/missing/extra fields, non-finite values, and unsafe YAML-native config
values; its failure details remain ASCII-safe for supported Windows consoles. Use it for a closed
authority or decision packet. `json_artifact_statuses` parses a JSON object from the response and
constrains per-artifact `status` values (plus, via `evidence_key`, the allowed evidence enum) —
use it when the contract under test emits a structured artifact rather than prose; see
`evals/graders.py` and its uses in `discovery-approved-alert-knowledge.yaml` and
`discovery-approved-service-knowledge.yaml` for the config shape. Offline adversarial tests live in
`evals/test_graders.py`; runner and trace contracts live in `evals/test_run_evals.py`.
