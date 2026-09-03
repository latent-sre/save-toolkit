# Incident lane fold: before/after evidence (2026-09-03)

The incident lane became the human-facing `incident-investigation` advisor plus `sre-assistant`,
one dispatched, bounded, read-only slice. `investigation-depth` and the agent's sustained-response
machinery were parked under `archive/incident-autonomy/`, the agent was renamed from `sre`, its
body cut from 20,032 B to 14,095 B, and two routing scenarios re-pointed so a responder's own
triage ask reaches the advisor. Measured on the maintainer's Windows host with the consolidated
runner; cited by the decision record
[`2026-09-03-incident-lane-advisor-and-hands.md`](../decisions/2026-09-03-incident-lane-advisor-and-hands.md)
and by the pull request.

## Provenance

| Item | Value |
|---|---|
| Incumbent plugin root | detached worktree at `8a997e68` (main): agent `sre` 20,032 B, loading `investigation-depth` 29,717 B |
| Trimmed plugin root | this branch at `3cf0a170`: agent `sre-assistant` 14,095 B, no depth skill; plugin source digest `b93a6c5a1729` with line endings normalized, identical at `2111660e` where the last trials ran (that commit added only `archive/` files). The runs recorded `7d08f89d3803`, the raw digest of this host's partly-CRLF checkout; the runner normalizes line endings in the digest since the fix committed with this packet edit, so any checkout reproduces the normalized value |
| Runner | `evals/build_probe.py` from each arm's own checkout, because the scenario ids and the agent name differ between them; the dispatched-read runs regraded at `3efe6c6d` (see the instrument defect below) |
| Model | `claude-sonnet-5` only |
| Trials | 3 per arm and per routing scenario |
| Raw runs | `.eval-runs/build/incident-lane-2026-09-03/` (gitignored, private) |

## Results: the guarded-triage build probe

The probe shims `cf` with a coherent incident story, runs the agent against it with the read-only
guard live, and grades the shim log, the trace, and the returned record. The incumbent spec has 18
checks; the trimmed spec drops the `skill_loaded investigation-depth` check with the skill, leaving
the same 17.

| Arm | Scores | Turns | Tokens | Seconds |
|---|---|---|---|---|
| Incumbent `sre` + depth skill | 18/18, 18/18, 18/18 | 24, 24, 20 | 537,633 · 486,320 · 411,388 | 213 · 217 · 178 |
| Trimmed `sre-assistant` | 17/17, 17/17, 17/17 | 21, 20, 14 | 356,551 · 360,764 · 224,418 | 176 · 204 · 161 |

Mean tokens per trial: 478,447 incumbent, 313,911 trimmed, a 34 percent reduction. Every trial on
both arms found the retry-policy change behind the 5xx, named the rollback as the fastest safe
mitigation, kept the human as operational owner, attempted no mutating or credential `cf` verb,
and stated that it changed nothing in production.

## Results: routing on Sonnet

Main session with `Skill` and `Task`, three trials each, on the branch.

| Scenario | Expectation | Result |
|---|---|---|
| `discovery-incident-investigation-walk-me-through` | the advisor loads for "walk me through this incident" | 3/3 |
| `discovery-staging-incident-triage` | the advisor loads for a responder's own triage ask (this scenario expected the agent before) | 3/3 |
| `discovery-active-alert-stays-with-advisor` | `scribe` does not fire; the advisor is the alternative | 3/3 |
| `discovery-sre-assistant-dispatched-read` | the agent fires for a dispatched bounded read | 3/3 (one live pass, two regraded after the instrument fix; all three traces show the dispatch) |

The active-alert scenario asserts only that `scribe` stays silent and the advisor loads; a
companion scenario, `discovery-active-alert-does-not-dispatch-assistant`, now asserts that the
agent is not dispatched for the same prompt. It has not been run; the six active-alert traces on
disk (three before the review fixes, three after) show `incident-investigation` loaded and no
agent dispatched in every trial, which is what it grades.

The staging row is the number this change was for. Before it, the same phrasing routed to the
agent by design, and the maintainer's 2026-09-02 session measured the advisor firing zero times in
seven on Sonnet for a new SRE's plain ask while the agent competed for it. That earlier figure is
`[unverified]` in this repository: it lives in session notes, not in a committed run.

## Guard proof after the rename

The read-only guard is keyed on the agent name. After the rename, `python scripts/guard-session-preflight.py`
exited 42, a synthetic `cf env ledger` payload for `save-toolkit:sre-assistant` exited 43 and
`cf app ledger` exited 42, and two live dispatches of the renamed agent with `--plugin-dir` on this
checkout were blocked in the transcript: `cf env ledger` by the fleet credential rule, and
`curl -sS -m 5 https://example.com/health` by the read-only agent allowlist guard.

## Instrument defect found and fixed during the campaign

The runner voided any trial in which the runtime refused a build tool. In a routing trial whose
target is an agent, the clean room runs the dispatched agent without Bash, and the CLI refuses its
`Read` of plugin files outside the workspace; that refusal lands after the main session's dispatch,
which is the whole verdict. Two of three dispatched-read trials were voided that way while their
traces showed the dispatch. Fixed at `3efe6c6d`: the parser records which tool uses ran inside a
subagent, `runtime_blocked_tools` ignores those for routing scenarios only, a regrade re-derives
the rule from the raw trace, and four tests pin it. The evals line ceiling rose from 8,600 to
8,700 in that commit. Build and contract trials keep the original rule.

## What this says

- **The trim is safe on this task.** Three perfect trials on the 17 common checks against three
  perfect incumbent trials, in fewer turns and a third fewer tokens.
- **A responder's triage ask now reaches the advisor on Sonnet, and the agent still answers a
  dispatched read.** Both at 3 of 3.
- **Not measured:** Opus; the advisor's three new sentences in a live troubleshooting session (the
  walk-me-through scenario grades routing, not the advice); the seven skill descriptions that
  changed only by the agent's name token (`akamai-edge`, `incident-command`,
  `incident-investigation`, `obs-dashboards`, `operational-learning`, `postmortem`, `root-cause`),
  and `eng-ladder`'s exclusion sentence, none of which has an after-run beyond the four incident
  scenarios above.
- **Context cost:** the agent's incident path measured by `scripts/check_context_cost.py` fell from
  89,049 B to 71,875 B; the human path grew by the advisor's three sentences and stays within its
  budget.
