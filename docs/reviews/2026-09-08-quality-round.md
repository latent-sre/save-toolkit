# Fleet quality round — analysis, fixes, and after-runs

Date: 2026-09-08 · Branch `work/quality-round-20260908` from `main` at `c960727d` · Claude Code
2.1.263, Windows host, `--plugin-dir F:/repos/sre-agents`.

Scope set by the owner: quality of skills and agents, not size. Sonnet and Opus run every test cell;
Fable plans, analyzes, and judges. This record covers the reading analysis, the iteration-1 baseline on
the unchanged fleet, two change sets (the four P1s with the six incident-lane P2s; the seven
engineering-lane P2s), and the owner-approved after-runs: iterations 2 and 3 on the incident lane,
iteration 2 on pcf-ops and obs-logs, and a first measurement of the engineering lane. The fifteen
platform and observability P2s are unaddressed; whether to run them is tracked as QUALITY-001 in the
roadmap, not decided here.

## Reading analysis

Four Fable analysts read every canonical skill and agent in full, one lane each, and checked
technical claims against primary documentation. Reports are private under
`.eval-runs/quality-20260908/analysis/` (observability, platform, incident-ops, engineering-agents).

| Lane | P1 (wrong guidance an SRE could act on) | P2 (degraded or contradictory) | P3 |
|---|---:|---:|---:|
| incident and ops-docs | 2 | 6 | 6 |
| platform | 1 | 7 | 14 |
| observability | 1 | 8 | 14 |
| engineering and agents | 0 | 7 | 15 |

Every batch-A finding was re-read at its cited source line before editing; none was stale. Several
engineering-lane line references were off (the files are shorter than cited) but the findings hold by
content.

## Iteration 1 — behaviour of the unchanged fleet

Method: one with-skill cell (`--plugin-dir` plus a Skill-tool pin, or `--agent save-toolkit:<name>`)
and one no-skill cell per prompt, on Sonnet and on Opus, in a clean room proven on this host the
same day (`--setting-sources ""`, workspace git roots under `F:\iso-tmp`, credential-only
`CLAUDE_CONFIG_DIR`; the positive control under the home directory quoted the global rules heading,
the candidate returned `NONE`). A tool-less Fable judge graded each cell against per-prompt
assertions and quoted its evidence. 22 prompts, 88 cells, 120 assertions, 0 failed cells; resolved
models `claude-sonnet-5` (43 cells), `claude-opus-5` (42), judge `claude-fable-5-1`.

| Target | Sonnet with / without | Opus with / without |
|---|---|---|
| incident-command (3 prompts) | 0.63 / 0.36 | 0.79 / 0.61 |
| incident-investigation (4) | 0.44 / 0.36 | 0.61 / 0.44 |
| runbook (2) | 0.92 / 0.58 | 0.92 / 0.67 |
| pcf-ops (3) | 0.55 / 0.64 | 0.75 / 0.62 |
| database-reliability (2) | 0.70 / 0.60 | 0.90 / 0.60 |
| obs-logs (3) | 0.73 / 0.60 | 0.93 / 0.60 |
| obs-alerting (3) | 0.53 / 0.47 | 0.67 / 0.67 |
| observability-engineer agent (2) | 0.90 / 0.73 | 0.82 / 0.73 |
| all 22 prompts | 0.64 / 0.52 | 0.78 / 0.60 |

`[verified]` from the traces, the defects that reached an answer:

- Rollback semantics (P1): with the skill, 0 of 2 runs stated that a revision carries env vars; the
  Sonnet run repeated the reference's "won't restore" wording; the no-skill Opus run had it right.
- Cancel during rollback (P2): one with-skill run said yes to `cancel-deployment` mid-rollback.
- Startup health-check timeout (platform P2, not in this change set): Sonnet with the skill 0.20
  against 0.60 without — the crash reference lacks the case and steered the model off it.
- Splunk scheduled-alert window (observability P2, not in this change set): with the skill 0 of 2
  runs lagged the window; without, 1 of 2 did.

Not reached: no with-skill run opened the pcf-ops crash reference, so the JVM sentence was fixed at
source only; no run copied the obs-logs `error` keyword, but the "empty result means missing
extraction" guidance landed in 0 of 4 runs.

Judge critique kept for iteration 2: the two database prompts never state the platform, so
assertions that require "Apps Manager" penalise correct answers, and no assertion checks SQL
correctness (a lock-mode error and a `pg_cancel_backend` recommendation against an idle-in-
transaction blocker passed ungraded).

Cost: about USD 17 for test cells, USD 36 for grading. Private cells, transcripts, grades, and the
two static review pages are under `.eval-runs/quality-20260908/`.

## Batch A change set

Edits were made by Sonnet and Opus implementers from exact specs; every new platform fact carries the
source given here; the reviewer re-fetched each source before accepting the diff.

| Finding | Change | Where |
|---|---|---|
| P1: whole-app `cf restart` offered as a reversible stopgap | Per-instance restart is the preferred form; whole-app restart stops every instance first (downtime unless `--strategy rolling`) and forecloses rule 2's held-back instance; the fast path covers per-instance or rolling restart only; the set-env row says what its restart costs | [`mitigation-selection.md`](../../skills/incident-command/references/mitigation-selection.md), [`incident-fast-path.md`](../../skills/production-change-gate/references/incident-fast-path.md) — cf CLI `restart` docs |
| P1: rollback semantics inverted | Rollback redeploys droplet, env vars and start command as a new revision described `Rolled back to revision <n>`, reverting variables changed since; bindings, routes, instance count untouched; pick a `deployable` row; readback checks the description, not the number | same file; advisor readback rule and example in [`incident-investigation/SKILL.md`](../../skills/incident-investigation/SKILL.md) — CF revisions docs |
| P1: JVM `OutOfMemoryError` is heap exhaustion | The message names the exhausted pool and picks the knob (heap, Metaspace/compressed class, native thread, direct buffer); raising heap or memory does not fix Metaspace or thread exhaustion | [`application-crashes-and-health-checks.md`](../../skills/pcf-ops/references/application-crashes-and-health-checks.md) — Oracle JDK 17 troubleshooting guide |
| P1: `error` keyword and "one empty group" in the top-offenders query | Base search scoped by index/sourcetype/time, `isnotnull(error_type)`, stable `by` fields; an empty result is a missing extraction, with the `count(error_type)` proof | [`spl.md`](../../skills/obs-logs/references/spl.md) |
| P2: rollback is a rolling deployment; cancel restores the bad droplet | One paragraph after the table; the abort row says a rollback in progress is an active deployment | `mitigation-selection.md` — cf CLI `rollback_command.go`, `cancel-deployment` docs |
| P2: no route to the ThousandEyes/Moogsoft procedures | Lane-table row to `obs-alerting`; symptom row "an external monitor or correlation Situation says we are down" | `incident-investigation/SKILL.md`, [`symptom-investigation.md`](../../skills/incident-investigation/references/symptom-investigation.md) |
| P2: commander evidence CLI-only; helper limited to three commands | Apps Manager views first with the CLI in parentheses; rule 3 names the guarded reads the helper's contract allows (instance state, events, logs, routes, revisions) | [`severity-and-declaration.md`](../../skills/incident-command/references/severity-and-declaration.md), `mitigation-selection.md` — `readonly-guard.py` `_CF_READ` |
| P2: runbook exemplar CLI-only, `last_verified` bound to another version | Console path first on every step with the cf equivalent after; `last_verified: null` with the reason in the teaching note; cf v8 output shapes; template step skeleton carries the console line | [`runbook-example.md`](../../skills/runbook/assets/runbook-example.md), [`runbook-template.md`](../../skills/runbook/assets/runbook-template.md) |
| P2: advisor hunts for a knowledge repository | Look once, say so once, record the gap, advise from supplied facts; never dispatch a locator; this toolkit's own repository is never incident data | `incident-investigation/SKILL.md` |
| P2: Events not named as the first read; example asks the owner for it | Apps Manager → app → Events → instance table → Splunk for a known PCF app; the worked exchange opens Events itself | `incident-investigation/SKILL.md`, `symptom-investigation.md` |

No description, frontmatter, tool grant, or delegation edge changed. Generated adapters regenerated.

### Ceilings

`[verified]` LF blob totals (`git ls-tree -r -l`): skills 604,117 → 610,565; agents unchanged at
115,983. `scripts/weights.json` `skills_bytes` rises to 610,565 in this diff. The
"PCF incident, human path" context budget rises from 73,000 to 77,000 bytes (measured
73,123). Size was explicitly out of scope for this round; these are the reviewed decisions the
gate asks for, not a claim of fit.

## Batch B change set — engineering lane

The seven engineering-lane P2s, reconfirmed by content (the analyst's line numbers were off) and,
for the two external claims, re-fetched: Spring Boot registers `ProblemDetailsExceptionHandler`
only `@ConditionalOnMissingBean(ResponseEntityExceptionHandler.class)`; the Claude Code skills page
describes 5,000/25,000 tokens as the post-compaction re-attachment budget and says an invoked body
"enters the conversation as a single message".

| Finding | Change | Where |
|---|---|---|
| `spring.mvc.problemdetails.enabled=true` presented as required beside a `ResponseEntityExceptionHandler` | The advice already maps the framework's exceptions; the property registers nothing extra; the real gap (Spring Security 401/403 and `/error` fallbacks) is named with the `AuthenticationEntryPoint`/`AccessDeniedHandler` fix | [`ProblemAdvice.java`](https://github.com/latent-sre/save-toolkit/blob/2f1380250c257bd55fe4bb321ca1a86aa0cb349f/skills/backend-craft/assets/ProblemAdvice.java), [`spring-boot.md`](https://github.com/latent-sre/save-toolkit/blob/2f1380250c257bd55fe4bb321ca1a86aa0cb349f/skills/backend-craft/references/spring-boot.md) |
| Security-sensitive surface listed as an escalation trigger | Moved into "How you work": independent security review, the fix stays builder-owned unless another trigger applies | [`builder.md`](../../skills/eng-ladder/references/builder.md) |
| 5,000/25,000 tokens presented as the invocation budget | Rewritten as the compaction re-attachment budget; an invoked body loads whole; no per-invocation truncation to design around | [`claude-code-frontmatter.md`](../../skills/agent-authoring/references/claude-code-frontmatter.md) |
| Starter CI job and deploy skeleton without `timeout-minutes` | `timeout-minutes` on both, matching the skill's own rule | [`ci.reusable.yml`](../../skills/ci-actions/assets/ci.reusable.yml), [`pcf-deploy-job.md`](../../skills/ci-actions/references/pcf-deploy-job.md) |
| OpenAPI starter requires bearer auth; contract test sends none and ships no fixture | An `auth_headers` fixture the project fills, passed on every protected request; the docstring says never to weaken auth to satisfy the starter | [`test_http_contract.py`](../../skills/backend-craft/assets/test_http_contract.py) |
| No fleet-level rule for preparing a reviewer dispatch | One sentence in the Handoffs convention: base and candidate identity plus an inspectable diff the reviewer can Read | [`AGENTS.md`](../../AGENTS.md) |
| Reviewer worked examples omit `Reviewed state:` and the non-execution line | Both examples carry every required slot | [`reviewer.md`](../../agents/reviewer.md) |

### Ceilings after batch B

`[verified]` LF blob totals: skills 612,873; agents 115,983 → 116,305. `scripts/weights.json` follows.

## Iteration 2 — incident-lane after-run on the changed bytes

Owner-approved after batch A. Same 9 prompts and 45 assertions for `incident-command`,
`incident-investigation`, and `runbook`; with-skill cells re-run at `31e2e89c` (clean tree) on
Sonnet and Opus, two runs per cell (36 cells, 0 failed); the no-skill baseline is the iteration-1
run, unchanged. Same Fable judge and assertion text, so the numbers compare directly. Cost about
USD 9 for cells and USD 16 for grading.

| Target | Sonnet old skill → new skill (no skill) | Opus old skill → new skill (no skill) |
|---|---|---|
| incident-command | 0.63 → 0.76 (0.36) | 0.79 → 0.92 (0.61) |
| incident-investigation | 0.44 → 0.67 (0.36) | 0.61 → 0.76 (0.44) |
| runbook | 0.92 → 1.00 (0.58) | 0.92 → 0.85 (0.67) |

`[verified]` per assertion, pooled over both models (old with-skill n=2, new n=4):

- Rollback restores env vars and start command: 0/2 → 4/4. New revision described `Rolled back to`,
  readback by description: 0/2 → 4/4. Cancel during a rollback answered no: 1/2 → 4/4. Rollback is a
  rolling deployment: 0/2 → 2/4; wait for completion before readback: 0/2 → 3/4.
- Apps Manager Events named first: 1/2 → 4/4; what each Events result means next: 0/2 → 3/4; one
  bounded attempt to find documentation: 1/2 → 3/4; declare and route edge evidence for an external
  monitor page: 0/2 → 2/4; no invented observations (both incident prompts): 1/2 → 4/4.
- Runbook steps console-first: 1/2 → 4/4; expected results in console terms: 1/2 → 4/4.

Still failing in every run, not targeted by batch A: a Splunk 5xx rate with a denominator on the
first page (0/4), a provisional severity with the fifteen-minute declare rule (0/4). Dips within
noise at these sample sizes (2/2 → 3/4) on restart blast-radius wording, runbook invented specifics,
and the minimal-change correction.

Two skill-induced patterns the judge's evidence exposes, left for the next edit: the answers adopt
decision rule 3's "watch 1–2 minutes" as the recovery criterion instead of a windowed, route-level
rate (recovery-criterion assertion 1/2 → 1/4), and one Sonnet run refused to name redeploying
revision 27 as the backout after reading the new cancel-deployment paragraph. One Opus run wrote
`<index>` instead of `3` because cf instance indices are zero-based and "instance #3" is
ambiguous; that caution is reasonable and the mitigation table could say so.

Review pages with iteration-1 outputs alongside: `.eval-runs/quality-20260908/review/iteration-2-{sonnet,opus}.html`.

## Iteration 3 — incident-command after the follow-up edits

Owner-approved. `75b67f4d` added three sentences to `mitigation-selection.md`: rule 3's attribution
pause is not the recovery criterion (the agreed user-outcome signal over the agreed window is); the
backout of a rollback is another rollback or a roll-forward through the full gate; the instance
index is zero-based, confirm the row. Same 3 prompts, 17 assertions, two with-skill runs per cell on
Sonnet and Opus (12 cells, 0 failed, about USD 3 cells and USD 5 grading); the iteration-1 no-skill
baseline is reused.

| incident-command | iteration 1 (old skill) | iteration 2 | iteration 3 | no skill |
|---|---|---|---|---|
| Sonnet | 0.63 | 0.76 | 0.83 | 0.36 |
| Opus | 0.79 | 0.92 | 0.98 | 0.61 |

`[verified]` per assertion, pooled over both models (iteration 2 → 3, n=4 each): recovery criterion as
a windowed route-level rate 1/4 → 4/4; Apps Manager Revisions path with the CLI fallback 2/4 → 4/4;
console-versus-CLI restart distinction 3/4 → 4/4; Priya as decider with a human executor 3/4 → 4/4;
rolling deployment stated 2/4 → 3/4. One dip, 4/4 → 2/4 on "new revision (28) described rolled back
to 26": both failing Sonnet runs said the rollback "redeploys revision 26's droplet as a new
revision" and to confirm the description reads `Rolled back to revision 26`, but never wrote the
number 28 — judge strictness on wording, the substance held.

Review pages with iteration-2 outputs alongside: `.eval-runs/quality-20260908/review/iteration-3-{sonnet,opus}.html`.

## After-runs on the remaining edits — pcf-ops, obs-logs, and the engineering lane

Owner-asked ("did we test the other items"). Same method as iteration 2 (with-skill cells at
`603236d3`, two runs per cell for the two skills with an iteration-1 baseline; both arms, one run
per cell, for the engineering lane, which had no baseline). 24 + 24 cells plus one rerun after a
copied OAuth token expired mid-run (a harness event, not a model result). Cost about
USD 12 for cells and USD 21 for grading.

| Target | Sonnet old → new (no skill) | Opus old → new (no skill) |
|---|---|---|
| pcf-ops | 0.55 → 0.62 (0.64) | 0.75 → 0.78 (0.62) |
| obs-logs | 0.73 → 0.87 (0.60) | 0.93 → 0.97 (0.60) |

| Engineering lane (iteration 1) | Sonnet with (no skill) | Opus with (no skill) |
|---|---|---|
| backend-craft: Spring problem-details 401 | 1.00 (0.80) | 1.00 (1.00) |
| backend-craft: FastAPI bearer starters | 1.00 (0.60) | 1.00 (0.60) |
| eng-ladder: IDOR fix, builder or escalate | 0.60 (0.40) | 0.80 (0.40) |
| agent-authoring: skill body token budget | 1.00 (0.40) | 1.00 (0.60) |
| ci-actions: reusable CI with uv | 1.00 (0.00) | 1.00 (0.50) |
| reviewer agent: working-tree diff review | 1.00 (0.17) | 1.00 (0.33) |

`[verified]` from the traces and grades:

- pcf-ops: every with-skill run on the JVM and crash-loop prompts read the rewritten crash reference
  (none did in iteration 1), and the JVM answers stayed correct (Metaspace ≠ heap 4/4). Sonnet's
  crash-loop score rose 0.20 → 0.50 with the startup health-check timeout identified 4/4; the two
  assertions that need the not-yet-written timeout case (rule out `$PORT`/memory/platform; tie to
  the droplet and name the console views) stay 0/4.
- obs-logs: "an empty result is a missing extraction" 0/2 → 4/4; both models 1.00 on the
  top-offenders prompt; zero-traffic guard 1/2 → 4/4; two dips within noise (2/2 → 2/4, 2/2 → 3/4).
- backend-craft: all four with-skill runs opened the changed files (spring-boot.md and
  ProblemAdvice.java; the OpenAPI starter and the contract test). The skill-specific assertions
  discriminate: 401 as problem+json 2/2 vs 0/2, the max-limit test 2/2 vs 0/2; the Spring "property
  is a no-op" fact 2/2 vs 1/2.
- reviewer: `Reviewed state:` and the non-execution line, the two slots the worked examples lacked,
  appear 2/2 with the agent versus 0/2 without; findings form and single next owner 2/2 vs 0/2.
- ci-actions: `timeout-minutes` on every job 2/2 vs 1/2; SHA pins and a pinned runner 2/2 vs 0/2.
- agent-authoring: compaction re-attachment budget explained 2/2 vs 0/2.
- eng-ladder: builder-owned with independent security review 2/2 vs 0/2; misses are the
  fail-before/pass-after test wording (0/2 both arms) and naming the escalation counterfactual (1/2).

Fleet-wide viewer totals (all 28 evals, both arms): iteration 1 Sonnet 70.5% vs 49.4%, Opus 81.9%
vs 59.6%; iteration 2 (incident lane, pcf-ops, obs-logs on the changed bytes) Sonnet 76.0% vs
49.3%, Opus 85.0% vs 57.2%. Pages: `.eval-runs/quality-20260908/review/iteration-{1,2,3}-{sonnet,opus}.html`.

## Review round: Codex on PR #245

Seven findings on `303d3d95` (three P1, four P2), each verified against the text it cites and fixed in
the same PR; CI was green on all four checks at that commit.

| Finding | Verified against | Fix |
|---|---|---|
| P1: the advisor's readback rule accepts a description or one converted instance while a rolling rollback is still in progress, so UNKNOWN can clear too early | `mitigation-selection.md`'s own paragraph: both revisions serve until completion | Readback shows the desired state only when the deployment has completed and every expected instance runs the intended droplet; mid-rollback, a description or one instance settles nothing |
| P1: per-instance restart "preferred" without a serving-headroom condition; a single-instance app or saturated survivors have none | the runbook exemplar blocks restart when headroom is unknown | Preference conditioned on headroom for the restarted share; unknown headroom blocks any restart; the fast path covers per-instance or rolling restart only with confirmed headroom, and a single-instance restart is a classified outage |
| P1: the record promised a "next batch" that the live roadmap did not carry | `docs/fleet-roadmap.md` is the only backlog | Roadmap item QUALITY-001 (`decision-needed`) holds the fifteen open P2s; the record points at it instead of promising |
| P2: "an empty offenders result is a missing extraction" overclaims when `error_type` is set only on error events | the query's own `isnotnull(error_type)` filter | Empty is ambiguous (no errors, or no extraction); prove extraction over a window known to contain errors or against an event known to carry the field |
| P2: the OOM knob mapping reads as universal | Oracle's list includes `Requested array size exceeds VM limit`; native-thread failures can be OS limits | Mapping scoped to the pool-exhaustion forms; array-size is a code defect, native-thread may be ulimit or cgroup pids; other reasons stay open |
| P2: the record's intro still said no after-run had happened | the iteration tables below it | Title and intro rewritten to the completed scope |
| P2: the runbook exemplar's 2026-02-11 history row was rewritten, against its own "never rewrite or delete" rule | `runbook/SKILL.md` history rules | Original row restored verbatim; a new newest-first row records the version-4 change and the cleared `last_verified` |

## Iteration 4 — after the Codex-round edits, with two controls

Owner-approved. With-skill cells at `288df23c` for incident-command (3 prompts), incident-investigation
(4), the pcf-ops JVM prompt, and the obs-logs top-offenders prompt; Sonnet and Opus, two runs per cell,
36 cells, 0 failed, about USD 8 for cells and USD 16 for grading. **Confound:** Claude Code
auto-updated from 2.1.263 to 2.1.265 between iteration 3 and iteration 4; every earlier number in this
record is on 2.1.263.

| Target | previous iteration → 4 (Sonnet) | previous → 4 (Opus) |
|---|---|---|
| incident-command (from iteration 3) | 0.83 → 0.78 | 0.98 → 0.91 |
| incident-investigation (from iteration 2) | 0.67 → 0.53 | 0.76 → 0.63 |
| pcf-ops JVM prompt (from iteration 2) | 0.86 → 0.79 | 0.93 → 0.86 |
| obs-logs top offenders (from iteration 2) | 1.00 → 1.00 | 1.00 → 1.00 |

Every fact assertion the round targeted stayed at 3/4 or 4/4; the incident-command dips were a missing
`[unverified]` tag on the Redeploy control and one Sonnet run omitting the CLI fallback for an
"Apps Manager only" user. The incident-investigation drop was broad (all four prompts), so two
controls were run before drawing a conclusion:

- **Judge drift:** the iteration-2 responses regraded by today's judge scored 0.74 / 0.67 against
  0.76 / 0.67 originally (three single-assertion flips in 46 verdicts). Not the judge.
- **Bytes versus environment:** the pre-Codex bytes (`8fb483e4`, which differ in this skill only by
  the readback sentence) re-run on CLI 2.1.265 scored Sonnet 0.54, Opus 0.69 — against 0.67 / 0.76 for
  the same bytes on 2.1.263, and 0.53 / 0.63 for the edited bytes on 2.1.265. Same bytes across the
  CLI change: −0.12 / −0.07. Old versus edited bytes on the same CLI: −0.02 / −0.06, with per-prompt
  moves in both directions (external monitor +0.17 Sonnet, −0.17 Opus).

`[verified]` conclusion: the Codex-round edits are not a measurable regression; the iteration-4
numbers sit on a different host baseline and must not be compared with iterations 1–3 directly.
What changed in CLI 2.1.265 that moves advisor scores by that much is `[unverified]`. From here, any
comparison needs both arms on the same CLI version, recorded in provenance (the runner already
records `claude_version`).

## The closing fields — owner decision and iteration 6

> **Naming.** This block was called "the state strip" while every measurement in this section was
> taken, and the prose below keeps that name because it is what the bytes under test carried. The
> skill renamed it to **"Where things stand"** on 2026-09-09, referring to the three fields as "the
> closing fields"; see [the rename](#the-rename--2026-09-09) at the end of this section.

The advisor carried a "board" on every reply until 2026-09-05, when
[PR #235](https://github.com/latent-sre/save-toolkit/pull/235) (`784211a7`) replaced it with an
on-request "conversation checkpoint", because a one-line explanation question was getting a full
report. The handover measurements in this round showed the cost of that trade: the rules the board's
lines used to carry survived only as prose and stopped landing — owner per open item with a read-back
0/4, no retry of an UNKNOWN restart 0/4, impact with a recovery criterion 1/4.

The owner's decision (2026-09-08, from simulation experience) was a middle position: a compact
three-line strip on every reply **once an incident is being worked**, none on a standalone question,
the full checkpoint still taking over at a transition or handover. `7592420b` adds it, plus a
handover example carrying the action states, per-item owners, recovery criterion and read-back
request. A later commit clarified the boundary (below).

Baseline before the change: 0 of 24 with-skill incident replies carried Applied/Open/Next labels.

**Does the strip appear where it should?** `[verified]` deterministic label check, three runs per
model per prompt at `7592420b`:

| Prompt | strip present |
|---|---|
| First page, new responder | 6/6 |
| External monitor Situation | 6/6 |
| What to look at first | 6/6 |
| Handover | Sonnet 3/3 strip; Opus 1/3 full checkpoint, 2/3 partial — pre-seam results, under the looser wording of that commit. `6fcb1210` makes a handover a checkpoint trigger, so a strip-only handover is a miss under the shipped contract, not an allowed outcome; re-measured below |
| Explanation asked mid-incident | 1/6 — **the boundary defect** |
| Standalone learning question (no live incident) | 0/6 — correct |

The mid-incident explanation exposed conflicting clauses in the new text: "once a live incident is
being worked, every reply ends with the strip" against "a standalone question — Explain mode, 'what
does this mean?' — gets no strip". Asked "what does 'waiting for a connection' mean here" while 500s
were live, five of six runs read the question's shape and dropped the strip. The rule now says the
test is whether an incident is being worked, not the shape of the question; only a postmortem
review, a learning question or a hypothetical gets none.

**The clarification was then verified deterministically** (`4f3aa7af`, three runs per model; the judge
was out of usage credits, so these are label counts, which is what the rule actually asserts):

| Prompt | pre-strip bytes | strip, before the fix | after the fix |
|---|---|---|---|
| Explanation asked mid-incident (ambiguous wording) | 0/6 | 1/6 | 4/6 |
| Explanation asked mid-incident (unambiguous: on the page, incident ID, errors climbing) | — | — | **6/6** |
| Standalone learning question | — | 0/6 | 0/6 |

The ambiguous prompt turned out to be a defective test rather than a defective rule: its symptoms were
past-tense with no page and no incident ID, and Sonnet's non-strip answers said so — "No live incident
is indicated here, so no state strip" and "is this an active incident right now?". Asking is the right
move on an ambiguous prompt. Rewritten so the incident is unambiguous, both models carry the strip on
every run, and the standalone question still carries none. The private prompt was corrected in the
workspace eval set; `scripts/check_strip.py` there performs this check without a judge.

**Quality on the four incident prompts**, both arms on CLI 2.1.265 (pre-strip bytes `84ca1192`
against strip bytes `7592420b`), three runs per cell:

| Prompt | Sonnet pre → strip | Opus pre → strip |
|---|---|---|
| First page | 0.43 → 0.50 | 0.43 → 0.54 |
| External monitor | 0.58 → 0.67 | 1.00 → 0.95 |
| What to look at first | 0.75 → 0.71 | 0.67 → 0.71 |
| Handover | 0.42 → 0.62 | 0.67 → 0.76 |
| mean | 0.54 → 0.64 | 0.69 → 0.73 |

The handover moved most, which is where the board's loss had been measured. Assertions that rose
(pooled, old n=4, new n=6): impact with an observation time and a recovery criterion 2/4 → 5/6; the
incoming responder inherits the investigation, not command authority 1/4 → 4/6; gaps plus the next
check with outcome meanings 3/4 → 6/6; no invented observations 3/4 → 5/6 on both incident prompts;
no retry of the UNKNOWN restart until reconciled 0/4 → 1/6. Assertions that fell: owner per open item
with a read-back 3/4 → 2/6; declare and route edge evidence 2/4 → 2/6; instance table plus a Splunk
check named next 1/4 → 0/6.

Cost: about USD 9 for cells and USD 14 for grading.

### The seam measurement — 2026-09-09

`6fcb1210` pointed the strip at the checkpoint's full trigger list, after a drill found that the strip
section named only "a transition or handover" while the checkpoint names four triggers. A candidate that
went further — lifting both out of "Recap or hand over" into a mode-independent section, then renaming
the strip — was measured against it and **rejected**.

Two arms, `with_skill` only, all six prompts, both models, three runs, CLI 2.1.265, both
`plugin_inputs_dirty=false`, 36/36 cells ok each. Handover, checkpoint-bearing replies:

| Arm | Sonnet | Opus | Total |
|---|---|---|---|
| `6fcb1210` (shipped) | 3/3 | 3/3 | **6/6** |
| `6b2fdafb` (placement + rename) | 0/3 | 2/3 | **2/6** |

Every other prompt was identical across arms: `first-page`, `external-monitor`, `what-to-look-first` and
`explain-mid-incident` all 3/3 strip on both models; the standalone learning question 3/3 none, so the
detector is not false-positiving. `explain-mid-incident` was already 3/3 at `4f3aa7af` (iteration 9), so
the placement change had no headroom to win and cost the handover instead — the adjacency of the
checkpoint to the recap section was load-bearing. The two candidate commits were not separated, so
placement versus rename is unattributed. Cost USD 16.30.

**The committed checker undercounts.** The workspace `check_strip.py` requires a colon within four
characters of a field label, so a checkpoint written as `### Follow-ups` or `### Next — the single most
useful check` scores as none. It reported the Opus candidate arm as 3/3 none when two of three replies
were substantively sound. The numbers above come from a format-tolerant detector applied identically to
both arms; a committed check must match on heading-style fields too.

### Judged quality on the merged bytes — 2026-09-09

The judge's usage credits returned, so iteration 13 — `aa65d458`, the head that merged as PR #246 —
was graded against the same assertions, by the same judge, on the same CLI (2.1.265) as iteration 6.
Three runs per cell, `plugin_inputs_dirty=false`. Judge cost USD 14.72 for 36 cells, plus USD 2.22
for the six iteration-9 cells that carry the boundary fix at `4f3aa7af`.

| Prompt | Sonnet | Opus |
|---|---|---|
| First page, new responder | 0.54 | 0.38 |
| External monitor Situation | 0.76 | 0.86 |
| What to look at first | 0.81 | 0.57 |
| Handover | 0.48 | 0.81 |
| Explanation asked mid-incident | 0.83 | 0.56 |
| Standalone learning question | 0.87 | 0.73 |
| **mean over prompts** | **0.71** | **0.65** |

Against iteration 6, on the prompts both iterations share, the substance assertions mostly rose: no
invented observations, declaring and routing the edge evidence, "4/4 running instances do not prove
successful requests", saying what each Events result means, and "the instance #2 restart must not be
retried until Dana or a readback reconciles it" (Opus 1/6 → 4/6).

**Two assertions fell, and both are about the closing fields themselves.**

- **Compactness.** "Ends with a compact state strip of about three lines" went from 9/9 to **0/9** on
  Opus across the three incident prompts common to both iterations (Sonnet 9/9 → 7/9). The judge's
  evidence is consistent: the block is labelled correctly and does end the reply, but runs ten to
  twenty lines, with `Open:` carrying four numbered hypotheses and their justifications and `Next:`
  restating the body's decision tree. `6fcb1210` let a field wrap rather than drop a standing
  candidate and `aa65d458` required an owner on every candidate; together they removed the pressure
  that kept the block short, and the models moved the answer into it.
- **Owner by name.** The handover's "names an owner by name for each open item" went 2/6 → **0/6**
  pooled. The replies do request a read-back and do attach owners, but as teams or roles — "owner:
  Kafka team", "Settled by: Kafka on-call", "unowned — needs a DB on-call name" — where the
  assertion wants a person.

Neither is settled here. Whether the long block is a regression or the "about three lines" assertion
has fallen behind the shipped contract is an owner call, and so is whether a role satisfies "owner"
when the prompt names no person for that item. Both sit under QUALITY-001.

### The rename — 2026-09-09

`c1c07085` renames the section to "Where things stand" and replaces "the strip" with "the closing
fields" in the eight places it was the referring noun. No rule content changes, and the section stays
under "Recap or hand over" — the placement candidate that moved it was rejected above, so the rename
was cut loose from the move and measured alone.

Presence, `[verified]` with the committed oracle applied identically to three arms, all on CLI
2.1.265, three runs per cell per model:

| Prompt | Rename `c1c07085` | Merged `aa65d458` | Seam `6fcb1210` |
|---|---|---|---|
| First page, new responder | 6/6 fields | 6/6 | 6/6 |
| External monitor Situation | 6/6 | 6/6 | 6/6 |
| What to look at first | 6/6 | 6/6 | 6/6 |
| Explanation asked mid-incident | 6/6 | 6/6 | 6/6 |
| Standalone learning question | 6/6 none | 6/6 none | 6/6 none |
| **Handover, checkpoint-bearing** | **3/6** | 5/6 | 6/6 |

Five of six prompts are identical across the arms. On the handover the rename arm carries the
checkpoint in three of six replies against five and six; the other three ended with the closing
fields only, which the shipped contract counts as a miss. The rename edited the sentence that fires
the checkpoint — "replaces the strip" became "replaces them" — so a weakened pronoun reference is the
first suspect, but three runs per cell cannot separate that from the heading change or from noise.
The owner reviewed this result and chose to ship the rename ([PR #247](https://github.com/latent-sre/save-toolkit/pull/247)).

The oracle and its test were renamed with it, to
[`probe_closing_fields.py`](../../evals/oracles/incident-closing-fields/probe_closing_fields.py) and
[`test_closing_fields_oracle.py`](../../evals/test_closing_fields_oracle.py); the classification
label `strip` became `fields`. No build scenario binds that oracle path — checked with a positive
control on a path that is bound — so scenario identity is unaffected.

### PR #247 checkpoint reference fix — 2026-09-09

The [open review finding](https://github.com/latent-sre/save-toolkit/pull/247#discussion_r3969292549)
identified the ambiguous replacement target. The follow-up to `2f138025` changes only "replaces
them" to "replaces the closing fields" in that sentence and regenerates the Copilot projection.
The explicit noun adds 14 canonical skill bytes, measured at 619,317; `scripts/weights.json`
records that ceiling in the same diff. No checkpoint trigger, field, or section placement changes.

`[verified]` The existing 15 closing-fields oracle tests pass before and after this edit; context
budgets pass 7/7. These checks preserve the static contract but do not detect pronoun ambiguity or
prove model compliance. `[unverified]` No live model batch was rerun for this follow-up, so the
historical 3/6 and 5/6 handover results above remain tied to their original revisions. This edit
does not establish recovery of checkpoint presence or answer-quality parity.

### Approved incident-skill repairs — 2026-09-09

The owner approved the five audit fixes and four optimization opportunities against `c8efc93b`.
The candidate extends [PR #248](https://github.com/latent-sre/save-toolkit/pull/248):

- The handover rubric and calibration now use the new higher rollback revision, deployment
  completion, and attempt reconciliation. Added negative examples reject target-number equality,
  partial deployment, and invented attempt timing.
- The closing-fields oracle keeps `classify()` as rough presence and makes `check()` require a
  complete terminal block with nonempty values. Ordinary prose, incomplete/empty fields, quoted
  examples, and blocks preceding a separate answer are regression cases. This remains a structural
  check; it cannot establish truth, useful reasoning, or semantic completeness of free-form prose.
- Generic interrupted-action reconciliation stays in the core; the PCF-specific readback and
  worked helper exchange move to linked references. The shipped helper and handover examples
  now carry their required closing fields and are exercised by the oracle tests.
- The three companion contract scenarios grant only `Skill,Read` and assert their relevant
  reference reads. Their regression rejects absent or denied reads and accepts successful reads.
- Navigation follows the confirmed PCF/GCP runtime. Closing fields summarize the supporting
  explanation; supplied names are preserved, known roles can remain pending, and missing owners
  stay unowned. These are the owner's selected compactness and ownership policies, not a claim
  that model output already meets them.
- The owner subsequently approved restoring an explicit review of the five opening questions:
  what changed and when, who else is affected, what failing cases share, whether impact is growing,
  and whether it reproduces from the user's side. Use supplied answers, ask together for missing
  answers that affect immediate advice, retain unanswered questions, and do not delay mitigation.
  This replaces the later optional-comparison sentence; it adds 248 canonical skill bytes.

`[verified]` The entrypoint shrinks from 21,707 bytes at `ae7252d7` to 20,110 bytes (1,597 bytes,
7.4%). This is an invoked-core reduction, not a reduction of the whole bundle or measured latency.
The complete canonical bundle grows because the repair retains conditional details and adds
complete examples. Exact totals and the evaluator's added test/code lines are reviewed in
`scripts/weights.json`; Gate A's structural roster is unchanged.

`[verified]` At `8216ac0c`, before the five-question follow-up, red-first regressions failed on the
old oracle and on all three scenarios' missing Read access. The corrected oracle passes 41 cases;
the full local suite passes 634 tests and
1,023 subtests, with four local-environment skips. Gate A passes 4/4 and scenario validation
passes 73 specifications / 343 expectations. Terra's independent static review found no actionable
defects. Including the five-question and evidence-label follow-ups, canonical skill content grows
by 2,919 bytes and evaluator Python by 201 lines.
Historical presence scores above used the old
oracle and are not reclassified as completeness scores. No build scenario previously bound this
oracle; the existing runner's reference-read assertions are reused without a new mechanism.

`[verified]` The five-question follow-up passes the adapter and closing-fields suites: 77 tests,
50 subtests, and two local symlink skips. Gate A passes 4/4 and `git diff --check` is clean.
These checks establish structural consistency; the opening-question behavior has not been run
against a fresh model.

`[unverified]` Fresh judge calibration and paired native model behavior remain separate checks.
Preflight found 141 calibration cases and zero reusable exact cache keys on this host; a full
calibration would make fresh model calls. The source repairs and size reduction do not establish
checkpoint reliability, reference-loading behavior, or answer-quality parity.

### Terra source-input follow-up — 2026-09-09

The owner approved correcting the exploratory Terra eval, verifying supplied instructions, and
changing the skill only for a demonstrated ambiguity or repeated failure. The earlier private
subagent run lacked complete source-read traces, overreached on a second handover's checkpoint
expectation, and omitted shared factual-integrity criteria. Its scores are not comparable with
this corrected run. The mitigation approval was supplied; only capture availability was invented
in that earlier response, not Morgan's decision to mitigate.

`[verified]` The rerun used Codex CLI 0.153.4 with `gpt-5.6-terra`, medium reasoning, recorded stdin
containing the complete skill and its bundled references (five source files), and persistent session IDs for the two
follow-up conversations. There were seven response turns in five sessions per arm, one trial per
case, and no automatic retries. CLI rollouts bind the model/configuration and source-bearing input;
the comparison normalizes only CRLF/LF. Personal host AGENTS instructions remained present and
were recorded, so this is matched prompt behavior, not a clean-room plugin-discovery result.
Private inputs, criteria, responses, traces, hashes, and grading are retained under
`.eval-runs/terra-pr248-v2-20260909/`.

The baseline is the `7c5abe1c` skill, SHA-256
`332162573b15cd4de69d5325d39c4519301c3b9f1730053d6cbc9ca6c1d55be5`.
Its first response still omitted user-side reproduction as an unanswered question. The new skill,
SHA-256 `c48c57f945c182c6c0dca52a41e51245ca7466eb753b0fe01b43e0e5360c9693`,
changes only the opening review to summarize supplied answers/name unanswered questions and the
existing handover example to separate a sourced attempt report from its unverified outcome.
Together these add 72 canonical bytes over `7c5abe1c`; the candidate response explicitly retained
user-side reproduction as unknown. Neither arm invented unavailable capture, but the candidate's
connection-wait explanation inferred a database destination; the baseline correctly left it open.
The candidate passed four of six cases versus two of six for the baseline, with mixed per-case
deltas. These are observations from one paired sample, not reliability rates or causal proof.

`[unverified]` Behavioral acceptance remains open: both arms still used closing fields after the
new-evidence case materially changed investigation direction, and the candidate's unsupported
database-destination claim remains a factual failure. Exact source inclusion does not
establish installed skill discovery, selective reference retrieval, or Claude-native behavior.
No further skill expansion or repeat-until-green campaign followed this comparison.

## Not established

- The judged gap left by the exhausted credits is now partly closed: iteration 13 (the merged bytes)
  and iteration 9 (the boundary fix) are graded above. Still ungraded are the rename arm (iteration
  12, 9 of 36 cells before the batch was stopped) and the seam arm (iteration 11), so the rename's
  effect on answer *quality*, as opposed to the presence of the closing fields, is `[unverified]`.
- The owner selected concise closing summaries and supplied-name/known-role/unowned handling in
  the candidate above. Their effect on the historical ten-to-twenty-line output and ownership
  scores still needs a fresh measurement; the old scores retain their original assertions.
- The engineering lane has no old-skill arm (its eval sets were written after the edits), so its
  numbers show new skill versus no skill, not the size of the fix.
- The Spring prompt does not discriminate on Opus (1.00 both arms); it confirms no regression, not gain.
- Apps Manager control semantics (per-instance restart, Redeploy) remain `[unverified]` and are
  labelled so in the text; the installed cf CLI version for the rolling-rollback default is
  `[unverified]`.
- The remaining P2s (platform and observability lanes) are unchanged; QUALITY-001 in the roadmap holds
  the owner's decision on them.
