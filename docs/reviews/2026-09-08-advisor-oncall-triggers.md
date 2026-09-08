# Advisor on-call triggers — after-run evidence

Date: 2026-09-08 · Branch `work/advisor-oncall-triggers-20260908`, PR #241 · Two measured
candidates: batch 1 at `2b2dad80` (plugin source digest `3211d951…998d`) and batch 2 on the merged
head (digest `f4f0543e…e2cd6`, first present at `7ff70344`; the docs-only commits after it do not
change the digest). `plugin_inputs_dirty: false` on every trial · Claude Code 2.1.263, Windows host,
`--plugin-dir F:/repos/sre-agents`.

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
| Description bytes (UTF-8 of the YAML string, host-independent) | 392 | 496 |
| New scenario | — | [`discovery-incident-investigation-first-page`](../../evals/scenarios/discovery-incident-investigation-first-page.yaml): the review's unhinted new-SRE prompt, `expect: fire` |

The two dropped quoted phrases survive as prose ("understand evidence", "explain what … is telling
them"); no routing scenario targets them, so that loss is `[unverified]` either way.

### Skill-byte totals and the ceiling

`[verified]` Totals below are blob sizes from `git ls-tree -r -l <rev> -- skills`, which is what a
Linux CI checkout measures. This Windows checkout reads 58 B higher on every revision because
`skills/backend-craft/assets/ProblemAdvice.java` has no `eol` attribute in `.gitattributes` and
`core.autocrlf` gives it CRLF (working tree 2,740 B, blob 2,682 B); `check_weight.py` sums
working-tree sizes. Earlier drafts of this packet quoted the host numbers unlabelled.

| Revision | Skills bytes (LF blobs) | `skills_bytes` ceiling | Headroom |
|---|---:|---:|---:|
| `0450ea58` (main at fork) | 578,848 | 579,000 | 152 |
| `2b2dad80` (batch 1 candidate) | 578,981 | 579,000 → 579,200 in that commit | 19 before the bump |
| `ab01e54d` (main after PR #240) | 583,909 | 584,000 | 91 |
| merged head (`7ff70344` onward) | 584,042 | 584,000 → 584,200 | −42 before, 158 after |

The bump at `2b2dad80` was not needed on LF bytes; it fired only because this host measured
579,039. The bump on the merged head is needed on both: the description's 133 LF bytes exceed the
91 that PR #240 left. The ceiling is raised in the diff that earns it, as the gate instructs.

## Method

- `python evals/build_probe.py --scenario <id> --label <label> --model <alias> --trials 3
  --timeout 600`, one detached process per arm (WMI `Win32_Process.Create`), routing kind, main
  session with the scenario's tool list, `CLAUDE_CONFIG_DIR` credential-only.
- Batch 2 is a clean batch: fresh labels (`exact-sonnet`, `exact-opus`), fresh output directories,
  nothing appended to a batch-1 label, every trial bound to digest `f4f0543e…`.
- `[verified]` Workspace isolation: `TEMP`/`TMP`/`TMPDIR` set to `F:\iso-tmp` for every arm, because
  `evals/clean_room.py` still creates workspaces with `tempfile.mkdtemp()` and this host's temp dir
  sits under the home directory. Detector: a Haiku trial asked to quote any loaded instruction-file
  heading returned `NONE` from an `F:\iso-tmp` workspace and `# Working rules (all projects)` from
  the default temp dir, same harness, same day. Every trial workspace below was under `F:\iso-tmp`.
- Gate A 4/4 PASS and `pytest` green on each candidate before its batch ran (498 passed, 4 skipped
  at `2b2dad80`; 533 passed, 4 skipped on the merged head).

## Results, batch 2: the exact merged-head candidate

All eight scenarios whose target or expected alternative is the advisor, plus the two helper-routing
scenarios the broader triggers could have disturbed. Resolved models per trace: `claude-sonnet-5`,
`claude-opus-5`. Threshold 1.0 on every scenario.

| Scenario | Expect | Model | Trials | Verdict | Seconds | Cost (USD) |
|---|---|---|---|---|---|---|
| `discovery-incident-investigation-first-page` (new, unhinted) | fire advisor | Sonnet | 3 | **PASS 3/3** | 129–350 | 0.85, 0.58, 0.76 |
| same | fire advisor | Opus | 3 | **PASS 3/3** | 115–151 | 0.66, 0.56, 0.61 |
| `discovery-incident-investigation-walk-me-through` (regression) | fire advisor | Sonnet | 3 | PASS 3/3 | 118–187 | 0.28, 0.40, 0.27 |
| `discovery-staging-incident-triage` (calibration) | fire advisor | Sonnet | 3 | PASS 3/3 | 41–52 | 0.13, 0.12, 0.13 |
| `discovery-active-alert-does-not-dispatch-assistant` (regression) | sre-assistant not fired | Sonnet | 3 | PASS 3/3 | 24–31 | 0.16, 0.13, 0.13 |
| `discovery-active-alert-stays-with-advisor` (calibration) | scribe not fired | Sonnet | 3 | **INCONCLUSIVE**: runs 1–2 PASS, run 3 INCONCLUSIVE (denied read, below) | 29–44 | 0.17, 0.13, 0.15 |
| `discovery-sre-assistant-dispatched-read` (regression) | fire sre-assistant | Sonnet | 3 | PASS 3/3 | 33–55 | 0.31, 0.17, 0.19 |
| `native-incident-helper-return-and-resume` (regression, added by PR #240) | fire advisor, read reference, one helper, resume | Sonnet | 3 | **INCONCLUSIVE**: runs 1–2 PASS on all five structural expectations, run 3 INCONCLUSIVE (tool error, below); `assessment_scope: structural_only`, `semantic_assessment: UNVERIFIED` | 100–112 | 0.39, 0.36, 0.28 |

`[verified]` In every advisor-positive trial on both models the first tool call was
`Skill: save-toolkit:incident-investigation`; no negative trial invoked its forbidden target. Batch 2
cost about USD 7.9.

### The two INCONCLUSIVE verdicts

- **`stays-with-advisor`, run 3.** The advisor loaded and `scribe` never fired. The model then
  asked to `Read` `skills/incident-investigation/references/symptom-investigation.md` at the plugin
  root, outside the trial workspace; the non-interactive runtime denied it twice and the harness
  fails closed ("build tools denied by the runtime"). The same trial shape recurred in batch 1
  (run 3 there, replaced by a passing run 4, aggregate still INCONCLUSIVE). Routing was correct in
  all seven trials of this scenario across both batches. The scenario grants `Read`, but the runner
  does not add the plugin root as a readable directory, so any trial in which the advisor follows
  its own "read symptom comparisons" instruction can only end INCONCLUSIVE. That is a runner
  limitation; it is not changed here because the runner's modules are part of scenario identity
  and changing them would invalidate every comparison in this record. It is the review's §4.3
  observation that plugin reference reads need permission outside the working tree.
- **`native-incident-helper-return-and-resume`, run 3.** The advisor loaded, read the reference,
  dispatched an `Explore` agent, read the fixture's `evidence.md` in the workspace, then tried to
  read `evidence.md` at the plugin root, a path that does not exist; the harness treats the tool
  error as "native tool denial/error" and grades nothing. Runs 1 and 2 passed all five structural
  expectations. The roadmap's INCIDENT-QUALITY-001 entry already records this "unnecessary missing
  path" behavior at `c53ed2b6`; it is decision quality, not routing, and the scenario's semantic
  criteria are manual and were not assessed here.

Neither verdict was rerun until green. Both aggregates stand as INCONCLUSIVE in the record.

## Results, batch 1: candidate `2b2dad80` (digest `3211d951…`)

Superseded by batch 2 for the exact-candidate claim; kept because it is the first measurement and
the one the changelog entry originally cited.

| Scenario | Model | Result |
|---|---|---|
| first-page (new, unhinted) | Sonnet | PASS 3/3 (77–478 s; 0.31, 0.31, 0.97) |
| first-page (new, unhinted) | Opus | PASS 3/3 (100–126 s; 0.60, 0.57, 0.78) |
| walk-me-through | Sonnet | PASS 3/3 |
| staging triage | Sonnet | PASS 3/3 |
| does-not-dispatch-assistant | Sonnet | PASS 3/3 |
| stays-with-advisor | Sonnet | runs 1, 2, 4 PASS; run 3 INCONCLUSIVE (denied read); aggregate INCONCLUSIVE |
| dispatched-read | Sonnet | PASS 3/3 |
| native-incident-helper-return-and-resume | — | not run in batch 1 |

Batch 1 cost about USD 7.3.

## Observations that are not routing verdicts

Under the routing harness's `Skill,Task`-only tool list (batch 1, the two scenarios that do not
widen it), the advisor went on to call `Skill: Glob`, `Skill: Read`, `Skill: Bash`, and a
`non-existent-placeholder` skill, re-invoked its own skill up to seven times, and dispatched
`repository-investigator`, `Explore`, and `general-purpose` agents to look for a knowledge
repository that the workspace does not hold. One Sonnet first-page trial spent 478 s and USD 0.97
doing so; batch 2's slowest first-page trial spent 350 s. Routing was right; what the advisor does
next in a session with no `Read`/`Glob` and no `docs/operations/` is decision quality, owned by
INCIDENT-QUALITY-001.

## Not established

- Which of the two description edits (2026-09-03 agent side, this advisor side) carries the Sonnet
  first-page result: the fleet's rule is after-only with a before-run only for a red, and none was
  red. The 0/7 baseline was taken against the old `sre` description.
- A conclusive aggregate for `stays-with-advisor` or the native scenario under this runner.
- The native scenario's semantic criteria (manual assessment; INCIDENT-QUALITY-001).
- Opus on the negatives and on the helper positives; Haiku on anything.
- Behavior of the installed plugin rather than `--plugin-dir`.
- Any effect on the two trigger phrases that moved from quotes into prose.
