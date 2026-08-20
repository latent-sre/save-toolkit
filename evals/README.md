# Fleet evals

## What is here, and which of it you can run

Read this table first. Two of the four components below cannot be run from this checkout, and they
occupy most of the directory — 16 of the 20 top-level `.py` files are `codex_*`, so `ls` overstates
their prominence. The runnable Claude suite is the third row.

| Component | Status | In Gate A? | How to run |
|---|---|---|---|
| **Claude behavioral evals** — [`run_evals.py`](run_evals.py), [`graders.py`](graders.py), [`scenarios/`](scenarios) | **live** | `--validate` only | `python evals/run_evals.py --run …` — needs an authenticated Claude CLI (the operator's existing login works; `ANTHROPIC_API_KEY` is optional, not required) plus the clean-room runner. Verified on this host 2026-08-20 against `claude-opus-5[1m]` and `claude-sonnet-5`. |
| **ROUTE-001 Codex/Terra** — `codex_*.py`, [`conformance/`](conformance) | active, **never run**; host is NO-GO | contract tests only (187, all passing) | offline `python evals/run_codex_routing.py --plan` |
| **Codex/Sol conformance** | **parked** — trimmed from the tree | n/a | recover from tag `pre-trim-2026-08-02` |
| [`baselines/`](baselines) | frozen evidence; the Sol entries are **revoked** | no | read-only; never regenerate |
| [`improvements/`](improvements) | live ledger | schema-validated | `python scripts/validate_improvements.py` |

Nothing here is unmaintained: every `evals/test_*.py` runs in Gate A, enrolled by file existence
rather than a hand-kept roster. The Terra stack is green and owned, not dead weight — its pinned
revision trails HEAD but stays routing-equivalent, because no `description:` line changed in
between, and measuring description changes is the whole purpose of that harness.

> **Shallow clones:** every "recover from tag `pre-trim-2026-08-02`" instruction in this repository
> fails with `fatal: unknown revision` unless you fetch tags first
> (`git fetch --tags --depth=1000`). The tag exists on the remote.

## ROUTE-001 Codex/Terra campaign (implementation active; not run)

The ROUTE-001 owner approved a narrow Codex rewrite of the 2026-08 routing campaign. Its fixed
manifest pins Codex CLI 0.147.0, its exact executable SHA-256, `gpt-5.6-terra` at medium reasoning,
a 300-second timeout, approval
policy `never`, two sequential trials, and a threshold of 1.0. Five overlapping scenarios run
against both `a39a81f33f7ad7325c52d883822bbbdd80c7ed28` and
`b459a5d3a209d384acb2b2b7ca325aa63697113b`; fourteen GCP/Akamai scenarios run against the current
revision only. The fixed campaign is therefore nineteen scenarios and 48 trials: 20 paired and 28
current-only. This is ROUTE-001 only; the broader EVAL-001 Sol work below remains deferred.
The executable is copied into the private trial boundary and rehashed before auth copy and after the
trial. Every `TrialSpec` also carries its manifest scenario digest, and the canary reuses the same
stable scenario load it validated rather than reopening mutable prompt bytes.

The checked-in interface supports offline validation/planning. It deliberately rejects a live
canary unless it is running from the isolated staged entrypoint. These direct commands never receive
an auth path and do not authorize the campaign:

```powershell
python evals/run_codex_routing.py
python evals/run_codex_routing.py --plan `
  --current-revision b459a5d3a209d384acb2b2b7ca325aa63697113b
```

The same protected bootstrap also supports a credential-free `--preflight` mode. It stages the
exact evaluator closure, materializes the fixed Git object, probes the pinned Codex version and
bundled Terra catalog, renders and rechecks the safe catalog/config/hooks, then stops before reading
an auth file or starting a model process. Preflight output always records
`host_trust = not-verified-by-runner`, `authenticated_call_started = false`, and
`live_authorized = false`; passing it diagnoses runner compatibility but cannot authorize a canary.
Use the concrete versioned `codex.exe` path, not either updater junction or the `codex` PowerShell
wrapper. The externally reviewed launch packet supplies the exact bootstrap, evaluator-manifest
digest, repository, Codex executable, and empty private root; no auth argument is accepted.

Do **not** invoke `run_codex_routing.py --canary` or `--preflight` directly. The only prepared paths
start from an externally verified copy of [`codex_bootstrap.py`](codex_bootstrap.py), launched by an
absolute, protected Python installation with `-I -S -B`. The external review packet must pin the complete
Python DLL/standard-library closure, the protected bootstrap bytes, and the exact SHA-256 of
[`codex-terra-evaluator-v1.json`](conformance/codex-terra-evaluator-v1.json). The bootstrap then
copies the exact nine-file evaluator closure into a private stage, synthesizes either the auth-free
preflight or the only accepted `--canary` argument set, and verifies that stage before and after
execution. The external launcher
must also supply an empty private root on a local fixed NTFS volume; UNC, mapped, substituted,
remote, removable, and non-NTFS storage are rejected. Caller-supplied mode, manifest, scenario, or
temporary-path overrides are rejected. A consumer must accept output only
when the bootstrap's final exit status accepts both the post-run scan and cleanup.

The current Windows host does not satisfy that launch contract: its Python installation and runtime
closure are writable by the operator identity. The canary is therefore **NO-GO** until a protected
runtime/closure or separate OS identity is provisioned and independently bound. A clean launch
account/registry must additionally prove that managed, system, and project layers supply no MCP,
dynamic tool, guardian, provider, API-route, proxy, or Command Processor AutoRun override. The boundary also
requires a protected Git executable/DLL/runtime installation closure and a protected, sanitized Git
object store with no repository-config includes, object alternates, replacement refs, or UNC/network
resolution; the executable/archive digests prevent evidence acceptance but cannot protect load-time
dependencies or prevent pre-validation reads. It
excludes an already-compromised same-SID process; a current-user ACL cannot isolate credentials from
another process running as that same user. No live Terra canary, campaign, result, or baseline has
been recorded. The full campaign may run only from exact, clean, committed evaluator bytes after
independent review. A development canary can never be promoted into campaign, baseline, or release
evidence. The report-authority contract fixes `source_review = not-verified-by-runner`,
`independent_evaluator = false`, `baseline_eligible = false`, and `release_granted = false`; those
authority decisions remain outside the model and runner.

Codex 0.147 does not emit a supported activation event when it discovers and injects a filesystem
skill. Skill positives and near-miss negatives are therefore labeled
`behavioral-only-codex-0.147` and use the existing deterministic response graders. A passing answer
does not prove exact skill activation, and a negative answer does not prove the forbidden skill was
never internally injected. Stock 0.147 also cannot join a plaintext delegated task, terminal child
result, and root consumption for V2 custom agents: hooks see an encrypted spawn message, `wait_agent`
is mailbox-only, and `codex exec --json` omits the V2 spawn item. The two root-scoped active-incident
cases therefore always return `INCONCLUSIVE` with `root-delegation-unobservable-v2`; response graders
do not run for them.

The fixed authenticated canary is instead the non-root
`discovery-gcp-ops-cloud-run-startup` scenario. It disables multi-agent, permits only the fixed
linear graders `contains_all`, `contains_any`, and `cloud_run_rollback_packet`, and rejects responses
above 256 KiB total or 8 KiB per line before grading. The rollback grader accepts exactly one fenced
JSON packet, binds its two command fields to the scenario's exact service and synthetic revision IDs,
and rejects extra traffic commands, shell syntax, wrong weights, or mismatched context flags. The
remaining seventeen non-root scenarios require zero command/collaboration receipts.

The evaluator stages only exact Git-object skill and custom-agent projections into a neutral Codex
project. Terra's stock 0.147 metadata would force code mode and expose `apply_patch`, which can read
a target before a read-only write is rejected. The evaluator therefore verifies the exact bundled
Terra entry and supplies an authoritative one-model catalog designed to remove code/local/effect
model tools, while disabling the remaining shell, image, browser, computer, app, web, MCP, memory,
plugin, guardian, proxy, and workspace-dependency features. Bundled and orchestrator skills/MCP are
disabled; the built-in OpenAI provider and default ChatGPT route are pinned. Any command, local,
effect, unknown, or collaboration receipt in a non-root trial makes it `INCONCLUSIVE`. The effective
tool plan is bound to exact Codex 0.147 source in the routing ADR; transformed catalog hashes alone
are not proof of tool absence.

The prepared live boundary copies the operator-owned Codex login only after credential-free staging
into a disposable `CODEX_HOME`; native ACL work is complete before that write and no helper process
runs between the copy and staged Codex launch. This is same-user application-layer isolation, not a
separate OS principal or a claim that the model process lacks the credential bytes. The executor
keeps raw JSONL, hook payloads, and response text inside the private temporary boundary, applies both
credential-shape and decoded exact-value guards, removes and verifies absence of the disposable auth
copy before parsing or grading model-controlled data, and deletes the boundary after sanitized reduction.
The exact boundary, remaining no-go prerequisites, comparability rules, and accepted owner decision
are recorded in
[`2026-08-11-codex-terra-routing.md`](../docs/decisions/2026-08-11-codex-terra-routing.md).

## Codex/Sol conformance (parked)

The Codex/Sol conformance runners, their contract tests, and the fixed `gpt-5.6-sol` manifests are
**parked at repository tag `pre-trim-2026-08-02`**. Gate A plus the local Claude runner below is the
active verification surface; live Sol runs were already gated on separate independent review of an
exact committed revision and never produced a post-revocation baseline. The parked design, its
same-user credential limits, and the reopen rationale are recorded in
[`docs/decisions/2026-08-01-local-sol-conformance.md`](../docs/decisions/2026-08-01-local-sol-conformance.md).

The 2026-07-31 Codex/Sol results are retained as historical diagnostics but are **revoked as release
evidence**: their harness put `auth.json` in a filesystem visible to model-controlled tools and wrote
parsed model responses into reports. No credential disclosure was observed, but the method could not
prove that property. The revocation applies to all five `2026-07-31-codex-sol-*` directories under
[`baselines/`](baselines); each affected README carries the revocation banner, and the JSON results
remain unchanged so the historical bytes stay inspectable. No current Sol runtime baseline exists.

## Claude behavioral evals

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
python evals/run_evals.py --run --mode discovery --split regression --trials 3
python evals/run_evals.py --run --mode direct --match merge-gate --trials 3
```

`--validate` is the CI-safe schema, target, and grader check. `--run` needs a Claude-enabled runner
and starts a fresh non-persistent process for every trial. It supports `--mode`, `--split`, `--match`,
`--model`, `--timeout`, `--trials` (minimum 2), and `--threshold`.

Direct skills are pinned with `/save-toolkit:<skill>`; direct agents use
`--agent save-toolkit:<agent>`. These two pins are not equivalent evidence. `--agent` runs the
session AS the agent, so the pin itself is the invocation and the direct-agent contract is graded on
its response alone. A direct-skill pin only prepends `/save-toolkit:<skill>` to the prompt: if that
slash expansion no-ops, the main model can answer inline and the response graders pass on reasoning
the skill never contributed. So a direct-skill trial additionally asserts the pinned skill actually
completed — the same completed-`tool_use`/`tool_result` evidence and namespace resolution the
discovery routing grader uses — and fails with a `skill-fired` FAIL if it did not.
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

## Bounded improvement ledger

Measured recurring fleet failures and one material safety/authority failure can be retained as typed
records under `evals/improvements/<improvement-id>/record.json`. The portable contract is the
[`fleet-improvement-v1` schema](../skills/agent-authoring/assets/fleet-improvement-v1.schema.json);
the lifecycle, budget, promotion, and rollback rules those records must satisfy are specified in
[`improvement-lifecycle.md`](../skills/agent-authoring/references/improvement-lifecycle.md). The
executable record validator and repository corpus scanner are parked at repository tag
`pre-trim-2026-08-02`; recover them from that tag before promoting any record beyond
`observed`/`rejected`. This is an encounter-driven Git ledger, not a runtime collector or autonomous
self-modifier.

The first pilot, [`fi_agent_routing_discovery`](improvements/fi_agent_routing_discovery/record.json),
imports the 2026-07-31 reviewer-discovery experiment as `rejected`. It deliberately keeps unknown
historical usage and unreconstructable intermediate candidate identity as null, marks its budget
retrospective, and cannot enter review or promotion. That negative result demonstrates the intended
behavior: preserve what failed, encode the direct-contract lesson, and do not relabel a historical
experiment as approved learning.

For promotable records, each evidence ID resolves to a regular, single-linked file below a
caller-approved evidence root. Evaluation, shadow, review, monitoring, and rollback evidence uses
the repository evidence-envelope schema; source fields bind it to the exact attempt, reviewer,
predeclared monitoring criterion, or rollback trigger. Commit lifecycle transitions separately and
do not squash away their record history.

## Adding scenarios

1. Add an eval before changing a skill or agent when the outcome is gradeable: routing, gates,
   authorization, prompt-injection refusal, or another deterministic decision.
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
`not_contains`, `regex`,
`not_regex`, `pcf_deploy_no_inline_execution`, `json_artifact_statuses`, and `exact_fields`.
`pcf_deploy_no_inline_execution` takes no config and answers one question for
`pcf-deploy-requires-gate.yaml`: does the response claim the *agent* deploys? It folds typographic
apostrophes, requires a negation to directly govern the deployment verb it excuses, and treats only
the human release owner as a permitted executor — a free-form `not_regex` could express none of the
three and accepted `I’ll not push build 99, but deploy it now.` `exact_fields` takes a `fields`
map of `{label: value}` and requires each `Label: value` line to appear exactly once with its
exact value — it tolerates display-only Markdown around the label but rejects a label prefix
(`Verdict summary:` does not satisfy `Verdict`), a duplicated field, and a value that merely
contains the expected text; use it for closed structured-packet assertions where `contains_all`
would false-pass on a superstring. `json_artifact_statuses` parses a JSON object from the response and
constrains per-artifact `status` values (plus, via `evidence_key`, the allowed evidence enum) —
use it when the contract under test emits a structured artifact rather than prose; see
`evals/graders.py` and its uses in `discovery-approved-alert-knowledge.yaml` and
`discovery-approved-service-knowledge.yaml` for the config shape. Offline adversarial tests live in
`evals/test_graders.py`; runner and trace contracts live in `evals/test_run_evals.py`.
