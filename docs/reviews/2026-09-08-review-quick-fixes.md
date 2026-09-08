# Independent-review quick fixes — change set and after-run

Date: 2026-09-08 · Branch `work/review-quick-fixes-20260908` from `main` at `ab01e54d` · Candidate
`ad8f345c`, plugin source digest `49dbeec6…`, `plugin_inputs_dirty: false` on every trial ·
Claude Code 2.1.263, Windows host, `--plugin-dir F:/repos/sre-agents`.

This record closes the low-cost findings of the 2026-09-02 independent review of `7c6721b6` (its
packet was never committed; the findings are restated here). It measures routing only. It does not
accept a release, prove installed-host behavior, or judge answer quality.

## Change set

| Review finding | Change | Where |
|---|---|---|
| Three documentation skills describe a fleet handshake, not the user's words (rec 7) | Descriptions lead with the capability and a human phrasing; the scribe-mode clause is last | [`runbook`](../../skills/runbook/SKILL.md), [`postmortem`](../../skills/postmortem/SKILL.md), [`operational-learning`](../../skills/operational-learning/SKILL.md) |
| No route for "which team owns payments" (rec 7) | `operational-learning` offers ownership and dependency lookup from the service cards and gains a read-path section that reports `[sourced]` from `docs/operations/` or says the card is missing | same skill, "Answer an ownership or dependency question" |
| Blast radius, golden signals, and the human roles are undefined (rec 8) | New `stack-profile` reference behind its own routing row; the two rotas nobody has recorded are labelled `[unverified]` | [`terms-and-roles.md`](../../skills/stack-profile/references/terms-and-roles.md) |
| `ci-actions` is the only skill with no exclusion (§4.2) | "Not for a failing application deploy (pcf-ops, gcp-ops) or a runtime bug (root-cause)" | [`ci-actions`](../../skills/ci-actions/SKILL.md) |
| `sre-assistant` searches the plugin repository when it has no data (rec 5) | "If the working tree is not the application's, do not search it for evidence; this toolkit's own files are never incident data." | [`sre-assistant.md`](../../agents/sre-assistant.md) |
| Rules an agent cannot act on (rec 6) | Reviewer loses the "never review from a worktree that auto-loads…" sentence (the next sentence already says what to demand); software-engineer loses "agree a time or cost budget" | [`reviewer.md`](../../agents/reviewer.md), [`software-engineer.md`](../../agents/software-engineer.md) |
| Arrows that are not edges (rec 6) | Scribe's Handoffs section states that every arrow is a recommendation returned to the caller, since the lane has no `Agent` tool | [`scribe.md`](../../agents/scribe.md) |
| README contradicts the reviewer body (§4.4) | The reviewer row now says it reports to its caller, who dispatches any fix; terminal, no delegation | [`README.md`](../../README.md) |
| The empty inventories are not stated plainly (§4.5) | A "How it works" bullet says the inventories and the `docs/operations/` tree are the team's to supply | [`README.md`](../../README.md) |

Left as they were, with the reason: the 780-byte handoff paragraph duplicated in
`observability-engineer` and `software-engineer` stays, because each plugin-loaded agent body is the
only copy that lane's model sees and no include mechanism exists; the host-capability sentences in
`repository-investigator`, `researcher`, and `reviewer` stay, because HOST-002 is live and they are
the one actionable sentence each.

### Ceilings

`[verified]` LF blob totals (`git ls-tree -r -l <rev>`): skills 583,909 → 586,654 (+2,745, of which
the terms reference is 1,813); agents 115,672 → 115,700. `scripts/weights.json` rises to
`skills_bytes: 587200` and `agents_bytes: 115800` in this diff. The first placement of the terms
table, inside the application reference, put the "Build a backend change" context path at 46,704
of 45,000 bytes; moving it behind its own routing row returned that path to 44,890.

## After-run

The description-change rule owes an after-run on each changed skill's targeting scenarios.
`ci-actions` and `runbook` already had one; `postmortem` and `operational-learning` had none, so
two routing scenarios were added for the new phrasing:
[`discovery-postmortem-write-for-incident`](../../evals/scenarios/discovery-postmortem-write-for-incident.yaml)
and [`discovery-operational-learning-owner-lookup`](../../evals/scenarios/discovery-operational-learning-owner-lookup.yaml).
Method as in PR #241's advisor on-call trigger record (not on this branch): detached arms,
`--model sonnet --trials 3 --timeout 600`, `CLAUDE_CONFIG_DIR` credential-only, workspaces under
`F:\iso-tmp` so no ancestor `CLAUDE.md` is discovered.

| Scenario | Expect | Trials | Verdict | Seconds | Cost (USD) |
|---|---|---|---|---|---|
| `discovery-runbook-incident-update` (regression) | fire runbook | 3 | PASS 3/3 | 282–442 | 0.72, 1.01, 0.66 |
| `discovery-ci-actions-harden-workflow` (regression) | fire ci-actions | 3 | PASS 3/3 | 19–24 | 0.12, 0.10, 0.10 |
| `discovery-postmortem-write-for-incident` (new) | fire postmortem | 3 | PASS 3/3 | 19–203 | 0.12, 0.13, 0.49 |
| `discovery-operational-learning-owner-lookup` (new) | fire operational-learning | 3 | PASS 3/3 | 215–328 | 0.81, 0.76, 0.57 |

`[verified]` The first tool call in all twelve trials was the target skill. Resolved model
`claude-sonnet-5`. Total about USD 5.6.

## Review round: Codex on PR #243

Five findings on `e605d103`, all verified against the sources they cite and fixed in `6ec6541f`
(plugin digest `8a188034…`), with the scenario correction in `1a14dfca`.

| Finding | Verified against | Fix |
|---|---|---|
| P1: the glossary said blast radius keys the Tier 2/3 classification | `production-change-gate/SKILL.md:37-55` chooses the tier from the action's reversibility and access-path effects and records blast radius afterwards | Blast radius is "required impact evidence after the tier is chosen; a small blast radius never lowers a tier" |
| P1: the reviewer lost its refusal for a worktree that auto-loads candidate instruction files | A trusted-base diff does not un-load a candidate `CLAUDE.md` the host already read | Refusal restored as a detectable condition: if the loaded instructions already match the candidate's version, refuse and ask for a trusted-base worktree. `agents_bytes` 115,800 → 116,100 (LF 115,983) |
| P2: the owner lookup asked for `last_verified` | The service-card template defines `last_reviewed` and `evidence_status` | Lookup reports those two fields |
| P2: the description dropped the `agent-engineer` exclusion | The skill's own invariant routes fleet prompt failures to `agent-engineer` | Exclusion restored within 600 bytes (593); a negative scenario guards it |
| P2: the release owner was defined by the change record | `incident-fast-path.md:53-64` defers the formal change record while the role still executes | "The human assigned to execute … named on the change record where the process requires one" |

### After-run on the restored exclusion (digest `8a188034…`, Sonnet, 3 trials)

| Scenario | Batch | Verdict | Seconds | Cost (USD) |
|---|---|---|---|---|
| `discovery-operational-learning-owner-lookup` (positive) | `after2-sonnet` | PASS 3/3 | 167–322 | 0.57, 0.79, 0.73 |
| `discovery-operational-learning-defers-fleet-failure` (negative, first prompt) | `after2-sonnet` | **FAIL 0/3**: no tool call in any trial | 11–18 | 0.11, 0.08, 0.08 |
| same, prompt corrected in `1a14dfca` | `after3-sonnet` | **INCONCLUSIVE**: run 1 PASS, runs 2–3 INCONCLUSIVE | 195–225 | 0.41, 0.43, 0.47 |

The first negative batch is a scenario defect, kept on record: the prompt said "I have the two
transcript excerpts" without supplying them, and in all three trials Sonnet named
`save-toolkit:agent-engineer` as the lane and asked for the paste before dispatching. A negative
passes only when the alternative is invoked, so the corrected prompt carries both excerpts.

`[verified]` from the traces of the corrected batch: all three trials dispatched
`save-toolkit:agent-engineer` and none invoked `operational-learning`. The two INCONCLUSIVE
verdicts come from what the dispatched agent did next: it tried to `Glob` and `Read` the scribe
agent's file at the plugin root (denied, outside the workspace), and in run 3 it wrote a note
into the trial's own auto-memory directory under the clean config dir, which the harness's
out-of-workspace guard flags. That is the third scenario in this record family where a correct
route ends INCONCLUSIVE because the routing harness grants `Read`/`Glob` but not the plugin root;
the runner change stays a separate decision. The aggregate stands as INCONCLUSIVE.

## Not established

- The negative's aggregate under this runner; only the trace-level claim above is verified.
- Whether the dropped machinery triggers ('runbook mode selected', 'postmortem mode selected',
  'knowledge closeout mode selected') mattered: `scribe` loads these skills by name, and no
  scenario exercised the scribe-driven path.
- Opus or Haiku on any of the four; the negatives for the three rewritten descriptions (no scenario
  asks whether an incident ask now leaks into `postmortem`, for example).
- That the owner-lookup answer is correct when a service card exists; the trial workspace had none,
  so the skill's "say the card is missing" branch is the one that ran.
- Behavior of the installed plugin rather than `--plugin-dir`.
