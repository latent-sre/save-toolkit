# Skills audit: what each skill costs and whether it is needed (2026-10-12)

Read-only audit of the 30 canonical skills at `7dec186d` (main after PR #370). The question is
the one the owner asked: the skills have grown fast, so which of them are not needed? The earlier
[six-pass fleet audit](2026-10-02-fleet-audit/README.md) asked whether the guidance is correct;
the [reference audit](2026-10-02-reference-audit/recommendations.md) asked whether each bundled
reference earns its place. This audit asks what each skill costs per session and whether the fleet
needs it at all. Nothing was changed by the audit itself.

## Conclusion

1. **The growth is real and recent.** [verified] Canonical `skills/` is 1,358,103 bytes, the largest
   it has been, up from 575,885 after the 2026-09-07 consolidation. **+424 KB (+45%) landed in the
   last week**, and 96% of it is in three skills: `grafana` +225 KB, `frontend-craft` +121 KB and
   `backend-craft` +61 KB.
2. **Bytes are not the cost that matters most.** Most of the new bytes are tested code and
   on-demand references that cost nothing until a task reads them. The cost every session pays is
   the **skill listing**: each model-invocable skill's name and description. [verified] That cost
   is **~5,170 tokens for save-toolkit's 29 listed skills**, plus ~2,400 tokens for the ten
   agents. Claude Code caps the listing at **1% of the context window**. When the listing is over
   the cap, it drops descriptions, starting with the least-used skills. The fleet routes by
   description, so a dropped description means a skill is much less likely to be picked.
3. **Little dead material inside skills.** [verified] Every bundled file is referenced. Every
   bundled script and asset is either exercised by a repository test or is the Go starter (below).
   A five-word-shingle scan of all 1,158 long paragraphs found **one** passage duplicated verbatim
   across skills: the telemetry-redaction paragraph in `obs-logs`/`obs-metrics`/`obs-traces`. The
   reference audit found 4–5 KB of supportable trims in 554 KB. The new craft material traces
   almost file-for-file to the owner's 2026-10-11 decisions. Another line-by-line trim pass would
   not repay its cost.
4. **The waste is at the level of whole skills and whole features.** Five places cost something
   on every session or on every maintenance pass, and have not shown what they deliver:
   - `fleet-atlas` returns no results as shipped.
   - `agent-authoring` serves only maintainers but ships to every SRE.
   - The Grafana investigation workflow (PR #370, about 191 KB of code and guidance plus 148 KB
     of tests) has no eval, no install path for SREs, and no coverage of Wavefront.
   - `obs-dashboards` is a 4 KB skill that already hands everything implementable to `grafana`.
   - Several skills serve platforms whose current use the repository does not record.

## Cost model and measurements

Claude Code loads a skill in three tiers. The tier decides who pays.

| Tier | What loads | When | save-toolkit today |
|---|---|---|---|
| Listing | name + description | every session, every user | ~5,170 tokens, 29 skills [verified] |
| Body | `SKILL.md` | each time the skill fires | ~71,000 tokens if every skill fired once, estimated by `claude plugin details` [verified] |
| References | bundled `references/*.md` | only when the task reads one | 656,690 bytes across 115 files [verified] |
| Code | scripts, assets, tests | never in context; costs CI time and maintenance | 470,382 bytes bundled, plus their tests under `scripts/` [verified] |

**Listing measurements.** [verified] Claude Code 2.1.296: `claude -p "/context" --plugin-dir .`
from a scratch directory.
- On a 1M-token window (Sonnet, Opus and Haiku all reported 1M here), the Skills row is
  **10k tokens, exactly 1.0%: the listing is at its cap**.
  - save-toolkit supplies 5,170 of the 9,770 counted tokens (53%).
  - Eighteen skills from other sources, all with long descriptions, already show `< 20` tokens:
    their descriptions were dropped.
- With `--settings '{"skillListingBudgetFraction":0.002}'` (2k tokens, the same budget a
  200K-token window gets at 1%), **all 29 save-toolkit skills fell to name-only**.
  - This is an emulation, not a run on a real 200K model.
  - A new install has no usage history. On a working SRE's machine, frequently used skills would
    rank higher and might keep their descriptions.
- `pcf-deploy` (`disable-model-invocation: true`) does not appear in the listing at all.
  `claude plugin details` still estimates ~110 tokens for it, so that estimate does not model the
  flag.

**Listing growth.** [verified] `claude plugin details` with `--plugin-dir` on a temporary
worktree of each commit:

| Commit | Date | Skills | Agents | Always-on (skills + agents + command) |
|---|---|---|---|---|
| `e6702ee0` | 2026-09-07 | 27 | 8 | ~6,005 tokens |
| `d90b22f6` | 2026-10-05 | 31 | 9 | ~7,339 tokens |
| `7dec186d` | 2026-10-12 | 31 | 10 | ~7,928 tokens |

The tool's "Skills" count includes the `adr` command. Always-on cost rose 32% in five weeks.
The open roadmap adds `go-craft` (BACKEND-002), five backend references (BACKEND-001) and frontend
deep references (FRONTEND-003). Only `go-craft` adds a listing entry. CONTRIBUTING's growth row
says "no mechanical ceiling remains", so nothing measures or limits the listing today.

[sourced] Platform facts come from live documentation fetched for this audit:
- Listing budget: `skillListingBudgetFraction`, default `0.01`.
- Per-description cap: `skillListingMaxDescChars`, default 1,536.
- When over the cap, the descriptions of the least-used skills are dropped and every name is
  kept.
- `disable-model-invocation: true` keeps a description out of context.

Sources: code.claude.com/docs/en/skills and /settings-reference. No save-toolkit description
exceeds the 1,536 or the 1,024-character spec limit; the longest is `frontend-craft` at 886.
VS Code documents no listing budget.

### Per-skill footprint

The listing tokens come from the 1M `/context` run. `Bytes` is the whole canonical skill directory.

| Skill | Listing tok | Bytes | Δ since 10-05 | Loaded by agents |
|---|---:|---:|---:|---|
| frontend-craft | ~310 | 137,261 | +120,866 | software-engineer, principal-engineer |
| incident-investigation | ~290 | 57,194 | 0 | all SRE lanes |
| backend-craft | ~260 | 124,590 | +60,525 | software-engineer, principal-engineer |
| operational-learning | ~220 | 21,532 | 0 | scribe |
| obs-logs | ~210 | 55,773 | 0 | observability-engineer, sre-assistant |
| agent-authoring | ~180 | 79,548 | +825 | agent-engineer only |
| akamai-edge, ci-actions, gcp-ops, python-craft, runbook, stack-profile | ~180 each | 18–56 K | ≈0 | various |
| obs-dashboards, obs-metrics, production-change-gate, resilience-analysis, root-cause | ~170 each | 4–28 K | ≈0 | various |
| eng-ladder, fleet-atlas, operator-cli, postmortem, service-lifecycle, toil-reduction | ~160 each | 4–37 K | eng-ladder +10,602 | fleet-atlas: none |
| grafana, obs-traces | ~150 each | 352,283 / 24,570 | +225,324 / 0 | grafana: observability-engineer, sre-assistant |
| obs-pipeline | ~140 | 25,738 | 0 | observability-engineer, software-engineer |
| database-reliability | ~130 | 21,775 | 0 | four lanes |
| obs-alerting, pcf-ops | ~120 each | 36,616 / 25,441 | small | several |
| pcf-deploy | 0 (manual only) | 18,589 | 0 | none |

## Findings and recommendations

The recommendations are ranked by evidence strength, then by what they recover. Listing savings
are each skill's measured `/context` tokens. Byte savings are canonical bytes; the generated
`.github/skills/` copies double them in the repository but not in context.

### Tier 1: supported now, low risk

**F1. `fleet-atlas` returns nothing as shipped. Remove it from the plugin until GRAPH-004 is
accepted.**
- [verified] `python3 -I scripts/fleet_atlas_v2.py check` at `7dec186d` exits 1 with
  `"atlas output is missing"`.
- The skill's no-execution fallback, `docs/fleet-atlas/v2/INDEX.md`, is not committed. Its own
  rules forbid regenerating during a lookup (`skills/fleet-atlas/SKILL.md:46,53`).
- No agent loads it. Its subject is this repository, so an SRE working in a service repository
  has nothing for it to answer.
- GRAPH-004/006 have been `decision-needed` since 2026-09-30.

Removing the skill recovers ~160 listing tokens per session. The 364 KB of `scripts/fleet_atlas_v2*`
tooling and its CI contract are a separate decision under GRAPH-004.

**F2. Fix the drift the audit found (correctness, not size).** All [verified] at `7dec186d`.
- `skills/frontend-craft/references/api.md:13-15` tells the UI to consume whatever document "its
  generator emits (oapi-codegen…)". The backend decision makes Go services code-first on Huma, and
  `backend-craft/SKILL.md:28` makes the committed document the only source.
- `skills/backend-craft/assets/ci/api-contract-fastapi.yml` and `api-contract-go.yml` have no
  `persist-credentials: false`, and `setup-uv` has no pinned `version:`. Both break
  `ci-actions/references/security-and-provenance.md`. The reusable `ci-actions` asset carries the
  setting twice.
- The TypeScript 6 pin is written in three places: `stack-profile/references/application-and-data-stack.md:32`,
  `frontend-craft/references/stack.md:14-16` and `frontend-craft/references/vue.md:13-14`. Keep
  one owner.
- `skills/grafana/SKILL.md` does not say that the workflow helper needs four libraries the plugin
  does not install. That is recorded only in `references/investigation-workflows.md:9-11`.
- `backend-craft/SKILL.md:33` lists Cloud Run as a runtime. `stack-profile` says the landing
  runtime is decision-pending and must not be presented as decided.

**F3. Shorten the two longest descriptions.**
- `frontend-craft` goes from 886 to 613 characters and `backend-craft` from 742 to 561.
- The drafts below keep every quoted trigger, every "Not for" boundary, and the "Mantine" token
  that a discovery scenario expects to fire on.
- [verified] Measured with `/context` on a temporary worktree carrying only these two edits:
  `frontend-craft` drops from ~310 to ~220 tokens and `backend-craft` from ~260 to ~200, so
  ~150 listing tokens are recovered. A routing-description change still needs its overlapping
  clean-room scenarios under CONTRIBUTING.

> frontend-craft: Build or change a web GUI for the team's apps and SRE tooling — consoles, in-app
> dashboards, status sites, form workflows — in React or Vue, wired to the team's OpenAPI services
> and served on localhost and PCF. Owns the design brief, component-kit choice and mixing
> (shadcn/ui, Mantine, MUI and others), the browser side of the API contract, error surfaces and
> accessibility. Triggers: 'build a UI for', 'add a page/form/table/console', 'make this look less
> generic', 'wire the UI to the API'. Not for the service behind the UI (backend-craft) or Grafana
> dashboards (obs-dashboards to design, grafana to operate).

> backend-craft: Build or change the team's backend services — FastAPI or Huma (Go) HTTP APIs,
> workers, schedulers, webhook receivers, and clients for platform and vendor APIs. Owns the house
> API contract (RFC 9457 problems, cursor pages, Idempotency-Key writes, /v1) and its OpenAPI gates
> (committed document, drift tests, Schemathesis, oasdiff), plus the service's operating surface.
> Triggers: 'add an endpoint', 'build an API or service for', 'wrap X behind an API', 'write a
> client for Y'. Not for UI work (frontend-craft) or live database operations (database-reliability).

### Tier 2: high value, but the owner's call

**F4. The Grafana investigation workflow (PR #370, merged 2026-10-12) is the largest single
addition and the least proven.**
- PR #370 added 222,921 of grafana's 225,324 new bytes. The workflow family is about 191 KB:
  `grafana_workflow.py` and ten library modules (173,066 B) plus `investigation-workflows.md`
  (17,636 B). It also grew grafana's tests from 63,694 to 263,608 bytes. [verified]
- [sourced] The PR says what it is for: "Give agents bounded Grafana query evidence … so agents
  can examine data and follow evidence without recollecting it." It states the context byte delta.
  It names no measured failure the workflow prevents, which CONTRIBUTING §3 requires of a new
  mechanism.
- Only `sre-assistant` is told to use it (`agents/sre-assistant.md:195-199`).
  `observability-engineer`, which owns Grafana writes, never mentions it. [verified]
- The collection path accepts only `prometheus` and `loki` datasources
  (`grafana_workflow.py:149`). Wavefront is "the live metrics UI for PCF applications today"
  (`stack-profile/references/observability-stack.md:13`). So the workflow cannot query the
  datasource behind most of today's PCF application panels. [verified; how many panels are
  affected is unknown]
- `investigate --agent-json`, the form the guard requires for the agent, refuses to run without
  `polars` and `promql-parser`, and without `pillow` for the render fallback
  (`grafana_workflow.py:29-52`). The plugin installs none of them, and installation is documented
  only for contributors (CONTRIBUTING §2). [verified by reading the code; not executed]
- Several pieces sit outside the skill's stated lane:
  - VS Code launch: 11.6 KB of code and 17.7 KB of tests. The guard forbids it for the agent.
  - Polars statistics that duplicate the reader's own summary: 8.5 KB.
  - Folder datasource-impact mapping: 23.1 KB, for datasource changes the skill excludes.
  - DeepDiff capture comparison: about 11 KB.
  - [unverified judgment]
- No eval mentions `grafana_read` or `grafana_workflow`. The same grep does find other Grafana
  evals. [verified]

Recommendation: keep `grafana_read.py`, its PowerShell wrapper and `dashboard_hygiene.py`, which
degrades gracefully without its optional parser. Move the workflow family out of the shipped
skill until three things exist:
1. An install path an SRE can follow.
2. A Wavefront answer: either support it or state the gap in `SKILL.md`.
3. One eval in which the agent completes an investigation with the workflow.

If the owner keeps it now, the smaller cut is the four out-of-lane pieces above: about 58 KB of
code and 46 KB of tests. Either way, this reverses part of a change the owner merged today, so it
is the owner's decision.

**F5. Ship `agent-authoring` to maintainers only.**
- README marks its only consumer, `agent-engineer`, "*(for maintainers)*". Every SRE session
  still pays ~180 listing tokens for it.
- A repository-local skill would load only when someone works in this repository. It would need
  generator, Gate A and Copilot-projection changes. [unverified: the exact wiring was not
  prototyped]
- Owner question: do SREs use the plugin to write their own agents or skills?

**F6. Fold `obs-dashboards` into `grafana` or `obs-alerting`.**
- The skill is 4,120 bytes with no references. Its own text sends dashboard search, JSON,
  variables, conventions, saving and rollback to `grafana`, and alert/SLO decisions to
  `obs-alerting`.
- Folding it recovers ~170 listing tokens.
- Cost: it is named in 3 agents, 7 other skill files and 9 eval files, and its routing scenarios
  would need re-measuring.

**F7. The Go starter (36,891 B) is no longer tested.**
- [verified] Commit `80b1dc8f` (2026-10-12) removed the repository's Go execution tests, including
  the starter suite in `scripts/test_backend_craft_assets.py`.
- A live-eval oracle still runs `go test` on agent-built Go code, but it does not touch
  `skills/backend-craft/assets/go/`.
- Choose one:
  - restore a Go job for the starter;
  - drop the starter until BACKEND-002 lands;
  - record it as unverified.

### Tier 3: depends on usage facts the repository does not hold

The audit could not measure how often any skill is used. The repository has eval coverage, not
usage. These calls depend on facts the stack profile leaves open.

**F8. GCP material.**
- The footprint is `gcp-ops` (20,577 B, ~180 listing tokens), three GCP query references in the
  obs skills (18,982 B), Cloud Run guidance in `backend-craft`, and 24 `build-gcp*` eval
  scenarios.
- The stack profile says the landing runtime is decision-pending.
- If nothing runs on Cloud Run in production, `gcp-ops` is a listing cost with no current
  incident to serve.

**F9. The additive OpenTelemetry stack.**
- `obs-traces` (~150 tokens) and `obs-pipeline` (~140) serve Tempo, and the Alloy/OTel path for
  Mimir/Loki/Tempo.
- The stack profile lists traces as a "new capability". It says the additive stack serves
  "services instrumented with OpenTelemetry" but does not say whether any production service is.

**F10. Possible merges.**
- `obs-logs` + `obs-metrics` + `obs-traces` into one telemetry-query skill: about 330 listing
  tokens recovered. The trade is a larger body on every query task. They share only the
  redaction paragraph verbatim.
- `toil-reduction` + `resilience-analysis`: about 160 recovered. Both are loaded only by
  `reliability-engineer`, whose lane is still awaiting acceptance (RELIABILITY-001).

Before taking any Tier 3 action, gather usage data. [sourced]
- `/skill-doctor` reports each skill's cost and flags listed skills that were never invoked. Run
  it on several SRE workstations.
- Alternatively, export the OpenTelemetry `claude_code.skill_activated` event. Plugin skill names
  are redacted to `custom_skill` unless `OTEL_LOG_TOOL_DETAILS=1` is set.

### Not recommended

- **Another reference-trimming pass.** The reference audit and this scan show low yield: under
  10 KB across 1.3 MB, all of it on-demand.
- **Cutting `python-craft` on a text read.** It holds no team-specific facts, but it is
  calibrated against ten `build-python-*` scenarios. Its necessity is an ablation question for
  those scenarios.

### What the recommendations add up to

| Scope | Listing tokens recovered | Notes |
|---|---:|---|
| Tier 1 (F1, F3) | ~310 | F2 is correctness only |
| + Tier 2 (F5, F6) | ~660 total | F4 and F7 change maintenance and on-invoke bytes, not the listing |
| + Tier 3, if usage data supports it | roughly 1,100–1,500 total | Overlapping options; not additive |

Even the full set leaves save-toolkit's listing near 3,700–4,500 tokens. That is under half of a
1M window's 10k budget, but still over a 200K window's 2k budget. **Which context window the team
actually runs**, in Claude Code and in Copilot, decides how much of this matters. On a 1M window
the problem is competition with the team's other plugins and built-ins. On a 200K window, most
descriptions are dropped regardless.

A durable guard would stop this recurring: a measured always-on token budget for the plugin,
checked in CI with `claude plugin details`. Any new skill would then name what it displaces.
That changes CI, so it needs the owner's approval first.

## Method and limits

- **Sizes and growth:** `git ls-tree -r -l` sums over first-parent `origin/main` history after
  `git fetch --unshallow`.
- **Listing costs:** Claude Code 2.1.296, `claude plugin details` and `claude -p "/context"` with
  `--plugin-dir`, run on this repository and on temporary worktrees of `e6702ee0` and `d90b22f6`.
- **References and coverage:**
  - Each bundled file's basename was searched across `skills/`, `agents/`, `commands/`, `hooks/`,
    `scripts/`, `evals/`, the root guides and the workflows.
  - The searches found every file. The detector fired on known-present names, but it was not
    tested against a planted orphan.
- **Duplication:** five-word shingles over paragraphs of 30 or more words. The positive control
  is the known redaction triplicate.
- **Grafana and craft:** two read-only helper reviews. Their load-bearing claims were rechecked.
  - Checked against the code: the dependency gate at `grafana_workflow.py:29-52`, the
    datasource check at `:149`, and the empty eval grep.
  - Checked against git and the files: the Go-test removal in `80b1dc8f`, the missing
    `persist-credentials`, and the `api.md` text.
  - One helper claim was corrected: `go test` does appear in a live-eval oracle. That oracle does
    not test the starter.
- **Not done:**
  - No real usage data.
  - No eval or behavioural run of any skill.
  - No 200K-window model; the budget was emulated.
  - No execution of the Grafana workflow.
  - No compile of the Go starter.
  - The judgment calls most likely to be wrong are the F4 lane-fit split and the F10 merge
    trade-off.
