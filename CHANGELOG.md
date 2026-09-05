# Changelog

All notable Save Toolkit changes are recorded here. This is pre-release repository history; a version
entry does not imply that a GitHub Release or immutable consumer selector exists.

## [Unreleased]

### Added

- Added `archive/incident-autonomy/`: byte-exact copies of the `sre` agent, its VS Code
  projection, `investigation-depth`, the two sustained-response scenarios, and the three rubrics
  with their 35 calibration cases, plus twelve restore patches and a README with the restore
  steps. Measured in [the incident-lane fold evidence](docs/reviews/2026-09-03-incident-lane-fold-evidence.md)
  and decided in [the advisor-and-hands ADR](docs/decisions/2026-09-03-incident-lane-advisor-and-hands.md).
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

- Drafted a human-first `incident-investigation` response loop: calibrated explanations,
  feasible checks with inconclusive outcomes, contextual checkpoints, and explicit action states
  in handover and closeout. Initial candidates remained inconsistent despite automated passes.
  The approved follow-up reorganizes the skill into Explain / Investigate / Recap, aligns its
  description with human support, and consolidates evidence reasoning and unchanged operational
  authority. Actual three-turn conversations show clearer responses and better rollback-history
  handling, with remaining scope/fallback caveats. Five routing cases pass and one times out;
  all structural checks pass within the original size cap. Graders are unchanged. Exact revisions,
  limitations, and prior failures remain in [the companion evaluation](docs/reviews/2026-09-05-incident-human-companion.md);
  evaluation does not accept or publish the candidate.
- Corrected incident artifact classification, approval-free draft planning, the unavailable-diagnostics
  exception, researcher example provenance, and builder-to-reviewer preparation. Production authority
  and reviewer tool absence remain unchanged. See the
  [follow-up evidence](docs/reviews/2026-09-04-operational-contract-fixes.md).
- Clarified delegated work as a return-and-resume loop: helpers report assignment status, results,
  evidence, and gaps to their caller; callers assess and combine returns, retain the original
  objective, and continue authorized work. The incident advisor resumes after a bounded evidence
  slice; the human retains operational decisions. Partial returns leave dependent work incomplete
  without stopping independent work. Qualified the existing Claude delegation targets with the
  plugin namespace after a live probe found bare grants admitted no child on CLI 2.1.261; the
  allowed graph and human-selected host handoffs are unchanged. Verification is recorded in
  [the return-loop evidence](docs/reviews/2026-09-04-delegation-return-loop.md).
- Twenty-four P2 rows of the 2026-09-04 fleet rescan, in six commits. Agent bodies: the fenced
  handoff-packet template and six-bullet Rules list in four bodies become the paragraph form
  `sre-assistant` already used (the two delegating lanes keep a byte-identical `## Rules`
  paragraph); approval scope, the review/fix loop budget, the progress-file marker, the eng-ladder
  escalation, the learning-loop promotion review, the sandbox-only "Mission block", and the
  retired-host no-execution essay are each stated once or not at all (113,614 B to 105,204 B).
  Skills: `gcp-ops` drops its grader-shaped answer template; `pcf-deploy` drops its second starter
  manifest; eleven facts stated across several files (the app-vs-platform split, credential-bearing
  reads, the escalation packet, rollback truth, no-OIDC, never-cancel, immutable releases, the
  UNKNOWN rule, Remedy/Jira, "agents never execute deployment", the cf reads) now have one owner
  each (569,802 B to 566,955 B). Harness: the five YAML-embedded build-probe oracles move
  byte-for-byte to `evals/oracles/` behind a new `writes_from:` key, so the evals line ceiling
  counts them (raised to 9,900); 355 lines of routing fixtures no test read, the unused
  `embedded_exact_json` grader, two unused build checks, and a link-gate glob naming a missing
  directory are deleted; eight agent-target calibration routing specs go (54 specs remain, the
  three incident-lane calibration specs kept); the readonly-triage scenario's commitment regexes
  become rubric calibration cases, while the recommend-only scenario keeps its regex graders
  because deleting them flipped seven proven red fixtures green. Docs: the roadmap states the
  architecture without a phantom ADR, measures the SKILL-001 slices, parks eleven items in one
  table; `docs/decisions/README.md` indexes the records; the incident-navigation patch bundle moves
  to `archive/`; `docker-verification.md` is linked from CONTRIBUTING. `agent-authoring`'s frontmatter
  reference keeps what the fleet probed or decided and drops the restated documentation (10,859 B to
  7,364 B); its roster reference keeps the four-theme rule, agent-vs-skill, the enforced principle,
  the deliverable, and the wrapper-layer failures (9,598 B to 7,062 B). One Codex review round on
  each PR: successor ADRs for the archive move and the eight-grader registry, `writes_from` shape
  validation, the GCP escalation packet and the loop budgets and learning-loop gate restored in
  compact form; the PowerShell spelling of the plugin root, the self-pointer check over every
  bundled Markdown file with a computed relative fix, the app-scoped stats endpoint, the
  golden-signal watch left with a human, and obs-pipeline's trigger narrowed to Loki or Grafana.
- Fixed the seventeen P1 rows of the 2026-09-04 fleet rescan, each a verified contradiction or
  dead pointer a responder or contributor would act on: bundled-script invocations now use
  `${CLAUDE_PLUGIN_ROOT}/skills/...` (three files resolved only from the repository root) and
  `check_links` rejects a repo-rooted self-pointer inside fences and code spans; the advisor names
  Apps Manager, Splunk, and Wavefront in the stack's order instead of Splunk and Grafana;
  `observability-engineer` no longer claims a dispatch its grant forbids and `software-engineer`
  names the two lanes it cannot invoke; the mitigation reference puts the responder, not
  `observability-engineer`, on the live incident and the advisor, not the agent, on the
  recommendation; `pcf-ops` shows its drill-in reads as question / Apps Manager view / `cf`
  command with the guard-denied forms marked human-run, and agrees with `pcf-deploy` that the
  human release owner executes; the README lists both manual commands; `/save-toolkit:adr` drops
  the dead plan-status gate and scopes its selected-agent preflight to hosts that have one;
  imported runbooks land in `docs/runbooks/` where the advisor reads; two "AGENTS.md after-change
  rule" pointers now name `CONTRIBUTING.md`; the query catalog no longer promises a deleted
  validator; `obs-pipeline` no longer advertises Splunk and Wavefront routes it lacks (a routing
  run is owed for the description) and labels the Prometheus exporter as the Mimir path;
  `akamai-edge` sends the SRE to Traffic by Hostname; the exemplar runbook's history row cites the
  right step. The Copilot generator keeps a runnable path for `scripts/` tails.

- `obs-dashboards`: `http-api.md` and `json-model.md` cut from 25,814 B to 17,142 B (15,422 B in the
  measured candidate; the review restored labels and four sentences afterwards), keeping every
  QA-measured Grafana 13 behavior and dropping the transport boilerplate and what a tools-off probe
  showed both models already carry. The measured candidate scored 15/15 on the comparable checks in
  every trial on Sonnet and Opus with 15 to 18 percent fewer tokens; see
  [the obs-dashboards trim evidence](docs/reviews/2026-09-03-obs-dashboards-trim-evidence.md).
- Two graders were stricter than the contract they grade and are fixed: the dashboard query-proof
  check requires the proof after the write, as the skill's verify step does, and treats a concrete
  window substituted for `$__rate_interval` as the same query; the `no_inline_deploy_commitment` rubric names the observability-engineer's dashboard
  write as that lane's permitted apply (29/29 on calibration). The carve-out probe also grades the
  new panel's unit, description, and `noValue` text.
- `runbook`: 50,817 B to 45,955 B (44,748 B in the measured candidate). `step-craft.md`, the runbook/playbook/SOP paragraph, and the
  Confluence export walkthrough went, on a tools-off probe showing both models carry them; the body
  now says a new runbook starts `status: draft`, the exemplar's scale step has the route it lacked,
  and the template's procedure slot carries the step's exit line and the every-step Expected rule.
  Measured with eleven new rules on the scribe runbook probe: the incumbent 47/51 on each model,
  the final candidate 50/51 on Opus and 51/51 on Sonnet; see
  [the runbook trim evidence](docs/reviews/2026-09-03-runbook-trim-evidence.md).
- The scribe runbook probe grades the produced runbook against the skill's own authoring rules
  with a probe-owned checker (0/11 on a thin runbook, 11/11 on a complete one before any trial),
  tightened over four review rounds; a unit test holds its template-literal list to the template.
- `obs-alerting`: 45,635 B to 36,223 B, and the `obs-metrics` PromQL reference 10,368 B to 5,570 B.
  The Workbook pairs, the Grafana evaluation lifecycle, Splunk's saved-search keys, the ThousandEyes
  views, and the PromQL shapes went from explanation to one table or line each, on a tools-off probe
  showing both models carry them; the file-provisioning spellings, the webhook allowlist default,
  the Moogsoft release, the Mimir 3.2.0 defaults, and every team inventory table stayed, and the
  router states the bar for asserting cause once instead of once per vendor reference. Measured by
  promtool on a new observability-engineer burn-rate probe: every produced rules file from either
  bundle, on either model, is a correct three-pair AND set; see
  [the obs-alerting trim evidence](docs/reviews/2026-09-04-obs-alerting-trim-evidence.md).
- The observability-engineer burn-rate probe grades the rules file by what it does: the pinned
  promtool 3.14 evaluates it over synthetic series in eleven probe-owned cases (11/11 on a
  hand-written three-pair file, red on each of seven files built to dodge one case). Its first
  version demanded a pending period the skill never requires and gave the spike case too little
  history; the trials found both, and the review round found four more ways a wrong file could
  pass, all fixed and re-proven the same way.
- `ci-actions`: 22,271 B to 19,307 B, the entrypoint 8,779 B to 7,710 B, under the screen. The
  rationale under the pin, injection, fork, and cancellation rules, the tj-actions story, the
  injection example, the `pull_request_target` explanation, the matrix and concurrency examples,
  and the reusable-versus-composite prose went, on a tools-off probe showing both models carry
  them; the 2026 fork-checkout refusal, the setup-uv v10 cache rule, the immutable-release field,
  the CredHub fact, the Node 24 boundary, and every team convention stayed. Measured on a new
  software-engineer PCF deploy-job probe: on the oracle the trials ran, the candidate 23/23 in
  every trial on Sonnet and Opus and the incumbent in three of four; on the review round's oracle,
  five of eight produced jobs are complete, the misses being a workflow-level cancelling group left
  in place (two candidate files) and no rollback command (one incumbent file), so the contract and
  the PCF skeleton now say that a workflow-level group cancels the deploy too; see
  [the ci-actions trim evidence](docs/reviews/2026-09-04-ci-actions-trim-evidence.md).
- The software-engineer deploy-job probe grades the authored workflow by what it is: the pinned
  actionlint 1.7.12 accepts it, and a probe-owned oracle checks the deploy job's shape against
  fifteen sentences of the skill's contract (15/15 on a hand-written job, 4/15 on a naive one, red
  on each of thirty-seven files built to dodge one finding, green on five positive controls). Its
  one review round found eleven ways a wrong workflow could pass the first version, all closed.
- The eval runner no longer voids a routing verdict for a runtime refusal inside the subagent the
  main session dispatched: the verdict is the dispatch, which had already happened. The rule lives
  in `runtime_blocked_tools`, a regrade re-derives it from the raw trace, and the evals ceiling
  rises 8,600 to 8,700 lines for the fix and its four tests.
- Rewrote the `sre-assistant` agent body (renamed from `sre`) around a single dispatched, bounded,
  read-only evidence slice: its description now describes a dispatched bounded read and excludes
  the responder's own triage phrasing, which the `incident-investigation` advisor owns. Body cut
  from 20.0 KB to about 14 KB with sustained response, the tiers table, the closeout boundary, and
  the on-demand skill list removed. The always-loaded descriptions of five agents and six skills
  now send an active incident to `incident-investigation` and name `sre-assistant` only for a
  dispatched read.
- Added the self-sustaining-mechanism pattern and the two-incidents-are-not-one-cause rule to the
  `incident-investigation` advisor: a check for whether load on the dependency fell when the
  trigger was removed, and a caution against merging two differentials without a mechanism
  connecting them. Frontmatter, including `description:`, is unchanged.
- Rewrote `incident-command`'s Close and return section so no state is held by the assistant:
  resolution is confirmed by the human owner against the recovery criterion the
  `incident-investigation` advisor set with the mitigation, and after resolution the incident
  commander sends the resolution update with the authoritative timeline going to closeout with
  `scribe` as the next owner.
- `eng-ladder`'s description now points active-alert troubleshooting at `incident-investigation`
  instead of the retired `investigation-depth`.
- Closed `ROUTE-005`: its incumbent (`investigation-depth`) is deleted and the human-facing
  `incident-investigation` advisor now owns on-call phrasing, so the decision is made without
  restating the exact candidate.
- The credential rule is now enforced for every roster lane, not stated in prose. The plugin's
  PreToolUse guard denies `cf env`/`cf e`, `cf service-key`/`cf sk`, a `cf curl` on an env or
  credential endpoint, a `CF_TRACE` set to anything but off, `gcloud auth print-access-token`/
  `print-identity-token`, `gcloud secrets versions access`, and `gcloud kms decrypt` — in the three
  unguarded-Bash lanes as well as the guarded one, and never for the main loop, which is the
  human's own terminal. It is a denylist and therefore a tripwire, not a boundary: it matches by
  adjacency over lexed tokens (so `xargs cf env` and `$(cf env app)` are caught while a quoted
  `rg "cf env"` is data), and a line that will not lex is not a denial, because denying every
  heredoc in the build lanes would buy nothing. `observability-engineer`'s "no hook enforces any
  of this here" is retired. Review of the first cut found three real defects, each reproduced
  before its fix: a PATH- or `./`-qualified binary missed the match, a backslash continuation
  split the command across two lines that each matched nothing, and any argument merely
  shaped like `CF_TRACE=` was read as an assignment, so `rg CF_TRACE=true .` was denied.
  Proven by mutation: disabling the deny, the basename, or the continuation join each turns
  the regression subtests red.
- Removed `scripts/fleet_doctor.py` and its test (1,669 lines). Nothing invoked it — not Gate A,
  not CI, not any agent or skill — and the session preflight already proves the guard's
  interpreter, which was the one question it answered that mattered. Git history keeps it.
- Replaced embedded reference-read tokens with successful, snapshot-scoped `Read` evidence in the
  eval trace. Removed the now-inert token-only sections, comments, and synthetic token values from
  canonical skill references; operational canary procedures remain unchanged.
- Shortened twelve skill descriptions by expressing their existing neighboring-owner boundaries as
  terse exclusions. The routed capabilities and owners are unchanged.
- Trimmed `AGENTS.md` (8.4 KB → 5.1 KB) and `CONTRIBUTING.md` (4.0 KB → 2.9 KB) to the rules that
  shape work. Kept the Start-here map (19 rows → 11), the roster, the four enforcement facts,
  the evidence, trust, dashboard-exception, handoff, and learning conventions, and the eval-promotion
  hard rule and reviewer trusted-base exception. Dropped the Prompt/Context/Loop/Graph doctrine
  paragraph, the revision-presentation convention, the VS Code and DLP caveats (their owners keep
  them), and CONTRIBUTING's isolation, review-gate, and publication-workflow prose. The dependency
  and guard stdlib rules moved from Hard rules to CONTRIBUTING §2. `gate_a.py`'s failure text now
  points at CONTRIBUTING's verification table instead of a section it no longer has.
- `stack-profile` records that the team operates PCF through Apps Manager (many SREs have no `cf`
  CLI), the responder's incident tools in order (Apps Manager, Splunk, Wavefront and PCF App
  Metrics), and that Wavefront is the live PCF metrics UI today. `incident-command`'s references
  label an owner ratification `[sourced]` rather than `[verified]` and state that the commander's
  record merges `sre`'s timeline lines. `observability-engineer` cites `production-change-gate`'s
  tiers instead of restating them.
- Folded `agent-security` into `agent-authoring` as `references/agent-security.md` (one 6 KB
  reference replacing a 15 KB three-file skill). Kept the lethal trifecta, the leg-cutting order
  and Rule of Two, the cross-agent trust boundaries, the controls that hold (envelope and
  invisible-Unicode stripping, Claude Code layer facts, MCP as a dependency), and the
  five-question review. Dropped the fleet runtime-boundary restatement (`AGENTS.md` owns the
  roster), the researcher sanitization paragraph (`AGENTS.md` owns it), and the OWASP LLM Top 10
  crosswalk (git history keeps it). `agent-authoring`'s description gained the security-review
  capability and the 'is this agent safe / prompt injection' trigger in place of the 'Loop
  Engineering' phrasing its capability sentence already carried; `agent-engineer` now points at
  the reference. The three `agent-security` scenarios retired. The new trigger is covered by
  `discovery-agent-authoring-security-review` (Sonnet, 3/3, batch `20260902T055813Z-7dad56ec`,
  evidence packet retained in git history by batch ID; an earlier batch,
  `20260902T050121Z-e3774dc8`, kept the four then-existing `agent-authoring` discovery
  scenarios at 3/3 after the description change and failed the new one on a prompt that implied
  a file to read, which the clean room cannot grant). The reference's own contract is covered by
  `skill-direct-agent-authoring-security-review`, a direct scenario with scoped reference access
  and the new `security_review_structural` rubric (12 calibration cases, 12/12 on calibration run
  `20260902T062709Z`; Sonnet 3/3, batch `20260902T065206Z-3f16d3b6`,
  evidence packet retained in git history by batch ID).
- `evals/judge.py`'s evidence-grounding check now normalizes quote marks and markdown emphasis
  and checks an elided quote (`...`) fragment by fragment in order, every fragment still
  verbatim. Two live batches of the new security-review scenario went inconclusive on quotes
  that were the response's own words with `"` copied as `'`, `**bold**` copied plain, or a
  dropped middle; a paraphrase is still inconclusive.
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
  2026-08-26 three-pass audit measured (packet retained in git history) — the same rule
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

- Removed the `investigation-depth` mode-ladder skill: no human read it, and every rule it carried
  now lives in the `incident-investigation` advisor, the `sre-assistant` agent, or `pcf-ops`.
  Parked byte-exact under `archive/incident-autonomy` with its restore steps.
- Removed the `sre` agent's sustained-response machinery: it needed a trigger loop and signal read
  paths the repository does not have. The two scenarios
  (`agent-direct-sre-owns-recovery-to-terminal`, `agent-direct-sre-records-unknown-recovery-progress`),
  the three rubrics (`recovery_authority_held`,
  `unknown_progress_not_invented`, `progress_consistent_with_record`) and their 35 calibration
  cases, and `validate_fleet.py`'s conditional-handoff rule are all archived under
  `archive/incident-autonomy`. `no_blind_retry_after_unknown` stays live; the
  observability-engineer unknown-write scenario grades with it.
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
