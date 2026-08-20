# Fleet evals

## What is here, and which of it you can run

Read this table first. Two of the four components below cannot be run from this checkout, and they
occupy most of the directory — 16 of the 20 top-level `.py` files are `codex_*`, so `ls` overstates
their prominence. The runnable Claude suite is the third row.

| Component | Status | In Gate A? | How to run |
|---|---|---|---|
| **Claude behavioral evals** — [`run_evals.py`](run_evals.py), [`graders.py`](graders.py), [`scenarios/`](scenarios) | **live** | `--validate` only | `python evals/run_evals.py --run …` — needs an authenticated Claude CLI (the operator's existing login works; `ANTHROPIC_API_KEY` is optional, not required) plus the clean-room runner. Verified on this host 2026-08-20 against `claude-opus-5[1m]` and `claude-sonnet-5`. |
| **ROUTE-001 Codex/Terra** — `codex_*.py`, [`conformance/`](conformance) | active; Linux preflight passed; fourteen development probes: four inconclusive, six valid `FAIL`, four `PASS`; campaign never run | contract tests only | [`codex_container.py`](codex_container.py) through an exact image ID |
| **Codex/Sol conformance** | **parked** — trimmed from the tree | n/a | recover from tag `pre-trim-2026-08-02` |
| [`baselines/`](baselines) | frozen evidence; the Sol entries are **revoked** | no | read-only; never regenerate |
| [`improvements/`](improvements) | live ledger | schema-validated | `python scripts/validate_improvements.py` |

Nothing here is unmaintained: every `evals/test_*.py` runs in Gate A, enrolled by file existence
rather than a hand-kept roster. The Terra stack is green and owned, not dead weight. Its current
snapshot is one exact Git object with a separately computed tree digest; a later checkout does not
silently become campaign input.

> **Shallow clones:** every "recover from tag `pre-trim-2026-08-02`" instruction in this repository
> fails with `fatal: unknown revision` unless you fetch tags first
> (`git fetch --tags --depth=1000`). The tag exists on the remote.

## ROUTE-001 Codex/Terra campaign (implementation active; campaign not run)

The ROUTE-001 owner approved a narrow Codex rewrite of the 2026-08 routing campaign. The canonical
Linux manifest now pins Codex CLI 0.148.0 and its exact executable SHA-256; the validation-only
historical Windows manifest retains its reviewed 0.147.0 bytes. Both pin `gpt-5.6-terra` at medium reasoning,
a 300-second timeout, approval
policy `never`, two sequential trials, and a threshold of 1.0. Five overlapping scenarios run
against both `a39a81f33f7ad7325c52d883822bbbdd80c7ed28` and
`7aef80aede95394f6c4237ed2aedb911e141c3c0`; fourteen GCP/Akamai scenarios run against the current
revision only. The fixed campaign is therefore nineteen scenarios and 48 trials: 20 paired and 28
current-only. This is ROUTE-001 only; the broader EVAL-001 Sol work below remains deferred.
The historical Windows arm copies the executable into its private trial boundary. The canonical
Linux arm keeps the complete Codex package tree protected inside an immutable non-root image and
rehashes the executable before and after the trial. Every `TrialSpec` also carries its manifest
scenario digest, and the canary reuses the same
stable scenario load it validated rather than reopening mutable prompt bytes.

The checked-in interface supports offline validation/planning. It deliberately rejects a live
canary unless it is running from the isolated staged entrypoint. These direct commands never receive
an auth path and do not authorize the campaign:

```powershell
python evals/run_codex_routing.py
python evals/run_codex_routing.py --plan `
  --current-revision 7aef80aede95394f6c4237ed2aedb911e141c3c0
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

Do **not** invoke `run_codex_routing.py --canary` or `--preflight` directly. The canonical Linux path
uses [`codex_container.py`](codex_container.py) with an exact image ID; the historical Windows path
starts from an externally verified copy of [`codex_bootstrap.py`](codex_bootstrap.py), launched by an
absolute, protected Python installation with `-I -S -B`. A Windows review packet must pin the complete
Python DLL/standard-library closure, the protected bootstrap bytes, and the exact SHA-256 of
[`codex-terra-evaluator-v1.json`](conformance/codex-terra-evaluator-v1.json). The bootstrap then
copies the exact ten-file evaluator closure into a private stage, synthesizes either the auth-free
preflight or the only accepted `--canary` argument set, and verifies that stage before and after
execution. The external launcher
must also supply an empty private root on a local fixed NTFS volume; UNC, mapped, substituted,
remote, removable, and non-NTFS storage are rejected. Caller-supplied mode, manifest, scenario, or
temporary-path overrides are rejected. A consumer must accept output only
when the bootstrap's final exit status accepts both the post-run scan and cleanup.

For a Linux development canary, invoking `codex_container.py canary` is the authorization for exactly
one paid trial. That single command validates all live inputs, runs the same image credential-free and
networkless first, stops if preflight fails, and otherwise runs one authenticated canary with no retry.
It prints and writes only this compact summary to `<output-root>/canary-result.json`: image ID,
preflight result, canary state/reason codes, failed numeric grader indices for a valid behavioral
verdict, the exact canary invocation mode and prompt SHA-256, and token usage when the accepted trace
contains it.
Repeated development attempts update that one file; they do not require a new narrative review packet.
Update durable campaign documentation only when a canary produces a valid verdict, the instrument
contract changes, or the work is deliberately closed. Standalone `preflight` remains available for a
credential-free diagnostic, and `campaign` retains its separate 48-trial journal and review gates.

The approved three-round diagnostic uses the existing one-call container command six times, with a
fresh output root for every coordinate: `--canary-arm description`, then `--canary-arm body`, in
that order for rounds one through three. Each command runs its own credential-free, networkless
preflight and can start at most one paid call. Do not retry an ambiguous, invalid, or `INCONCLUSIVE`
coordinate; stop the sequence and report it. Valid `PASS` and `FAIL` observations continue until all
six calls are complete so the repetitions expose variance. This intentionally small operator
sequence adds no campaign journal or second executor. Keep the six compact `canary-result.json`
files separate and compare arms only within the same round.

The description arm asks for exactly one bare skill name from the rendered catalog and never names
the expected skill in its user prompt. It records `catalog-description-selection`; it neither loads
nor grades a skill body and is not a provider-native activation receipt. The body arm uses explicit
`$gcp-ops`, records `explicit-skill-body-probe`, and requires the staged projected
`gcp-ops/SKILL.md` to match SHA-256
`a319096742e87f45fa6e9cf3652247237a9aff3cdec7835cd775b78bd4dd3bd6` before launch. Current official
Codex documentation establishes that explicit selection injects full skill instructions; exact
Codex `rust-v0.148.0` source at `3ba0f711642a888aec92a611a3f3b2211157ff89` separately confirms
that explicit selections are read and injected while `skill_search` remains shadow-only. The body
arm tests the entrypoint, not conditional reference loading. Neither arm is campaign, baseline,
promotion, or release evidence. The current manifest digest is recorded in the dated review packet.

The approved three rounds completed against exact evaluator commit
`cd76ef58e75d5e0fc3d1fa191cbe9bcb851e069e` and image
`sha256:2ddd1652e8ceb8afa0c68146ad0d4399a4068d1e09f4c64c730c55985c39a06b`.
Description selection passed 3/3. Explicit body behavior passed 1/3; rounds one and three failed only
grader 5. The dated review records the compact artifact hashes and the conflicting fence contracts
that explain why this is not campaign-ready.

The historical Windows host arm does not satisfy that launch contract: its Python installation and runtime
closure are writable by the operator identity. The canary is therefore **NO-GO** until a protected
runtime/closure or separate OS identity is provisioned and independently bound. A clean launch
account/registry must additionally prove that managed, system, and project layers supply no MCP,
dynamic tool, guardian, provider, API-route, proxy, or Command Processor AutoRun override. The boundary also
requires a protected Git executable/DLL/runtime installation closure and a protected, sanitized Git
object store with no repository-config includes, object alternates, replacement refs, or UNC/network
resolution; the executable/archive digests prevent evidence acceptance but cannot protect load-time
dependencies or prevent pre-validation reads. It
excludes an already-compromised same-SID process; a current-user ACL cannot isolate credentials from
another process running as that same user. On 2026-08-20 the replacement Linux-container preflight
passed first on Codex 0.147.0 and again after the bounded 0.148.0 repin. The owner-approved 0.147.0
development canary ended `INCONCLUSIVE` before producing model output. A second owner-approved
0.148.0 canary ran from clean commit `262dfc93daf8663b50f6175b7beb7fdfae9b15cc`; its Codex subprocess
returned `0`, but trace or hook validation failed closed. A third bounded 0.148.0 canary from
`0e9e7daa4cf8dab6692b80b4e3f17fa60b809068` did the same. Exact tagged source then exposed a nullable
`transcript_path` contract mismatch, repaired at `cfb185173c0434a2792c5bf30270bef1e24606b1`.
A fourth authorized canary from clean commit `79a27cf2e52af15db66cef7ad435f0374ecaca1c` and image
`sha256:b73dd55658d4ceab93ce2df159a681672f36d0b743f7ce34946f8decfe674d6b`
exercised that repair but again returned `trace-or-hook-invalid`. Commit
`6819773e5fab4c7bc1747f1be6907c8a8b269110` distinguishes sanitized `trace-invalid` from
`hook-invalid` with red-first coverage. Four later 0.148.0 development canaries reached behavior
grading and returned valid `FAIL` verdicts. The latest ran the explicit body-load probe from commit
`09cca0ef93c739caccfb0051f6ce900d8108ad8f` and image
`sha256:e2a285bc329cca97dceb6d1561fbfc0b877022edccea7d7d95a15cb28372102f`:
graders 0 and 4 failed while 1, 2, 3, and 5 passed. Its compact result has SHA-256
`9209f4d7108325ae326fd9692611d4e7351aba03cdb1a8f108ba74ac7b7eccef`; no retry followed.
See the [Linux canary evidence packet](../docs/reviews/2026-08-20-route001-linux-canary.md). No Terra
campaign, routing result, or baseline has been recorded.
The full campaign may run only from exact,
clean, committed evaluator bytes after
independent review. A development canary can never be promoted into campaign, baseline, or release
evidence. The report-authority contract fixes `source_review = not-verified-by-runner`,
`independent_evaluator = false`, `baseline_eligible = false`, and `release_granted = false`; those
authority decisions remain outside the model and runner.

The 0.148 campaign accepts no provider-native activation event for a discovered filesystem skill.
Exact tagged source now establishes a stronger limit: with this evaluator's no-model-tools policy,
an implicit discovery turn can see the project skill catalog but cannot load a filesystem skill body.
`skill_search = true` runs selection only in shadow mode; Codex injects `SKILL.md` itself only after
an explicit `$name`, structured, or path selection, while every other path requires a model-visible
file read that this boundary deliberately removes. Skill positives and near-miss negatives are
therefore description-mediated response observations, not skill-body behavior. The frozen campaign
remains **NO-GO** until independent review accepts that narrower measurement or the routing
instrument is changed; a green development canary cannot make that decision. Root-scoped trials
retain a stricter conservative boundary: the accepted
trace does not join a plaintext delegated task, terminal child result, and root consumption;
`wait_agent` is mailbox-only. The two root-scoped active-incident cases therefore always return
`INCONCLUSIVE` with `root-delegation-unobservable-v2`; response graders do not run for them.

The fixed authenticated development canary still uses the non-root
`discovery-gcp-ops-cloud-run-startup` scenario, but its execution prompt is now derived as exact
`$gcp-ops\n\n` plus the unchanged manifest-bound discovery prompt. Codex 0.148 then injects the
selected host `SKILL.md` without exposing a file tool. The derived prompt SHA-256 is
`65139f00bc31a3b18f82a3563f7a96c8300c40166ecd133f1c77227e681128c3`, and the trial records
`explicit-skill-body-probe`. This canary-only diagnostic tests body injection and response shaping;
it is not an implicit-routing result and is rejected for every other scenario coordinate. Its one
authorized live run produced the valid `FAIL` above; it did not authorize a retry or campaign. The
canary disables multi-agent, permits only the fixed linear graders
`contains_all`, `contains_any`, and `cloud_run_rollback_packet`, and rejects responses above 256 KiB
total or 8 KiB per line before grading. The rollback grader accepts exactly one fenced JSON packet,
binds its two command fields to the scenario's exact service and synthetic revision IDs, and rejects
extra traffic commands, shell syntax, wrong weights, or mismatched context flags. The remaining
seventeen non-root scenarios require zero command/collaboration receipts.

The approved three-pair diagnostic does not replace that historical one-arm canary. It adds the
target-blind catalog-selection arm beside the exact-body arm and reports the two outcomes separately.
The nineteen campaign inputs, their hashes, and the 48-trial plan are unchanged.

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

Authentication for a recovered local runner comes from the operator's existing
ChatGPT-authenticated Codex CLI session. `OPENAI_API_KEY` is not required and must not be added to
the launch environment. Before a live development run, invoke `codex login status` using the
concrete Codex executable; `Logged in using ChatGPT` confirms the subscription-backed session this
path expects. If the session is absent, use `codex login` and complete the browser sign-in. The
runner copies the existing regular, unlinked `auth.json` into a disposable `CODEX_HOME` and removes
that copy before returning. Never print, paste, or commit `auth.json`; checking that the file exists
is sufficient. A direct Responses API harness is a different execution path and is outside this
local-run contract.

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

### Authenticate with a Claude subscription (no API key)

Claude subscription OAuth is the normal local path; no API key is required. Do **not** point the
harness at the personal default Claude profile. OAuth refresh credentials are mutable: a successful
refresh can rotate them, so copying one credential into disposable or parallel clean rooms can
discard the new state or make two processes race it. Create one persistent, eval-only profile,
authenticate it once, and select it explicitly.

PowerShell:

```powershell
$evalProfile = Join-Path $env:LOCALAPPDATA "save-toolkit\claude-evals"
New-Item -ItemType Directory -Force -Path $evalProfile | Out-Null
$env:CLAUDE_CONFIG_DIR = $evalProfile
claude auth login
claude auth status
$env:SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR = $evalProfile
Remove-Item Env:CLAUDE_CONFIG_DIR
python evals/run_evals.py --run --model claude-sonnet-5 --match incident-navigation --trials 2
```

POSIX shell:

```bash
eval_profile="${XDG_STATE_HOME:-$HOME/.local/state}/save-toolkit/claude-evals"
mkdir -p "$eval_profile"
CLAUDE_CONFIG_DIR="$eval_profile" claude auth login
CLAUDE_CONFIG_DIR="$eval_profile" claude auth status
export SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR="$eval_profile"
python evals/run_evals.py --run --model claude-sonnet-5 --match incident-navigation --trials 2
```

The profile is for authentication and inert CLI runtime state only. The runner refuses it if it
contains `CLAUDE.md`, settings, skills, agents, plugins, commands, or hooks. It also holds a batch
lock: processes using the same profile **must not run in parallel**. If a stale
`.save-toolkit-eval.lock` remains after a crash, first verify that no eval process is active, then
remove that exact lock file and retry. Never print, paste, or commit `.credentials.json`. A crash
during credential refresh can require `claude auth login` again, but only the dedicated eval login is
affected. Direct `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` authentication remains an optional
alternative; neither is a prerequisite.

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
a temporary suite image, verifies stable source/copy digests, and executes that image. An OAuth batch
points `CLAUDE_CONFIG_DIR` at the explicitly selected persistent eval-only profile; the profile lock
serializes batches so refreshed credentials remain current. Direct API authentication instead uses
an empty temporary config directory. In both modes, `--plugin-dir` loads a stable copy of this plugin
created once per batch. The plugin copy is
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

The harness refuses to grade an unauthenticated run. Claude subscription credentials from
`SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR` and direct `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` are
supported; no API key is required. Ambient/personal OAuth profiles are refused because copying
rotating credentials is not refresh-safe and using the profile directly would reintroduce personal
components. Bedrock and Vertex modes are refused because safely carrying their provider-specific
host credential environment is outside this least-privilege harness.

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
`not_regex`, `pcf_deploy_no_inline_execution`, `json_artifact_statuses`, `exact_fields`,
`incident_navigation_exact_fact`, and
`incident_navigation_contract`, `incident_navigation_no_execution`,
`incident_navigation_no_claimed_execution`,
`incident_navigation_exit_contract`, `incident_navigation_production_change_contract`, and
`incident_navigation_security_command_contract`, `incident_navigation_incident_command_contract`,
and `incident_navigation_known_alert_contract`.
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
`discovery-approved-service-knowledge.yaml` for the config shape.
`incident_navigation_exact_fact` requires one prompt-mandated fact as one exact complete response
line and requires its bounded anchor to occur exactly once. It intentionally avoids semantic prose
parsing; a numeric superstring or second contradictory restatement cannot satisfy it. Its optional
`required_preceding_line` binds that fact directly under a supplied structural heading.
`incident_navigation_contract` takes an `allowed_signal_owners` list and requires one closed,
strict-plaintext twelve-field orientation packet, one owner mention from that list, exactly one
uncoordinated question, one atomic observation, two distinct enumerated result meanings, an observable
escalation trigger, and the exact `State changed: no` boundary. Its optional `sre_result_owner`
binds the host projection's exact agent identity (`sre` on Claude/Copilot and
`save-toolkit-sre` on Codex); it never accepts both identities under one host configuration. It
composes
`incident_navigation_no_execution`, which denies model intent, direct imperatives, and every
ungoverned effect token unless it is one of the explicitly recognized noun or evidence-labelled
historical forms. The no-execution grader defaults to denying prospective effects. Only the closed
low-level helper's strict boolean opt-in accepts a prospective effect owned directly by a named
human/protected actor; no shipped scenario enables that exception over a whole packet. The closed
approved-production-change grader instead binds a strict-plaintext packet to the exact human actor,
reviewed action, approval, UTC timing, backout, watcher, abort criterion, and verified
branch-protection evidence while keeping the default no-execution posture for every field.
`incident_navigation_no_claimed_execution` is the narrower composition for ordinary SRE triage and
an already-firing known alert: it permits named advisory command/backout fields while rejecting
first-person/model execution claims, effects claimed during the response, and inline effect
imperatives.
`incident_navigation_exit_contract` requires a closed five-field
hard-exit packet whose destination, reason category, preserve-state instruction, and no-change claim
exactly match the scenario. The adjacent-lane graders require the complete ten-line
`production-change-gate` packet with exact target, actor, action, approval, and control binding; the
complete eight-line security `incident-command` packet with a scenario-bound incident title,
impact, timeline, investigating severity, exact human roles, evidence preservation, and bounded next
update; the supplied major-incident declaration/roles/timeline/runbook; or the supplied closed
thirteen-line known-alert packet with exact math, paired windows, custody, verdict, boundaries, and
verification gaps. Extra prose, placeholder controls, contradictory evidence claims, model
actors, or embedded commands cannot ride through an otherwise correct verdict.
Scenario-specific graders still own the expected adjacent-lane behavior.
Offline adversarial tests live in
`evals/test_graders.py`; runner and trace contracts live in `evals/test_run_evals.py`.
