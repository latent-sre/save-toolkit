# Sibling-repo adaptation — `latent-sre/sde-agents` → `save-toolkit`

**Date:** 2026-08-05
**Scope:** A deep two-way scan of this fleet against the sibling `latent-sre/sde-agents` fleet
(scanned at commit `528fb7d`, "ledger/drift-reachability", 2026-08-04), adopting the improvements
that fit this repo's stack and recorded decisions. No new agents were added; the roster stayed at
eight. This is a dated evidence record, not a live task list — the only live tracker is
[`fleet-roadmap.md`](../fleet-roadmap.md).

The two fleets forked from a common ancestor and diverged: theirs went deeper on craft references,
per-task learning cadence, and a large structural validator; ours went deeper on evidence-label
rigor, gates, guarded-Bash safety, observability, and PCF/production operational safety. The scan
mined theirs for what ours lacked while protecting the places ours is stronger.

## Adopted in this pass

### Guard hardening (`scripts/readonly-guard.py`, `scripts/test_readonly_guard.py`)

Nine allowlist bypasses that let a read-only agent (`sre`/`observability-engineer`) write files or
execute code were confirmed live against our guard and closed, each added to the deny corpus first:

- `sort -o`, `tree -o`, `less -o` (and `less`'s interactive exec) — write channels with no shell
  redirect; removed from `_SIMPLE_READERS`.
- `ag` — documents `--pager COMMAND` (an exec lever) and is redundant with `rg`/`grep`; removed.
- `rg --pre` / `--hostname-bin` / `--search-zip` / `-z` — run an external program mid-search; gated
  by `_RG_EXECUTION_FLAGS` and a new `rg` dispatch branch.
- `git grep -O<CMD>` / `--open-files-in-pager` — pager execution; gated by `_GIT_READ_EXEC_FLAGS`
  plus an explicit `-O`-prefix reject (the attached short form the `split("=")` test can't see).
- `git help -w`/`-i` — launches a browser/info reader; `help` removed from `_GIT_READ`.
- `gh ... --web`/`-w` — launches `$BROWSER`; gated by `_GH_EXECUTION_FLAGS`.

`git check-ignore` was added (a genuine, clean-surfaced review read). And **GOV-001** — a truncated
guarded payload flipping from deny to allow because `except: _allow()` vouched for unparseable
input — is fixed with `EXIT_INDETERMINATE = 44`: malformed input and non-dict envelopes now exit
indeterminate, so the hook falls through to its blanket deny rather than certifying the payload.

### Validator rules (`scripts/validate_fleet.py`)

Six silent-disarm tripwires added, all currently green on the real repo:

- A `Bash`-holding agent with no write tool that is **not** on the guard roster now fails (its
  read-only posture would otherwise be an unenforced promise) — the high-value reverse of the
  existing forward check.
- The guard's own `GUARDED_AGENT_NAMES` and the generator's `GUARDED_AGENTS` must name the same
  agents (two independent literals nothing previously compared).
- A guard-roster entry that resolves to no real agent now fails (a typo would silently guard
  nobody).
- The guard's `PLUGIN_NAME` must equal the manifest `name` (a rename that misses it disarms the
  namespaced-`agent_type` match).
- A scoped grant on a non-`Agent` tool (`Bash(git diff:*)`) now fails — the runtime ignores it, so
  it is a limit that looks real and isn't.
- Duplicate tool grants fail; and the evidence-label triad is now all-or-nothing (dropping
  `[sourced]` while keeping `[verified]`/`[unverified]` is rejected).

### Structural gate (`scripts/gate_a.py`)

`test_check_links.py` (236 lines) had been authored and wired into **nothing** — Gate A's
hand-kept step list omitted it and no other runner reached it. Gate A's `test_*.py` steps are now
glob-derived from `scripts/test_*.py` and `evals/test_*.py`, so a new test file enrolls itself and
this drift class cannot recur. Non-test structural steps stay explicit and ordered.

### Eval runner (`evals/run_evals.py` and tests)

Direct-skill scenarios now prove the skill actually fired (not merely that text arrived); negative
routing cases are zero-tolerance regardless of `--threshold`; the summary records measurement
`conditions` (timeout, trials, threshold, selection) so two runs are comparably documented; and a
batch spanning more than one resolved model warns loudly.

### Content lifts into existing agents and skills

No descriptions were edited (routing evals need live API runs). Body/reference content only:

- `agents/sde.md` — findings-response protocol (severity order, evidence-backed pushback,
  entangled/independent split, usage-check before "implement it properly", anti-sycophancy), the
  Findings-response packet slot with packet right-sizing, the "whatever's best" default clause, the
  altitude-doesn't-move clause.
- `agents/reviewer.md` — invariant-comment findings (Read/Grep-reachable) and revert-as-data
  request without adding Bash; integrity rules recast as a rationalization table for our
  no-execution posture.
- `agents/researcher.md` — answerable-question reframing, deterministic-read rule, a worked
  example; `agents/repository-investigator.md` — "start at the execution surface".
- `skills/language-idiom/**` — richer bash/python/go/tdd/safe-refactor references and the two
  universal rules; `skills/backend-craft` — endpoint failure matrix, sunset protocol, rate-limit
  headers; `skills/ci-actions` — SHA cooldown, image-digest vs commit-SHA, fork-secret split,
  timeouts, pinned runner, cache hygiene; `skills/root-cause` — in-loop hypothesis table, cheapness
  ranking, bisect, fix-at-origin, three-strikes ownership; `skills/postmortem` — evidence-for-no-
  data-loss, detection-source-is-a-finding, artifact-per-action, near-miss write-ups;
  `skills/frontend-craft` — new React/Vue references with detection predicates, interface-copy and
  keyboard-pass gates; `skills/obs-alerting` — last-success-timestamp staleness alerting and a
  verify-before-done gate; `skills/eng-ladder` — ownership-vs-consult and score-against-remit;
  `skills/agent-security` — the cut-a-leg menu, cross-handoff trifecta, five-question review.

## Protected — where this fleet is stronger and was not regressed

Our allowlist-not-denylist guard design, its plugin-rename and field-rename canaries, transactional
adapter writes, TOCTOU-safe Codex installer, clean-room allowlist env with runtime-boundary
enforcement, evidence-label default blockquotes, the taint-propagating handoff packet, gates as
separate skills, the six-skill observability set, `database-reliability`, and `check_plan_status.py`
enforcement all stayed as-is.

## Deliberately not ported

- **`effect_broker.py` and `run_state.py`** — these are the sibling's implementations of our own
  deferred `EFFECT-001` and `STATE-001`, whose roadmap entries explicitly say not to import a broker
  or state store before a named consumer exists.
- **The hook raw-JSON `case "$IN"` prefilter** — our repo forbids it by enforced rule
  (`generate_platform_adapters.py`, `test_hook_wiring.py`): it would bypass the Python identity
  canary. Our blanket-deny-on-unavailable design is the stronger posture.
- **The learning-ledger store** (`learning/candidates/*.json`, `learning_ledger.py`) — a large,
  single-writer, lock-file surface whose analog here (`operational-learning` + the parked
  fleet-improvement lifecycle) already carries schema-versioned packets. The transferable *ideas*
  (a drift watch over promoted candidates, forward freshness deadlines) are recorded as roadmap
  work, not the storage.
- **`.claude/agents` Codex `/import` staging** — would register the fleet twice (bare + namespaced)
  in every session and manufacture the contamination the sibling's own isolation probe warns of.
- **Homelab skills** (`lab-audit`, `lab-incident`, `host-onboard`, `upgrade-campaign`,
  `security-audit` as a running-lab sweep) and the Tier-0..3 change vocabulary — structurally
  incompatible with our PCF/human-release-owner gate model.
- **The four-command validate block** transcribed into their `AGENTS.md`/PR template — ours points
  at the single `gate_a.py` entrypoint by design.

## Second pass — bundle-level sweep (references, assets, agents)

A follow-up deep sweep compared every `references/`, `assets/`, and schema file on both sides, plus
the sibling's agents, for content the first (prose-level) pass missed:

- **`skills/backend-craft/references/fastapi.md`** (new) — the Python + FastAPI stack-mechanics
  reference we lacked entirely, the backend mirror of the react/vue frontend gap: app-factory
  lifespan, `pydantic-settings` validate-at-startup, `response_model` allowlist, authn/authz DI
  split, service-layer `IntegrityError`-not-precheck, async-all-the-way, ASGI integration tests.
  Cross-references retargeted to our layout (migrations point at `save-toolkit:database-reliability`,
  which we own as a skill rather than a backend reference).
- **`skills/agent-authoring/references/`** — enriched `claude-code-frontmatter.md` with newer probed
  platform facts (`${CLAUDE_PLUGIN_DATA}`, `CLAUDE_ENV_FILE` for SessionStart, the plain-scalar
  `description:` parser trap that can fail `claude plugin tag`, the platform listing cap noted
  against our tighter 1024-byte validator rule), all time-stamp-labeled; added a JIT-overuse
  counterbalance and a symptom→cause table to `context.md`, a tool-sprawl heuristic to `tools.md`,
  and a multi-agent pattern catalog plus a wrapper-layer failure taxonomy to `roster.md` (adapted
  from the sibling's `multi-agent-architect`, whose remit we do not adopt as an agent).
- **`skills/ops-tooling/`** — from the sibling's `sre-tool`: right-sizing as an explicit early exit,
  spawn-capable degradation (inline self-review never counts as the gate — name it blocked /
  inconclusive), review quality judged by coverage not finding count, contested-finding
  reconciliation, and "what the handoff omits, the agent will improvise", plus additive CLI and
  multi-component reference material. The sibling's `run_state.py` control-plane paragraph was not
  ported (we do not ship that script).

Confirmed strictly stronger and left unchanged: our obs-* six-pack over their five obs references,
our seven-rung `eng-ladder` over their three, our `frontend-craft/auth.md` and `consuming-apis.md`
over their trimmed versions, and our versioned schemas (`schemas/`, the knowledge-update pair) —
the sibling ships no schemas at all. The learning-system method port (`self-improve-loop`
references, the ledger, `research-basis.md`) remains deferred to `ADAPT-001`: it maps onto our
scribe-bundle-validated `operational-learning` and the parked improvement-lifecycle, and its
transferable half is already scoped there.

## Follow-on work

Captured as roadmap item `ADAPT-001`. The larger sibling ideas worth a later, bounded pass —
a promoted-candidate drift watch, forward freshness/retention deadlines on knowledge packets,
AGENTS.md path/import drift enforcement in `check_links.py`, a `RETIRED_GENERATED_ROOTS` check, and
CRLF-independent adapter generation — are recorded there with their evidence, not started here.
