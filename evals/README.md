# Fleet evals

Behavioral evals for the agents + skills — the layer above the structural gate
(`scripts/gate_a.py`, which only checks structure/spec). These check that the fleet *behaves*: that a request routes
to the right place, a gate blocks what it should, and an agent treats untrusted content as data.

Built on Anthropic's eval shape (["Demystifying evals for AI agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)):

- **Task** — a scenario file in `scenarios/*.yaml`: a `prompt`, human-readable `success_criteria`, and
  machine `graders`.
- **Trial** — one attempt. Model output varies, so run several (`--trials`, default 3) and aggregate.
- **Grader** — scores the **outcome** (what the response decided), *not the path taken*. Prefer the
  deterministic graders in `graders.py`; add a model-based judge only for genuinely subjective quality.

## Run it

```bash
python3 -m pip install -r requirements-dev.txt   # one-time: the eval harness needs PyYAML
                                                 # (the fleet validator + guard tests are stdlib-only)
python evals/run_evals.py --validate     # check the suite itself (no model) — the CI-safe gate; wire into CI or run locally
python evals/run_evals.py --list         # show scenarios
python evals/run_evals.py --run          # invoke the fleet and grade (needs a Claude-enabled runner)
```

`--run` shells out to `"$CLAUDE_BIN" -p <prompt> --plugin-dir <repo>` (default `claude`) in a
**fresh process per trial** — a fresh session so leftover authoring context can't mask gaps. Swap
`run_agent()` in `run_evals.py` for the Agent SDK if you'd rather drive it programmatically.

## Discovery (routing *without* a target hint) — retired, re-author against the shipped fleet

`run_evals.py` prepends `"(Use the <target> skill/agent.)"` to every prompt, so it grades the
**outcome given the right skill** — it cannot tell you whether the model *discovers* the right
skill on its own. A discovery probe (`discovery_probe.py` + `discovery/*.yaml`) used to fill that
gap, but the whole set was authored against the retired legacy fleet and was removed in the
2026-07 cleanup — recoverable at tag `pre-cleanup-2026-07-15`, along with its measured baselines.
Re-author both the probe and its scenarios against the canonical plugin (`agents/`, `skills/`) when
discovery measurement is needed again.

## The clean room (and why a baseline states its namespace)

Every trial runs with `CLAUDE_CONFIG_DIR` pointed at a temp dir holding only your credentials
(`evals/clean_room.py`) while `--plugin-dir` loads this repository explicitly. The model therefore
sees this plugin and **nothing else** from the operator's personal agents, skills, installed plugins,
or global `CLAUDE.md`.

This is not tidiness. Those things do not shadow the fleet by name; they **compete with it for
discovery** — the property a discovery probe exists to measure. Before the clean room, every
number the retired probe produced was a property of the machine it ran on — and every baseline
note said so ("treat as a LOWER BOUND").

**A baseline note must state the namespace it was taken in.** A number without one is not a
baseline. Notes marked `namespace: CONTAMINATED` predate the clean room and are not comparable to
clean numbers.

The harness **aborts** if it cannot authenticate. It does not degrade: a credential-less run still
emits a well-formed trace containing no `Skill()` call, which would score as a clean no-route —
turning a broken instrument into a fake finding about the fleet. (If you authenticate via
`ANTHROPIC_API_KEY`/Bedrock/Vertex instead of `/login`, there is no `.credentials.json` to copy at
all — the clean room detects this and yields an empty config dir; isolation is unaffected.)

**Run clean trials from a throwaway git worktree**, not your working checkout — the same mandate
`--agents` already carries. `CLAUDE_CONFIG_DIR` isolates `~/.claude`, but Claude Code also reads
`.claude/settings.local.json` from the **CWD** on every invocation, regardless of `CLAUDE_CONFIG_DIR`.
That file is untracked and usually benign (Bash allow-rules today), but it can carry `env`, `hooks`,
and plugin keys — operator-machine state inside the "clean" namespace. `clean_env()` prints a WARNING
(not a refusal) if it finds one; a throwaway worktree avoids the question entirely.

## Discipline (how to add a scenario)

1. **Eval before docs — for skills with a *gradeable* outcome.** When writing/changing a skill whose
   behavior is deterministic and checkable — a gate that must BLOCK, a guard that must DENY, a routing
   decision, an injection it must refuse — add ≥1 scenario that fails without it first. For prose-quality
   skills (e.g. `craft`, `api-design`, `runbook-template`) a keyword grader can't judge quality, so a
   scenario is **optional**, not mandated — don't write a tautological eval just to satisfy a rule.
2. Grade the **outcome**, not the trajectory — don't require a specific tool order.
3. Keep graders deterministic where you can; if you need a judge, calibrate it against a few hand-graded
   cases before trusting it.
4. Read a transcript occasionally even when graders pass — confirm the agent got there legitimately.

## Graders available (`graders.py`)

`contains_all` · `contains_any` · `not_contains` · `regex` · `not_regex` (passes iff the pattern does
*not* match — used for "must not propose to act" checks). Each scores the response text and returns
`(passed, detail)`. Add new ones to the `REGISTRY`. The graders and the stream-json parser are
unit-tested offline (run them in CI or locally): `python evals/test_graders.py` (includes adversarial
should-fail verdicts — e.g. a `BLOCKED … does not pass` that must not score as PASS).

> The bundled graders are keyword/structural proxies — fast, deterministic, and good at catching
> "it routed to the wrong agent" or "it complied with an injection." They do **not** judge prose
> quality; that's a deliberate trade for CI-stability. Layer a model-based grader where nuance matters.
