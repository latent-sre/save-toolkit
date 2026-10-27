# Running evaluations

[Evaluation home](../README.md) · [Verification policy](../../CONTRIBUTING.md#3-verify-in-proportion-to-the-change)

## Run it

The [multi-model testing block](../../docs/fleet-evaluation/multi-model-testing.md) freezes
matched Sonnet, Sol, Luna and Terra controls through the existing native and structured
Codex runners. It keeps their identities, verdicts and unknown costs separate. The
[current follow-through plan](../../docs/fleet-evaluation/run-plan-followthrough.md) binds
the aggregate testing budget and the requested Linux/Windows WP-04 coverage.

`--max-invocation-usd` optionally supplies Claude's USD limit on each invocation.
Persistent sessions retain the tighter of that value and their existing USD 0.75 limit.
This is separate from `--max-batch-usd` scheduling, and may overrun by a final response;
neither flag establishes a provider-side hard cap across multiple campaigns.

The separate [`codex_probe.py`](../codex_probe.py) adapter admits fifteen named artifact cases:
the twelve structured WP-10 injection cases, `--pair reliability` for the single proportionate-options
assessment, and `--pair gcp01` for startup A/B. It stages canonical guidance and serves scoped tools
through [`codex_fixture_tools.py`](../codex_fixture_tools.py). Reliability may write only its requested
assessment; GCP uses an exact synthetic read-query catalog prepared by
[`codex_gcp_queries.py`](../codex_gcp_queries.py). No candidate shell or live cloud interface is exposed.
GCP query-attempt checks explicitly describe that transport instead of inventing native Bash calls.

Its `codex-record-v1` artifacts are a separate baseline outside the native v1 importer. The
[original Luna campaign](../../docs/reviews/2026-10-15-wp10-structured-case-acceptance.md) retains 33 PASS,
two FAILs and one INCONCLUSIVE on its current case versions, plus three earlier-version records.
The [reliability/GCP continuation](../../docs/reviews/2026-10-15-luna-reliability-gcp01.md) binds the newer
candidate, evidence mapping and run scope. Neither profile establishes native routing, hooks or
live helper continuation.
The MCP server explicitly uses strict UTF-8 on its pipes; isolated Python ignores environment-only
encoding settings on Windows. Completed tool-error responses still require exact argument, result
and failure-status agreement with the independent receipt; transport corruption remains INCONCLUSIVE.

`--approve-fixture-tools` requires the owner's approval of the profile's exact tools. There is no
retry/overwrite mode; each invocation runs at most one pair or the reliability singleton and stops
on incomplete evidence. GCP's declared semantic-review gate remains INCONCLUSIVE even with complete
instrument evidence; it permits the second arm but never counts as PASS. Reliability's mechanical
PASS also requires separate review of the assessment's reasoning.
The Code Mode path accepts one literal scoped file or query call per wrapper, or a metadata-only
`text(ALL_TOOLS)` query, optionally filtered by literal `name.includes`/`description.includes` terms
joined by `&&`. Calls still require matching returns; arbitrary JavaScript stays unmeasured.
The reader also recognizes the built-in `list_mcp_resources({})` call only when its
completed result proves an exact empty catalog and its session call/return matches.
The literal text call and observed fixed text-only projection are supported; nonempty
catalogs, resource reads, server arguments and arbitrary wrappers remain unmeasured.
Subscription dollar cost is unknown; wall time, tool limits and token usage are recorded.

Use the latest **Python 3.14** patch for development and component-test CI. The repository-wide
compatibility floor is Python 3.12, including the native runner and installed hooks; structural CI
exercises that minimum.

```bash
python -m pip install -r requirements-dev.txt
python evals/build_probe.py validate                        # offline schema/grader/target check
python evals/build_probe.py run --scenario all --label baseline --model sonnet --trials 3 \
  --out .eval-runs/<iteration>
python evals/build_probe.py run --scenario discovery-runbook-incident-update --label desc-change \
  --model sonnet --trials 3 --out .eval-runs/<iteration>
```

`validate` is the CI-safe check and the one to run on any scenario edit. `run` needs a
Claude-enabled runner and starts a fresh non-persistent process per trial. The other jobs are
`regrade`, `rescore`, `diff` and `schema`; `build_probe.py COMMAND --help` describes each. The flat
flags of earlier runners (`--validate`, `--regrade DIR`, `--rescore DIR --out DIR`,
`--rescore-diff BASE CANDIDATE`, and a bare run) remain supported compatibility forms and reach the same jobs.
Every scenario must declare `max_turns`; validation refuses a missing or invalid limit before
preflight. The CLI's native execution preflight also requires observed CLI, host, account and elevation evidence and
an unelevated account. An unknown or elevated runtime is refused with exit 3 before a trial starts.

**Pin `--model` on every run.** The fleet's measurement default is the `sonnet` alias unless the
roadmap item names another tier: it is the tier the existing routing evidence was taken on. A run on
a different tier is a different baseline — record it and never average it with a Sonnet run.

Compare an incumbent with `--plugin-root <worktree> --label incumbent`; `--expect-plugin-digest`
refuses any other bytes. `--overwrite` replaces the selected run slots; use a new label when changing
the candidate or scenario. `regrade` re-grades saved traces offline only when the original scenario
identity matches, and `rescore` and `diff` compare runner revisions on saved traces (see
[Provenance](internals.md#provenance)). Trials run on the host; externally authored code runs only in separately
authorized CI, so the former `--container` mode was removed (`EVAL-011`).

`python evals/compare_runs.py .eval-runs/<iteration> --incumbent A --candidate B` compares two labels
from their v1 records (EVAL-012 WP-01): counts, attempts and known and unknown spend per arm, then each
case as a gain, regression, unchanged, unmeasured, missing pair or not compared, then unusable records
and legacy runs. An arm pools against a case's native threshold only while the scenario still has the
digest its records name. `--json` prints the logical report. It grades nothing, so it is not part of
the runner's identity; [`fixtures/v1-bundle`](../fixtures/v1-bundle) is its synthetic test bundle.
`python evals/turn_counts.py .eval-runs [--scenario ID ...]` summarizes the turn counts saved trials
recorded, per scenario, as evidence for setting a scenario's `max_turns`; it also grades nothing.
Older `total_duration_seconds` values are accepted when trial-only elapsed time is absent; they
may include judging, so budget sizing treats them conservatively.

Native agent conversations pin the parent with `agent:` rather than routing to it as another
helper. The legacy two-message profile's sole-helper boundary cannot also permit a second agent dispatch. Skill-based native
conversations retain positive main-session routing. Measure agent discovery with a separate unhinted
routing scenario. Saved native agent runs require matching `--agent` evidence on both invocations;
an old main-session trace cannot be reclassified as agent acceptance. The opt-in
[`incident-v1` profiles](../incident-conversations/README.md) extend this path with ordered sessions,
per-invocation helper contracts and frozen evidence branches. They retain then-visible judge contexts
and actual resume evidence; semantic review remains separate from structural PASS.

The standalone [`campaign_report.py`](../campaign_report.py) accounts for selected slots, kept and
incomplete attempts, original results, late operational failures, separate measured/estimated spend
and unknown review dimensions. Its [operator guide](../../docs/fleet-evaluation/campaign-report.md)
describes the selection shape and portable evidence links. It does not grade or promote candidates.

External benchmark preparation has separate entrypoints: [WP-04 ITBench](../itbench_pilot.py),
[WP-08 SWE-bench](../swebench_repair.py), [WP-09 SWT](../swt_pilot.py), and
[WP-09 Harbor/Terminal-Bench](../harbor_pilot.py). Their source manifests, static-authoring admissions,
independent verifiers and live gates are separate from the native fixture runner. See the
[complex-campaign plan](../../docs/fleet-evaluation/implementation-complex-campaigns.md) for scope;
offline tests establish neither live benchmark performance nor exact-candidate acceptance.
## Muse runner (separate baseline, never comparable)

[`muse_probe.py`](../muse_probe.py) runs the same scenario catalog on Muse (`muse exec --json`)
for a Muse host baseline. It is a separate entry point with its own `muse-record-v1` records:
the model, harness and tool names differ, so its results are never averaged with or compared
against a Sonnet baseline. Agents and skills are pinned by injecting the canonical definition
into the prompt (`pin: prompt-injected`), shell/write/web access is approximated from the pinned
agent's own grants, and any expectation a Muse trace cannot carry — skill-load completion,
dispatch targets, tool arguments, a rubric judge — is INCONCLUSIVE rather than graded on
invented evidence. Routing is credited only structurally — a fleet SKILL.md read in
tool-carrying events, or a spawn record naming its own target — never from a name mentioned in
tool output or the prompt echo; a retained Muse session log, when found, corroborates dispatch
targets only under the same same-line rule, and its absence is recorded rather than read as a
negative. Checks are gated by the evidence they declare they read, so a check needing a raw or
ordered trace, a judge, or a backing service is INCONCLUSIVE here instead of graded on an empty
summary. Trials are staged in the probe's seeded temp workspace under the Claude probe's isolated
child environment (with the Muse credential file copied byte-for-byte into the isolated home,
outside the trial workspace), so routing on Muse measures a staged workspace — fleet-component
discovery there is unmeasured by design and reports INCONCLUSIVE rather than a verdict.
`python evals/muse_probe.py validate` checks the catalog offline;
`run --scenario <id> --label <label> --out <dir>` executes live trials.
## Inspect AI + Inspect SWE pilot

[`inspect_pilot.py`](../inspect_pilot.py) runs the existing word-frequency fixture through Inspect
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
modernization work are in [Python and eval modernization](../../docs/python-eval-modernization.md).
