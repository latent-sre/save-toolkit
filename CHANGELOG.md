# Changelog

Recent changes to the current Save Toolkit. This is a pre-release repository; entries do not
assert a published release or acceptance of an evaluated candidate. Releases before 0.51.3 are in
Git history at `562a654b`. Unfinished work belongs in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## [Unreleased]

### Fixed

- Defects that predate the runner rewrite, fixed by the owner's decision of 2026-11-03, each with a test
  that failed first:
  - a candidate cannot escape a FAIL with file names: a state file or a repository file whose name is not
    UTF-8 is kept as `\xNN` text and graded, instead of crashing the attempt (and its batch) or turning a
    forbidding change check INCONCLUSIVE; a changed file that cannot be read back under its name is not
    shown free of a forbidden needle;
  - the forbidding probes read the checkout before any other probe runs, so the candidate's code, run by
    an oracle or a suite, cannot rewrite what they read;
  - the CLI's result fields are typed by the parser: a value of another type is unknown, never an
    attempt that raises;
  - an attempt that raised before the CLI started records a known zero cost, so it no longer blocks a
    capped re-run of its label;
  - a crash of `build_probe.py` exits 2 (INCONCLUSIVE) with its traceback, never 1, a FAIL verdict's code.
- The second bug pass over the runner rewrite (adversarial, older-run and failure-path reviews) found
  eleven defects the pull requests or the first pass's fixes left, each fixed with a test that failed
  first (RUNNER-001):
  - a regrade of a run saved before evidence-v1 refuses a state file its trace summary names outside the
    state directory, as one named in `evidence.json` already was;
  - the runner's git reads switch off `core.fsmonitor`, so a plugin root a saved run names never runs a
    command its repository configuration supplies, in a regrade or in `check-evidence`;
  - the evidence-only regrade checks the judged response against the run's own grade again, so an edited
    final text cannot turn a judged FAIL into a PASS;
  - a kept outcome counts only as the kind the scenario keeps it as, so relabelling a judgment in the
    evidence no longer escapes the stale-judge rule;
  - whatever one saved run raises is that run's error in `regrade`, `rescore` and `check-evidence`,
    nesting too deep to read included, and a pinned agent's frontmatter that no longer reads leaves a
    native run unmeasured under a reason that names the plugin root;
  - the attempt log records `invoked` when the CLI ran before the attempt raised, and an attempt log that
    cannot be written warns instead of leaving a stale summary row over a published run;
  - `regrade` and `check-evidence` count only the runs they read, `check-evidence` names a run that lost
    the `evidence.json` its record lists instead of passing it as pre-evidence, and says when the runner
    changed since the run.
- Two batch failures that predate the runner rewrite, each with a test that failed first. A rerun onto
  a label's existing slot crashed with a traceback and exit 1, a FAIL batch's code, and an offset that
  reached a taken slot did so after paying for the trials before it; every planned slot is now checked
  before the first trial, and a taken one refuses the job (exit 3). A batch summary cut short by a full
  disk or a kill crashed the next resume the same way; the summary is now replaced whole, never
  rewritten in place, and one that cannot be read refuses the append (exit 3), in the native batch and
  the Inspect batch alike. The record and evidence models' refusal of an integer written as `5.0`,
  which their JSON Schemas accept, is documented in `contracts.md` and pinned by a test.
- The first of three bug passes over the runner rewrite (PRs #460 to #470) found thirteen defects the
  pull requests introduced, each fixed with a test that failed first (RUNNER-001):
  - a run the CLI ends at its declared turn limit grades its `tool_call_count` checks again: the CLI's
    error result variants carry `errors`, not a `result` text, and still close an intact stream;
  - the state directory and `.agents` are read before any probe runs, so an oracle that executes the
    candidate's module with the fixture env (`build-natural-injection-helper-*`) no longer fails
    `state_file_absent` with its own write;
  - a `state_file_absent` name must be one file directly in the state directory, and a state file the
    evidence names outside it is refused on a regrade, never written;
  - a kept instrument failure names a backing service as the trial's reason only when the failure is the
    service's, and a regrade's kept marker on a reason is no difference from the live grade;
  - one unreadable `evidence.json` is reported as not regraded instead of ending the iteration's
    regrade, and an older incident run whose conversation index is damaged regrades INCONCLUSIVE naming
    it instead of raising;
  - an older run's kept verdicts are found by the saved scenario identity and position again, as before
    the cut-over, not by position alone;
  - `check-evidence` checks an older native record that lacks its trace summary, and exits 2 when it
    checked no run at all;
  - the attempt log records `invoked` only when the CLI ran;
  - an incident answer with CRLF line endings saved on Windows by a runner before the fix regrades as
    it was graded.
- Five defects a review of the evidence-only regrade found, each with a test that failed first: a native
  run whose older evidence cannot regrade alone and whose trace summary is gone is skipped and counted
  again instead of ending the iteration's regrade; removing a native run's first `invocation.json` no
  longer switches off the check that its remaining files agree with its evidence (a native run regrades
  from all of its files or none); a damaged `argv` in an older native run is reported INCONCLUSIVE
  instead of raising; `check-evidence` replays native turns as the evidence-only regrade does; and an
  incident answer with CRLF line endings regrades as it was graded, its `response.md` written without
  newline translation and compared with universal newlines (RUNNER-001).

### Added

- A run with its own evidence regrades from `evidence.json` alone. Each native turn now records its
  parsed trace, workspace, the credential-marker names its raw trace held, and an incident turn's
  released input, release record and judge context by digest, with the conversation index; the
  boundary and release replay runs over those turns through the same core that reads an older run's
  files. Where the run's files are still beside the evidence they are replayed too and must agree, and a
  raw trace whose bytes differ from its recorded digest is refused. The new evidence-v1 fields are
  optional, so records written before them load and regrade from files as before (RUNNER-001).
- `build_probe.py check-evidence ITERATION_DIR`: grades every saved run that wrote `evidence.json`
  from that record alone, with no model, workspace or judge call, and exits 1 when a verdict differs
  from the run's own grade, naming the scenario when it changed since the run. It is the offline check
  that the evidence holds what the live grade read, the design record's named failure mode, on real
  runs rather than only the goldens (RUNNER-001).
- pytest-timeout and pytest-socket in the test group and CI: a 300-second ceiling per test, and no socket
  from the test process beyond loopback and Unix sockets; Hypothesis properties on the read-only guard's
  fail-closed composition rules; a uv override that gives the Harbor group filelock 4.x against litellm's
  declared bound, with the evidence in `pyproject.toml`.
- Inspect AI orchestration of the native routing and contract scenarios: `evals/inspect_fleet.py` runs the
  unchanged native trial as an Inspect task (one sample per scenario, one epoch per trial slot, the same
  published runs and batch summary), with offline tests, a `inspect-native` track, and a
  [parity run plan](docs/fleet-evaluation/run-plan-inspect-native-parity.md). The native CLI stays the
  acceptance reference ([decision](docs/decisions/2026-11-02-inspect-orchestrates-native-runner.md)).

### Changed

- The test suite passes under an elevated account: the tests that bind a runtime to the host (the
  SWE-bench runner and smoke fixtures, the batch cleanup test) read the host as an ordinary account
  through `probe_testkit.unelevated_host`, so a root container no longer reports 21 failures and 77
  errors that every change had to be argued past. The elevation rule itself is still tested with an
  identity it is handed.
- `cli.run` is the batch's plan, its scheduling under the budget stop, and its conclusion, three
  functions over two records (`Batch`, `Scheduled`) instead of one; no exit code, event, flag or
  saved-run interface changes (stage 5 of the runner rewrite, RUNNER-001, brought into scope by the
  owner on 2026-11-03).
- The evidence engine is the runner's one grading path: a live attempt's probes run once in its
  workspace and are recorded as evidence before the rules read them, the grade is read from the
  attempt's `evidence.json` as a regrade reads it later, and a regrade of a run that wrote one no
  longer reads its raw trace (the owner's decision of 2026-11-02). The old live grader and regrade
  loop, `shadow.json` and the `shadow` command are removed; `attempt.json` records the `probed`
  phase. The owner waived the shadow gate on 2026-11-03, so the cut-over is proven on the goldens
  alone (stage 4 of the runner rewrite, RUNNER-001).
- Refresh the lock to the releases of the last day (anthropic 2.4.0, filelock 4.2.7, jsonpatch 1.41,
  jsonpointer 3.8, python-discovery 1.9.1, langchain-core 1.7.4) and drop the `orjson` and `rich` pins,
  which nothing in the repository imports; rich remains as Inspect's dependency.
- State the action-reference rule: a floating major tag where the action publishes one, otherwise the
  exact release tag, both moved by Dependabot; setup-uv is pinned to its release 10.3.3, since it
  publishes no alias past v7, and the workflow test admits both forms.
- Parse fleet frontmatter as YAML, the way Claude Code and Copilot read it: `scripts/fleet_frontmatter.py`
  loads with PyYAML's safe loader (duplicate keys rejected, line-numbered diagnostics) instead of its
  own grammar, so typed scalars and lists reach the validators; Gate A now installs the locked `gate`
  group (PyYAML only) on the 3.12 floor. Every canonical and projected file parses to the same mapping
  as a plain safe load, and the generated projections are byte-identical.
- Manage dependencies as a uv project: `pyproject.toml` declares the dependency groups and `uv.lock`
  holds every exact version, replacing the six requirements files; CI installs with `setup-uv` and
  `uv sync --locked`, Dependabot proposes weekly lock updates, and the weekly run audits the locked sets
  ([decision](docs/decisions/2026-11-02-uv-project-lockfile.md)). The project environment re-resolved to
  current releases; Harbor, the SWT runtime and the sandboxes keep their contract pins, the Harbor set
  installs again, and the SWE-bench, SWT and Harbor adapter identities now hash the manifest and lock.
- The evidence engine grades every attempt in shadow: `probe/rules.py` names the eight result rules,
  `probe/engine.py` grades a scenario from its `evidence.json`, and `shadow.json` beside each live
  grade and each regrade records whether it agrees with the authoritative grade; `build_probe.py
  shadow ITERATION_DIR` counts the shadow grades against the owner's stage 4 gate. `attempt.json`
  records each phase an attempt passes through. A regrade now records a grading-machinery failure as
  a grader error, as the live grade does, instead of voiding the run (result rule 5 as amended
  2026-11-02); the `machinery_failure` golden's regrade view changes accordingly (stage 3 of the
  runner rewrite, RUNNER-001).
- The check registry is the `probe/checks/` package: the registry and one module per domain
  (checkout, text, changes, services, trace, state, graders), each declaration saying whether it
  is a check or a probe; `probe/checking.py` is a facade that keeps every name importable. The
  catalog and the conversation validator share a `specs` leaf instead of importing each other, a
  saved run's folders are read through `layout`, and the runner identity binds the sub-package
  (stage 2 of the runner rewrite, RUNNER-001).
- Each graded attempt writes `evidence.json`, the evidence-v1 record of what it observed and no
  verdict, validated by `probe.evidence.EvidenceV1` and published as
  `docs/fleet-evaluation/eval-evidence-v1.schema.json` (`build_probe.py schema --model evidence`);
  a written regrade of an older run writes the evidence `probe.legacy` reads back beside its
  assessment. The regrade's reconstruction moved into `legacy` unchanged (stage 1 of the runner
  rewrite, RUNNER-001).
- The golden saved runs gain three native conversations (a pass, a resumed call under the wrong
  session, a follow-up cut short) and a batch view per case recording what the result row tells the
  batch under rules 1, 5, 6 and 7; a written regrade is proved to land beside the original (rule 8).
  The native conversation stub moves into the probe test kit (stage 0 follow-up, RUNNER-001).
- The result rules of the 2026-10-03 eval-harness decision record have their own heading and, by
  owner amendment, name what a backing service that never starts, a grading-machinery failure and a
  cleanup failure after grading record; the runner-rewrite record carries the owner's decisions on
  the evidence artifact, the shadow gate, stage 5 and runner identity (RUNNER-001).
- Golden saved runs for the eval runner: one stub-driven attempt per threat-model result rule and
  run ending under `evals/fixtures/runner-goldens`, with the verdict views a regrade and a fresh trial
  must reproduce (stage 0 of the runner rewrite, RUNNER-001).
- The scenario loader parses with libyaml's C loader and the catalog CLI parses each scenario once;
  a full load drops from 1.4 s to 0.2 s and the scenario-heavy fast tests run about three times faster.
- The Inspect pilot tests join the heavy set, so the fast shards no longer import `inspect_ai`
  in every collecting worker.
- Test HTTP servers, the SWE-bench proxy and the runner's backing services shut down on a 10 ms
  poll instead of the 500 ms default; the proxy tests drop from 36 s to 2 s.
- CI skips the eval-machinery shards on a pull request that touches only documentation or agent and
  skill prose; `scripts/eval_tests_needed.py` names the trigger paths and `CONTRIBUTING.md` the rule.
- Trim the eval self-tests: the GCP grader-mechanics checks run on the 11-family pilot instead of
  all 31 families, the python-craft exit cross-products become diagonals, and the webhook oracle's
  test allowances shrink so a non-recovering mutant fails in ten seconds rather than twenty.
- Cut `AGENTS.md` to its map, three enforcement bullets, three conventions and the hard rule; rules the
  README, `CONTRIBUTING.md` and agent bodies already carry leave it, and the labels-in-transit clause
  leaves it and `helper-exchange.md` (LABELS-001 tracks the rest); the postmortem method now says the
  record stays blameless.
- Retire the `agent-engineer` agent; the `agent-authoring` skill now handles prompt, agent, skill,
  eval and roster work directly in your session, and routing that named the agent names the skill.
- Remove tests that only pinned exact wording in agents, skills, and templates; keep deletion guards
  for production-authority rules, the runbook fast-path banner, and the Confluence token prompt.
- Remove the retired Fleet Atlas archive from the working tree; its files remain in Git history at
  `3db39edc`.
- Retire the five-file review dispatch scenarios and the checks that graded carried evidence labels;
  grade a stale review finding by behavior instead of a fixed marker.
- Trim selected software-engineer reporting, escalation, and helper-dispatch instructions while
  retaining its existing builder workflow and caller-owned review rules.
- Refresh Claude Code and Copilot frontmatter guidance for plugin support and fields supported by
  each host; keep existing tool grants and generated header fields.
- Repair Windows evaluation fixtures, recognize CRLF verifier failure markers and allow
  bounded loopback refusal detection; retain explicit gaps for unavailable symlink privileges.
- Reconcile EVAL-012 preparation with recorded Linux trials, Windows verification gaps and the
  measured Docker quota failure; retain outstanding campaign and human-acceptance requirements.
- Clarify authoring reference selection and API client scope; trim repeated CI and database guidance
  while preserving operational authority, recovery rules, and executable examples.
- Consolidate `operational-learning`, `runbook`, and `postmortem` into `operational-docs` (27 to 25
  skills) with methods, assets, and importer behavior intact ([evidence](docs/reviews/2026-10-24-operational-docs-consolidation.md)).
- Trim the references of 22 skills, removing repeated narration, tutorials, and unconfirmed claims;
  contracts, recorded decisions, and fenced command blocks are unchanged.
- Correct reference facts: MSW 3 imports, configurable TraceQL windows, non-GPU startup-probe scope,
  Direct VPC sizing, and Confluence page-URL provenance; PCF rollback now checks installed capability.
- Drop unconfirmed observability team mandates; burn-rate thresholds and Splunk lookups are
  examples, and MQL, Alloy retention, Moogsoft, and ThousandEyes claims are corrected.
- Dashboard presentation and portability findings are advisory: advisory-only checks exit 0, query
  and missing-target findings exit 1, and unsupported or malformed input exits 2.
- Move the agent roster from `AGENTS.md` to README's Tools and delegation table, still validated
  against frontmatter by Gate A; two maintenance notes move from `AGENTS.md` to `CONTRIBUTING.md`.
- Condense this changelog to one entry per change and keep only the last two releases;
  `CONTRIBUTING.md` now states that rule.

### Removed

- The six `requirements-*.txt` files; `uv.lock` replaces them and the adapter identities hash the
  lock instead.
- Roadmap items SKILLS-001, SKILLS-002, SKILLS-003, FLEET-AUDIT-20261023 and HANDOFF-002, whose
  outcomes merged in PRs #420-#424, #429, #430 and #438, with the skills-audit report and the
  49-file agent and skill audit packet they cited; both stay in Git at `b55b5bbc`.
- The superseded 2026-10-11 frontend-craft ADR and the rejected 2026-10-23 review-gate-hook ADR;
  the decision index links their last revision.
- The unimplemented 2026-10-04 judge case-material ADR and the seven September 2026
  incident-quality review packets; INCIDENT-QUALITY-001 and the index link their last revision.
- The superseded VS Code 1.135.0 host row, the Fleet Atlas pointer, the pre-PR-#235
  `incident-investigation` snapshot, the WP-04 receipt and two sandbox upgrade receipts; Git keeps them at `b55b5bbc`.
- Fleet tests that pinned `software-engineer` wording; a two-phrase check keeps the caller-owned
  review path.
- From `AGENTS.md`: the Grafana-exception bullet, the stack-profile load sentence, and passages
  repeated in the frontmatter reference or `CONTRIBUTING.md`.
- Five completed review packets that only the old changelog entries cited; Git keeps them at
  `562a654b`.

### Fixed

- The SWE-bench runner tests write their fixture scripts with LF line endings, so the runner no
  longer rejects them on Windows hosts.
- The model-free smoke tests fake only the `docker` binary lookup, so the guard step finds `bash` on
  Linux again instead of the fake Docker path.

## [0.51.4] - 2026-10-23

### Changed

- `software-engineer`: compress the handoff rows and remove `## Rules`; its one unique rule, hand to
  one agent at a time, moves into Handoffs.
- `sre-assistant`: remove text its skills or the guard already cover; it states that its developer
  access to team apps is read-only use.
- `observability-engineer`: principles and method steps defer to `obs-alerting` and
  `obs-dashboards`, and a caller's requested output format wins.
- Trim the `stack-profile`, `agent-authoring`, `toil-reduction`, and `pcf-ops` cores to what their
  readers lack; the MCP output-cap rule moves to the frontmatter reference.

### Removed

- Fleet-wide agent body-shape checks and the tests that pinned `sre-assistant` wording; the
  tool-authority checks remain.

### Fixed

- `software-engineer` treats a push or tag push as a CI submission and again keeps embedded
  remote-URL credentials out of its context.
- The routine-completion grader matches the current return-header fields.

## [0.51.3] - 2026-10-22

### Added

- `go-craft`, a candidate skill for Go services, CLIs, libraries, and workers; native routing and
  benefit are unmeasured (BACKEND-002).
- WP-12's GCP catalog: 20 families (40 A/B cases); the owner accepted all 64 cases at `9147ff91`
  under DEC-14.

### Changed

- `software-engineer` gets a leaner core for dispatched work (issue #403): caller-owned review,
  named verification scope, and the final message as the report; the `Changed` packet slot returns.
- `observability-engineer` drops its unguarded-Bash paragraph; the ADR, the guard, and the
  `grafana` trust rule still hold.
- Rename `backend-craft` to `api-craft`, scoped to HTTP APIs, webhook receivers, HTTP clients, and
  API-accepted work, with corrected FastAPI, Huma, and credential-renewal guidance.
- EVAL-005 ran six Sonnet trials, all FAIL under the all-checks threshold
  ([run record](docs/reviews/2026-10-18-eval-005-run.md)).

### Fixed

- Oracle and handoff validation use contract checks instead of arbitrary count and length
  thresholds.
