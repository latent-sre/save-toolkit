# Changelog

All notable Save Toolkit changes are recorded here. This is pre-release repository history; a version
entry does not imply that a GitHub Release or immutable consumer selector exists.

## [Unreleased]

### Added

- Added `incident-investigation`, the human-facing troubleshooting advisor a responder runs in
  their own session. Every turn puts the loop on the first screen: what is known now, two or three
  ranked candidate causes with evidence for and against, the one check whose results separate them
  with what each result would mean, the reversible mitigation when users are hurting, who to page
  and when, and a board (ruled out, open, checked, next, follow-ups) that stops the responder
  looping back to a dead candidate. It reads the knowledge repository (service and alert cards,
  runbook, postmortems, index) as `[sourced]` data, names no platform CLI, runs nothing against a
  live target, writes no document, and at resolution fills a closeout packet routed to `scribe`
  for the postmortem and knowledge closeout.
- Added and closed the bounded `GRAPH-003` operating layer for the accepted offline
  `checkout-payments-timeout-drill/v1` graph. Existing metrics, logs, alerting, and runbook skills
  now carry graph-specific indicator, failure-plane, one-page, and response references; a
  pure-standard-library evaluator proves readiness fire/healthy resolve and preserves an unresolved
  `UNKNOWN` effect across unrelated success. Current exact-revision Docker evidence covers eight
  injected cases plus recovery. A discovery near-miss keeps live graph impact with `sre`; no
  dashboard, notification route, pager, credential, production target, or new authority is added.
- Added `incident-investigation`, a dedicated evidence-selected incident-depth router for first
  response, hypothesis investigation, systemic failure, and optional signal characterization, with
  the sustained-recovery lifecycle and the handoff packet as predicate-loaded references. The `sre`
  agent now uses those work modes while assisting the human incident team, defaults to bounded
  assistance, and enters sustained response only on explicit assignment; `eng-ladder` returns to
  Builder/Principal/Distinguished engineering altitude only. Guarded read-only investigation and
  human-executed production effects are preserved. (`sre-ladder`, briefly used for this router on
  the same day, stays on the stale-name denylist.) New direct contracts with red/green fixtures
  cover bounded assist, human ownership, first response, and the suspected-compromise carve-out;
  the measurement notes record the runner and grader findings from the implementation.
- Added durable-by-default measurement capture (`EVIDENCE-001`): sealed eval summaries now produce
  bounded, escaped evidence under `docs/reviews/`; host-owned exercises use the same validated
  envelope; Gate A rejects live-roadmap batch IDs that resolve to no committed review record. Raw
  transcripts, prompts, tool payloads, session identifiers, temporary paths, and credentials stay
  outside the durable record.
- Added the canonical `workflow-graph-engineering` skill (`SKILLS-003`): a runtime-neutral design
  and review contract for executable workflow/state graphs — typed state, node and edge classes,
  fan-out/fan-in, scheduling and admission, retries, effects with idempotency keys and an explicit
  `UNKNOWN` outcome, approvals, durability, cancellation, termination, taint, and graph-level
  evals — with six predicate-keyed references and a fourteen-section artifact template.
  Then-`prompt-engineer` (now `agent-engineer`) routes executable-graph design there; `agent-authoring` keeps the
  roster/delegation graph and excludes the executable contract. Five routing scenarios cover the
  positive case and the roster, code-graph, runtime-implementation, and runtime-selection near
  misses. No runtime, schema, or validator is selected or added.
- Added the explicit-only `incident-drill` skill: run a synthetic incident end to end through the
  fleet's real lanes (as plugin agents, with their real grants and the real hook guard) and retro
  what it finds. Ships a scenario pack — a checkout service with a two-release history, a staged
  evidence pack, and fourteen per-lane handoff packets — plus a scaffold script that materializes a
  drill directory, a lane runner, a cost/gap reporter, and timeline, observation-log, and retro
  templates. `check_links.py`'s manual-only allowlist gains `incident-drill` (a drill spends real
  money and writes files, so it must never be model-invoked), with a focused regression proving the
  requirement red before green.

### Changed

- Rewrote the incident stack around the human responder. `incident-investigation` now leads every
  turn with the next check, in the tools this team uses (Apps Manager, Splunk, Wavefront and PCF
  App Metrics, the Cloud Run console) via a new `references/first-checks.md`, with the advisor's
  voice and pressure traps in `references/advising.md`; `investigation-depth`'s modes, signal
  shapes, and terminal rules are folded into it. The `sre` agent is now the bounded read-only
  evidence-slice helper (19.5 → 10.6 KB): it says when the `cf` CLI is absent where it runs, carries
  its handoff packet inline, and has no recovery-state machine or tier ladder. `observability-engineer`
  cites `production-change-gate`'s tiers instead of restating them. `[verified: owner ratification]`
  became `[sourced]`, and the commander's record is stated as the only timeline, merging `sre`'s
  slices. `stack-profile` records that PCF is operated through Apps Manager and that Wavefront and
  App Metrics are the live PCF metrics UI.
- `run_evals.py` reconfigures stdout and stderr with `errors="replace"` at start: a judge
  evidence quote containing an arrow crashed a batch on a cp1252 Windows console after two
  trials, losing its summary and packet (2026-09-02).
- `evals/test_graders.py`'s `check()` now asserts as well as recording, so `python -m pytest`
  sees its failures; since the move to pytest every test in that file had passed regardless of
  its checks, and one Splunk alerting fixture had been red since #209 without anyone seeing it.
  The fixture now carries the scenario's fixed runbook link.
- Every agent handoff packet is now six slots (`→ Handing to`, `Goal`, `Change`, `Findings`,
  `Verified`, `Not done`) in `software-engineer`, `reviewer`, `observability-engineer`, `scribe`,
  and the `sre` contract in `investigation-depth/references/incident-handoff.md`; the seven slots
  only the eval harness read are gone, and the Rules block keeps one owner, named change,
  evidence labels, claim-level taint, non-actions, and the production gate. The `agent-authoring`
  roster's rule requiring `Run/attempt:` and `Model:` on every packet is removed with them: it was
  the last statement of a contract no agent body has carried since the eval-harness doctrine was
  cut. `scribe` keeps a seventh slot, `Follow-up:`, because the operational-learning disposition
  policy routes a blocked closeout's tracker reference or filing owner through it.
- Removed the 23 "ownership map only, not a load" sentences from skill bodies and references; a
  body no longer names a sibling skill in order to tell the model not to load it. The 15 copies in
  skill descriptions are routing metadata and stay until their evals are run.
- `docs/fleet-roadmap.md` is the six-field contract only (status, owner, outcome, next action, one
  evidence link): 100 KB → 17 KB for the same live items; closed and superseded items are one line
  each in `roadmap-closed.md`. `docs/rules.md` and `docs/README.md` are folded into AGENTS.md's
  "Start here" table; the three entry documents are README, AGENTS.md, and CONTRIBUTING.
- `fleet_doctor.py` emits a plain JSON report instead of an evidence envelope; explicit-only skills
  are checked for `disable-model-invocation: true` by `check_links.py` instead of by a prose test.
- Hardened the calibrated `rubric` judge after review: every evidence item must be a verbatim quote
  from the graded response, a verdict from a model other than the pinned identity is inconclusive,
  the prompt travels on stdin instead of argv (a NUL or an over-long response is no longer a
  mid-eval crash or a platform command-line failure), and the spawn honours `CLAUDE_BIN`.
  Calibration takes the judge identity from its own first live call (or, for a fully cached run,
  from the cached verdicts, saying so and spending nothing), scores agreement over conclusive
  judgments only, and fails the run on any inconclusive rather than counting a timeout as agreement
  with an expected FAIL. Judge cost, elapsed time, and resolved identity are recorded
  per trial and rendered in durable evidence; `build_probe.py --regrade` keeps a rubric check's live
  verdict instead of spending a fresh judge call. The contract is the accepted
  `docs/decisions/2026-09-01-rubric-judge-evaluation-contract.md`, which supersedes the multi-engine
  evaluation ADR and its `EVAL-003` roadmap item.
- Replaced nine regex-based eval graders that judged natural-language policy (production-action
  claims, deploy commitments, recovery authority, unknown-outcome reconciliation, retirement effect
  claims, blind retry, invented recovery progress, progress-vs-record consistency, gate posture)
  with one calibrated `rubric` grader that spawns a clean-room, tool-less `claude -p` judge turn
  against a named rubric in the new `evals/rubrics.yaml`; fails closed on any broken judge and
  caches verdicts by (model, rubric, rendered text, response). The twelve scenarios that used those
  graders now reference the equivalent rubric; every other grader is unchanged. Calibrate with
  `python evals/judge.py --calibrate`, checked against `evals/rubrics-calibration.yaml`.
- Compacted three skills under SKILL-001, descriptions byte-identical, measured as canonical
  UTF-8 bytes against `main`: `backend-craft` SKILL.md 11,123 → 10,131 (endpoint, upstream-client,
  and persistence test mechanics routed to their references, which grew 29,198 → 30,182; the
  selected stack now wins over an unconditional PostgreSQL default); `obs-alerting` SKILL.md
  7,930 → 5,804 (generic SLI and worked burn-window recitation removed, references unchanged);
  `obs-dashboards` SKILL.md 11,419 → 7,160 and references 83,298 → 34,480 (generic dashboard
  advice and volatile tool catalogues removed; dashboard-only write authority, API-family
  concurrency, ambiguous-write reconciliation, rollback, readback verification, and
  version-specific storage rules kept). The observability build probe now fails closed before any
  model launch when a fixture service is unavailable, and reaches fixture services through a pinned
  fixed-target relay because Docker Desktop 29 suppresses host publication on internal networks.
  Two discovery scenarios were repaired: the tool-less dashboard case asks for an explicitly
  `[unverified]` procedure, and the Splunk alerting case supplies fixed fictional route and runbook
  values instead of rewarding invention.
- Removed eval-harness doctrine from all eight agent bodies: the run/attempt and resolved-model
  identity rules, the two matching handoff-packet slots, the absent-versus-guard-denied rule, and
  the failed-delegate paragraph (kept as one sentence in the three delegating lanes). No runtime
  user supplies a run ID; the evidence-label triad, taint rules, and handoff packets are unchanged.
- Gate A now runs two structural validators, `check_links.py` and `validate_fleet.py`, instead of
  eight. `check_links.py` keeps frontmatter grammar and link containment and drops its prose-style
  rules; `validate_fleet.py` keeps the tools-authority matrix, delegation graph, guard wiring, and
  handoff and evidence anchors and drops the scribe-bundle phrase regexes.
- Component tests run under `python -m pytest` (pinned in `requirements-dev.txt`, configured by
  `pytest.ini` over `scripts/` and `evals/`); the CI component-tests job calls it directly. Test
  files remain plain `unittest` modules and still run individually.
- Renamed the evidence-selected incident-depth router skill `incident-investigation` to
  `investigation-depth`. Its body, description, references, and canary tokens are byte-identical
  apart from the frontmatter `name`; the `sre` agent, `incident-command`, `eng-ladder`, the fleet
  validator, graph-contract and canary tests, the nine scenarios and four profiles that named it,
  and the generated adapters follow the rename. The `incident-investigation` name is reserved for
  the human-facing incident skill introduced in the follow-on change.
- Pinned VS Code beta packaging to the supported selector-based Copilot plugin format: the platform
  validator now rejects an Agent Plugins 1.0 `$schema` unless the component layout is deliberately
  migrated, and the quickstart documents source, Copilot CLI marketplace, and isolated-local plugin
  installation separately from checkout-only agent discovery.
- Added a pinned VS Code agent-to-agent beta fixture and probe that separates complete plugin
  discovery, a real allowed fleet edge, a synthetic allowed child, and explicit forbidden-child
  rejection, while keeping the `adr` slash command out of the 33-skill inventory. Model-visible
  filtering and human-selected handoff buttons no longer count as proof of model-driven delegation
  enforcement.
- Added the missing portable skill-metadata gates: names stop at 64 characters and optional
  `compatibility` text must be a single-line scalar stopping at 500, so an invalid or
  normalization-bypassing generated skill cannot pass locally and then disappear silently in
  Copilot.
- Raised SKILL-001's advisory Phase 2 entrypoint screen from 7,500 to 7,800 immutable bytes and
  remeasured the exact campaign head through Git objects. The six undispositioned slices are
  unchanged; `gcp-ops` and `incident-investigation` are below the new screen while `obs-alerting`
  remains above after its GRAPH-003 reference link. The screen still selects evidence checkpoints
  only—size alone is not a finding or permission to cut content.
- Closed `GRAPH-002` after owner acceptance of the repository-integrated `graph-sandbox/v1`
  candidate at merge commit `4a745fb311ad7df83ec6aeaf3268356ce4780db5` (PR #193). This accepts only
  the offline `checkout-payments-timeout-drill/v1` implementation; GRAPH-003, live Terra execution,
  credentials, production connectivity, and production authority remain outside the boundary.
- Reconciled four stale or evidence-pending roadmap items. `INCIDENT-001` and `SURFACE-001` now
  close against their already merged exact revisions instead of inviting duplicate work.
  `DRILL-001` retains a three-case Terra acceptance candidate and `ROUTE-002` a 7/7 Terra overlap
  transfer; both state the host-transfer and missing-telemetry limits. The owner accepted those
  limits after PR #176 merged, so both entries moved to the closed register without treating an
  eval result as its own promotion authority.
- Closed the current `GRAPH-001` incident-drill and production-`UNKNOWN` review gaps: byte-valued
  timeout output is retained, empty and setup-failed attempts are explicit failures, report run IDs
  cannot escape their root, retries require a safe terminal readback and affirmative human owner,
  and the production scenario rejects agent-executed reconciliation claims. The three
  `GRADER-003` direct contracts also carry frozen Terra transfer forms: 1/9 before the bounded grader
  correction and 9/9 after it, with existing incomplete/adversarial responses still rejected.
  `GRAPH-001`, `EVIDENCE-001`, and `GRADER-003` closed after exact head `1875057` merged in PR #176 at
  `810f7e6`; the owner kept the three direct grader scenarios in `calibration` rather than
  relabelling host-neutral Terra transfer as native Claude behavior.
- Cut the body/reference duplication the
  [2026-08-26 three-pass audit](docs/reviews/2026-08-26-three-pass-skill-audit.md) measured — the same rule
  bought twice whenever a reference loaded alongside the body that already states it. **Context:**
  `agent-authoring`'s `artifact.md` no longer restates SKILL.md's source-trust gate, four method
  steps, description rule, failure→form table, or handoff/production-gate rules; it now owns only
  what the body leaves open (case-set sizing, the per-symptom fix table, the wrong form each
  failure invites) and states its candidate budget once instead of three times. `context.md` and
  `tools.md` defer to the body's trust and handoff rules the same way. `operational-learning`'s
  `disposition-policy.md` keeps the event→artifact map, default paths, and evidence rules, and
  defers `prepared`/`duplicate` to SKILL.md's invariants — while retaining the validator-pinned
  checkout-binding and promotion sentences the fleet deliberately states in every layer (both
  regressions went red during the cut and were restored, which is the pin working). `obs-logs`'
  SPL and LogQL references keep only dialect-specific escaping/quoting mechanics under the body's
  identifier-trust and rate-not-count rules. Fleet-wide body-sentence echoes by the audit's own
  measure drop 64 → 33; every remaining echo is a router-table line matching its reference's gate,
  a validator-pinned multi-layer rule, or `incident-command` text owned by active roadmap item
  `INCIDENT-001` and deliberately left untouched. **Surface (`SURFACE-001`):** the two
  self-retracting worked examples — `pcf-deploy`'s manifest-name interaction and `runbook`'s
  worked excerpt — keep their `[unverified]` labels as one-line footnotes instead of retraction
  paragraphs. Adapters regenerated; Gate A, `check_links`, `check_canary_tokens`,
  `validate_fleet`, `run_evals --validate` (107 scenarios), and the scripts/evals unittest suites
  pass, minus one pre-existing `test_fleet_doctor` envelope error also red on the unchanged base.
- Audited `backend-craft` against the four-theme design rule and repaired what the audit found.
  **Correctness:** `consuming-apis` cited a product name one rename stale against `stack-profile`
  (Wavefront/Aria Operations for Applications, now Broadcom DX OpenExplore) and omitted Moogsoft's
  current vendor, under a heading that told the reader to cite current names — the per-integration
  section now carries an ownership pointer making `stack-profile` the single place a rename lands;
  its blanket "reflect a hard-down critical dependency in `/readyz`" contradicted SKILL.md's
  qualified readiness rule and now defers to it; and seven references pointed at
  `skills/backend-craft/SKILL.md`, a path that does not resolve once the skill ships in a plugin,
  now `../SKILL.md` as elsewhere in the fleet. **Context:** `api-design` restated SKILL.md's method
  semantics, status codes, and pagination default nearly verbatim, charging for them twice whenever
  it loaded, and now owns only what SKILL.md leaves open; `consuming-apis` carried two overlapping
  sections covering the same five topics and an ops-tooling voice inside a general-purpose skill;
  five references repeated their own H1 as a section heading; `auth` had one bullet list split by a
  stray blank line; SKILL.md stated the `429`/`Retry-After` rule twice within one section.
  **Loop:** the OpenAPI starter had drifted from the contract SKILL.md asserts — no `request_id`
  extension and no rate-limit response at all — so it now carries both, pinned to SKILL.md by a
  focused regression proven red before green; `fastapi` gained the Pydantic v2 / SQLAlchemy 2.0
  version caveat `spring-boot` already carried. Two routing scenarios now cover the skill's two
  trigger arms, which had no eval coverage among the previous 94. **Hosts:** the repo-rooted
  path was broken in the Copilot projection too, where the bundle sits under a different
  prefix entirely, so `check_links.py` now rejects a reference naming its own `SKILL.md` by
  repo-rooted path — the pattern `CODE_PATH_RE` never covered. Arming it surfaced the same
  defect in seven `frontend-craft` references, fixed here; a focused regression proves the
  self-pointer red and both `../SKILL.md` and a sibling-skill mention green.
- Assessed merging `agent-authoring` and `agent-security`; kept them separate and recorded why. The
  bundles share no distinctive vocabulary (trifecta, prompt injection, Rule of Two, tool absence all
  appear zero times in `agent-authoring`), `artifact.md` already declares `agent-security` the owner
  of the independent threat review, and then-`prompt-engineer` composed them on a predicate rather than
  needing one file. Merging would push the always-loaded body to roughly 4.5k tokens against a 5k
  budget, and collapse eight routing scenarios including three deferral contracts.
- Refreshed `ci-actions` on `actions/checkout` fork-checkout refusal: the behavior shipped in v7.0.0
  on 2026-06-18 and was **backported to every supported major on 2026-07-16**, so the reference's
  "v7.0.0 and later" framing no longer described a pinned v5 or v6 workflow that had started failing
  without moving — the skill's own "why is this workflow failing" trigger. Added the exact refusal
  conditions and the `allow-unsafe-pr-checkout` opt-out, framed as an unsafe design to review rather
  than a fix. Added the two routing scenarios `ci-actions` lacked, one of them the pwn-request
  request that a helpful assistant would otherwise fulfil, and gave `agent-security` and `ci-actions`
  the `argument-hint` the rest of the fleet carries.
- Corrected the README roster's `Routing` column for `observability-engineer` and then-`prompt-engineer`,
  which mixed real `Agent(...)` delegation edges with handoffs the caller must dispatch. Both agent
  bodies state the constraint explicitly ("this role cannot invoke `software-engineer`; the
  recommendation returns to the caller"), and the `sre` row already modelled the distinction, so the
  two rows now follow it. AGENTS.md's `Delegates to` column is bound to `EXPECTED_DELEGATION` by
  `validate_roster_graph`; README's `Routing` column is prose and is not, which is why it could drift
  into naming edges the frontmatter never granted.
- Deepened the `runbook` skill from process coverage to authoring craft. It was already strong on
  protocol — structure, accretion, Confluence import, alert linking, Crawl→Walk→Run — but every
  asset in the bundle was a blank skeleton, so an author got slots and rules and never saw what
  filling them well looks like. Adds a complete worked exemplar
  (`assets/runbook-example.md`): a matured runbook whose triage branches route *away* from the
  wrong action, whose expected-output lines separate partly-worked from failed, and whose incident
  history shows three real incidents changing it. Adds `references/step-craft.md` on how a
  correct-looking step produces a wrong action under pressure — ambient targets, success-only
  expectations, steps reached out of order, non-idempotent rollbacks, unbounded retries,
  placeholders with no source, scope that quietly grew. Adds a *Before you publish* readback to the
  body: four questions asked as the tired responder rather than the author, since authors cannot
  see the gaps they hold the context for. The exemplar is pinned to the frontmatter schema and to
  its own exemplar disclaimer by two focused regressions, each proven red before green — a
  demonstrated-but-invalid example teaches the wrong shape more effectively than the schema teaches
  the right one. Two routing scenarios join the existing pair, which tested only routing: one
  measures whether authored steps carry branches, stop conditions, and rollbacks; the other hands
  the skill a prompt that actively invites confabulation ("just put in whatever is plausible") and
  checks the honest gaps stay visible as gaps. Body grows from ~1.7k to ~2.2k tokens against the
  ~5k budget.
- Renamed the `prompt-engineer` agent to `agent-engineer`. The lane owns agent bodies, skills, tool
  and grader descriptions, bounded eval loops, roster and delegation graphs, and workflow-graph
  designs; prompt text is one artifact class among those, so the old name understated it the same way
  `coder` understated the build lane. This is a breaking address change from
  `save-toolkit:prompt-engineer` to `save-toolkit:agent-engineer`; description, tool authority, body
  contract, and the single `Agent(researcher)` edge are unchanged
  ([ADR](docs/decisions/2026-08-26-agent-engineer-rename.md)). No routing comparison was run —
  the decision rests on human legibility, as its predecessor did, and the prior rename's measured tie
  is the only evidence that a name change of this kind does not move automatic routing. Retiring the
  name also removes one of the three role-name collisions with another installed agent suite.
- Renamed the `sde` agent to `software-engineer` so the public component name reflects its full
  implementation, testing, and operations-tooling lane. This is a breaking address change from
  `save-toolkit:sde` to `save-toolkit:software-engineer`; tool authority and delegation are
  unchanged ([ADR](docs/decisions/2026-08-25-software-engineer-rename.md)).
- Generalized `release-gate` so non-GitHub distributions can prove immutable artifact identity
  without inheriting GitHub Release controls, while GitHub Releases still require current
  repository immutability and matching tag-ruleset evidence.
- Folded `merge-gate` and `release-gate` into `production-change-gate` as its merge-readiness and
  release-readiness references; one skill now answers "ready to merge", "ready to ship", and "may
  this act on production", each with its own checklist and a shared verdict shape. 24.6 KB across
  three skills is now 12.7 KB in one; `SKILL.md` is 7,488 B.

### Removed

- Removed `skills/investigation-depth` (folded into `incident-investigation`) and the two `sre`
  scenarios that graded the `incident-state/v2` recovery-state machine; the recovery rubrics and
  their calibration cases stay in place without a scenario.
- Removed `skills/merge-gate` and `skills/release-gate`.
- Removed 60 uncited dated packets under `docs/reviews/` (kept: everything a test or a live
  document cites; history is `git log -- docs/reviews`), `docs/rules.md`, and `docs/README.md`.
  `check_links.py` now reads `docs/reviews/*.md` as well, so a retention pass that keeps a packet
  while deleting one it cites fails the gate instead of passing it.
- Removed the verification apparatus that guarded only itself: `mutation_guard.py`,
  `evidence_envelope.py` and its schema, the `fleet_doctor` envelope (a plain report that still
  names the inspected root and revision replaces it), and the five prose-contract test files (`test_graph_contracts`,
  `test_observability_skill_contracts`, `test_platform_skill_contracts`,
  `test_release_skill_contracts`, `test_skill_asset_contracts`) that pinned sentences in agents
  and skills by substring; `test_graders.py` keeps one positive, one negative, and one adversarial
  case per assertion class.
- Removed the nine natural-language-policy graders from `evals/graders.py`
  (`production_execution_claim`, `pcf_deploy_no_inline_execution`, `incident_recovery_authority`,
  `production_unknown_outcome`, `service_retirement_no_effect_claim`,
  `unknown_write_no_blind_retry`, `unknown_recovery_progress`, `recovery_progress_consistency`,
  `gate_posture`) and their dedicated adversarial regex-fixture tests in `evals/test_graders.py`
  (graders.py 1706→677 lines, test_graders.py 5788→4354 lines); their calibrated adversarial
  corpus lives on in `evals/rubrics-calibration.yaml` instead. The six structural graders
  (`exact_fields`, `exact_json`, `embedded_exact_json`, `json_artifact_statuses`,
  `cloud_run_rollback_packet`, `learning_loop_promotion`) and the five basic ones (`contains_all`,
  `contains_any`, `not_contains`, `regex`, `not_regex`) are unchanged.
- Removed the document-convention gates and their tests: `check_plan_status.py`,
  `check_evidence_refs.py`, `check_stale_names.py`, `check_canary_tokens.py`,
  `check_query_catalog.py`, `check_test_layout.py`, the sequential `run_component_tests.py`, and
  the three graph-contract tests that asserted the deleted agent doctrine by substring. Canary
  tokens inside references stay; `run_evals.py` still reads them at runtime.
- Retired the unpublished repository-specific release workflow, request and workflow contracts,
  release-only tests, and release runbook; no immutable release channel had been activated.
- Retired the standalone multi-host lifecycle probe and focused suite because no workflow, CI job,
  or named manual consumer called them.
- Retired the stale local Sol evaluation and unimplemented durable-state backlog items, retaining
  their historical evidence and explicit consumer-driven reopen triggers.
- Retired Codex as a **distribution target**: the generated `.codex/agents/` and
  `plugins/save-toolkit/` projections and the conflict-safe agent installer are gone
  ([ADR](docs/decisions/2026-08-23-retire-codex-distribution-target.md)). Codex remains a
  supported way to *work in* this repository — it reads the root `AGENTS.md` and needs none of
  those bytes. **Breaking for anyone who installed the Codex agents or skills plugin:** deleting
  the projections cannot reach copies already written into a Codex home, and the marker-aware
  installer that owned them is removed here. The ADR's *Migration* section carries the exact
  cleanup — match the whole first line against the `save-toolkit`/`sre-agents` markers, never a
  filename or prefix, because another installed suite's marker can differ by one character and
  share three role names.
- Removed the multi-engine execution-profile and result-envelope eval stack (`engine_contract.py`,
  `execution_profiles.py`, `eval_evidence.py`, `resolved_context.py`, the `evals/profiles/`
  approved-profile directory, the `--profile` flag, and the Codex adapter/dispatch path in
  `engine_adapters.py`/`run_evals.py`): it never changed a prompt, its cost field always reported
  `unavailable`, and Codex live execution was already hard-disabled before `subprocess.run`. The
  legacy `--run`/`--validate`/`--mode`/`--split`/`--match`/`--model`/`--trials` Claude-plugin path
  is unchanged.
- Retired 99 scenarios from `evals/scenarios/` in the eval-corpus cut (28 on skills slated for
  merge or labs, 26 templated deferral negatives, 32 keyword-only direct scenarios, 13 duplicate
  discovery positives); 46 remain (15 policy or structural direct, 25 one-per-target discovery
  positives, 6 curated negatives) plus the six build probes.

## [0.1.0] - 2026-08-11

> **Prepared repository baseline, not a published release.** No `save-toolkit--v0.1.0` tag or GitHub
> Release exists. The date above records when this baseline was prepared; the later retirement of
> its unpublished release machinery is recorded under `Unreleased` rather than rewriting this
> historical inventory.

### Added

- Eight canonical engineering and SRE agents, with 30 canonical skills and one ADR command.
- Deterministic Copilot/VS Code and Codex projections generated from the Claude-native sources.
- Fail-closed guarded-Bash enforcement for the SRE lane, plus structural tests for
  tool authority, hook wiring, generated-byte parity, links, schemas, and routing scenarios.
- Conflict-safe standalone Codex-agent installation and disposable host install/inventory/uninstall
  probes that do not write user-owned configuration.
- Evidence envelopes, evidence-bound operational documentation closeout, release/readiness gates,
  and the single Gate A structural entrypoint used on Linux and Windows.
- Exact-SHA immutable release preparation with permanent version reservations, non-replacing request
  serialization, attempt-addressed evidence artifacts, and consumer rollback instructions.

### Changed

- Renamed the fleet and plugin to Save Toolkit and consolidated observability ownership under the
  `observability-engineer` lane.
- Added GCP operations and Akamai edge-routing skills while preserving explicit PCF, active-incident,
  and observability lane boundaries.
- Gave declared incidents an explicit fast path through `production-change-gate`: a named
  never-skipped core (classification, human confirmation of an exact command or an IC-approved
  bounded envelope, blast radius, backout, named decider) with every other record reconciled after
  resolution, scoped to Tier 0–2 operational mitigation and rollback to an already-live artifact.
  Shipping a new artifact and any Tier 3 action stay on the full gate.
- Trimmed duplicate checklist items from the three gates and scoped handoff SHA pinning to
  references whose byte identity decides something downstream.
- Documented the four design disciplines the fleet is built on — loop, graph, handoff, and learning
  engineering — in `AGENTS.md` with depth in `agent-authoring/references/roster.md`.
- Rewrote the README around installation and first use, relocating validation, eval, and release
  detail to the documents that own it.

### Security

- Generated hosts state their weaker enforcement explicitly instead of claiming Claude hook or tool
  semantics they cannot enforce.
- External research is separated from private-checkout investigation, and destructive or production
  effects remain human- or protected-workflow-owned.
- Every read-only-guard denial now names the rule that fired instead of printing one static
  paragraph, and the guard permits shapes proven harmless (quoted comparison operators via
  token-level redirect detection, `>/dev/null`, `2>&1`, `timeout <n> <allowed command>`, and
  display-only `date`) without weakening command-substitution or backgrounding rules.
- Release host proof derives exact ordinary-file paths and Git blob bytes from the observed tagged
  commit, then requires both marketplace and installed Claude/Codex trees to match before publication
  can finalize; linked, special, missing, changed, and extra content fails closed.

### Known limitations

- Copilot CLI distribution is out of scope by owner decision; VS Code discovery is verified at the
  workspace-file level, not through its UI.
- Codex custom-agent discovery is verified at the installed-file level; no model session is part of
  the release smoke.
