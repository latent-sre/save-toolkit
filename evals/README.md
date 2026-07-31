# Fleet evals

## Codex/Sol conformance

Codex has a separate conformance runner because its plugin discovery, custom-agent surface, CLI
trace, and model identifiers are not Claude contracts. It never rewrites or combines the historical
Claude/Opus baselines in this directory.

The committed manifest pins `gpt-5.6-sol`, high reasoning, a read-only sandbox, and approval policy
`never`. A direct-skill lane passes only when both conditions hold:

- the final JSON matches the deterministic oracle; and
- the trace contains exactly one completed command against the selected skill under the isolated run
  root (installed cache, frozen marketplace, or a Codex-owned staging path), and its output matches
  the full plugin skill after UTF-8/Windows PowerShell decoding normalization and, where present, one
  terminal transport newline. Chained commands, redirects, environment reads, and credential-file
  references cannot satisfy this oracle.

A `reference-direct` lane adds every named progressive-disclosure file to that same proof. It passes
only when the trace contains one separate, simple, full-content read for the skill and for every
required reference; a correct-looking answer with one missing, duplicated, chained, unrelated, or
partial read fails. The current reference lanes cover API design, TypeScript, database restore drills,
frontend design/accessibility/interface copy, and multi-component tooling.

Validate the offline contract in Gate A. Run the live lane manually:

```powershell
py -3 evals/run_codex_conformance.py --validate
py -3 evals/run_codex_conformance.py --run --output result.json
```

The live runner copies only `auth.json` into a temporary `CODEX_HOME`, registers a frozen local
marketplace snapshot, installs exactly one plugin, and executes from an empty temporary git root with
an allowlisted process environment. Raw JSONL is reduced in memory to deterministic facts and hashes;
it is not saved. This is not a credential sandbox: Codex's read-only shell can read its temporary
config tree. Therefore the runner accepts only fixed prompts committed in the manifest, and a
live run fails closed unless both plugin and harness inputs match HEAD. Live execution also refuses
custom manifest paths so an arbitrary prompt cannot share the temporary credential boundary. Missing
auth, CLI/model failure, timeout, or an incomplete trace is `INCONCLUSIVE`, never a fleet failure.
During deliberate development of team-authored inputs, `--allow-dirty-plugin` and
`--allow-dirty-harness` opt out of those checks separately; never use either for imported or
unreviewed content.

Codex plugin skills and standalone custom agents are separate host surfaces. These lanes prove plugin
installation plus direct skill/reference loading; they do not yet claim direct custom-agent
behavioral coverage.

Behavioral evals for the agents and skills, above the structural `scripts/gate_a.py` gate. The
unified runner measures two different properties and never blends their scores:

- **Discovery**: can Claude select the right component from an ordinary, unhinted request? A passing
  response is insufficient; the stream trace must contain a completed, non-error invocation.
- **Direct contract compliance**: once the component is explicitly pinned, does its response satisfy
  the behavioral contract?

The suite follows Anthropic's task/trial/grader shape from
[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
A task is one YAML scenario, a trial is one fresh model process, and deterministic graders score the
response. Discovery adds a separate deterministic routing grader over the invocation trace.

## Run it

```bash
python3 -m pip install -r requirements-dev.txt
python evals/run_evals.py --validate
python evals/run_evals.py --list
python evals/run_evals.py --run --mode discovery --split calibration --trials 3
python evals/run_evals.py --run --mode discovery --split held_out --trials 3
python evals/run_evals.py --run --mode direct --match merge-gate --trials 3
```

`--validate` is the CI-safe schema, target, and grader check. `--run` needs a Claude-enabled runner
and starts a fresh non-persistent process for every trial. It supports `--mode`, `--split`, `--match`,
`--model`, `--timeout`, `--trials` (minimum 2), and `--threshold`.

Direct skills are pinned with `/sre-agents:<skill>`; direct agents use
`--agent sre-agents:<agent>`. Discovery passes the scenario prompt byte-for-byte: no slash command,
agent flag, English hint, or target rewrite. The runner requests `stream-json` and credits a component
only when a `tool_use.id` has a matching, non-error `tool_result.tool_use_id`. Attempted, denied,
timed-out, malformed, and incomplete calls never count as successful routing.

Agent descriptions are routing hints, not a dispatch guarantee. In one-shot headless Claude Code,
the main model can answer a request inline even when the matching plugin agent is available and its
description says to use it proactively. Treat agent-discovery scores as an observational host/model
metric; do not infer that a failed discovery trial means the agent's behavior is broken. Direct agent
contracts pin the agent with `--agent` and are the behavioral gate. For deterministic interactive use,
select the plugin agent explicitly rather than depending on autonomous delegation.

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
components remain present and are recorded separately from the `sre-agents` plugin. The CLI receives
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
expected alternative and response graders must also pass.

Existing tuned cases are `direct/calibration`. Never relabel a case held-out after tuning against it.
Add a genuinely new held-out prompt, run calibration while iterating, then run held-out once before
accepting the prompt change. Record numerator/denominator, CLI/model, plugin commit, and suite digest.

## Adding scenarios

1. Add an eval before changing a skill or agent when the outcome is gradeable: routing, gates,
   authorization, prompt-injection refusal, or another deterministic decision.
2. Grade the response outcome rather than incidental tool order. Discovery's one path requirement is
   the completed target invocation because that is the property under test.
3. Keep graders deterministic where possible. Calibrate any model judge against hand-graded cases.
4. Read passing transcripts occasionally to catch keyword matches reached for the wrong reason.

Available response graders are `contains_all`, `contains_any`, `not_contains`, `regex`, and
`not_regex`. Their offline adversarial tests live in `evals/test_graders.py`; runner and trace
contracts live in `evals/test_run_evals.py`.
