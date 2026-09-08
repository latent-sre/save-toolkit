# Fleet quality round — analysis, iteration-1 evidence, and batch-A fixes

Date: 2026-09-08 · Branch `work/quality-round-20260908` from `main` at `c960727d` · Claude Code
2.1.263, Windows host, `--plugin-dir F:/repos/sre-agents`.

Scope set by the owner: quality of skills and agents, not size. Sonnet and Opus run every test cell;
Fable plans, analyzes, and judges. This record covers the reading analysis, the first behavioural
iteration on the unchanged fleet, and the first change set (the four P1s and the six incident-lane
P2s). No eval has run on the changed bytes; that after-run waits for the owner's approval.

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
| `spring.mvc.problemdetails.enabled=true` presented as required beside a `ResponseEntityExceptionHandler` | The advice already maps the framework's exceptions; the property registers nothing extra; the real gap (Spring Security 401/403 and `/error` fallbacks) is named with the `AuthenticationEntryPoint`/`AccessDeniedHandler` fix | [`ProblemAdvice.java`](../../skills/backend-craft/assets/ProblemAdvice.java), [`spring-boot.md`](../../skills/backend-craft/references/spring-boot.md) |
| Security-sensitive surface listed as an escalation trigger | Moved into "How you work": independent security review, the fix stays builder-owned unless another trigger applies | [`builder.md`](../../skills/eng-ladder/references/builder.md) |
| 5,000/25,000 tokens presented as the invocation budget | Rewritten as the compaction re-attachment budget; an invoked body loads whole; no per-invocation truncation to design around | [`claude-code-frontmatter.md`](../../skills/agent-authoring/references/claude-code-frontmatter.md) |
| Starter CI job and deploy skeleton without `timeout-minutes` | `timeout-minutes` on both, matching the skill's own rule | [`ci.reusable.yml`](../../skills/ci-actions/assets/ci.reusable.yml), [`pcf-deploy-job.md`](../../skills/ci-actions/references/pcf-deploy-job.md) |
| OpenAPI starter requires bearer auth; contract test sends none and ships no fixture | An `auth_headers` fixture the project fills, passed on every protected request; the docstring says never to weaken auth to satisfy the starter | [`test_http_contract.py`](../../skills/backend-craft/assets/test_http_contract.py) |
| No fleet-level rule for preparing a reviewer dispatch | One sentence in the Handoffs convention: base and candidate identity plus an inspectable diff the reviewer can Read | [`AGENTS.md`](../../AGENTS.md) |
| Reviewer worked examples omit `Reviewed state:` and the non-execution line | Both examples carry every required slot | [`reviewer.md`](../../agents/reviewer.md) |

### Ceilings after batch B

`[verified]` LF blob totals: skills 612,873; agents 115,983 → 116,305. `scripts/weights.json` follows.

## Not established

- Behaviour on the changed bytes: no eval has run since the edits (owner approval pending). The
  iteration-1 cells are the baseline for that after-run.
- Apps Manager control semantics (per-instance restart, Redeploy) remain `[unverified]` and are
  labelled so in the text; the installed cf CLI version for the rolling-rollback default is
  `[unverified]`.
- The remaining P2s (platform and observability lanes) are unchanged; they are the next batch.
