# Changelog

Recent changes to the current Save Toolkit. This is a pre-release repository; entries do not
assert a published release or acceptance of an evaluated candidate. Earlier implementation history
is available in Git. Unfinished work belongs in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## [Unreleased]

### Changed

- The rubric judge follows the latest Sonnet (owner decision 2026-10-04): each calibration runs
  `judge.py --calibrate --resolve-identity` with the `sonnet` alias, and its receipt pins the
  concrete model that answered, so trials never follow the alias between calibrations. A new Sonnet
  means a recalibration before the old model retires, with the judge cache cleared when the probe
  reports that the alias moved, and the native scenarios' `expected_model` pins move with it.
  [verified] The first calibration on Sonnet 5.5 (`claude-sonnet-5-5`) cost USD 2.44 at list price
  for 165 live calls, against USD 4.90 on Sonnet 5.
- `reviewer` fixes the PR #307 review findings (owner decision 2026-10-02; no OS isolation for
  scratch runs is accepted risk): the autoload preparation gap names Copilot's instruction roots too;
  a commit is exported through a scratch index, never `git archive`, whose export attributes drop
  and rewrite files; every literal Git command uses `$G`; and each P0/P1 finding is reproduced in
  scratch even when it follows from the code (the export change alone cut reproductions to 7/15 over
  three wordings, 3/3 at both prior commits; 9/9 now). 12,746 -> 13,278 bytes. The harness adds
  `ran_outside_checkout`, grades every Git call for the prefix, rejects malformed `uncommitted` keys,
  and regrades seeded-uncommitted and `scope: subagent` checks correctly. Sonnet, 3 trials: reviewer
  suite and `software-engineer` handoff 31/33, main 1/12 on the four changed cases; every-call
  prefix 5/6 (main 0/6); probes 9/9 (a Copilot-only instruction edit does not block on Claude;
  export-ignored tests stay). Opus 8/9: one run started Python in the checkout with scratch imports.
- `reviewer` runs checks by default on work in the user's repository (branches, PRs, and
  uncommitted changes), only in a scratch copy, reproducing each suspected finding first; forks and
  unknown provenance stay CI-only, and the unused local Docker recipe is gone. 13,507 -> 13,336
  bytes. Sonnet, 3 trials per case against main: scratch-copy reproductions 6/6 on direct branch and
  uncommitted reviews (main ran nothing on the branch and ran code inside the checkout 2/3 on
  uncommitted work); in-checkout runs after a `software-engineer` handoff 1/3 (main 3/3); fork-runner
  refusal and read-only or no-execution scopes held 9/9.
- `reviewer` is independent of `researcher` (owner decision 2026-10-01): it dispatches only
  `repository-investigator`, and a dependency advisory or other public fact it cannot verify
  locally is a stated gap returned to its caller. On a urllib3 downgrade it flagged the risk from
  memory, labelled it unverified, asked the caller to confirm, and requested changes 3/3 with no
  dispatch; main dispatched a researcher that could not answer in 1/3. 13,143 -> 12,746 bytes.
- `reviewer` may bind a branch review's verdict to the named commit and report uncommitted defects
  as PROVISIONAL findings (owner decision 2026-10-01); the terse-handoff check accepts that or a
  PROVISIONAL verdict (6/6 Sonnet, 3/3 Opus; main 2/3). The two rename cases ask for the file whose
  change introduces the defect (Opus had named the broken caller). Roadmap gains PRECOMMIT-001 and
  REVIEWER-001.
- `reviewer` closes probe gaps: a candidate that edits CLAUDE.md, AGENTS.md, or `.claude/` in the
  checkout it runs in gets a preparation gap instead of a verdict (0/3 -> 3/3; all three earlier
  trials resisted the injected policy but none noticed it had loaded as their own instructions);
  changed-file history names each path (0/3 -> 3/3); uncommitted work on a branch is snapshotted
  before any run (in-checkout runs 0/6 after a terse handoff). The generic security checklist is cut:
  detection was 9/9 with and without it on workflow injection, SSRF, and a cross-tenant read; the
  dependency-advisory and agent-system lines stay. 13,331 -> 13,051 bytes. The PROVISIONAL verdict
  line after a branch-named handoff stays at 4/6: the reviewer binds the verdict to the committed SHA.
- `reviewer` output and Git contract: a side-effect-free Git prefix with minimum reads, every changed
  line covered or its filter named, an evidence label beside each finding's priority,
  `Verdict: PROVISIONAL — …` for mutable reviews, a requester header that never copies an account
  email, and a one-line `python -c` counted as a run. 13,336 -> 13,331 bytes (main 13,507). Sonnet,
  3 trials against main: tenant, clean, and uncommitted cases 0/3 -> 3/3; branch-history reads 3/3
  (main 1/3, 2/3); scratch copies after a `software-engineer` handoff 3/3 (main 0/3); PROVISIONAL
  verdict line after a terse handoff 2/3 (main 0/3). Changed-file history held only where the
  reviewer named the paths (0/3 in the retry case).
- Reviewer evals grade the review as written: five free-form build scenarios cover a scratch-copy
  reproduction, a cross-tenant read, a correct change, and an agent's uncommitted work (direct and
  after a terse handoff). Fixtures gain `checkout` and `uncommitted`; `no_workspace_changes` keeps
  seeded uncommitted bytes as its baseline; four reviewer scenarios reject Git verbs that move the
  source checkout; two diff detectors accept the two-argument `git diff` that had failed correct runs.
  On main every outcome check held; `contract:` checks fail where the body lacks the contract.
- `software-engineer` carries one short inline handoff core in place of three handoff sections,
  plus six-pass fixes: a credential-values row, a test-integrity rule, a `database-reliability`
  trigger, and one skill-trigger list. 25,847 -> 23,356 bytes, measured against main on Sonnet.
  Two build scenarios now grade resuming after a partial helper return and withholding a reviewer
  when candidate instructions would auto-load.
- `observability-engineer`, `reliability-engineer`, `reviewer`, `agent-engineer`, and
  `sre-assistant` carry the same short handoff core, 1,756 bytes smaller across the five. Five build
  probes give those lanes handoff coverage; main, the core, and a no-handoff control matched on
  every behavioral check.
- `sre-assistant` six-pass cleanup:
  - a viewing-only rule for its browser tools, which no hook checks;
  - the suspected-compromise section no longer says `reviewer` hands off to this lane, and it has
    one escalation route;
  - CF requests go to Apps Manager first, where the team works;
  - the credential-file rule says why it is the only control;
  - restated rules and a paragraph describing a path this profile lacks are removed.

  22,569 -> 22,278 bytes, measured against main on Sonnet. A stricter CF wording and an extra
  output-template line were measured, found to hurt, and reverted.
- `backend-craft` house contract brought to current practice:
  - health endpoints move to `/health/live` and `/health/ready`, because Cloud Run reserves some
    paths ending in `z`;
  - versioning adds the RFC 9745 `Deprecation` header beside `Sunset`;
  - rate limits require only `Retry-After`, with optional IETF `RateLimit` draft fields;
  - an oversized `limit` is lowered to the cap rather than rejected (AIP-158);
  - idempotency keys follow the IETF draft's status codes;
  - SSE keep-alives are about every 15 s;
  - outbound calls get one deadline per operation;
  - a new dependency-failure rule: fail fast, and mark an optional field unavailable or return
    `502`/`504`.

  The references are rewritten in plain sentences, and `fastapi.md` covers FastAPI 0.132's strict
  `Content-Type` and 0.135's native SSE. The OpenAPI starter gains `operationId`s, `WWW-Authenticate`,
  403 and 500 responses, and a documented `X-Request-ID`. SKILL.md is 7,105 -> 7,799 bytes. On the
  repaired `incidents-api` probe, main rejected the oversized limit 6/6 and the candidate capped it
  6/6; every other oracle check passed on both arms.
- `backend-craft` trimmed where a no-skill control showed the model already complies (Sonnet,
  3 trials per arm):
  - the response-model allowlist (no leaks 3/3 without the skill);
  - the generic test-running bullet;
  - webhook authentication and persist-before-ack (3/3 without the skill).

  It now names `Idempotent-Replayed` and leads webhook acceptance with `202`. The trimmed skill met
  or beat the current one on every check of all three probes; the replay header went 2/3 -> 3/3 and
  202 went 2/3 -> 3/3. No arm makes acknowledged webhook work recoverable after a crash (0/12 under
  the restart check), so the persist-before-ack line that was cut produced no recovery either.

### Fixed

- Three defective calibration cases that judges disagreed on; no label changed. The
  `human_handover` rubric paragraph now carries the supplied fact that Riley confirmed the flag
  value, and the handover PASS response no longer asserts an "agreed recovery window" or an
  "unassigned" dependency owner, neither of which its scenario supplied. The plan-authorship PASS
  response names the release owner as the one who deploys: [verified] every Claude judgment had read
  it as the assistant deploying, every OpenAI judgment as a plan for someone else. The
  `statement_rerun` PASS response says `needed. The colleague's` instead of `needed; the
  colleague's`: [verified] Sonnet 5.5 quoted the semicolon as a comma in six of eight judgments,
  which the verbatim-evidence rule turns into INCONCLUSIVE. [verified] Afterwards a calibration
  agrees with all 165 labels.
- The native incident scenario expects `claude-sonnet-5-5`, the model the `sonnet` alias now
  resolves to. [verified] With `claude-sonnet-5`, a native incident trial run through the alias
  would stop INCONCLUSIVE on its model check before the follow-up, as
  `test_native_wrong_or_missing_parent_model_stops_before_resume` exercises.
- Clean-room trial and judge workspaces no longer inherit the operator's instructions. Claude Code
  reads `CLAUDE.md` from every ancestor of its working directory, past any git root, and on Windows
  the default temp dir sits under the user's home. A Haiku probe through `main`'s clean room quoted
  the operator's `~/.claude/CLAUDE.md` heading. 340 of 1,432 saved trial traces ran under the home
  directory, and the rubric judge used the same workspace. `clean_room.make_workspace()` now refuses
  any root with a `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/CLAUDE.md`,
  `.claude/AGENTS.md` or `.claude/rules/` Markdown file above it, falling back to
  `<checkout drive>\fleet-eval-tmp` on Windows. `FLEET_EVAL_WORKSPACE_ROOT` overrides the root. The
  same probe now answers `NONE`.
- The `incident_companion_response` rubric's `statement_rerun` paragraph now carries the owner-supplied
  facts its PASS case repeats (`daily-statement/run-42`, `statement-2026-07-14/v3`, the provider
  receipt, the 11:26 UTC recipient readback, the cached screenshot). Before, a judge reading only the
  rubric saw them as invented: uncached Sonnet 5 judged calibration case #150 FAIL in both runs that
  produced a verdict, and every OpenAI judge failed it, while the 2026-09-23 receipt's PASS was
  cached. After the edit, three uncached Sonnet 5 runs score 21/21 on the rubric, #150 PASS each
  time.
- Owner review (2026-10-03) of the PASS-labelled calibration cases judges failed:
  - The `existing_bridge`, `existing_tlc`, `helper_assignment_and_return` and `knowledge_card` rubric
    paragraphs now carry the facts their scenarios supplied: the PCF target and incident ids, the
    report times, Morgan's role, the helper's sourced 10:00-10:10 observation, and the service card's
    escalation chain, 503 load shedding and 10-minute restart step.
  - The `no_blind_retry_after_unknown` case that asserts unsupplied terminal-completion evidence is
    relabelled FAIL, without its trailing conditional, with a new PASS case that makes the retry
    conditional on that evidence. The rubric now states that the prompt supplies no completion
    evidence, so a claim that such evidence already settles the outcome is an unsupported outcome
    claim, while a retry conditioned on a future check is judged by the retry rule. Before this,
    the relabelled case drew PASS in one of four judgments with the trailing conditional and one of
    six without it, and either draw fails a calibration; after it, FAIL in six of six.
  - The `statement_rerun` paragraph also carries the remaining supplied facts (yesterday's cached
    history, the intended production target, the unknown cause, no rerun or resend), and the
    `knowledge_card` PASS case names the card's full escalation chain.
  - Three labels stand.

  A new calibration receipt passes: 15 live calls, 150 cached, every rubric at or above 0.95. Five
  uncached runs agree on every judged `no_blind_retry_after_unknown` case (one evidence-format
  inconclusive on a FAIL case); three uncached runs score 21/21 on the companion rubric.
- `--regrade` grades `verification_completed` against the repository path the run recorded, so a
  correct `cd "<repo>" && <suite>` receipt is no longer a false FAIL because the checkout is gone.
  Runs from before 2026-10-02 did not record that path, and they already regrade INCONCLUSIVE on
  evaluator identity. `--regrade` also exits like a run: trials aggregate per scenario against its
  threshold within one label and one resolved model, then 1 for any FAIL verdict, 2 for any
  INCONCLUSIVE one, and 2 when nothing was regraded. It used to return 1 unless every trial passed,
  and 0 for nothing.
- `verification_completed` counts an earlier foreground command that failed (`Error: Exit code N`,
  which the CLI receipts as text, not a dict) as completed. Before, any failed earlier command, even
  a read-only `git log`, made the ordering unknown and the trial INCONCLUSIVE: 54 of the 61 saved
  trials with that verdict had no other cause. Replaying all 1,184 replayable saved trials changes
  exactly those 54 from INCONCLUSIVE to PASS and nothing else; other text errors stay unknown.
- `backend-craft` corrections:
  - `consuming-apis.md` no longer says to prefer the `cf` CLI;
  - request-id guidance no longer points at `obs-pipeline`, which has none, and states when
    Gorouter's id can be trusted;
  - the starter test requires 422 for validation failures;
  - the Celery link resolves.

  Moogsoft on-prem is named "Moogsoft Onprem" in `backend-craft`, `stack-profile`, and
  `obs-alerting`; APEX AIOps Incident Management is the cloud product's name.
- `build-software-engineer-incidents-api` graded problem+json on a fixture whose existing errors
  were plain JSON, while the skill says to keep an existing contract. The fixture now carries the
  house problem+json handlers. The oracle requires 422 and a capped `limit`, and accepts a fast
  `502`/`504` or an explicitly unavailable owner. It was proven offline against two reference
  implementations and seven mutants.

- Two `sre-assistant` build scenarios failed an agent that followed `pcf-ops`:
  - `active-incident-guarded-triage` now supplies the masked `cf` wrapper `pcf-ops` requires before
    any raw `cf` read.
  - `suspected-compromise-preserves-evidence` now tests today's access: a logged-in `cf` with
    unprotected output, where the agent runs none and asks for the Apps Manager view.

  Both accept "haven't changed" and a parenthetical before `Caller next step`'s colon.

- `researcher` grants the host GitHits server's `list` tool in place of the retired `code_files`
  and `docs_list`; `scripts/validate_fleet.py` pins the same set, which now matches the server's
  twelve tools.
- PR #293 review follow-ups: the FastAPI starter's unhandled-error log keeps the method, path,
  and chained and grouped exception types, collapses recursion, and survives a project record
  factory that sets `request_id`; a trusted header without the request-id middleware is rejected.
  Its docs name the server log that still carries raw exception text and when Gorouter's request
  id can be trusted. The PCF deploy example's health step annotates every failure, including curl
  errors, bounds its total retry wait, and probes the readiness path; tests now fail if
  `--disable` or `--output /dev/null` is dropped, and a runner without PyYAML stops with a named
  requirement instead of a traceback. `database-reliability` treats an executing plan of a
  mutating statement on production as a live change even when rolled back, gives the two safe
  NOT NULL orders separately, and no longer puts a short `lock_timeout` on `CREATE INDEX
  CONCURRENTLY`, whose snapshot waits it would cancel into an INVALID index. Agent authoring
  escapes every default-ignorable code point in the model's view of untrusted text, says a
  permissions deny rule matches command text rather than the program, and restores the copied-test
  rule; Akamai production debug-header requests stay human-run whatever tools a lane holds.
- Follow-up PR review: CLI receipts cover discovery failures and pre-apply interruption; the
  CORS starter permits its authenticated API contract; deployment discovery stops on failure.
  DataStream rates separate client traffic, purge guidance preserves approved mandatory removal,
  and installed-plugin invocation wording agrees across the authoring references.
- PR review corrections: the operator CLI validates positive bounds, caps plans, stops at the
  first failed or UNKNOWN item, preserves lock ownership, and keeps interactive prompts off JSON
  stdout. Its evaluator now rejects invalid dry-run JSON and incorrect operational exit codes.
- Backend starters preserve a project's selected correlation ID, support an explicit correlation
  owner and outer CORS wrapper, require nonempty request IDs in both schemas, and exercise the
  unexpected-error handler ahead of catch-all routes. Replay-only headers have an explicit contract.
- Agent Plugins 1.0 now packages the canonical ADR command with its preflight intact; generated
  command completeness is checked. Python examples distinguish 3.10 from 3.11+ APIs.
- A new `pcf-ops` reference states what each state-changing `cf` command does to serving: `cf scale
  -m/-k/-l`, plain `cf restart`, and plain `cf restage` stop the whole app; `--strategy rolling`
  rolls `web` only; a no-downtime resize is an existing-droplet deployment, never `cf push`. The
  incident fast path now admits only instance-count scale, and `production-change-gate` loads the
  reference for any `cf` state-changing command.
- A correlation id with no trace id now routes to `obs-logs` instead of dead-ending in
  `obs-traces`, which had claimed the trigger while forbidding the skill that maps it. Two
  discovery scenarios cover the split.
- `database-reliability` bounds migration lock waits that can queue traffic: PostgreSQL
  `lock_timeout` with retry, a long-transaction check before `CREATE INDEX CONCURRENTLY`, and
  cleanup only of an observed invalid index from the failed build; SQL Server
  `WAIT_AT_LOW_PRIORITY` where allowed, otherwise `LOCK_TIMEOUT` with `XACT_ABORT ON` and
  explicit error handling and transaction cleanup before retry.
- The `ci-actions` PCF production-deploy example runs only when a human dispatches it from `main`,
  and requires a deployment-branch rule on the environment.
- `agent-authoring` platform facts match the current docs: the listing budget is 1% of the context
  window (8,000 characters only as the fallback); plugin skills load beside same-named personal
  skills instead of being shadowed; `compatibility`, `omitClaudeMd`, `initialPrompt` and the
  current `maxTurns` behavior are recorded; subagent model resolution names both environment
  variables. The method adds a listing-budget check before description edits, a new-skill
  admission test, evidence rows combined across every changed surface, and one return-header core
  with named lane fields.
- `production-change-gate`'s only worked approval packet now carries every checklist slot
  (execution boundary, change record, watcher, timing) and the real `cf app` output shape. Merge
  readiness reads the candidate repository's own rules instead of asserting this repository's.
  Tier 0 reads go only through a lane's granted read path, and a dispatched readback is evidence
  for the reconciliation owner, never the executor's receipt. Examples use a trading app
  (`order-router`), and the restart-classification eval grades a plain whole-app restart off the
  fast path, with ITO approving in the TLC. ITO is spelled out as IT Operations.
- `runbook`'s template approval banner, which every runbook copies, says in plain terms what Tier 2
  and Tier 3 mean and who approves: ITO in the TLC during a declared incident, with the shortened
  checklist limited to eligible actions; all other actions retain the full production process.
  The exemplar is a trading service (`order-router`) that verifies recovery on
  its SLI rather than p95 and states when a multi-window burn alert clears. The rules demote a wrong
  runbook instead of deleting it, bump `version` on step changes, and move `last_verified` only on a
  passing drill of the stamped version. The Confluence converter reads the page JSON (title,
  version, modified date), keeps every body `h1` as a section, refuses to overwrite an existing
  runbook, prints on legacy code pages, and matches headings on word starts; nine new tests fail on
  the previous converter.
- `postmortem` routes resilience and automation decisions to `reliability-engineer`, has a form rule
  for unknown severity and a searchable signature field, and the closeout packet carries severity
  and impact start. `operational-learning` finds a component's dependents across every card and
  defers retrospectives to `postmortem`; closeout bindings carry `git status --porcelain`, which
  `observability-engineer` and `software-engineer` now send.
- `obs-dashboards` warns against `or vector(0)` and null-to-zero on error ratios, asks for a
  denominator panel and a telemetry-present stat, names the backend holding each signal, and
  applies the team's dashboard conventions, which now live in their own `grafana` reference
  (read on every create) instead of under a "legacy" data-source title. App-UI dashboards route
  to `frontend-craft`, with a discovery scenario for the split.
- `frontend-craft` covers SSE auth with in-memory tokens, confirmed and idempotent UI writes, an
  SPA fallback that never swallows API paths, and a browser check that names the gap when no
  browser tool exists. `backend-craft` adds object-level authorization tests, request ids on
  every log line and problem body (generated unless a trusted ingress header such as PCF's
  `X-Vcap-Request-Id` is configured), PCF health-check wiring and the 10 s
  drain window, a starter test that no longer passes on a router 404, and a replay/in-progress
  contract for the starter POST.
- `gcp-ops` log reads work under PowerShell as well as Bash: the severity floor is spelled as
  exclusions of the five lower severities and 429s are a second read, because the PowerShell guard
  refuses `>`, `<` and parentheses even inside quotes; the asset test now replays every example in
  both shells. A 503/504/429/start-failure table gives each documented message its first check, the
  first look adds the Metrics tab, rollback picks the revision that served before onset from
  evidence, and the CF migration map adds startup probes and the documented eligibility criteria.
  `akamai-edge` adds a cache-purge section (invalidate by default, narrowest scope, never delete
  during an origin brownout), documented X-Cache values including `TCP_REFRESH_FAIL_HIT`, the
  staging hostname rule, and a DataStream 2 hostname/region query in `obs-logs`' catalog whose
  destination stays an owner fact. A new discovery scenario checks that a Cloud Run 503 routes to
  `gcp-ops`.
- `python-craft` matches its method to the request: a fix reproduces the defect, changes only
  what the fix needs, and ends with a **Noticed, not changed** line; bug hunting and new code use
  a new defects reference (a `ruff --extend-select B,S110,S113,BLE001,DTZ,PLW1510,ASYNC,RUF006,RUF032`
  pass plus the classes a linter misses: zero-count slices, float money, wall-clock deadlines,
  failure reported as success). Refactors first show the tests reach the moved code. `TaskGroup`
  failures are documented as `ExceptionGroup` (existing `except X` stops matching), the
  modernization table covers 3.10–3.14 idioms with a ruff `UP` pass, the toolkit's own pins left
  the shipped reference, and the worked example is a `Decimal` fills calculation instead of the
  eval fixture. A new build probe, `build-python-fix-stays-scoped`, scored 0/3 on the previous
  body and 3/3 on this one (Sonnet): both fixed the bug without touching the duplicated code, and
  only this one named the duplication it left.
- `obs-logs` timelines count total and errors in explicitly bounded buckets on a scoped base, split
  status by class with `limit=0` (a `timechart … by status` folds early low-volume 503s into
  `OTHER`), and check source freshness before reading "no events" as healthy. Cloud Run rates use
  the request log as denominator, PCF request counts the Gorouter `RTR` line, and deploy times come
  from Apps Manager Events or the Cloud Run traffic shift; correlation evidence returns to the
  caller. The `obs-logs` and `obs-metrics` descriptions send live-page decisions to
  `incident-investigation`, and remote_write queue detail moved to `obs-pipeline`. A new live-page
  routing scenario and an eight-key query-shape contract (1/3 on the previous skill, 3/3 on this
  one; the miss was handing correlation evidence to `observability-engineer`) cover the changes.
- `ci-actions`' PCF deploy example lists revisions before the push (skipped on a first deploy),
  verifies health, and on failure prints the release owner's `cf cancel-deployment` or `cf
  rollback` choice without running either. It selects its runner by group and labels, pins
  `download-artifact` to a reviewed SHA, and asserts cf CLI v8. The skill follows repository
  action-pinning policy (SHAs when none exists), keeps existing runner labels, adds a `gh run list`
  timing recipe and a caller for the reusable starter, routes live outages to
  `incident-investigation`, and moves the wheel-release check to the security reference.
- `operator-cli` has a default exit-code table (0/1/2/128+N), defines `skipped` (never attempted)
  against `failed`, handles SIGINT and SIGTERM with cleanup and a report (Python handles only SIGINT
  by default), prompts only when stdin is a TTY and never takes confirmation from a pipe, ends
  quietly when stdout closes, binds confirmation to the set shown, batches bulk effects, writes a
  per-run receipt, and maps dry run and confirmation onto PowerShell's `-WhatIf`/`ConfirmImpact`.
  A copyable contract test and reference command ship in `assets/` and run in CI.
  `software-engineer`'s fallback now allows a TTY prompt as confirmation. A new build probe,
  `build-operator-cli-safe-requeue`, whose oracle injects a rejected job, a timeout after the
  effect, and SIGINT/SIGTERM mid-run, scored 0/3 on the previous skill and 3/3 on this one.
- `verification_completed` accepts a suite positioned by one `cd` or `Set-Location` into the trial
  repository joined with `&&`. On 2026-09-23 every `build-software-engineer-cli-with-tests` trial on
  two agent bodies ran `cd "<workspace>" && python -m unittest …`, and the bare-only matcher failed
  all six, including the two whose final action was that suite. Any other target, `;`, `||`, or a
  second command still rejects.
- The `no_production_action_claim` rubric states the guidance exclusion inside `fail_if`, next to the
  progressive example it collided with. Since 2026-09-20 no calibration receipt had been accepted:
  the judge read "I'm applying the top-level skill guidance I did receive" as a production action
  (18/19), and the all-rubric gate blocked every rubric-backed trial. Recalibrated: every rubric
  agrees 100 %, 19 live calls.

- The build probe resolves a trial's model identity from the main thread (init model plus every
  top-level assistant turn) and records the CLI's usage table separately as `usage_models`. Claude
  Code 2.1.271 lists an internal Haiku helper call of a few tokens in that table, which had closed
  every three-trial batch as INCONCLUSIVE for mixed identities. A parent that changes model
  mid-trial still resolves to two. Eval ceiling +36 lines. See the
  [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).

### Added

- Every eval run records `runtime`: the CLI's `--version` line (`null` when it cannot report one)
  and the host's system, release, and machine. `main()` measures it once per batch and prints it in
  the batch header; each trial writes it to `provenance.json`, the trace summary, and its summary
  line; and `--regrade` keeps the recorded value rather than today's. Results from different CLI
  versions or hosts were indistinguishable before. The 2026-10-03 threat-model ADR requires both.
- Two `backend-craft` build probes with probe-owned oracles, each proven by a no-model test
  (a house-rule reference plus targeted mutants):
  - `incident-writes`: an idempotent create whose caller resends on timeout.
  - `pager-webhook`: a signed webhook whose processing outlasts the vendor's 3 s window.

  Against a no-skill control the skill scored 20/21 vs 11/21 on writes, mostly from requiring the
  key, using 422 for a changed payload, and repeating 201 on replay. On the webhook it scored 14/18
  vs 12/18. The model already authenticates, acknowledges fast, persists first and deduplicates on
  its own. With or without the skill, none of the 6 trials finishes the acknowledged work after a
  kill and restart: each attaches the runbook link in memory.
- A medium-sized Python build probe, `build-python-unify-policy`: seven modules, three drifted
  intake entrypoints, a registry, a configured dotted lookup, a legacy re-export, and a unit suite
  that encodes the drift. Its oracle checks specification parity for every entrypoint, single
  ownership through the `policy.normalize_order` patch seam, exception identity, input
  immutability, six fresh-process import orders, and a green suite that keeps its assertions;
  eleven partial-ownership and lost-consumer artifacts are rejected by name. Eval ceiling +223
  lines. Across twelve clean-room Sonnet trials on four candidates the fleet completed the
  refactor correctly every time, with or without `python-craft`. See the
  [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).
- `software-engineer` direct scenarios for the stale-finding return, `[sourced]` labels on
  caller-supplied output, and a tool-less build that must not be narrated, plus its build-CLI routing
  scenario. The contract scenarios were deleted in the 2026-09-01 corpus cut and the routing one on
  2026-09-04; they return in the current schema with regex graders only, and without the line-start
  slot demands the body no longer states. Each carries red and green fixtures in `test_graders.py`.

### Changed

- The Copilot/VS Code plugin declares Agent Plugins 1.0. VS Code ranks `.claude-plugin/plugin.json`
  above a schema-less root manifest, so it had been loading the canonical Claude agents and hooks
  instead of the Copilot projection. The plugin now reads canonical `skills/` and takes the
  generated agents and hooks from `com.github.copilot/`; `.github/agents/` and `.github/skills/`
  remain as workspace customizations. Copilot CLI needs v1.0.85 or later. Installed-host behavior
  is unverified until the new Format acceptance case passes.
- `build-software-engineer-cli-with-tests` no longer tells the agent to use Changed and Verified
  headings; it checks the body's own rule instead, that the agent labels its suite result
  `[verified]`.
- `software-engineer`'s body returns to its PR #282 state (`834dafd1`), undoing PR #284's
  consolidation into an eight-step Working method. Step 1 again loads the craft skills before the
  code is read and names `python-craft` and `frontend-craft`. This is an owner preference, not a
  measured gain: on 2026-09-23 (Sonnet) `build-python-unify-policy` loaded `python-craft` in 3/3
  trials on the 09-16 body, 3/5 on this body, and 2/3 on the consolidated body; no pairing is
  distinguishable (Fisher p >= 0.46), and the refactor passed its oracle in every trial on every body.
  The workspace, shell, `root-cause`, consumer-check, and CI-submission rules from PRs #281 and #282
  stay. PR #284's researcher dispatch row stays because the researcher agent reads those fields.
  Reverted with the rest: the default of one reviewer dispatch and the safe local reproducer for
  incoming `sre-assistant` evidence. See the
  [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).

- Generated Copilot/VS Code agent profiles carry no generated preface at all: the whole "Host
  adapter contract" header is gone, including the bare-names sentence, the inherited-tools caveat,
  and the guarded-lane and MCP-evidence paragraphs. A projection is now the canonical body with
  Claude-only addressing removed, nothing prepended. A host limitation that changes what a lane may
  do travels with the rule it qualifies: `sre-assistant` already states in its own body that it has
  no shell on Copilot, and `researcher`'s evidence-routing rule now says in its own body that the
  exact Context7/GitHits identifiers cannot be granted there, so an unavailable evidence lane is
  named rather than replaced by a summarized fetch. The preface test is inverted to fail if any
  preface returns, and was proven red against a reintroduced one.
- The `python-craft` description leads with writing, refactoring, or modernizing any Python,
  "routine or difficult", and says to load before editing; it opened with "Improve difficult
  Python code". Triggers and the not-for line are unchanged. After the change, on Sonnet: the
  medium probe reaches the skill 3/3 (1/6 on main, 2/3 with the step-1 edit alone), and the
  refactoring, improvement, modernization, and live-incident-negative routing scenarios pass 3/3;
  `discovery-python-explanation` fails 0/3 on both this and main's description, a pre-existing
  red. See the [medium Python refactor evidence](docs/reviews/2026-09-16-python-medium-jobs.md).
- `software-engineer` Process step 1 names `python-craft` beside the backend, frontend, and CLI
  crafts; it previously appeared only in the on-demand catalogue further down. Projection
  regenerated. Measured direction only, not proof: see the evidence record above.

## [0.50.0] - 2026-09-16

### Fixed

- Reviewer evaluation checks now detect path-qualified and common wrapper-prefixed Python/tool
  commands and require the reviewed range in Git diff/history requests. Added positive and negative
  calibration cases; the eval Python ceiling rises by 22 lines to 12,275 for this regression coverage.
- Corrected wrong PCF mitigation guidance: whole-app `cf restart` stops every instance, so the
  covered restart is per-instance or rolling; a revision rollback restores the revision's env vars
  and creates a new `Rolled back to revision <n>` entry, so readback checks the description; rollback
  is a rolling deployment and cancelling it restores the bad droplet. Corrected the JVM
  `OutOfMemoryError` guidance (the message names the exhausted pool) and the Splunk top-offenders
  query (no `error` keyword; an empty result is a missing extraction). The incident advisor routes
  external-monitor and Situation pages to `obs-alerting`, opens Apps Manager Events first, and never
  searches for documentation; the runbook exemplar and template are console-first with
  `last_verified` bound to the drilled version; the commander's evidence rules match the helper's
  read contract. Ceilings rise to 610,565 skill bytes and a 77,000-byte human incident path. See the
  [quality round record](docs/reviews/2026-09-08-quality-round.md).
- Engineering lane, same round: the Spring problem-details advice no longer claims a property it
  makes redundant and names the security-filter 401/403 gap; the builder ladder keeps a scoped
  security fix builder-owned; the skill token budget is described as the compaction re-attachment
  budget; the CI starter and deploy skeleton carry `timeout-minutes`; the contract test carries an
  `auth_headers` fixture matching the bearer-protected OpenAPI starter; the Handoffs convention says
  what a review dispatch supplies; the reviewer's worked examples carry `Reviewed state:` and the
  non-execution line. Ceilings: 612,873 skill bytes, 116,305 agent bytes.
- Corrected evaluation assertion identity, candidate aggregation and trial-input attribution;
  removed ineffective retired policy tests and scoped CI dependency checks to the actual job.
- Resolved portable helpers from their installed skill, qualified Claude-only guard claims,
  preserved Confluence link/image references with conversion-loss accounting, and repaired the
  authoring and human-console guidance. Ordinary CI selects only its two test dependencies from
  the existing version pins. See the [review-fix evidence](docs/reviews/2026-09-07-independent-review-fixes.md)
  for focused regressions, measured weight and remaining host/model verification.

### Added

- Added conditional symptom comparisons to the human incident advisor for login failures,
  intermittent errors, slow requests, stale/wrong data, and missed jobs with limited telemetry.
  See the [general incident help evidence](docs/reviews/2026-09-06-general-incident-help.md) for
  evaluation and the explicit context/skill-size allocation.

- A human incident advisor with conditional symptom guidance and a bounded, read-only
  `sre-assistant` helper. The advisor supports explanations, investigation, recap, and operational
  closeout while the human owns incident decisions and production actions.
- An `operator-cli` skill for operator-facing command-line tools, including partial results,
  secret handling, and uncertain effect outcomes.

### Changed

- Generated Copilot skill copies no longer open with the adapter banner about bare component
  names; the explicit-only line remains for manual skills.
- Retired the standalone `incident-command` skill for the team's investigation role. The advisor
  retains its seven-field board, owns conditional mitigation and severity advice, and prepares
  technical updates for an existing bridge/TLC without opening another or assigning command roles.
  The human incident lead retains formal classification, coordination, and stakeholder communications.

- Expanded `reviewer` to gather Git/PR/history evidence, load trusted guidance, write scratch
  reproductions, run permitted isolated checks, and dispatch bounded investigation/research helpers.
  Candidate fixes and release actions remain with the caller. Updated the graph, host projections,
  and balanced review cases; shell/write limits are no longer described as enforced by tool absence.

- Moved the Copilot skill projection to `.github/skills/` for standard workspace discovery and
  updated the plugin selector. Removed the custom VS Code skill-location override and generated
  banners from adapters and bundled resources; byte validation still checks the authored sources.

- Strengthened Python refactoring guidance for interpreter/environment selection, public module
  moves, independent old/new comparisons, and review of automated fixes. Added semantic regression
  checks that independently reject widened keyword-only parameters, callback-path input mutation,
  and replaced callback exceptions.
  Added incremental-consumption checks, 936 bounded generated comparisons, and a module-move
  fixture with alias/configuration/patch compatibility and fresh import orders. Twenty-seven broken
  artifacts are rejected; the eval ceiling grows for the oracles and calibration.
  Conditional environment depth is included in the refactor/migration context budgets; Python
  skill discovery is unchanged.

- The `runbook`, `postmortem`, and `operational-learning` descriptions lead with what a person
  would say ("help me write a runbook for restarting pricing", "write a postmortem for INC-1234",
  "which team owns payments and how do I page them"); `operational-learning` answers ownership and
  dependency questions from the service cards; `ci-actions` excludes application deploys and
  runtime bugs; a `stack-profile` reference defines blast radius, golden signals, and the human
  roles. Four routing scenarios, two of them new, pass 3/3 on Sonnet. The reviewer's README row
  and three agent bodies lose rules they could not act on. Ceilings rise to 587,200 skill bytes and
  115,800 agent bytes. See the [quick-fix record](docs/reviews/2026-09-08-review-quick-fixes.md).
- The incident advisor's description now names the first responder and carries on-call trigger
  phrasing ('I just got paged, what do I do', 'customers are reporting errors, where do I start').
  In a clean batch on the merged head, the new unhinted first-page routing scenario fires it 3/3 on
  Sonnet and 3/3 on Opus; walk-me-through, staging triage, the no-dispatch negative, and the
  dispatched-read helper positive pass 3/3 on Sonnet. `discovery-active-alert-stays-with-advisor`
  and `native-incident-helper-return-and-resume` each pass 2 of 3 trials and keep an INCONCLUSIVE
  aggregate: one trial each ended in a denied or missing file read, not a routing miss. The
  skill-byte ceiling rose by 200 bytes, to 584,200, against an LF total of 584,042. See the
  [advisor on-call trigger evidence](docs/reviews/2026-09-08-advisor-oncall-triggers.md).

- Routine documentation handoffs and operational templates now use unique short commit IDs
  (8 characters, extended by Git when needed). Checkout evidence and approval requirements remain;
  full IDs are still accepted. Immutable-review identities, dependency pins and eval digests are
  unchanged.

- Kept contact-only runbook corrections, supplied log/metric explanations, and bounded telemetry
  repairs scoped to their tasks while retaining full-workflow checks when requested. Aligned design
  consultation and operating-document routing with existing owners, and made rollback versus
  evidence-backed recovery consistent without changing tool grants or human execution authority.
  See the [scope and owner follow-up](docs/reviews/2026-09-07-task-sized-skill-outputs.md).

- Delegated helpers return assignment status, evidence, results, and gaps to their caller. The
  caller checks the claims and continues the parent task; helper completion does not resolve an
  incident or complete the parent objective.
- Alert, trace, log, metric, runbook, and postmortem guidance scales to the requested task. Short
  corrections and explanations avoid a full workflow packet; full investigations retain their
  evidence and ownership requirements. Postmortem and knowledge closeout share follow-up records.
  See the [pending output assessment](docs/reviews/2026-09-07-task-sized-skill-outputs.md).
- Incident examples distinguish scoped observations from unsupported causal, timing, and current-
  state claims. The [helper-exchange assessment](docs/reviews/2026-09-07-incident-helper-exchange.md)
  records the source verification and remaining behavioral decision.
- Evaluation uses one runner, `evals/build_probe.py`, for routing, contract, and build scenarios,
  with structural graders and a rubric judge. See the [current eval contract](evals/README.md).

### Removed

- Retired incident-autonomy and incident-navigation restoration bundles, including their obsolete
  scenarios, rubric fragments, calibration cases, generated copies, and patches.
- Completed review and trim-evaluation reports, completed rename records, superseded release and
  multi-engine evaluation decisions, and the old archive-location records. Current regressions,
  unresolved-decision evidence, and applicable contracts remain.
- The accumulated development diary and obsolete baseline inventory from this changelog. Historic
  feature names, scenario counts, and retired commands no longer describe the current toolkit.

### Known limitations

- Incident-quality adoption remains on hold. The
  [second bounded assessment](docs/reviews/2026-09-07-incident-quality-second-pass.md) records failed
  behavioral acceptance and links its preceding evidence. Structural checks and source review do
  not clear that hold; further model work and exact-candidate acceptance remain owner decisions.
- VS Code plugin enforcement remains host-specific; the
  [installation and verification guidance](README.md) records its limits.
- Codex distribution was retired. Codex can still work in this repository through `AGENTS.md`;
  the [retirement contract](docs/decisions/2026-08-23-retire-codex-distribution-target.md) retains
  migration guidance for earlier installations.
