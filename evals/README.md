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

Validate the offline contract in Gate A:

```powershell
py -3 evals/run_codex_conformance.py --validate
```

Live execution is an operator-run local operation. Source review is a separate prerequisite:

```powershell
py -3 evals/run_codex_conformance.py --run --output .eval-runs/codex-sol-skills.json
py -3 evals/run_codex_agent_conformance.py --run --output .eval-runs/codex-sol-agents.json
```

Each `--output` path must be new. A repository-local report is accepted only under `.eval-runs/`;
the runner never overwrites an existing file or follows a linked/reparse output path.

The runners use the existing Codex login from `CODEX_HOME` (or `~/.codex/auth.json`), copy only
`auth.json` into a disposable home, and delete that home before returning a sanitized report. An
explicit `--auth-file` is available for an equivalent operator-owned login file. This is not a
security boundary: model-controlled read-only tools can read the same-user session file. Therefore
the live runners accept only this repository checkout and the fixed committed manifests. Review and
commit source before running; never use this mode to inspect a hostile or unreviewed external PR.

The isolated run still registers a frozen marketplace snapshot, installs exactly one plugin, and
executes from an empty temporary git root with an allowlisted process environment. Raw JSONL and
parsed final messages are reduced to hashes and equality facts; neither is written to the report.
The reports retain exact commit/tree identities, input digests, verdicts, usage, timeouts, and typed
evidence envelopes, but no auth-file path, auth digest, raw response, or parsed final message.
Skill invocations structurally remove collaboration tools by setting `agents.enabled=false` and
disabling both multi-agent feature versions. Agent invocations pin the V1 registry to one live child
with depth one and the V2 registry to root plus one live child. Both runners also enable Codex's
140,000-token rollout budget, which is shared by the root and subagents. That runtime budget accounts
weighted non-cached input and output after each response, so one response can cross it and cached
input is outside that counter. Each lane and suite therefore retains a separate trusted numeric
post-response acceptance ceiling; a missing, malformed, or excessive usage record stops execution
before another lane. These controls are not a provider-side spend limit, so the operator's account
must retain its own quota. The live path requires fixed manifests and clean plugin/harness inputs by
default; scoped ignored untracked files count as dirty because the plugin snapshot would otherwise
include bytes absent from the commit. Scoped tracked files marked `assume-unchanged` or
`skip-worktree` also count as dirty rather than hiding working-tree changes. Missing login,
CLI/model failure, timeout, or an incomplete trace is `INCONCLUSIVE`, never a
fleet failure. Dirty development switches remain available for harness iteration, but the resulting
report has `exact_revision: false` and an `inconclusive` evidence verdict. Every report—clean or
dirty—sets `source_review` to `not-verified-by-runner`, `independent_evaluator` to false, and both
`baseline_eligible` and `release_granted` to false. To accept a behavioral baseline, pair a
clean exact-revision report with independent review evidence for the same immutable commit; that
outside review never changes the runner's authority labels.

Codex plugin skills and standalone custom agents are separate host surfaces. These lanes prove plugin
installation plus direct skill/reference loading. The standalone agent runner proves its own surface:

```powershell
py -3 evals/run_codex_agent_conformance.py --validate
```

The agent runner freezes and installs all eight generated custom-agent TOMLs in the same isolated
Codex home as the plugin, then runs one no-history delegation lane per agent plus behavior lanes for
both trust-separated research roles, a supplied-diff authorization review by `reviewer`, and the
non-executing evidence boundary of `scribe`. The full
plugin snapshot must contain only passive skill components, and every custom-agent TOML must use the
fixed constrained field set. Prompt or capability changes are committed and independently reviewed
before a live agent baseline can exercise them. A lane passes only
when
the private session rollouts prove all of the following:

- exactly one successful `spawn_agent` call names the expected role and `fork_turns: none`;
- the parent receives exactly one completion from the named child (an explicit wait is optional when
  the child completes before the parent's next turn);
- exactly one child session is linked to the parent with the expected `agent_role`;
- the child receives the exact installed `developer_instructions` bytes;
- parent and child runtime contexts expose `gpt-5.6-sol`, high reasoning, read-only sandboxing, and
  approval policy `never`; and
- the text-only child makes no tool calls, its canary or structured refusal oracle matches, the
  parent's exact JSON oracle matches, and stderr contains no runtime error.

Self-reported delegation is deliberately insufficient. This catches the observed failure mode where
Codex rejected an incompatible spawn request but the main model still returned `delegated: true`.
Unlike the ephemeral skill JSONL, the temporary parent/child turn context exposes the resolved model.
The runner reduces those rollouts to hashes and structural facts, then deletes the complete temporary
Codex home, its copied login, and raw sessions before writing the sanitized report. Live agent runs
require clean plugin, generated-agent, and harness inputs by default; the three separate
dirty-development switches always produce non-exact, inconclusive evidence.

The 2026-07-31 Codex/Sol results are retained as historical diagnostics but are **revoked as release
evidence**. Their harness put `auth.json` in a filesystem visible to model-controlled tools and wrote
parsed model responses into reports. No credential disclosure was observed, but the method could not
prove that property. This revocation applies to all five `2026-07-31-codex-sol-*` directories,
including the former current snapshots:

- [`2026-07-31-codex-sol-expanded-conformance`](baselines/2026-07-31-codex-sol-expanded-conformance)
  - formerly 11/11 skill and progressive-reference lanes;
- [`2026-07-31-codex-sol-seven-agent-conformance`](baselines/2026-07-31-codex-sol-seven-agent-conformance)
  - formerly 9/9 custom-agent delegation and trust-boundary behavior lanes.

The JSON results remain unchanged so the historical bytes are inspectable; each affected README now
carries the revocation. A new current Sol baseline does not exist until both local runners complete
against a clean committed revision and the sanitized reports are paired with independent review of
that same revision. The governing rationale and trust labels are recorded in the
[`local Sol conformance decision`](../docs/decisions/2026-08-01-local-sol-conformance.md).

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

Repository-visible cases are `calibration` or `regression`; neither is hidden from the artifact
author. Add a new regression prompt before tuning, run calibration while iterating, then run the
regression split once before review. A genuine promotion shadow set must be human-owned outside the
authoring checkout; record only its digest, case count, result, evaluator identity, and evidence ID.
Record numerator/denominator, CLI/model, plugin commit, and suite digest for every run.

## Bounded improvement ledger

Measured recurring fleet failures and one material safety/authority failure can be retained as typed
records under `evals/improvements/<improvement-id>/record.json`. The portable contract is the
[`fleet-improvement-v1` schema](../skills/agent-authoring/assets/fleet-improvement-v1.schema.json);
the bundled [validator](../skills/agent-authoring/scripts/fleet_improvement.py) additionally enforces
append-only observations/evidence/attempts/reviews, predeclared reservations plus evaluator-recorded
actual usage, cumulative three-attempt and resource budgets, legal transitions, caller-owned path
roots, resolved evidence-envelope hashes, exact candidate/review/merge/monitor/rollback bindings,
and external transition authority. The portable contract hard-caps each record at 60 model turns,
60 evaluator calls, 1,000,000 tokens, 14,400 wall-clock seconds, USD 100, and a 16 KiB aggregate
target-path argv; trusted callers may lower those ceilings, while record content cannot raise them.
For a fresh evaluation, the envelope producer must match `evaluation.evaluator`, the envelope must
repeat the reservation and `actual_usage` exactly, and each actual value must fit its reservation.
Monitoring evidence is likewise bound to `monitoring.observed_by`. Any retained protected-shadow
result must pass before review or promotion, duplicate JSON object keys are rejected before lifecycle
validation, and schema plus executable validation require literal uppercase `T` and `Z` in UTC
timestamps.

The canonical `sre-agents-git-artifact-selection-v1` digest covers the requested path set and each
selected regular Git blob's mode, canonical path, size, and raw SHA-256. Candidate subjects must be
real commits descended from their recorded parent and touch every declared target. Promotion is the
exact reviewed commit or a two-parent merge with it as one direct parent. The other parent must
descend from the base and have the base target digest; that base must be the parents' unique actual
merge base; and an object-only full-tree comparison rejects merge-only files or divergent parent
changes. Raw trees must use canonical Git ordering and valid modes/types, contain no empty injected
directories, stay within hard bounds, expose a cross-host-portable UTF-8 NFC namespace, and prove
that every non-gitlink leaf exists as an actual Git blob. The merge cannot change the reviewed
artifact digest. Trusted Git queries ignore commit graphs, grafts, and replace objects and supervise
input, output, and process completion under one deadline.

A rollback must be the exact one-parent inverse of the candidate-exclusive promoted delta, or a
two-parent object-only application merge of that revert. It must preserve unrelated pre-rollback
bytes, reject later candidate-path drift and rollback-only injection, descend from the promotion,
and restore the base artifact digest. Prior monitoring remains attached when a later security,
authority, merge, or owner trigger fires. A direct `merged -> rolled_back` transition cannot add
monitoring; monitoring failures and inconclusive results must first enter `monitoring`, then roll
back separately. An encoded terminal lesson must resolve to a regular Git blob at its ledger
revision. Subject-bound shadow, evaluation, and review envelopes name the exact digest algorithm,
so older incompatible repository digests cannot become promotion evidence. A `changes_requested`
review first enters `in_review`; an author retry back to `candidate` or a reviewer/protected-workflow
rejection is a separate transition. Records must predeclare `monitoring_fail`,
`monitoring_inconclusive`, `security_finding`, `authority_revoked`, and `merge_error` as rollback
triggers; `manual_owner_decision` is optional.

The corpus scanner, `py -3 scripts/validate_improvement_ledger.py --repository-root .`, discovers
every record and rejects promoted bootstrap states, deletions anywhere in merged history including
merge-result-only deletions, non-linear record histories, and cross-record
fingerprint/event/evidence duplication, then replays retained Git transitions. It requires complete
history (for GitHub Actions, `actions/checkout` needs `fetch-depth: 0`). Its synthetic history roles
validate structure only; protected workflows authenticate the real actors. This is an
encounter-driven Git ledger, not a runtime collector or autonomous self-modifier.

Run the corpus scanner and repository evidence validator only from an `sre-agents` source checkout.
An installed skill bundle includes the portable schema and standalone validator, but not the
repository-root `scripts/evidence_envelope.py` or `scripts/validate_improvement_ledger.py`; installed
callers must supply equivalent trusted code or use the source checkout. The manually disabled
**Validate fleet** workflow stays untouched; before re-enabling it, set its checkout to
`fetch-depth: 0` so the ledger scan does not run against shallow history.

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

Available response graders are `contains_all`, `contains_any`, `not_contains`, `regex`, and
`not_regex`. Their offline adversarial tests live in `evals/test_graders.py`; runner and trace
contracts live in `evals/test_run_evals.py`.
