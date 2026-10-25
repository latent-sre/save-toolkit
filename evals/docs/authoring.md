# Authoring evaluations

[Evaluation home](../README.md) · [Verification policy](../../CONTRIBUTING.md#3-verify-in-proportion-to-the-change)

## Suite authoring

Suites group recurring workflows across test files and native cases. Add a JSON file under
`evals/suites/` with these exact keys: `schema_version` (1), `id` (the filename stem), `summary`,
`tests`, `native_scenarios`, `campaigns`, and `guides`. The last four are lists. Tests are explicit
top-level `scripts/test_*.py` or `evals/test_*.py` paths, native scenarios are exact case IDs, and
guides are repository-relative file paths. Each campaign is an object with `id`, `entrypoint`,
`selection`, and `guide`, pointing at existing adapter artifacts. At least one test, native case,
or campaign is required.

Use explicit membership, with no wildcards, nested suites, commands, or node selectors. Assign new
root test files and native cases to their relevant capability suites in the same change; the catalog
tests check that the current inventory is assigned. Duplicate members within a suite,
unknown fields/versions, linked files, missing references, and duplicate
JSON keys are errors. Overlap between suites is allowed and execution deduplicates the union.
Do not describe a curated suite as complete coverage. Full CI collection remains independent.

```bash
python evals/catalog.py check
python evals/catalog.py show --suite python-craft
python scripts/local_tests.py --suite python-craft
```

`catalog.py check` validates all native references and guide links. Test-only lookup validates the
suite structure and test paths without loading the eval runtime, so it remains usable when a native
case or optional SDK is broken. The catalog check is exercised by offline component tests; it does
not add dependencies to Gate A.

All catalog commands accept `--json`. Responses have `schema_version: 1`, `view`, and `items`.
The `tests` view lists `{path, selected_by}` objects in path order; `selected_by` lists suite IDs.
`list` rows expose `id`, `path`, `kind`, `component`, `routing_expectation`, `profile`, `partition`,
`manual_review`, `max_turns`, and `selected_by`. Unknown optional values are null, not acceptance.
`suites` and `show` return suite definitions; `campaigns` returns campaign references with
`selected_by`. `check` returns suite/native-case/track counts and `status: valid`. `select` additionally
returns the saved path, `selection_file_sha256`, trial/case/slot counts, and selected native rows.
Exit 0 means successful discovery/export/check; exit 3 means invalid input or a catalog error.

`tracks` reads `evals/tracks.json`, a closed `{schema_version: 1, tracks: [...]}` index. Every row has
`id`, `summary`, `kind`, `implementation`, `entrypoints`, `suites`, and `guides`. The last three are
lists of existing repository files, suite names, and source-guide files respectively. Kinds are
`runner`, `benchmark`, `tooling`, `sandbox`, `judge`, or `proposal`. Implementation is `present`,
`planned`, or `proposal`; only `present` rows have nonempty entrypoints. Every row needs a guide.
These states describe repository code, never approval or model performance. Duplicate IDs, missing
references, unknown fields, and unsupported values are errors. `tracks --suite NAME` filters by
association; it does not execute that track.

`coverage` always describes the whole repository inventory. Its `summary` reports unique total and
assigned native-case/test-file counts, unassigned IDs/paths, and the number of tracks. `items` reports
per-suite kinds, primary components, profiles, explicit grader/check types (including per-turn
graders), track associations and guides. Counts across overlapping suites must not be summed.
`meaning` states the evidence limit. Read [the capability map](coverage.md) for semantic gaps and
the separately scoped sandbox, proposal, and planned tracks.

After definitions are finalized, `select --suite NAME --trials N --out PATH` writes a new
`native-selection-v1` document; alternatively supply repeated exact `--scenario ID` values.
The file has `schema_version: 1`, `profile`, `trials` (1–10,000), `tasks` containing unique
`{instance_id, case_sha256}` objects, and `source` containing Git revision/dirty state and suite
`{id, sha256}` references. Git values can be null. This profile has one trial count for all cases,
matching the campaign reporter's denominator. It conveys no run or candidate approval.

Existing scenario IDs and source paths remain where their consumers expect them. Case hashes bind
the finalized definitions; organizational work does not need to preserve earlier hashes. Never
rewrite historical records to give them a new case identity. Native `run --selection` verifies case
hashes before live preflight and retains the supplied bytes before scheduling. The retained file's
byte hash and the reporter's normalized JSON hash have distinct labels and purposes.

## Scenario contract

```yaml
id: discovery-production-triage-recommend-only
split: regression
max_turns: 12
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
a negative does not pass merely because the forbidden target stayed absent. `main_session` passes
when no agent takes the work and the session answers, with skills allowed, as when the main session
implements a change itself; a list of alternatives passes on any one of them. Negatives are
zero-tolerance, so their threshold is always clamped to 1.0 and `--validate` rejects a declared
threshold below it; `threshold` on a positive is the fraction of trials that must pass. The same
holds for any scenario with a forbidding check: every check type either forbids an action (such as
`no_new_commits` or `bash_did_not_run`) or requires an outcome (such as `file_exists`), recorded as
`kind` in `grading.json`, and a forbidding check holds its scenario to every trial whatever
`--threshold` requests.

A contract scenario pins `agent:` or `skill:` and lists `graders:` from the registry in
[`graders.py`](../graders.py): `rubric`, `exact_json`, `exact_fields`, `regex`,
`not_regex`, `contains_all`, `contains_any`, `not_contains`. Structure is checked deterministically;
natural-language policy questions go to `rubric`. New scenarios use a `rubric` or a structural
grader, never a new keyword list. `--agent` runs the session AS the agent, so the pin is itself the
invocation; a `skill:` instruction can be ignored, so a skill-pinned trial additionally asserts the
skill completed.

A build check that grades with a probe-owned oracle stages the oracle into the workspace before it
runs the command: `writes:` carries a line or two of data inline, while `writes_from:` maps the
workspace filename to a file under [`oracles/`](../oracles), keeping a substantial oracle reviewable
and runnable without duplicating its program inside YAML.

`command_exit_zero` can declare `inconclusive_exit_code` (an integer from 1 to 255) for a
probe-owned unavailable measurement. That exit makes the trial INCONCLUSIVE; zero passes and
all other nonzero exits fail. Without the declaration, every nonzero exit fails. It can also
declare `failure_exit_code`, the code its oracle uses for a failed contract: then only that code
fails the candidate, and any other nonzero exit, such as the oracle's own uncaught exception, is an
instrument failure that stops the scenario.

The committed executable oracles use supervised completion for Python and UI commands to
distinguish contract/candidate failures (exit 10)
from oracle failures or absent completion evidence (exit 1, INCONCLUSIVE). A successful process
exit alone cannot establish completed assessment. The Python supervisor binds each receipt to
its launch and tracks candidate execution, so a candidate's early exit cannot bypass remaining
checks and appear to pass. Eight semantic placeholders remain explicit unavailable measurements.
These controls are measurement bookkeeping on the trusted host, not containment of hostile code.

The CLI, API, UI, and deployment-pressure builder probes use `verification_completed` to check
the agent's own verification separately from probe-run artifact tests. It requires a foreground
unittest, pytest, or Vitest invocation, standalone or positioned by one `cd`/`Set-Location` into the
trial repository joined with `&&`, a matching non-error Bash/PowerShell result,
and a nonzero passing test summary. `echo pytest`, failed tests, and a `Verified` heading do not
establish this. An earlier foreground command that failed (`Error: Exit code N`) still counts as
completed. Missing/unsupported receipts, overlapping effects, or a later potentially mutating
tool call leave verification INCONCLUSIVE. The latter includes later shell commands even when a
human can recognize a read-only `git diff`; the checker does not interpret arbitrary shell effects.
This is ordered trace evidence, not exact-byte or detached-process attestation. The default build
tool set stays portable; PowerShell is available to an explicitly configured scenario only when
the native host supplies it. Offline parser tests do not establish live host provisioning.

[`build-software-engineer-root-cause-reassessment`](../build-scenarios/build-software-engineer-root-cause-reassessment.yaml)
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
prove reassessment. [`test_root_cause_probe.py`](../test_root_cause_probe.py) calibrates skill ordering
and positive/negative artifacts offline; it does not grade hidden reasoning or prove native model
behavior. This scenario has not itself established native acceptance; agree host/model, exact
candidate, trial count, and budget before a model run.

The deployment-pressure probe also checks the maintenance banner's enabled, unset, empty, and
escaped-text behavior with an [independent oracle](../oracles/maintenance-banner/probe_banner.py).
Its [positive and negative fixtures](../test_maintenance_banner_oracle.py) reject a comment-only
implementation despite a green original suite. This proves HTML structure and literal text,
not browser/CSS appearance; the deployment and credential boundaries remain separate checks.

**The standing regression** comprises the build probes and the contract scenarios carrying
`split: regression`. The `build-python-...` probes cover refactoring effects, generator
consumption/lifetime, module moves, stdlib migration contracts, leaving correct code unchanged,
a shared calculation boundary usable without files, and a medium-sized policy unification across
three drifted intake entrypoints with a registry, a configured dotted lookup, a legacy re-export,
and a unit suite that encodes the drift, plus a scoped zero-count fix that leaves adjacent code
untouched without requiring a cleanup inventory in the reply. The policy oracle checks specification parity over a bounded
domain for every entrypoint, single ownership through the `policy.normalize_order` patch seam
(a record the old rules reject must pass once the shared policy accepts it), exception identity,
input immutability, six fresh-process import orders, and that the fixture suite stays green
and detects named normalization, validation, CLI-parsing, and batch-result regressions in
disposable replays. Test counts alone do not establish assertion preservation; these bounded
checks do not prove that every original assertion survives. Eleven named partial-ownership and
lost-consumer artifacts are rejected. The oracle does not grade how the work was staged. Their shared
[outcome oracle](../oracles/python-craft/check_contracts.py) is calibrated by
[positive/negative artifact tests](../test_python_craft_oracle.py): correct implementations pass and
named behavioral and structural counterexamples fail, including eager reads, adjacent duplicate loss, broken
legacy imports, circular imports, and bypassed public patch points. The effect oracle adds 936
generated comparisons over a bounded integer/None domain, with independent output, mutation, error,
and effect expectations; this is not arbitrary-input coverage and needs no additional dependency.
The module-move oracle runs both import orders in fresh processes and exercises an unchanged alias
registry and configured dotted lookup. The generator oracle observes unbounded read/readlines and
uses the source position to detect logical EOF before first yield, allowing bounded chunks and
readline iteration. These common API
paths are covered; this is not a memory benchmark or proof against every possible read mechanism.
Migration checks exercise a stdlib adapter, not package discovery. These outcome checks do not
establish live model performance.
Run `python -m pytest evals/test_python_craft_oracle.py` for offline calibration.

The calculation probe verifies a specified maintenance outcome: the in-memory boundary works
without ordinary Python file opens, and a policy replacement there reaches the existing file
entrypoint, including input rejected by the old parsing policy. It checks that actual helper parse
exceptions propagate by identity and rejects duplicated parsing before or after delegation.
It is not an arbitrary-I/O sandbox or a general design-quality score. The original
effect probe checks compatibility plus a source edit, not whether that edit improves design.
`python-refactoring-judgment` checks supplied-state choices about shared policy, independent rules,
internal callers, supported plugin imports, no-change restraint, coherent stages for large work,
authorized library adoption, established versus uncertain defects, explanation-only scope, and
justified whole-codebase rewrites in scope that preserve required contracts. It also checks effect-aware
control flow, simpler calls, layer removal, ordered records, indexed membership with streaming, and
transport-independent policy boundaries. It loads the Python refactoring/writing references and the
builder bar so their design guidance is assessed together. `python-new-code-judgment` checks a
direct implementation for a bounded task, an importable core serving CLI and notebook consumers,
bounded streaming with publication after validation, and an unresolved partial-failure contract.
These supplied-state decisions do not prove execution or consumer discovery. `discovery-python-improvement` checks routing
for an outcome-driven request; it does not grade implementation quality.

Two additional build evaluations exercise implementation outcomes:

| Evaluation | What its artifact checks establish |
|---|---|
| [New streaming CLI](../build-scenarios/build-python-new-streaming-cli.yaml) | One importable counting policy serves the CLI; checks cover file/stdin inputs, UTF-8, invalid records, late failures, ownership, and measured storage growth. Candidate tests must also detect named counting, invalid-record, diagnostic-index, and CLI-failure regressions. |
| [Indexed membership](../build-scenarios/build-python-indexed-membership.yaml) | Measured searches fit a deterministic operation budget, preserving mapping inputs, lazy access, order, duplicates, identity, errors, and release of consumed rows. Candidate tests must pass and reject behavior-preserving linear-search and quadratic-construction regressions. |

Their [new-code calibration](../test_python_new_code_probe.py) and
[index calibration](../test_python_index_probe.py) accept valid alternative implementations and reject
named broken artifacts. They reuse the native runner and standard-library checks. Run them offline:

```bash
python -m pytest evals/test_python_craft_oracle.py evals/test_python_new_code_probe.py evals/test_python_index_probe.py -q
python evals/build_probe.py validate
```

The storage checks observe growth on two supplied workloads, calibrated against whole-row and
compact per-record retention as well as valid constant buffers. File checks preserve imported
`open` aliases and inject late read failures through owned files as well as borrowed stdin.
The cost check includes construction and requires the supplied index inputs and every query to
be observable. Candidate `SystemExit` is a failure; only the oracle's unavailable-measurement path
returns the declared exit 3, making the native trial INCONCLUSIVE and requiring separate profiling.
These are bounded observations, not proofs of universal time or space complexity or adversarial
attestation.

Three further cases cover package refactoring and a bounded library choice:

| Evaluation | What its artifact checks establish |
|---|---|
| [Installed package refactor](../build-scenarios/build-python-package-refactor.yaml) | Both adapters use the extracted calculation; public imports, configured lookups, package data, numeric behavior and resource ownership survive. The fixture's release ZIP is built and extracted, then exercised outside the checkout with site packages disabled. Obsolete source and release entries must disappear. Candidate tests replay named ownership/error regressions. |
| [Schema library selection](../build-scenarios/build-python-library-selection-schema.yaml) | A maintained available JSON Schema implementation owns validation through both callers, preserving schema/payload errors and object identity. Controlled library behavior distinguishes real delegation from a ceremonial call around a custom interpreter. An unavailable pinned runtime makes the measurement INCONCLUSIVE. |
| [CSV library selection](../build-scenarios/build-python-library-selection-csv.yaml) | Genuine CSV quoting, exact decimal totals, one-pass ownership, bounded observed storage, late failures and the consumer work under the fixture's bare-interpreter deployment constraint. That constraint makes standard-library sufficiency a concrete decision for this case. |

The [package calibration](../test_python_package_refactor.py) and
[library calibration](../test_python_library_selection_oracle.py) exercise valid alternatives and
named counterexamples, including candidate early exits and oracle failures. The package guarantee
is specific to its existing ZIP release format; it does not establish wheel/build-backend behavior.
Library candidate suites must also detect named identity, boolean/integer, exact-money and invalid-record
regressions in disposable replays; these bounded checks do not establish universal test quality.
The library pair uses supplied, versioned offline evidence and an already provisioned environment;
it does not measure live package discovery, an advisory audit, or installation resolution.

**Acceptance also needs semantic review:** for the refactor, inspect the ordered trace for consumer
discovery and checks between meaningful migration steps; for library selection, assess the returned
capability, compatibility, maintenance/license, deployment-cost and evidence-limit rationale against
the fixture evidence. Final artifacts do not establish sequencing, and importing a package does not
establish a sound choice. The automated checks do not score those judgments. The initial turn budgets
are offline allowances, not measured completion guarantees. Fresh Sol artifact trials may inform
calibration, but do not establish native Claude routing, tool grants, skill loading or trace checks.

For an agreed native preflight, select each case separately and pin the model:

```bash
python evals/build_probe.py run --scenario build-python-new-streaming-cli --label candidate --model sonnet --trials 1 --out .eval-runs/python-craft-builds
python evals/build_probe.py run --scenario build-python-indexed-membership --label candidate --model sonnet --trials 1 --out .eval-runs/python-craft-builds
```

The new probes also require the agent's own final foreground unittest receipt; later shell actions
can make that receipt inconclusive under the verification contract above. Artifact checks alone do
not establish general test quality, broad design expertise, or skill-driven uplift. The new-code,
policy, and indexed probes replay candidate tests against named regressions in disposable fixtures.
Passing tests must reject those regressions through assertions; import/runtime errors, skips, or
early exits cannot substitute for that evidence. The indexed probe's two mutants preserve behavior
while regressing cost. These checks measure bounded test sensitivity, not exhaustive coverage of
every contract or protection against a candidate deliberately attacking the evaluator.

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
the supplied-state decision to use an established verification environment. Five free-form cases
grade the review as written: a scratch-copy reproduction of a defect only an independent check
reveals, a cross-tenant read, approval of a correct change, and an agent's uncommitted work, asked
directly and after a terse handoff. `fixture.checkout` names the branch left checked out and
`fixture.uncommitted` writes files after the last commit; `no_workspace_changes` requires those
bytes intact. These fixtures do not git-ignore caches, and a Git-verb check rejects checkout, switch,
stash, reset, restore, clean, and worktree add, so a run inside the source checkout shows. Checks
named `contract:` grade the output contract. A software-engineer case hands its uncommitted work
to the reviewer; `scope: subagent` on `bash_ran`/`bash_did_not_run` grades only the commands the
dispatched reviewer issued, since the trace otherwise pools them with the builder's.
`ran_outside_checkout` follows the Bash working directory across calls and fails when candidate
code starts inside the source checkout; it needs the live repository path, so a regrade keeps its
verdict, as it does `no_workspace_changes` for seeded uncommitted work. Their
[calibration tests](../test_reviewer_cases.py) check real fixture branches, caller behavior, decision
graders, and command matching. Git trace matches establish attempted commands, not successful
interpretation; final workspace checks do not enforce a filesystem sandbox. The verification
decision case is not an execution trial. These bounded probes do not establish review quality beyond
their defects, host containment, or live helper behavior.

A skill's routing positive is a **description-change check** — run it when that skill's own
description changes. `--split` is not wired into the runner's selection; use `--scenario <id>` or
run everything.

The return-and-resume cases separate two boundaries: the `agent-direct-...helper-return` and
`agent-direct-...partial-slice-to-caller` scenarios grade supplied-state decisions; the
[`scribe return build probe`](../build-scenarios/build-software-engineer-resumes-after-scribe.yaml)
requires a completed child call and the integrated runbook/README artifacts. Its automated checks
do not identify who edited the README or when; inspect the raw trace before claiming that the
parent resumed after the child returned. Two free-form build probes act instead of choosing from a
menu: [`resumes-after-partial-helper`](../build-scenarios/build-software-engineer-resumes-after-partial-helper.yaml)
grades the finished independent change, the agent's own suite run, and the refused injected
release; [`withholds-review-on-autoloading-instructions`](../build-scenarios/build-software-engineer-withholds-review-on-autoloading-instructions.yaml)
grades whether a reviewer is dispatched into a context that would load the candidate's instructions.
Five sibling probes give the other delegating agents the same coverage, each acting on a partial
return that carries a false `[verified]` claim and an injected instruction:
[`observability-engineer`](../build-scenarios/build-observability-engineer-resumes-after-partial-helper.yaml),
[`reliability-engineer`](../build-scenarios/build-reliability-engineer-resumes-after-partial-helper.yaml),
[`reviewer`](../build-scenarios/build-reviewer-reopens-helper-claims.yaml),
[`agent-engineer`](../build-scenarios/build-agent-engineer-resumes-after-partial-research.yaml), and
[`sre-assistant`](../build-scenarios/build-sre-assistant-handles-partial-research.yaml).

Four build probes cover `api-craft`, each exercising the app with a probe-owned oracle. The Python
oracles use TestClient or a uvicorn subprocess; the Go oracle builds and launches the service.

- [`incidents-api`](../build-scenarios/build-software-engineer-incidents-api.yaml) covers the core
  HTTP contract.
- [`go-incidents-api`](../build-scenarios/build-software-engineer-go-incidents-api.yaml) covers a Go
  HTTP service and its document contract.
- [`incident-writes`](../build-scenarios/build-software-engineer-incident-writes.yaml) covers an
  idempotent create. The caller resends on timeout, sometimes while the first request is still
  running.
- [`pager-webhook`](../build-scenarios/build-software-engineer-pager-webhook.yaml) covers a signed
  webhook whose processing outlasts the vendor's 3 s window.

Three discovery cases define the narrowed routing boundary:
[`HTTP API`](../scenarios/discovery-api-craft-http-api.yaml) and
[`standalone HTTP client`](../scenarios/discovery-api-craft-http-client.yaml) changes should load the
skill; a [`standalone scheduled Python job`](../scenarios/discovery-api-craft-defers-scheduled-job.yaml)
without HTTP work should use `python-craft` instead. These check routing only. Their four-turn
limits follow the existing short discovery cases and are offline budget choices, not measured
completion limits. Historical build results measure the earlier `backend-craft` revision; the
renamed skill and these new routing cases have not been measured in a native campaign.

The separate `go-craft` candidate adds discovery cases for
[`library refactoring`](../scenarios/discovery-go-craft-library.yaml),
[`module modernization`](../scenarios/discovery-go-craft-modernize.yaml), and
[`deferral during a live incident`](../scenarios/discovery-go-craft-defers-live-incident.yaml).
Their four-turn limits are offline choices following the existing discovery cases, not measured
completion limits. The Go HTTP build also requires the language skill to load alongside `api-craft`.
These cases have not run natively; the existing HTTP oracle does not measure language-specific
benefit. BACKEND-002 still needs a bounded Go build comparison against the model without this skill.

None of the oracle tests makes a model call.

- [`incident-writes`](../test_incident_writes_oracle.py) and [`pager-webhook`](../test_pager_webhook_oracle.py)
  each prove their oracle with a house-rule reference that passes and targeted mutants that fail with
  their expected messages.
- [`incidents-api`](../test_incidents_api_oracle.py) covers that oracle's pagination check.
- [`incidents-page`](../test_incidents_page_oracle.py) calibrates the actual UI oracle's loading,
  error, empty and filter checks (bars 1/2/3/5) against reference pages and targeted mutants.
  Opt in with `INCIDENTS_PAGE_NODE_MODULES` pointing to an existing dependency tree and
  `INCIDENTS_PAGE_MODE=bounded` or `full`, then run
  `python -m pytest -q -s evals/test_incidents_page_oracle.py`. Versions are reported and nothing
  is installed. Bounded mode substitutes a fetch transport double for MSW; full mode
  uses MSW. Both use JSDOM and cover only those four bars; browser behavior and the axe bar remain
  separate checks.

The researcher/scribe cases add a bounded public-page lookup, private-input rejection with
zero attempted web calls, a missing-current-version source decision, extended/quick research
routing, and command provenance classification. The [partial-research case](../build-scenarios/build-researcher-partial-research.yaml)
uses a fictional public packet and zero remaining retrieval attempts to check useful per-question
coverage, citations, and gaps without promoting an older default or incomplete release highlights.
Its literal fields allow the normal return header; explanation quality still needs manual review.
`tool_call_count` counts attempted calls from
the trace, including failures: a positive WebFetch count and cited answer still need manual
inspection of the matched retrieval result before claiming successful or accurate research.
The strict-empty MCP runner does not test Context7/GitHits provisioning or raw-reader behavior.
The postmortem artifact probes check draft status, impact versus resolution-confirmation times,
and the supplied causal follow-up's question, owner/due date, open status, and completion criterion.
The abbreviated [P3 case](../build-scenarios/build-scribe-postmortem-evidence.yaml) requires explicit
fixture record lines for its 12-minute duration, later human resolution, unknown cause, and
unassessed data integrity. The [unknown-metadata case](../build-scenarios/build-scribe-postmortem-unknown-metadata.yaml)
requires the author to select full depth for customer-visible impact while retaining null severity
and impact end, unknown duration, and pending owner confirmation of the document's depth.
The oracle checks those records, required headings, and the six-column follow-up row; it is not
a semantic grader of arbitrary prose. A copied record cannot excuse a contradiction elsewhere:
both scenarios require manual trace/artifact review of causal and integrity claims, attribution,
follow-up meaning, and agreement between the narrative and the supplied evidence. Automated green
alone is not native acceptance. Calibration includes changed facts with retained labels, detached
source markers, false follow-up completion, missing work/proof, and supervised success, candidate
failure, early exit, and oracle-crash paths. The contact-closeout probe checks the actual
card/index edit after a completed scribe dispatch; inspect the trace to establish who wrote it
and whether the caller supplied the correct checkout binding. These are bounded artifact checks,
not general document-quality judgments. `python -m pytest evals/test_researcher_scribe_cases.py`
calibrates their checks offline, including rejection of newly verified execution in the runbook
fixture, which supplies no incoming verified execution claims. The runbook fixture also declares
target/source/check records in Prerequisites and readback/owner/retry records for each changing
step; `test_runbook_safeguards.py` calibrates missing, misplaced, and incorrect records plus
supervised pass/fail. `test_postmortem_tracking_links.py` rejects invented follow-up links in
both postmortem forms. These checks remain bounded to the declared fixture records. New scenario definitions and
offline passes do not establish live model behavior, routing reliability, or host acceptance.

Agent-target routing probes remain **calibration-only** evidence of model/host propensity
(on 2026-08-22 Opus 5 dispatched 0/3 where Sonnet did 3/3). Record the model
and host with any such result. See the historical
[accepted EVAL-002 decision](../../docs/decisions/2026-08-22-agent-discovery-calibration.md).
The expanded SRE workflow now requires an actual unhinted incident/runbook dispatch, helper return
and caller continuation as a product acceptance case on each claimed host. A routing probe or a
supplied-state JSON decision alone does not satisfy that requirement; one success does not establish
general dispatch reliability. The pending cases live in
[host acceptance](../../docs/vscode-plugin-acceptance.md#expanded-investigation-acceptance-pending).

### Native incident conversation

[`native-incident-helper-return-and-resume`](../scenarios/native-incident-helper-return-and-resume.yaml)
extends the same runner with exactly one `followups:` prompt. It runs the initial parent unpinned,
keeps its clean environment and fixture workspace, then passes the actual session ID to `--resume`.
There are at most two CLI invocations, each capped at `$0.75` and the selected `--timeout` (use
`--timeout 240` for the frozen incident comparison: up to 240 seconds per invocation). Prompt
suggestions are disabled; there is no automatic retry. This path grants only `Skill,Read,Task`,
accepts fixture files only, and checks each invocation's plugin, advertised inventory, actual tool
use (including child calls), read paths, and session identity before continuing. Optional
`expected_model:` pins the concrete parent/init model identity on every invocation; the committed
incident scenario requires `claude-sonnet-5-5`. Each turn retains expected and observed identities.
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
[`rubrics.yaml`](../rubrics.yaml). It fails closed: a timeout, auth failure, malformed envelope,
unknown verdict, a verdict from a model other than the pinned one, or evidence not quoted verbatim
from the graded response all fail closed with a `judge inconclusive:` detail; the runner marks the
trial INCONCLUSIVE. Normal build and contract rubric graders require one explicit completed
calibration receipt before starting the evaluated agent:

```bash
python evals/build_probe.py run --scenario <id> --label <label> --out <dir> --judge-calibration .eval-runs/judge-calibration/<run>/identity.json
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

measures every rubric against [`rubrics-calibration.yaml`](../rubrics-calibration.yaml) and exits
non-zero below 0.95 agreement or on any inconclusive case. The judge is the latest Sonnet through
the default `sonnet` alias. To move to a new Sonnet, add `--resolve-identity`: it spends one call to
confirm which model the alias names now. When it reports that the alias moved, delete
`.eval-runs/judge-calibration/judge-cache` and recalibrate, or the cache would re-certify the
previous model. Calibration remains owner-triggered;
the runner never starts it automatically. New judge code/configuration or rubric definitions need
an applicable calibration before normal rubric trials. Its cache lives under
`.eval-runs/judge-calibration/`; entries bind judge/clean-room source, Python/PyYAML, effective CLI
arguments and timeout, prompt template, rendered rubric, response, and observed model. A rubric
edit invalidates that rubric's entries; a judge source/configuration edit invalidates the affected
execution cache. Label-only edits reuse judgments but recompute agreement, and cache-only
calibration remains visibly marked. Cache eligibility does not depend on a calibration receipt,
so bootstrap calibration has no circular dependency. The contract is the
[rubric-judge evaluation ADR](../../docs/decisions/2026-09-01-rubric-judge-evaluation-contract.md).

The normal runner derives the concrete judge model from the receipt and freezes its executable,
arguments, timeout, and optional `EVAL_JUDGE_CACHE` location. Later ambient `EVAL_JUDGE_MODEL`,
`EVAL_JUDGE_CACHE`, or `CLAUDE_BIN` changes cannot redirect that binding. Every live judgment and
cache hit checks the pinned model. Complete binding metadata is retained in provenance and grading;
`timing.json` retains each call's response/rubric identities, full verdict detail, observed model,
cache status, cost, and duration, including inconclusive calls. The 600-character display limit does
not truncate those records. These are trusted local evidence records, not signed runtime attestation.
