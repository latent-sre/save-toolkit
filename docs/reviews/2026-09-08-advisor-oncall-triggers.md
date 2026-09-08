# Advisor on-call triggers — after-run evidence

Date: 2026-09-08 · Candidate: `2b2dad80` on `work/advisor-oncall-triggers-20260908`, from `main`
at `0450ea58` · Plugin source digest `3211d951…998d`, `plugin_inputs_dirty: false` on every trial ·
Claude Code 2.1.263, Windows host, `--plugin-dir F:/repos/sre-agents`.

This record measures one description change. It does not accept a release, prove installed-host
behavior, or judge answer quality; INCIDENT-QUALITY-001 remains on hold.

## The change

The 2026-09-02 independent review (uncommitted packet at the time of writing) found that a new
SRE's first-page prompt reached the `incident-investigation` advisor 4/4 on Opus and 0/7 on Sonnet
at `7c6721b6`, and asked for two edits: the `sre` agent's description gains a "not for" toward the
advisor, and the advisor's triggers gain on-call phrasing. The first landed on 2026-09-03 with the
`sre-assistant` rename; this is the second.

| Item | Before | After |
|---|---|---|
| Use-when clause | "Help the human SRE understand evidence and choose the next useful step during a live incident." | adds "including a first responder who does not know where to start, or explain what a graph, log, or alert is telling them" |
| Quoted triggers (`check_links` allows 2–4) | 'walk me through this incident', 'help me understand what is going on with INC', 'what should I check next', 'what is this telling me' | 'I just got paged, what do I do', 'customers are reporting errors, where do I start', 'walk me through this incident', 'what should I check next' |
| Description bytes | 392 | 496 |
| New scenario | — | [`discovery-incident-investigation-first-page`](../../evals/scenarios/discovery-incident-investigation-first-page.yaml): the review's unhinted new-SRE prompt, `expect: fire` |
| `scripts/weights.json` `skills_bytes` | 579,000 (65 B headroom) at the measured candidate; 584,000 (4 B headroom) after PR #240 | 579,200 at `2b2dad80`; 584,200 on the merged head, where tracked skills measure 584,100 |

The two dropped quoted phrases survive as prose ("understand evidence", "explain what … is telling
them"); no routing scenario targets them, so that loss is `[unverified]` either way.

## Method

- `python evals/build_probe.py --scenario <id> --label after-<model> --model <alias> --trials 3
  --timeout 600`, one detached process per arm (WMI `Win32_Process.Create`), routing kind, main
  session with the scenario's tool list, `CLAUDE_CONFIG_DIR` credential-only.
- `[verified]` Workspace isolation: `TEMP`/`TMP`/`TMPDIR` set to `F:\iso-tmp` for every arm, because
  `evals/clean_room.py` still creates workspaces with `tempfile.mkdtemp()` and this host's temp dir
  sits under the home directory. Detector: a Haiku trial asked to quote any loaded instruction-file
  heading returned `NONE` from an `F:\iso-tmp` workspace and `# Working rules (all projects)` from
  the default temp dir, same harness, same day. Every trial workspace below was under `F:\iso-tmp`.
- Gate A 4/4 PASS and `pytest` 498 passed / 4 skipped on the candidate before any trial ran.

## Results

All targeting scenarios for the advisor, plus the two helper-routing scenarios the broader
triggers could have disturbed.

| Scenario | Expect | Model | Trials | Result | Seconds | Cost (USD) |
|---|---|---|---|---|---|---|
| `discovery-incident-investigation-first-page` (new, unhinted) | fire advisor | Sonnet | 3 | **3/3 PASS** | 77–478 | 0.31, 0.31, 0.97 |
| same | fire advisor | Opus | 3 | **3/3 PASS** | 100–126 | 0.60, 0.57, 0.78 |
| `discovery-incident-investigation-walk-me-through` (regression) | fire advisor | Sonnet | 3 | 3/3 PASS | 75–317 | 0.29, 0.27, 0.68 |
| `discovery-staging-incident-triage` (calibration) | fire advisor | Sonnet | 3 | 3/3 PASS | 46–61 | 0.15, 0.13, 0.12 |
| `discovery-active-alert-does-not-dispatch-assistant` (regression) | sre-assistant not fired | Sonnet | 3 | 3/3 PASS | 17–35 | 0.16, 0.13, 0.13 |
| `discovery-active-alert-stays-with-advisor` (calibration) | scribe not fired | Sonnet | 3 + 1 | runs 1, 2, 4 PASS; run 3 INCONCLUSIVE (below). Label aggregate stays `INCONCLUSIVE` at threshold 1.0 because the harness keeps the run-3 record | 27–60 | 0.13, 0.13, 0.18, 0.13 |
| `discovery-sre-assistant-dispatched-read` (regression) | fire sre-assistant | Sonnet | 3 | 3/3 PASS | 60–76 | 0.26, 0.21, 0.20 |

Resolved model per trace: `claude-sonnet-5` and `claude-opus-5`. Total spend for the campaign is
about USD 7.

`[verified]` In every advisor-positive trial on both models the first tool call was
`Skill: save-toolkit:incident-investigation`; the negatives never invoked the forbidden target.

## Observations that are not routing verdicts

- **The INCONCLUSIVE trial routed correctly.** It loaded the advisor, never touched `scribe`, then
  asked to `Read` `skills/incident-investigation/references/symptom-investigation.md` from the
  plugin root, outside the trial workspace. The non-interactive runtime denied it twice and the
  harness fails closed (`build tools denied by the runtime`). This is the review's §4.3 note that
  plugin reference reads need permission outside the working tree; an installed plugin's cache path
  is still unprobed.
- **Under the routing harness's `Skill,Task`-only tool list**, the advisor went on to call
  `Skill: Glob`, `Skill: Read`, `Skill: Bash`, and a `non-existent-placeholder` skill, re-invoked its
  own skill up to seven times, and dispatched `repository-investigator`, `Explore`, and
  `general-purpose` agents to look for a knowledge repository that the workspace does not hold. One
  Sonnet first-page trial spent 478 s and USD 0.97 doing so. Routing was right; what the advisor
  does next in a session with no `Read`/`Glob` and no `docs/operations/` is decision quality, owned
  by INCIDENT-QUALITY-001.

## Merged head versus measured candidate

PR #240 merged to `main` (`ab01e54d`) while the trials ran. Merge commit `7ff70344` brings it into
this branch; the only conflict was `scripts/weights.json`, resolved to #240's ceilings plus the
200-byte allowance above, and the Copilot adapter was regenerated rather than hand-merged.

- `[verified]` The advisor description on the merged head is byte-identical to the measured one.
- `[verified]` The plugin source digest on the merged head is `f4f0543e…e2cd6`, not the measured
  `3211d951…998d`. The difference is #240's content: six body lines in the advisor's
  "Knowledge, evidence, and helper returns" section, its `symptom-investigation.md` reference,
  `incident-command`'s mitigation-selection reference, two `obs-logs` references, and three agent
  bodies. None of it is routing text.
- `[unverified]` That routing on the merged head matches the table above. The routing function
  (descriptions) is unchanged, so the result is expected to transfer; a maintainer who wants the
  exact-revision proof re-runs the seven scenarios on the merge head.

## Not established

- Which of the two description edits (2026-09-03 agent side, this advisor side) carries the Sonnet
  first-page result: the fleet's rule is after-only with a before-run only for a red, and none was
  red. The 0/7 baseline was taken against the old `sre` description.
- Opus on the negatives and on the helper positive; Haiku on anything.
- Behavior of the installed plugin rather than `--plugin-dir`.
- Any effect on the two trigger phrases that moved from quotes into prose.
