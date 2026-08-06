# Copilot fleet redesign — first-principles rebuild for VS Code / GitHub Copilot

**Date:** 2026-07-13
**Status:** superseded — historical design; current work is governed by
[`docs/decisions/2026-07-31-multi-platform-plugin-packaging.md`](../../decisions/2026-07-31-multi-platform-plugin-packaging.md)
and [`docs/fleet-roadmap.md`](../../fleet-roadmap.md)
**Supersedes:** the Claude-Code-targeted fleet in this repo (9 agents / 37 skills) as the *distributed* artifact. This repo remains the source; the fleet it ships is rebuilt.

## Problem

The current fleet has grown to 46 units (9 agents, 37 skills) and exhibits all four failure modes the owner named:

- **Routing confusion** — one incident prompt loaded six skills at once (recorded probe trace: `incident-severity, pcf-ops, rollback-mitigation, splunk-triage, sre-ladder, …`); **three** skills have never fired on their own on-target prompts (`agent-security`, `ops-cli`, and, pre-clean-room,
  `sde-ladder`). *(An earlier draft counted four, including `pcf-deploy`. That one sets `disable-model-invocation: true`
  — its `saw: none` is the flag working as designed, not a discovery failure. Counting it inflated the problem.)*
- **Context cost** — ~8.3k tokens always-on (AGENTS.md ~3.3k + CLAUDE.md ~1k + 37 skill descriptions ~3.9k) before any work starts.
- **Maintenance rot** — prose transcribing facts that drift: a fabricated WQL clause, a blue-green playbook that inverts on its second run, a security skill wrong about its own guard. The git history is a parade of `fix(guard)`/`fix(skill)` commits patching a denylist that is permanently behind.
- **Can't hold it in your head** — 46 units defeats roster-level reasoning.

Separately, the **target runtime changed**: the consuming team works in **VS Code + GitHub Copilot chat**, not Claude Code. And the **stack changed**: Grafana 13.x + Alloy/Loki/Tempo/Mimir/Prometheus (LGTM) arrives alongside the incumbent Splunk/Wavefront/Moogsoft/ThousandEyes stack (coexistence, not replacement), with a possible GCP onboarding later in 2026.

## Decisions already made (with the owner, in order)

| Decision | Choice |
|---|---|
| Depth of change | **First-principles redesign** (not prune, not consolidation-in-place) |
| Target runtime | **VS Code Copilot chat** only (not Copilot CLI, not the cloud coding agent) |
| Consumers | **A team of SREs** — not an org rollout; no org-admin dependencies; works in any repo they open; self-updates when this repo changes |
| Distribution | **Agent plugin, plugin-first** (owner-verified docs: private-repo marketplaces, 24h auto-update, full skill folders) with a clone+point fallback |
| Stack posture | All incumbent tools stay; LGTM is additive and first-class; **stack churn is a design axiom** (GCP lands as reference files, not restructure) |
| Sister repo | `latent-sre/sde-agents` is a **harvest source** — its doctrine, agent chassis, guard philosophy, and eval machinery import; its home-lab units do not |
| Fleet size | 5 agents / **26 distributed skills** (see count correction note in Section 4) — growth from the initial estimate was accepted "for the right reason" (backend-craft, frontend-craft, service-onboarding earn slots) |

### The sister repo (harvest source), located

`sde-agents` is the owner's *other* agent fleet — a leaner, newer-generation Claude Code plugin
(7 agents / 9 skills: code review, engineering ladder, root-cause debugging, backend/frontend craft,
plus home-lab operations). It is **not** part of this repository and never becomes one — it stays an
independent personal fleet; content imports here are one-way copies that this repo then owns.

- **GitHub:** https://github.com/latent-sre/sde-agents
- **Local checkout (this machine):** `C:\Users\hawkins\sde-agents`
- **Files this spec cites from it:** the plan-format template
  (`docs/superpowers/plans/2026-07-12-fleet-doctrine-alignment.md`), the allowlist guard
  (`scripts/readonly-guard.py` + `hooks/hooks.json`), the doctrine spec
  (`docs/superpowers/specs/2026-07-12-fleet-doctrine-alignment-design.md`), and the agent/skill
  bodies named in the provenance columns below.

The full harvest ledger is the Provenance summary at the end of this document; every roster table
marks imported units SDE (from sde-agents), SRE (from this repo's old fleet), or NEW.

## Section 0 — Run protocol: how every session on this spec opens and closes

This spec is built across many sessions by agents that start cold. Two things must therefore be mechanical,
not remembered.

### Open: sync from `main`, and let it fail loudly

```
git status --porcelain                   # must be empty; a dirty tree makes the next line half-fail
git fetch --prune origin                 # --prune: phase branches get merged and auto-deleted
git switch main && git pull --ff-only origin main
git log --oneline -1                     # record the SHA this phase branched from
git switch -c <phase-branch>             # branch from main, NEVER from another phase branch
```

`--ff-only` is the load-bearing flag: it **fails** rather than silently manufacturing a merge commit when
local `main` has drifted.

**The owner merges PRs mid-session, so `main` moves *under* a long-running phase.** Fetching alone does not
fix that — it updates remote-tracking refs and leaves your branch exactly where it was, so you learn `main`
moved and change nothing. Before opening each PR, actually **move the branch**:

```
git fetch --prune origin
git rebase origin/main
git log --oneline origin/main..HEAD      # assert: ONLY this phase's commits
```

That last line is the real check. The failure this prevents is not an error — it is a **silently inflated
diff**: if a PR is stacked on another phase branch and that parent merges and auto-deletes, GitHub
**re-targets the child to the parent's base rather than erroring**, absorbing the parent's commits into your
diff. Branch every phase from `main` and the mode cannot occur.

### Close: four audits, in cost order

A phase is not done until **A–C** are green. **D** runs at the end of **Phase 3** (the first point the fleet is
content-complete) and again at **Phase 6** — not at every phase boundary, because "0 dark skills" over a
half-built skill set is vacuously true, which is a green light that measured nothing.

| Audit | Catches | Cannot catch | Cost |
|---|---|---|---|
| **A — Mechanical** | broken structure: bad frontmatter, unwired hooks, dangling references, non-kebab names | anything about whether the *content* is true | free |
| **B — Content regression** | a known-bad fact ported forward verbatim | — *(once mechanized; see below)* | free |
| **C — Adversarial review** | design holes, security regressions, spec non-conformance, **unverifiable stack facts** | things no reviewer thought to look for | model |
| **D — Behavioral** | dark skills, routing fan-out, guard false-denies, token budget | correctness of any individual answer | model + time |

**A — Mechanical.** One command. It is the same entrypoint CI runs, so the two cannot drift:

```
python scripts/gate_a.py
```

It resolves its own interpreter (`sys.executable`), which settles the `python` / `python3` / `py -3` question
by not having an opinion — `python3` on Windows is the Microsoft Store stub, the bug that once silently
disarmed the read-only guard. It preflights the pinned deps rather than letting a cold agent reach for a bare
`pip install pyyaml`. **Do not transcribe its steps back into this document**; that is how the previous draft
of this section shipped a step-list that had already dropped the dependency install.

**B — Content regression. The audit that exists because of our own history.** The Tier-2 bugs in
the removed `docs/AUDIT-2026-07-12.md` (git history only) are **live on `main` right now**, and this migration's
core operation is *copying content forward* — so verbatim-move discipline will faithfully preserve every one of
them. They are not stylistic: a prod-password leak in `argv`, a blue-green playbook that pushes onto the live app
on its second run, an SPL filter that guarantees the alert under-fires, an error-budget script that prints
"within budget" at 5.50x burn, a fabricated WQL clause, and Grafana data sources needing an Enterprise license we
do not have.

> **Mechanize this gate — do not leave it as prose.** As a manual "diff each ported skill against the ledger"
> pass it is the most skippable gate in the stack, and it is the one we already know we need. All six bugs are
> **string-detectable**. **Phase 1 deliverable: `scripts/test_no_regressions.py`** — six assertions, pure stdlib,
> wired into `gate_a.py`. B then collapses into A: free, permanent, unskippable. The repo's own doctrine is
> *structural enforcement over prose*; B is currently prose.

**C — Adversarial review.** Independent eyes on the diff: `code-reviewer`, `security-reviewer`, and one reviewer
briefed only on the spec, checking conformance rather than code. **Not ceremony — it has already paid, twice.**
The independent sanity review of this spec found the hole neither the author nor the design caught (the fallback
channel shipped **no hook guard at all**, so `sre`/`observer` would have gone out with `execute` and no
allowlist). The review of *this very section* caught that Gate A, as first written, **could not run at all from
Phase 1 onward** — Phase 1's opening `git mv` moved the directories the validator hardcoded.

C also owns the one class **no other gate covers**: a stack fact we *invent* during the port. B catches
*known*-bad facts; nothing else looks at truth. Since a fabricated WQL clause is the fleet's own headline rot
mode, C carries an explicit rule: **every stack-specific command, query, or API field in a ported skill is either
executed against the real system and labeled `[verified]`, or labeled `[unverified]`.** An unlabeled claim is a
review finding.

**D — Behavioral.** Run **Section 8's acceptance table in full**, through the clean-room rig
(`evals/clean_room.py`) so the operator's personal skills cannot compete with the fleet for discovery. The table
is the source of truth; it is deliberately *not* re-listed here.

> **Gate A cannot catch a single Tier-2 bug, and that is the whole point of running four.** This is
> demonstrated, not argued. On `main` at `36812ed`, the entire mechanical suite passes — *"Validated 37 skills
> and 9 agents… VALIDATION: PASS"*, 11/11 validator tests, 505/505 guard cases, 25/25 scenarios — while
> `.claude/skills/github-actions-ci/SKILL.md:107` reads `cf auth "$CF_USERNAME" "$CF_PASSWORD"`, putting the
> production password in `argv` where any process on the box can read it. The validator is *structural*: it
> checks that a skill is well-formed, never that it is right. **A green Gate A over a leaking fleet is the
> normal case, not the edge case.** Auditing means B and C ran too, or it means nothing.

## Section 1 — Distribution: plugin-first, clone-and-point fallback

**Primary channel.** This repo becomes an **agent plugin**: **`.claude-plugin/plugin.json`**, the *single* manifest location (matching the sister repo; VS Code auto-detects the Claude plugin format). **There is no second `plugin.json` at the repo root** — "no second source of truth" is one of this fleet's own imported rules. Plus `agents/`, `skills/`, `commands/`, `hooks/`, `.mcp.json`. Each engineer adds the team repo to `chat.plugins.marketplaces` (any git remote works; private repos supported — VS Code falls back to cloning directly) and installs once from the Extensions view (`@agentPlugins` filter). Marketplace-sourced plugins auto-update every 24h under `extensions.autoUpdate`. Skills arrive as `/sre-agents:<skill>`; agents appear in the chat dropdown; hooks and MCP config ride the same bundle.
*[sourced: code.visualstudio.com/docs/agent-customization/agent-plugins, fetched 2026-07-12]*

**The marketplace layer (was missing — a builder hits this on day one).** A git repo becomes a
marketplace via **`.claude-plugin/marketplace.json`** at its root; VS Code's plugin docs defer to this
schema *[sourced: code.claude.com/docs/en/plugin-marketplaces]*. **One repo can be both marketplace and
plugin.** Our entry:

```jsonc
// .claude-plugin/marketplace.json
{ "name": "latent-sre", "owner": { "name": "latent-sre" },
  "plugins": [ { "name": "sre-agents",
                 "source": { "source": "github", "repo": "latent-sre/sre-agents", "ref": "release" },
                 "description": "SRE + SDE fleet for VS Code Copilot" } ] }
```

**Why a `github` source with `ref`, not a relative `"./"` path — this is a security decision, not a
style one.** A relative source tracks whatever the marketplace repo is cloned at (effectively default-branch
HEAD, and the exact ref behavior is *undocumented*). Git-based sources accept **`ref`** (branch/tag/commit)
and **`sha`** (40-char, the effective pin) *[sourced: same]*. This plugin **ships hooks that execute shell
on every engineer's machine**, and VS Code says so itself: *"Plugins can include hooks and MCP servers that
run code on your machine. Review the plugin contents and publisher before installing."* With a `./` source,
**any merge to `main` reaches the whole team within 24h, unreviewed at the point of delivery.**

**Release discipline (consequence of the above).**
- The marketplace pins **`ref: release`**. `main` is the working branch; **`release` is what engineers run.**
- Promotion `main` → `release` requires green CI *and* human review. **Branch protection on this repo — especially `hooks/`, `scripts/`, `plugin.json`, `.mcp.json` — is now a workstation-security control**, equal in weight to the prod-boundary check in Section 5, and belongs in CODEOWNERS (Section 9).
- **Rollback:** revert on `release`; engineers pull within 24h, or immediately via **Extensions: Check for Extension Updates**. Announce in the team channel — a silent revert is indistinguishable from a broken update.
- Bump `version` in `plugin.json` on every promotion (the field VS Code uses for update decisions).

**The gate checks (three, not one — they run in Phase 5, Distribution).** An earlier draft called `chat.plugins.enabled`
"the design's only admin dependency," and fronted the plan with it. Both were wrong: there are three gates, and none of
them gates *content* — they decide which channel delivers a fleet that is identical either way. They belong with
Distribution:
1. **`chat.plugins.enabled`** — defaults false, **org-managed**. Flippable, or policy-blocked? (Decides channel.)
2. **Copilot org policy — "Editor preview features."** Agent plugins are Preview; an org toggle can gate preview features independently of the VS Code setting. *[unverified — verify here rather than assert]*
3. **Model availability.** Section 3 pins Claude-first fallback arrays. Anthropic-model access depends on org model policy and license tier. Confirm the named models are actually selectable, and record the assumed tier (Business/Enterprise) as a stated assumption.

**Platform-contract probes** are *not* gathered here. The only one that can invalidate the design — does `tools:` omission genuinely deny? — is answered by the first real agent in Phase 1; the hook-payload probes run in Phase 4, where they are first needed. See Section 7.

**Fallback (if policy blocks plugins).** Clone to a fixed path; point the GA settings `chat.agentFilesLocations` / `chat.agentSkillsLocations` into the clone; sync via scheduled `git pull --ff-only` (or a SessionStart hook, preview). **The repo layout is identical for both channels** — choosing the channel is a per-engineer setting, not a repo fork.

**Onboarding — `setup.ps1`, one-time. The two channels are different scripts, not one sequence:**

- **Preflight (both):** `git` reachable; `gh auth status` OK (the production-change gate shells `gh api`, and a
  missing auth fails mysteriously later); VS Code settings path found.
- **Plugin channel:** write `chat.plugins.enabled` + `chat.plugins.marketplaces: ["latent-sre/sre-agents"]` →
  print the one manual step (Extensions → `@agentPlugins` → Install → accept the trust prompt). **That click is
  deliberately not scriptable** — it is VS Code's publisher-trust gate for code that will run on the machine, and
  given the hook-execution risk above, we *want* it conscious.
- **Fallback channel (if the Phase-5 gate checks fail):** clone to a fixed path, write `chat.agentFilesLocations` +
  `chat.agentSkillsLocations` into it, have **`setup.ps1` register the scheduled task** running `git pull --ff-only`
  (not the engineer — an unregistered sync means a permanently stale fleet), **and register a USER-LEVEL HOOK.**
- **The fallback channel must carry the guard, or "identical either way" is false in the one dimension that matters.**
  Section 5 says the hook runs from the plugin's installed copy — but the fallback channel *has no plugin*, so as
  originally written it would have shipped `sre` and `observer` holding `execute` with **no allowlist at all**, and
  nothing said so. VS Code reads hooks from **`~/.copilot/hooks`** (user scope, **no plugin required**); they
  **coexist** with plugin hooks, and `command` may point at an arbitrary script path
  *[verified: code.visualstudio.com/docs/agent-customization/hooks, fetched 2026-07-13]*. So `setup.ps1`'s fallback
  path registers a user-level hook pointing at the fixed clone. **Section 5's rule is therefore "never a copy the
  workspace under review supplies" — not "never outside a plugin"**: a user-controlled clone at a fixed path is not
  attacker-supplied. Only with this are the two channels equivalent in safety, which is what permits the org gates to
  wait for Phase 5.
- **JSONC hazard:** VS Code `settings.json` is **JSONC** — comments and trailing commas are legal. `ConvertFrom-Json`
  either fails or silently strips the engineer's comments on rewrite. Use a comment-tolerant parse + targeted key
  insertion, or instruct a manual paste and confirm with `-Verify`.
- **`setup.ps1 -Verify`** reports: active channel · installed plugin commit/ref · whether skills actually load ·
  `gh auth` state. `setup.sh` twin for non-Windows.

**Rejected channels, with reasons pinned:**
- **VS Code Marketplace extension** (`chatAgents`/`chatSkills` contribution points): stable API, native auto-update — but `chatSkills` points at a single `SKILL.md`; skill folders with `references/`/`scripts/` are unsupported (microsoft/vscode **#304721**, open, assigned, no milestone). The redesign leans on references. **Revisit trigger: #304721 closes** and a private distribution channel exists.
- **Org-level agents** (`{org}/.github(-private)/agents`) and **enterprise-managed plugins**: solid mechanisms, wrong scope — this is a team, not an org, and both require org-admin control. Revisit if the org ever adopts the fleet. Org-level *skills* don't exist yet ("coming soon" per GitHub community discussion #189753).
- **`gh skill install`**: real and GA, but covers skills only and updates are manual per-engineer.

## Section 2 — Taxonomy: map the fleet onto Copilot's seven layers

Derivation rule: **each piece of the old fleet moves to the lowest layer that can carry it.**

| Copilot layer | What moves there |
|---|---|
| Custom agents (`.agent.md`) | Only lanes with a distinct **tool scope** — the agent-vs-skill rule, machine-enforced by `tools:` |
| Agent skills | Playbooks, checklists, query patterns — auto-loaded by description or `/invoked` |
| Slash commands (`commands/`) | One-shot workflows (the `adr` scaffold; a Bamboo walkthrough if any migration remains) |
| Hooks | The read-only guard, rewritten (see Section 5) |
| MCP servers | Live tooling — a Grafana MCP server is the LGTM-exploration vehicle *(existence/fit: verify during implementation)* |
| `agents:` + `handoffs:` frontmatter | The old `route-request` + `handoff-protocol` layers, dissolved into native mechanics |
| Plugin | The distribution wrapper |

**Structural consequences:**
1. **AGENTS.md dies as always-on context.** Plugins don't inject ambient instructions into arbitrary repos — which force-ends the 3.3k-token tax. Each `.agent.md` body is self-contained; the stack profile becomes a small **`stack-profile` skill** loaded on demand. The stay-in-lane rule lives *only* there, phrased as current fact ("runtime today: on-prem + TAS; GCP under evaluation late 2026"), so one file changes when the ground shifts.
2. **Read-only becomes real.** An agent whose `tools:` omits `execute`/`edit` cannot run or write, period — enforcement by absence. The hook guard survives only as an audit/deny layer on agents that genuinely need `execute`.

## Section 3 — The agent roster: 9 → 5

| Agent | Tools (GitHub alias vocabulary) | Lane | Chassis provenance |
|---|---|---|---|
| **sre** | read, search, execute, web | Triage, RCA, incident investigation | sre-agents `sre-engineer` method + sde-agents doctrine + **Tier 0–3 change authority** |
| **sde** | all | Build/fix/refactor code and ops tooling; absorbs test-writing | **sde-agents `sde-fullstack`** (forks, checkpoint contracts, red-flags table, review packet w/ worked example) |
| **reviewer** | read, search **only** | Code + security review (two lenses, one tool scope) | **sde-agents `code-reviewer`** (`[caller-flagged]`/`[independent]` + mandatory independent-P0/P1 count; evidence gate; injection rule) + sre `security-reviewer` lens |
| **observer** | read, search, edit, execute | Obs-as-code: dashboards, alerts, SLOs; LGTM home | sre-agents `sre-monitor` + Tier 0–3 + "never cut the branch you're sitting on" |
| **scribe** | read, search, edit (**no execute**) | Runbooks + postmortems; documents commands from evidence, never runs them | sre-agents `runbook-author` modes + sde-agents `runbook` leanness |

### The tool vocabulary is UNVERIFIED and it is the primary safety control

The table above uses the GitHub alias vocabulary (`read`/`search`/`execute`/`edit`/`web`/`agent`). VS Code's own
custom-agent docs show a **different, namespaced** vocabulary (`search/codebase`, `web/fetch`, `edit`, `agent`).
Which one VS Code chat actually accepts — and, critically, **whether an unrecognized alias fails closed (agent gets
nothing) or open (agent gets defaults)** — is unconfirmed. If it fails open, `reviewer` and `scribe` silently run
with full tools and **the entire safety model is decorative.**

**Blocking check (Phase 1, on the first real agent):** author `reviewer` (`read`, `search` only) first, load it, and ask
it to run a shell command. If it can, the vocabulary is wrong or an unrecognized alias fails **open** — either way the
primary control is decorative and `reviewer`/`scribe` must be hook-guarded instead. Stop and amend Section 5 before
authoring the other four; pin the verbatim `tools:` arrays into this spec at that point.

### The delegation graph (was unspecified — Phase 1 cannot start without it)

`agents:` = who this agent may **auto-delegate** to (model-initiated subagents). `handoffs:` = **buttons a human
clicks** to move the conversation to another agent. Default deny: an edge not listed here does not exist — **`[unverified]` until the Phase-1 probe (assertion 4) proves that omitting `agents:` denies rather than allows all.**

| Agent | `agents:` (may delegate to) | `handoffs:` (human-clickable) |
|---|---|---|
| **sre** | `observer` (pull a dashboard/alert), `scribe` (read an existing runbook) | → `scribe` *"write this up"* (investigate→document) · → `sde` *"fix the root cause"* |
| **sde** | `reviewer` (pre-merge self-check) | → `reviewer` *"review this diff"* · → `scribe` *"document the new ops steps"* |
| **reviewer** | *(none — it is terminal and read-only)* | → `sde` *"apply these findings"* |
| **observer** | `scribe` (link the runbook a new alert requires) | → `sre` *"this signal is now an incident"* · → `scribe` *"runbook for this alert"* |
| **scribe** | *(none)* | → `sde` *"automate this instead of documenting it"* |

No other edges. `reviewer` and `scribe` deliberately delegate to nobody: a read-only reviewer that can spawn a
write-capable agent is not read-only, and that is the "delegation is not isolation" rule the old fleet learned the
hard way (see the removed `docs/AUDIT-2026-07-12.md` in git history, Tier 4).

### Model arrays (the ellipses were unbuildable)

`model: ['Claude Sonnet 5 (copilot)', 'Claude Opus 4.8 (copilot)', 'GPT-5.4 (copilot)']` — a prioritized array; the
first *available* model wins. **Selection rule** (so this survives the model lineup churning): primary = the strongest
Claude model exposed in the team's Copilot picker at ship time; final fallback = the org's default non-Claude model,
so an agent still runs if Claude is policy-blocked. **The chosen pair is recorded in `stack-profile`**, not scattered
across five agent files.

**Timing (the model check is free, and earlier than Phase 5).** Agents are authored in Phase 1 but model availability
is formally checked in Phase 5 — which sounds like a hole and is not: the array is a *prioritized fallback*, so an
unavailable model degrades to the next entry rather than failing. In practice you learn the answer in Phase 1 for
nothing: **loading the first agent shows you which model it actually picked.** Phase 5 only confirms it for the whole
team under their license tier.

Every agent also gets the uniform **doctrine layer**: `[verified]/[sourced]/[unverified]` labeling, an output packet
**with a worked example**, "recommend better, never silently substitute," "ask the forks, assume the details."

### `stack-profile` must actually load — or the stay-in-lane rule silently dies

Today "do **not** suggest Kubernetes / cloud-managed services; escalate platform-internal problems" is **always-on**
(AGENTS.md). Moving it into an on-demand skill removes that guarantee, and the failure is invisible until an SRE is
told to use Kubernetes. Two mechanisms, both required:
1. **Every agent body carries one line:** *"Before recommending a runtime, tool, or infrastructure change, load
   `stack-profile`."*
2. **A canary probe** whose prompt invites an off-stack recommendation and asserts the skill loaded. It is in the
   canary set built in Phase 4 alongside the other content probes — but it is a **required** canary, not an optional one:
   an unloaded `stack-profile` is a silent correctness regression, so the Acceptance bar (Section 8) fails without it.

**Cut:** `test-engineer` (tool scope identical to sde → its content is sde's testing sections), `researcher` (Copilot `web` tool + native subagents; also held the fleet's widest egress), `prompt-engineer`-as-agent (→ authoring skill pack), `route-request` + `handoff-protocol` (→ native `agents:`/`handoffs:`), the sister repo's ladder agents (altitude stays skill-carried; their method arrives via eng-ladder references, **rewritten self-sovereign** since the agent files they defer to won't exist).

**Known trade:** merging the reviewers loses the dedicated security-review lane identity; the reviewer body carries both lenses explicitly. Reversible (one file) if it proves wrong.

## Section 4 — Skills: 37 → 26, structured for stack churn

> **Count correction (caught in spec self-review).** Conversation tallies said "~21"; the actual
> roster below is **26**. The error was arithmetic (a miscounted "16-core" baseline carried across
> turns), not scope creep — every skill below was individually argued and approved. Net change:
> 46 units → 31 (5 agents + 26 skills), a one-third cut with disjoint triggers, rather than the
> ~45% implied earlier. If the count matters more than the boundaries, the compression candidates
> are: the three gates → one `gates` skill with modes (−2, but un-fixes solved routing);
> incident-command + postmortem → one incident skill (−1); craft + eng-ladder → one engineering
> skill (−1, muddies a measured-good trigger). Default: keep 26; boundaries beat count.

**Observability by signal, not by product** (products churn; signals don't). Each skill body teaches the investigation *shape*; per-backend `references/` teach the dialect, gated by frontend-craft-style predicate tables ("if the question involves X → read references/Y **before** writing"):

| Skill | Question | References today | Later |
|---|---|---|---|
| obs-logs | "the answer is in the logs" | SPL, LogQL | Cloud Logging |
| obs-metrics | "the answer is in the metrics" | PromQL (Mimir), WQL | Managed Prometheus |
| obs-traces | "follow one request" (new capability — **NEW**, no SRE feeder) | TraceQL; OTel *trace semantics* (span/attr conventions) | — |
| obs-dashboards | Grafana 13.x as code | provisioning; legacy Wavefront | — |
| obs-alerting | alert, correlate, page | Grafana unified alerting; SLO burn-rate (script survives); Moogsoft; ThousandEyes | — |
| obs-pipeline | what ships telemetry where | Alloy, collectors; OTel *instrumentation/SDK* (from instrument-service) | GCP exporters |

Boundary note: `frontend-craft/references/data-viz.md` owns **product-UI charts** (Recharts/uPlot); `obs-dashboards` owns **Grafana**. Stated in both descriptions so they never compete.

**Full skill roster** (provenance: SRE = sre-agents, SDE = sde-agents, NEW):

| Skill | Provenance / notes |
|---|---|
| stack-profile | NEW — the single stack-definition point; current-fact phrasing |
| obs-logs, obs-metrics, obs-dashboards, obs-alerting, obs-pipeline | SRE content restructured; LGTM references NEW |
| obs-traces | **NEW** — no SRE feeder (the old fleet had no tracing skill) |
| pcf-ops | SRE (factually clean per audit) |
| pcf-deploy | SRE, **blue-green playbook fixed** (name rotation); stays `disable-model-invocation` |
| service-onboarding | **SDE `service-onboard` reshaped for work** — the LGTM adoption playbook; audit mode from `lab-audit` (evidence rules: "no finding without the command output"; "top three fixes, not thirty"); `disable-model-invocation` |
| incident-command | SRE `incident-severity` + rollback decision content |
| postmortem | SRE `blameless-postmortem` |
| runbook | **SDE body** + SRE template as asset |
| merge-gate, release-gate, production-change-gate | SRE (eval'd well separated); prod gate gains the **Tier 0–3 model** + branch-protection check |
| craft | SRE (already the model: per-language references) |
| backend-craft | **SDE, imported whole** (6 references); `references/stack.md` rewritten for work stack; absorbs api-design/ops-stack-integration |
| frontend-craft | **SDE, imported whole** (5 references); absorbs spa-architecture |
| ops-tooling | body = **SDE `sre-tool` pipeline** (mission transaction, environment card, right-sizing, review-seeding rules); CLI patterns reference absorbs ops-cli |
| root-cause | **SDE, replaces debug-rca** (measured winner: 2/2 misroutes went *to* it) |
| eng-ladder | **SDE base** (one skill, three tier references, rewritten self-sovereign) + SRE track content |
| ci-actions | SRE `github-actions-ci`, `cf auth` argv leak fixed. Bamboo content: **default delete** (recoverable from git); becomes a prompt file only if live migrations remain — confirmed in **Phase 2** (an earlier draft said Phase 3, which no longer exists) |
| database-reliability | SRE |
| agent-authoring | SDE `prompt-craft`/`prompt-engineer` method + SRE `agent-authoring`; references absorb tool-design, context-engineering, multi-agent-architect's "should this be multi-agent at all?"; teaches **personal-first, promote-by-PR** and compose-with-fleet-agents |
| agent-security | SRE, rewritten Copilot-native (tool-scope containment) — ships because teammates *will* build their own agents |

Prompt files: `adr` (scaffold). The complete fate of every existing unit is the **Disposition ledger** (appendix at the end of this document); the implementation plan turns that ledger into dependency-ordered tasks.

## Section 5 — Safety model

1. **Primary control: `tools:` omission.** reviewer and scribe physically cannot execute; scribe cannot run what it documents.
**The VS Code hook contract differs from Claude Code — do not port the exit codes.** VS Code: **exit 0 means stdout is parsed as JSON** (`permissionDecision`: `allow` | `deny` | `ask`); **exit 2 is a blocking error**; other codes are non-blocking warnings; and **"most restrictive wins"** across mechanisms *[verified: hooks reference, fetched 2026-07-13]*. The sister repo's 42/43 positive-ALLOW codes are a *Claude Code* contract and must **not** be copy-ported. The hazard they existed to close still applies, though: **exit 0 with empty stdout reads as ALLOW**, so a missing or broken interpreter would silently permit everything — exactly how the old guard shipped dead on Windows. **The launcher must fail closed: if it cannot start the guard, it emits a `deny` JSON itself.** Probed in Phase 4.

2. **The hook guard — allowlist, imported doctrine.** *"Enumerating the ways a command can write is unbounded and always a step behind; enumerating what an agent needs is bounded, knowable, and fails loud."* (sde-agents; sre-agents' 20+ guard-fix commits are the proof by exhaustion, capped by the live `python -m pip` bypass found 2026-07-12.) The new hook: **allowlist**; **positive-ALLOW protocol** (distinctive exit codes so a stand-in interpreter exiting 0 cannot read as ALLOW; fail closed); **parser humility** (substitution/redirection/subshell → deny by construction); **self-scoping** on the payload's agent identity because **VS Code ignores hook matchers** — hooks fire on every tool, so the script filters on `toolName` itself; **camelCase payloads**; **runs only from the plugin's installed copy**, never a workspace copy (a repo under review could supply its own guard); **never touches non-fleet sessions** — deny-for-the-guarded-agent AND never-touch-anyone-else are both tested, because getting either wrong is worse than no guard.
3. **Change authority: Tier 0–3** (observe / prepare / reversible-live / destructive-or-access-path), imported from sde-agents `homelab-platform`: classify before acting; approval covers only the commands shown; a material change re-enters the gate; independent Tier 0/1 work continues while approval pends; worked approval-request example (target, diff, exact command, blast radius, verification, rollback). Woven into sre + observer bodies and production-change-gate.
4. **Prod boundary unchanged:** GitHub branch protection + protected environments, with the gate's `gh api …/protection` check (must return `enforce_admins: true`, 404 = BLOCK).

### 5a. The allowlist, actually enumerated (doctrine is not a list)

Importing "allowlist, not denylist" without writing the list leaves the builder to invent the guard. **Guarded:
`sre` and `observer`.** **`sde` is unguarded by design** — it holds `all` tools and its whole job is running builds
and tests; a guard there would be theater. That is a **trust decision, stated**: `sde` is for code the team authored
(the untrusted-diff refusal rule from the audit's Tier 4 lives in its body).

| Agent | Allowed (seed set — Phase 4 finalizes against real use) |
|---|---|
| **sre** | `cf` read verbs (`app`, `apps`, `events`, `logs`, `curl`-free), `git log/diff/show/blame/status`, `gh run/pr view|list`, `rg`/`grep`, `ls`/`cat`/`head`/`find` (no `-exec`), `jq`, `dig`, `ss` |
| **observer** | the `sre` set **plus** config validators it genuinely needs (`promtool check`, `jq empty`, `grafana` CLI lint) — the audit proved the read-only guard denies exactly these, which is why `sre-monitor` could never take the old hook |

Everything else denied, including all interpreters (`python -c`, `-m <module>` — the audit's live bypass class),
local scripts, and build/test runners. **A blocked legitimate read is a loud, one-line fix; a missed writer is
silent.** `cf env` stays denied (it leaks credentials to an agent with egress).

### 5b. Precedence when agent identity is indeterminate (the two guarantees can conflict)

The spec promises both *fail closed* and *never touch non-fleet sessions*. If a Copilot upgrade renames or drops the
agent-identity field (Risk 4), the guard cannot tell fleet from non-fleet — and those two promises point opposite ways.
**Ruling: no-op, and emit a loud audit line naming the missing field.** Denying every tool call in the user's own
session would be an outage of their editor, and a hook that breaks VS Code gets uninstalled — which removes the guard
anyway, permanently, in exchange for a temporary one. The loud line is what triggers the probe re-run. *(This makes the
never-touch guarantee the stronger one; it is a deliberate ordering, not an oversight.)*

### 5c. `web` is egress, and the new `sre` agent holds the full trifecta

The old fleet documented this and refused to hide it; the redesign must not regress it. `sre` = `read` (repo/secrets)
+ untrusted input (logs, PR bodies, alert payloads) + `execute` + **`web`** — all three legs, and `web` is an egress
channel **the hook cannot see** (it guards commands, not tool calls). Deleting `researcher` for holding "the widest
egress" and then handing `web` to `sre` without saying so would be exactly the drift the audit condemned.

**Decision (recommend, owner may overrule): keep `web` on `sre`, contain it at the boundary.** Rationale: an SRE mid-
incident genuinely needs to look up a vendor status page or an error code, and routing that through a human is a real
cost at 3am. Containment is the **outbound network allowlist** (the load-bearing control, unchanged from the old
fleet) plus the trifecta note in the agent body. **The alternative** — strip `web` from `sre`, look-ups go to the human
— is one line to apply if you'd rather not carry the risk. Either way it is now *recorded*, not silent.
5. **Probed, not assumed.** Platform facts the safety model rests on get **probes re-run after every VS Code/Copilot upgrade** (the sde-agents discipline: `hooks:`-on-plugin-agents silently ignored and `Bash(git diff:*)` scoping inert were both *probed*, not read). New-fleet probe list: hook payload shape (camelCase, agent identity field), plugin skill/agent loading, hook firing for plugin-shipped hooks, `disable-model-invocation` behavior.

## Section 5d — Reference files: the pattern is right for Claude Code and BROKEN for VS Code

The whole design leans on progressive disclosure — 26 lean skills whose depth lives in `references/`, loaded on
demand. It is why we rejected the Marketplace-extension channel (it cannot ship skill folders). So the mechanism has
to actually work, and **as imported, it would not.**

**The rule.** VS Code loads bundled files in three levels — name+description, then the `SKILL.md` body, then
*"as Copilot works through the instructions, it accesses additional files"* — and pointers must use
**Markdown link syntax with relative paths**, e.g. `[test template](./test-template.js)`. The doc is blunt about the
failure mode: **"If a file isn't referenced in the instructions, it won't be loaded."**
*[verified: code.visualstudio.com/docs/agent-customization/agent-skills, fetched 2026-07-13]*

**What we were about to ship.** Both source fleets point at bundled files with **bare code-spans**, not links:

| Repo | Markdown links | Bare code-spans |
|---|---|---|
| `sde-agents` (the harvest source) | 3 | **19** |
| old `sre-agents` fleet | 21 | **26** (14 skills affected) |

`frontend-craft`'s predicate table — the exact mechanism the six observability skills copy — is entirely
code-spans: `` | a form or any user input to submit | `references/forms.md` | ``. **In Claude Code that works**, because
the model simply calls Read on the path. **In VS Code the file is never loaded at all**, and the failure is *silent*:
the model answers from memory of what `forms.md` probably says. That is precisely the failure sde-agents' own
doctrine-alignment spec diagnosed — *"every branch is a chance to skip the read, hallucinate it, or answer from
memory"* — reproduced in a runtime where it is worse, because the file is not merely un-read but un-loaded.

**This is the one place the verbatim-move discipline must NOT apply.** Section 7 tells the porter to relocate prose
unchanged, precisely to avoid transcription drift. Reference *pointers* are the stated exception: **every bundled-file
pointer is rewritten to Markdown-link syntax during the move.** A verbatim port would faithfully preserve the bug.

**Rules for every skill in the new fleet:**
1. **Every** pointer to `references/`, `assets/`, or `scripts/` is a **relative Markdown link**:
   `[forms](./references/forms.md)`, never `` `references/forms.md` ``.
2. **Predicate tables keep their shape**, but the right-hand cell becomes a link:
   `| a form or any user input to submit | [forms](./references/forms.md) |`
3. **Every bundled file is linked from the body.** An unlinked file is dead weight that never loads — so if it
   isn't worth linking, delete it.
4. **The skill body names the trip condition and orders the read**: *"read it **before** writing that code, and name
   what you read in your packet."* Progressive disclosure is not just "the file exists"; the model must be told when
   to open it and be held to having done so.

**Validator v2 enforces this (new rules, both errors — not warnings):**
- A bundled-file path appearing as a **code-span rather than a link** in a `SKILL.md` body → **error**. This is the
  rule that would have caught the bug above, and no existing validator has it: sde-agents' validator existence-checks
  reference links but never their *syntax*, because in Claude Code the syntax does not matter.
- A **linked file that does not exist** → error (existence check, imported).
- A **bundled file that nothing links to** → error (it can never load).

**And a probe (Phase 4), because the validator only proves the link is well-formed:** trip a predicate and assert the
reference was actually read — sde-agents does this for exactly one of its eleven routing rows and openly flags the
other ten as unverified. In the new fleet **every predicate row gets a canary**: a distinctive string in each
reference file, asserted to appear when its condition trips. That is the only thing that distinguishes "the model read
the file" from "the model guessed what was in it."

## Section 6 — Validation & maintenance machinery

- **Validator** (rewritten for Copilot artifacts): unknown-frontmatter-key rejection (the `hooks:`→`hook:` war story — a typo silently disarms), **kebab-case name enforcement** (silent load failure class), `agents:`/`handoffs:` targets must exist, description trigger-format lint (verbatim user phrasings — the one pattern with 3/3 baselines), bundle-reference existence, `plugin.json` manifest integrity, schema-vs-policy error separation, `--write-inventory` regenerating the README fleet table. Also imported from sde-agents' validator (found in the completion sweep): **doctrine enforced by machine** — canonical evidence-label phrasing and the required end-of-packet headings are validator checks, not conventions; the hook must resolve the guard through the plugin root; no definition may resolve a fleet file outside the plugin; validator tested against **broken-fleet fixtures** (evidence-drift, inventory-drift, missing-packet). Two-layer validation: the repo validator owns *fleet policy*; the platform's own validator owns the *platform contract* — **open question:** does VS Code ship a plugin-validate equivalent, or do the probes carry that layer alone?
- **Routing evals** (sde-agents format + sre-agents clean-room rig): overlap clusters, positives + **near-miss negatives** ("shares vocabulary, should route elsewhere"), graded deterministically off transcripts, reported as **rates over runs**, cases phrased to measure routing without spawning long sessions. Two refinements from the completion sweep: **negatives are cross-cluster positives** (one cluster's near-miss should route to another cluster's member — one case set nets the whole fleet), and routing evals run **manually, before/after description edits — never as a CI gate** (variance would flake-fail honest PRs; sde-agents documents this deliberately). Honest limitation carried forward: this measures **Claude Code as proxy** — nothing measures Copilot's actual routing today. **Open item:** evaluate Copilot CLI as a native headless probe.
- **Behavioral probes with canary strings** (plant a distinctive string in a skill; its appearance in output proves loading) + **tripwire tests guarding the canaries** (an innocent copy-edit would silently disarm the oracle).
- **Hook wiring tests** run the command string from `hooks.json` exactly as the runtime does — testing the script is not testing the hook.
- **CI**: the restored workflow extends to the new validator + tests. Anti-rot rule from the audit, now doctrine: **a skill never transcribes an artifact that lives in the repo — point at it.**

## Section 7 — Migration plan (phases; each independently valuable)

> **Ordering rule: the fleet is the product; the machinery protects it. Content first — and no phase that
> produces nothing.**
> Two earlier drafts got this wrong in opposite directions. The first put the machinery before the content, so the
> validator, the canaries, and the guard allowlist were all written against artifacts that did not exist yet — and
> every content decision churned them. The second over-corrected into a *spike phase* plus a *scaffold phase*, neither
> of which ships anything: the scaffold is `mkdir` and one `git mv` (minutes, not a phase), and the gate checks it
> fronted decide **which channel delivers the fleet, never what the fleet is** — the layout is identical either way,
> so asking them early buys nothing.
> What remains true is narrow: **exactly one platform fact can invalidate the design rather than cost a frontmatter
> edit** — whether `tools:` omission genuinely denies. That question is answered by the *first real agent*, not by a
> throwaway. Everything else that tests or guards content (canaries, routing evals, the allowlist, the validator) is
> written **after** the content it tests; the allowlist in particular is only knowable once you have watched `sre` and
> `observer` actually work.
> Content also carries standalone value: if distribution turns out policy-blocked, a finished fleet still ships via
> the fallback channel. A finished validator with no fleet is worth nothing.

**Phase 1 — THE AGENTS (5).** The first phase, and the first one that produces the product.

*Opens with the scaffolding, which is minutes of work, not a phase of its own:*
- `.claude-plugin/{marketplace.json,plugin.json}` — **one manifest location, no root duplicate** — plus empty `agents/`, `skills/`, `commands/`, `hooks/`, `.mcp.json`.
- **`git mv .claude/{agents,skills} legacy/claude-fleet/`** — *not cosmetic.* VS Code discovers skills from
  `.claude/skills/` **in any open workspace**, so leaving the old fleet in place means anyone opening this repo
  double-loads **37 old + 26 new** skills — the exact routing confusion the redesign exists to kill, at its worst
  during the phases used to judge whether it worked. Frozen, not deleted (git-recoverable). The
  `.claude-plugin/plugin.json` keeps the repo loadable in Claude Code (`--plugin-dir .`), which the owner uses and
  the routing-eval proxy needs.
- **`cp AGENTS.md CLAUDE.md legacy/claude-fleet/`** — **the root docs must be preserved *beside* the fleet, not left
  to git archaeology.** They sit at the repo root, so the `git mv` above does *not* capture them, and both are
  slated for rewrite-in-place (Appendix 2). But they carry content the new agent bodies must **absorb, not lose**:
  the stack profile, the roster and routing tables, the read-only-agent doctrine, the egress/trifecta census, the
  gate layering, and the shared conventions. A rewrite that silently drops them is exactly the failure this
  redesign exists to prevent. **Phases 1–3 mine `legacy/claude-fleet/AGENTS.md` while authoring; the rewrite of the
  live `AGENTS.md` happens last, once its content has a new home.**

*Then the five agents* — sde-agents bodies + doctrine layer + the delegation matrix, tool arrays, and model arrays
from Section 3.

**The blocking check rides on the first agent — no separate spike phase.** Author `reviewer` (`read`, `search` only)
**first**, load it in **VS Code Copilot**, and assert **four** things. "It couldn't run a command" is **not** a pass on
its own: that is equally consistent with the vocabulary being wrong and the agent getting **nothing at all**.

| # | Assertion | If it fails |
|---|---|---|
| 1 | `reviewer` **can read** a file | grants are not landing — the vocabulary is wrong. **Stop.** |
| 2 | `reviewer` **can search** | same. **Stop.** |
| 3 | `reviewer` **cannot run a shell command** | `tools:` omission fails **open**, so "read-only by tool absence" is dead and `reviewer`/`scribe` must be hook-guarded instead. **Stop and amend Section 5.** |
| 4 | `reviewer` **cannot delegate to `sde`** (ask it to) | `agents:` omission fails **open**: a read-only agent can spawn a `tools: all` one, and the read-only model is decorative by a *second, unguarded* route. **Stop.** |

Assertion 4 exists because this spec asserts *"default deny: an edge not listed here does not exist"* — the
**identical** fail-open assumption we correctly refused to make about `tools:`. The sister repo has direct precedent for
the class: a scoped grant like `tools: Bash(git diff:*)` *looks* like it narrows Bash and does nothing.

**Where it runs (a real dependency, previously unstated).** `--plugin-dir .` loads into **Claude Code**, which cannot
evaluate `.agent.md` frontmatter — so the check would never actually execute there. It must run in **VS Code
Copilot**. Stand up the **fallback channel** on one machine as part of the scaffold (`chat.agentFilesLocations` /
`chat.agentSkillsLocations` — both **GA, no admin needed**). Minutes of work, and it makes Phase 1's done-when
genuinely testable.

**Done when:** the five agents load and work against a real repo via `--plugin-dir .` (or the fallback channel).
**The fleet is usable here**, unguarded — and using it is what teaches Phase 4 the guard allowlist and the canary
prompts.

**Phase 2 — THE SKILLS (harvest + fix).** Direct imports (root-cause, eng-ladder, runbook, backend/frontend-craft,
ops-tooling) → SRE domain skills **with the audit's Tier-2 fixes applied — blue-green name rotation, the WQL `by`
deletion, SPL `timechart` bucketing, `cf auth` argv, error_budget severity, Grafana licence notes. Every fix is
specified in the removed `docs/AUDIT-2026-07-12.md` (git history); none may be ported as-is.** Confirm the Bamboo
decision, and the `adr` home (if plugins can't ship prompt files, `adr` becomes a skill — a one-line disposition
change, not a design change).

**Phase 3 — THE OBSERVABILITY SKILLS.** Six by-signal skills; LGTM references written; legacy references carried over
post-fact-check. **End of Phase 3 the fleet is content-complete:** 5 agents, 26 skills, working.

**Phase 4 — Machinery** *(written against artifacts that exist, and against usage observed in Phases 1–3 — no churn)*:
validator v2 · the allowlist hook (Section 5a — **seeded from what `sre`/`observer` actually ran**, not guessed) ·
hook wiring tests · canary + tripwire probes, one per real skill · routing evals rewritten for the real roster · CI
extension. The hook payload shape is probed here, where it is first needed.

**Phase 5 — Distribution** *(and only here do the org gates matter — they decide the channel, never the content, and
the layout is identical either way)*:
- **The three gate checks**, on one engineer's machine: `chat.plugins.enabled` flippable, or policy-blocked? The
  Copilot org **"Editor preview features"** policy? Are the named Claude **models** selectable under the team's
  license tier? *(Whatever the answers, the fleet built above still ships — plugin channel or fallback.)*
- `setup.ps1` + `-Verify`, the `release` ref and promotion gate, CODEOWNERS, README, the rollback runbook (Section 1).

**Phase 6 — Pilot:** one engineer, real work repos. Exit only on the Acceptance bar (Section 8) — not "fix what
reality finds."

**Phase 7 — Team rollout** (promote `main` → `release`), then retire `legacy/claude-fleet/` and the owner's personal
`~/.claude` duplicates (`root-cause`, `eng-ladder`, `runbook` — the shadowing the clean-room rig diagnosed).

### The routing-eval rig needs a decision, or Phase 4 deadlocks

The eval harness shells out to `claude -p` and reads which `Skill(...)` fired from stream-json — it measures **Claude
Code, as a proxy for Copilot**. Against the new Copilot-layout fleet it has nothing to load. **Decision:** keep
`.claude-plugin/plugin.json` in-repo (Phase 1 already does, for the owner) so Claude Code can load `skills/` from the
plugin root — the proxy keeps working at zero extra cost, and VS Code auto-detects the Claude plugin format anyway.
**Agent-level** routing cases have no proxy (`.agent.md` frontmatter is Copilot-only): they are **rewritten as
skill-level cases or dropped**, stated per case in the machinery ledger. The honest limitation stands — nothing
measures Copilot's *own* routing until the Copilot-CLI probe (open item) lands.

**Migration ordering rule** (imported): fix internal contradictions first — the one class of change needing no behavioral baseline.

**Implementation-plan format** (imported from sde-agents' plan doc, found in the completion sweep): dependency-ordered tasks with explicit **Interfaces** between them ("Task 5's probe asserts this path — do not rename it"); a **Global Constraints** block carrying machine-specific gotchas (on this machine: **Python is `py -3`, not `python3`** — bakes into setup.ps1, the validator shebang strategy, and CI matrix); **verbatim-move discipline** for content relocations (the plan names the section to move, never re-types it — re-typing invites silent transcription drift), **with one stated exception: bundled-file pointers are rewritten to Markdown-link syntax (Section 5d), because a verbatim port would faithfully preserve a bug that silently breaks every reference in VS Code**; and probes/tests written **first and failing** before the change that makes them pass — **scoped to the artifact under change.** That discipline governs each phase's *internal* task order (write the failing canary, then the skill); it does **not** mean writing the whole test suite before the whole fleet, which is the loop the ordering rule above forecloses.

## Section 8 — Acceptance: how we know it worked

The problem was quantified; success must be too. Without a bar, Phase 6 can't end and Phase 7 is a judgment call
dressed as a milestone — and "silent dark skills" (Risk 3) goes unmeasured, which is precisely how the old fleet rotted.

| Dimension | Bar | How measured |
|---|---|---|
| **No dark skills** | **0 of 24 model-invocable skills** fail to fire on their own on-target prompt | discovery canary per skill |
| **Side-effect skills load when called** | `pcf-deploy` and `service-onboarding` (both `disable-model-invocation`) load via `/sre-agents:<name>` and their canary appears | **invocation** canary. By design they *cannot* fire on a prompt, so a discovery bar over all 26 would be unsatisfiable and Phase 6 could never exit. |
| **Routing precision** | no near-miss negative fires **at all**; positives ≥ old-fleet clean-room baseline | cluster routing evals, rates over runs |
| **Fan-out** | a single incident prompt loads **≤ 2** fleet skills | routing eval with a `max_skills` assertion (the old fleet loaded **6**) |
| **Always-on context** | **≤ 4.5k tokens** before any work (was ~8.3k) — and **≤ 150 tokens per description**, so it cannot creep | measured in a real Copilot session |
| **Guard** | 0 false denies across the pilot; 0 silent load failures | `setup.ps1 -Verify` + hook audit log. The allowlist is *seeded from observed Phases 1–3 usage*, not guessed. |
| **Pilot exit** | one engineer, **one week** of real work touching **≥ 3 agents**, no unrecovered routing failure, no guard false-positive | pilot log |
| **Rollout safety** | any acceptance regression in week one → **revert `release`**, team announce | Section 1 rollback runbook |

**The token bar, honestly (an earlier draft said ≤3k, which this design makes impossible).** The always-on cost is
31 descriptions (26 skills + 5 agents) — and the discoverability fix *requires them to be longer*: verbatim user
phrasings plus boundary clauses are what makes a skill fire at all. Measured against the old fleet (37 descriptions,
avg 426 chars ≈ 106 tokens), 31 descriptions at the same length already cost ~3.3k, and with the added triggers
~4.0–4.6k. **So there is a real trade this design makes and must name: better routing costs context.** The structural
saving is not the descriptions — it is `AGENTS.md` + `CLAUDE.md` no longer being injected into every session
(−4.3k). Net ~8.3k → ~4.5k, a ~45% cut, with the routing failure mode fixed rather than traded away. A bar set below
what the roster can achieve would simply be ignored.

## Section 9 — Ownership and lifecycle

**Ownership.** The fleet needs a named maintainer — the person who gets pinged when an update breaks the team.
**OWNER DECISION, not a builder guess: CODEOWNERS, the README, and the rollback announcement all block on this name.**

**CODEOWNERS — protect everything that executes on a teammate's machine, *and* the gate that protects it:**
`.claude-plugin/` | `hooks/` | `scripts/` | `.mcp.json` | **`.github/`** | **`skills/*/scripts/`** | **`skills/*/assets/`**.
The last three were missed, and each is a live hole:
- **`.github/`** — the CI workflow **is** the `main` to `release` promotion gate. An unreviewed edit to it neuters the
  gate protecting everything else on this list. That is the audit's own through-line — *"a check that reports success
  without executing the thing it names"* — reproduced one layer up.
- **`skills/*/scripts|assets/`** — a top-level `scripts/` glob does **not** match them, and the fleet ships executable
  content *inside* skill folders (`obs-alerting/scripts/error_budget.py`, `pcf-ops/scripts/triage.{sh,ps1}`,
  `ops-tooling/assets/cli_skeleton.py`). Same bundle, same machines, unprotected path.

**`release` branch protection must forbid force-push.** The marketplace pins a *branch* (`ref: release`), not a `sha`,
so the pin is only as strong as the protection on that branch.

**Contribution: personal-first, promote-by-PR.** Teammates build in `~/.copilot/{agents,skills}` (VS Code reads them
per-user, so this is free). When a second person wants one, it graduates into the fleet by PR. This is **repo policy in
CONTRIBUTING**, not merely content the `agent-authoring` skill teaches.

**Renames and version skew.** Engineers pull on their own 24h cycle, so **the team is never all on the same fleet
version** — an operational fact, not a bug. Consequence: mid-incident, one teammate may be on `/incident-severity`
while the runbook says `/incident-command`. Rules:
- A rename ships with a **one-release stub** at the old name whose description redirects to the new one.
- Renames on the **incident path** need a team ack before merge.
- The marketplace's `renames` map handles *plugin* renames automatically — **not skill renames**, which is why the
  stub is needed.
- Onboarding states the ≤24h skew explicitly, and `Extensions: Check for Extension Updates` forces a pull.

## Glossary (terms this spec uses that are not self-evident)

- **Clean-room rig** — `evals/clean_room.py` (merged in PR #52). Runs an eval trial with `CLAUDE_CONFIG_DIR` relocated
  so the operator's personal `~/.claude` skills/agents/plugins can't compete with the fleet for discovery. It proved
  every pre-2026-07-13 baseline described *the laptop*, not the fleet — and that the contamination cut **both ways**
  (it suppressed `sde-ladder` and *flattered* `sre-ladder`).
- **Shadowing** — the above: a personal global skill out-competing a fleet skill of similar purpose.
- **The audit** — removed `docs/AUDIT-2026-07-12.md` (git history only). Five parallel reviewers, every load-bearing
  claim hand-reproduced. Source of every "audit fix" this spec names.
- **Dark skill** — a skill that never fires on its own on-target prompt (`saw: none` in a probe). The old fleet had four.
- **Trifecta / lethal trifecta** — an agent holding all three of: sensitive data · untrusted input · egress. Any one leg
  broken defeats a prompt injection. See Section 5c.
- **Ralph** — an unattended agent-loop pattern (`scripts/ralph-loop.sh`) the old `self-improve-loop` skill taught.
  Claude-Code-specific; deleted (Machinery ledger).
- **Canary / tripwire** — a distinctive string planted in a skill; its presence in a transcript proves the skill loaded.
  A *tripwire test* guards the canary so an innocent copy-edit can't silently disarm the probe.

## Explicitly deferred / out of scope

- GCP skills (trigger: onboarding becomes real → `references/gcp.md` additions)
- Extension packaging (trigger: #304721 closes + private channel exists)
- Enterprise-managed plugins / org-level anything (trigger: org adoption)
- Copilot-native routing measurement (open research; CLI probe candidate)
- Old-fleet content named **deleted** in either ledger (Appendix 1 = agents/skills, Appendix 2 = machinery). Nothing is dropped by silence — the catch-all is gone.

## Risks (ranked) and open questions

1. **Agent plugins are Preview** — format churn could break the team at once. Mitigations: identical-layout fallback channel; probes catch loading regressions; pin plugin versions if churn appears.
2. **`chat.plugins.enabled` org-policy-blocked** — fallback channel exists, identical layout; checked in Phase 5, because it changes the channel and never the content.
3. **No Copilot routing measurement** — descriptions are grounded in the one measured pattern (verbatim triggers) and the Claude proxy; risk of silent dark skills recurring. Probe + canary loading checks partially cover.
4. **Hook payload details under-documented** — probed in Phase 4. **Two different failures, two different rulings**
   (an earlier draft had this contradicting Section 5b): the guard **fails closed** on a *command* it cannot parse; it
   **no-ops with a loud audit line** on an *agent* it cannot identify (5b explains why — a hook that denies the user's
   own session gets uninstalled, trading a permanent guard for a temporary one). **That audit line has a reader:**
   `setup.ps1 -Verify` exits non-zero if the hook log contains an identity-missing entry, which is what makes Section 8's
   "0 silent load failures" measurable rather than aspirational.
5. **Reviewer merge could dilute security reviews** — watch review outputs during pilot; split is one file if needed.

## Provenance summary

- **sre-agents contributes:** domain content (PCF, obs queries, incident process, gates, DB reliability), the clean-room eval rig, the restored CI, the audit's factual fixes.
- **sde-agents contributes:** the agent chassis (reviewer/sde bodies), the doctrine layer (packets + worked examples + verification labeling), allowlist guard philosophy + positive-ALLOW protocol, Tier 0–3 change authority, service-onboard/lab-audit shapes, eng-ladder, root-cause, backend/frontend-craft, canary probes, tripwire tests, cluster routing evals, validator hardening patterns, "no second source of truth."
- **New:** plugin packaging, six by-signal obs skills, LGTM references, stack-profile, setup.ps1, Copilot-native validator/hook/probes.

## Appendix — Disposition ledger (every existing unit, old → new)

Verbs: **survives** (ported, possibly renamed/fixed) · **merges into** (content combined with another unit) · **reference under** (demoted to a `references/` file, loaded on demand) · **dissolves** (replaced by a native platform mechanism) · **deleted** (content dropped; recoverable from git history).

### Skills (37 → 26)

| Old skill | Disposition |
|---|---|
| adr-template | → **prompt file `adr`** (template asset kept) |
| agent-authoring | survives, rebuilt on the sde-agents method (prompt-craft/prompt-engineer) |
| agent-security | survives, rewritten Copilot-native; per-agent census dropped (anti-rot: point at `tools:` frontmatter, not prose) |
| api-design | → reference content under **backend-craft** (`references/stack.md` work rewrite; OpenAPI asset rides along) |
| bamboo-to-actions-migration | **deleted** (default; prompt file only if live migrations remain — Phase 3 confirms) |
| blameless-postmortem | survives as **postmortem** (renamed) |
| context-engineering | → reference under **agent-authoring** |
| craft | survives as-is (per-language references) + gains process references from safe-refactor/tdd-workflow |
| database-reliability | survives |
| debug-rca | **replaced by root-cause** (sde-agents; measured routing winner) |
| github-actions-ci | survives as **ci-actions** (`cf auth` argv leak fixed) |
| grafana-dashboards | merges into **obs-dashboards** (Grafana 13 rewrite; Enterprise-plugin licensing facts added) |
| handoff-protocol | **dissolves** → `handoffs:` frontmatter + packet templates in agent bodies (SHA-pinning + taint doctrine woven in) |
| incident-severity | survives as **incident-command** |
| instrument-service | → OTel reference under **obs-pipeline** |
| merge-gate | survives (AGENTS.md-duplication cut; severity rubric added per audit) |
| moogsoft-correlation | → reference under **obs-alerting** |
| ops-cli | → CLI reference under **ops-tooling** |
| ops-stack-integration | → reference content under **backend-craft** (`consuming-apis` + stack) |
| pcf-deploy | survives (blue-green name-rotation fix; stays `disable-model-invocation`) |
| pcf-ops | survives (audit-clean) |
| production-change-gate | survives (+ Tier 0–3 model; branch-protection check already merged) |
| release-gate | survives |
| rollback-mitigation | merges into **incident-command** (the reversible-action decision table) |
| route-request | **dissolves** → native model-initiated delegation + `agents:` allowlists |
| runbook-template | merges into **runbook** (sde-agents body; this template becomes its asset) |
| safe-refactor | → process reference under **craft** |
| sde-ladder | merges into **eng-ladder** (sde-agents base) |
| self-improve-loop | **deleted** (Ralph/Claude-specific machinery; its move-failures-left principle survives in agent doctrine) |
| slo-error-budget | merges into **obs-alerting** (burn-rate patterns; `error_budget.py` ported with severity fixes) |
| spa-architecture | → reference content under **frontend-craft** |
| splunk-triage | → SPL reference under **obs-logs** (3-sigma bucketing fix applied) |
| sre-ladder | merges into **eng-ladder** (responder/investigator/elite as the SRE-track tier references) |
| tdd-workflow | → sde agent body (tests-first discipline) + process reference under **craft** |
| thousandeyes-network | → synthetics reference under **obs-alerting** |
| tool-design | → reference under **agent-authoring** |
| wavefront-queries | → WQL reference under **obs-metrics** (fabricated `by`-clause fixed) |

### Agents (9 → 5)

| Old agent | Disposition |
|---|---|
| sde-engineer | → **sde** (chassis replaced by sde-agents `sde-fullstack`; domain content carried) |
| code-reviewer | → **reviewer** (chassis: sde-agents `code-reviewer`) |
| security-reviewer | merges into **reviewer** (its threat lens = review dimension 2; split back is one file if pilot shows dilution) |
| test-engineer | **deleted** (tool scope identical to sde; testing method → sde body; untrusted-code refusal doctrine kept) |
| sre-engineer | → **sre** (+ Tier 0–3 change authority; compromise-handling rules kept) |
| sre-monitor | → **observer** (+ "never cut the branch you're sitting on") |
| runbook-author | → **scribe** (loses `execute` entirely — cleaner than the guard it wore) |
| researcher | **deleted** (native `web` tool + subagents; also held the fleet's widest egress) |
| prompt-engineer | **deleted as agent** → **agent-authoring** skill carries the method |

Count check: survivors + merges + new = 26 skills (roster table, Section 4); 5 agents (Section 3). Nothing in the old fleet is unaccounted for.

## Appendix 2 — Machinery ledger (everything that is not an agent or a skill)

The first ledger claimed "nothing in the old fleet is unaccounted for" while covering only the 37 skills and 9 agents.
That claim was false: the machinery, the eval corpus, the root docs, and the in-skill assets were all unnamed — and the
"Explicitly deferred" catch-all would have **deleted them silently**. Same verbs as Appendix 1.

### Evals (the largest omission — 70 case files)

| Item | Disposition |
|---|---|
| `evals/discovery/*.yaml` (**45 cases**) | **Rewritten, not ported.** Every case names an old skill/agent (`craft-sde-ladder`, `agent-sre-engineer`). Rewrite one per surviving unit as the **canary set** that Section 8's "0 dark skills" bar is measured against. The 2 unpassable cases (`disable-model-invocation` targets) are **deleted** — they measure the flag, not discovery. |
| `evals/scenarios/*.yaml` (**25 cases**) | **Port per surviving unit.** These are the behavioral regression tests — the gates' blocking behavior, injection refusal, handoff taint. Section 4 justifies keeping three separate gates *because they "eval'd well separated"*; dropping their evidence machinery would gut that argument. Cases for deleted units (`researcher`, `route-request`) are deleted with them. |
| `evals/clean_room.py` | **Survives, load-bearing.** Merged PR #52; it is what makes any eval number trustworthy. |
| `evals/run_evals.py`, `discovery_probe.py`, `graders.py` | **Survive, adapted.** They drive the Claude-Code proxy (Section 7). Graders gain the `max_skills` fan-out assertion (Section 8). |
| `evals/test_graders.py`, `test_discovery_probe.py` | **Survive** — including the adversarial `_BLOCK_CASES` the audit's Tier-1 #3 hardened. |
| `evals/README.md` | **Rewritten** for the new rig; keeps the "manual, never a CI gate" discipline. |

### Scripts, CI, hooks

| Item | Disposition |
|---|---|
| `scripts/readonly-guard.py` + `readonly-guard-hook.sh` | **Replaced** by the Copilot allowlist hook (Section 5a). The denylist is not ported — twenty-plus fix commits and a still-live `-m pip` bypass are the argument. Old files deleted in Phase 4. *(An earlier draft kept them to "guard `legacy/`" — dead reasoning: after the Phase-1 `git mv` out of `.claude/`, nothing loads the legacy agents, so there is nothing to guard.)* |
| `scripts/test_readonly_guard.py` | **Rewritten** for the allowlist. Keeps the launcher + fail-closed cases (they exist because the guard once shipped silently dead on Windows). |
| `scripts/validate_fleet.py` | **Rewritten** = validator v2 (Section 6). |
| `scripts/ralph-loop.sh` | **Deleted.** Claude-Code-specific unattended-loop machinery; its owning skill (`self-improve-loop`) is deleted, and nothing in the Copilot fleet drives it. |
| `.github/workflows/validate.yml` | **Survives, extended** to validator v2 + the new tests. Gains the `main` → `release` promotion gate (Section 1). |
| `requirements-dev.txt` | **Survives.** Machine constraint: on Windows `python3` is the Microsoft Store stub, not an interpreter — use `python` or `py -3`. **Moot in practice:** every gate goes through `scripts/gate_a.py`, which re-invokes its sub-steps under `sys.executable` and is therefore correct under all three. Don't reintroduce a hardcoded interpreter name. |

### Root docs

| Item | Disposition |
|---|---|
| `AGENTS.md` | **Preserved to `legacy/claude-fleet/` in Phase 1 before any rewrite** (see Phase 1 — it is at the repo root, so the fleet `git mv` misses it, and its content must be *absorbed* into the new agent bodies, not lost). Then **split — it has two roles the spec previously conflated.** (a) *Shipped fleet context* → **dies** (its stack profile becomes `stack-profile`; its roster/routing become native `agents:`/`handoffs:`; its egress census becomes Section 5c). (b) *This repo's own project instructions*, for people working **on** the fleet → **survives, rewritten** and much shorter. Note VS Code also reads `AGENTS.md` from any open workspace, so it must not carry shipped-fleet content once the plugin exists. |
| `CLAUDE.md` | **Preserved to `legacy/claude-fleet/` in Phase 1**, then **survives, minimal** — the Claude Code entrypoint for developing the fleet (`@AGENTS.md`), matching the sister repo's convention. |
| `README.md` | **Rewritten** — install (marketplace + the trust prompt), the maintainer name, `--write-inventory` fleet table. |
| `docs/RESEARCH.md` | **Survives, updated** — retarget from Claude Code sources to the VS Code/Copilot doc set (the five pages this design is built on). |
| `docs/AUDIT-2026-07-12.md` | **Later removed** — was the evidence base for every "audit fix" in Appendix 1; retained in git history only. |
| `docs/superpowers/{specs,plans}/` | **Survive** — decision history (this document included). |
| `LICENSE` | Survives. |

### In-skill assets and references (the strays)

| Item | Disposition |
|---|---|
| `ops-cli/assets/cli_skeleton.py` | → asset under **ops-tooling**. |
| `api-design/assets/openapi.starter.yaml` | → asset under **backend-craft**. |
| `pcf-deploy/assets/*`, `github-actions-ci/assets/*` | Survive with their skills (CI asset gains the `cf auth` fix). |
| `runbook-template/assets/*`, `adr-template/assets/*` | → assets under **runbook** and the `adr` prompt file. |
| `route-request/references/fan-out.md` | **Deleted** with `route-request` — but its cost model (fan-out ≈ 15× tokens; right-sizing band) moves into **agent-authoring**'s multi-agent reference. |
| `sre-ladder/references/golden-signals.md` | **Survives** → reference under **eng-ladder** (SRE track). *(Named because the first ledger listed only the three tier files and would have dropped it.)* |
| `craft/references/{python,bash,powershell,go,typescript,react}.md` | Survive under **craft** — **but see the boundary note below.** |
| `pcf-ops/{references,scripts}/*`, `splunk-triage/references/*`, `wavefront-queries/references/*`, `grafana-dashboards/references/*`, `moogsoft-correlation/references/*`, `thousandeyes-network/references/*` | Survive as the per-backend references of the six by-signal obs skills. `pcf-ops/scripts/triage.{sh,ps1}` survive (human-run). |
| `slo-error-budget/scripts/error_budget.py` | **Survives with fixes** → **obs-alerting** (severity ladder + window-pair binding; audit Tier-2 #4). |
| `agent-authoring/references/*`, `sde-ladder/references/*`, `route-request/references/*` (others) | Fold per Appendix 1. |

### Two skill boundaries that must be pinned (or they become the next six-skill pile-up)

Routing confusion is failure mode #1; only one boundary (data-viz vs obs-dashboards) was pinned. Two more overlap:
1. **`craft` vs `backend-craft`/`frontend-craft`.** `craft` = *per-language* conventions (Python/Bash/PowerShell/Go/TS/React).
   `backend-craft`/`frontend-craft` = *per-layer* design (contracts, resiliency, layout, state). **Decision: `craft` keeps
   only the languages the layer skills don't cover** — Python, Bash, PowerShell, Go. **Its `react.md` and `typescript.md`
   are deleted**, since `frontend-craft` owns that layer whole. Each description states the split.
2. **`backend-craft/references/persistence.md` vs `database-reliability`.** persistence = *writing* the data layer
   (drivers, pools, migrations, transactions). `database-reliability` = *operating* it (slow queries, lock contention,
   replication lag, connection-pool exhaustion during an incident). Build vs. debug. Both descriptions say so.
