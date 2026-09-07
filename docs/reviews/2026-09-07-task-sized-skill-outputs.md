# Task-sized skill outputs

Status: implemented and independently source-reviewed; behavioral verification unrun pending approval.
Scope: the human approved item 2 of the skill review: small tasks should not require full reports.
Baseline: `4201686b9a264e32c54bc95ed404496aa981cd83`; plugin digest
`10dac4f5d1db7414a513bfdb686153e1dece7080a7153f4a2a7c459b82ec5a62`.

## Change contract, before source edits

| Task | Required result | What must not be lost |
|---|---|---|
| One freshness/correlation alert question | Answer the question with supplied scope/evidence, relevant limits, and a useful next step; no unrelated burn-rate packet | No-data is not health; hypothetical design is not a tested alert; human change authority |
| Burn-based alert design | Retain the selected long/short pair, both measurements or explicit gaps, exact query/target, owner, route, runbook, and fire/resolve verification status | No single-window page, invented tests, or production notification |
| Bounded span interpretation | Explain the supplied span observation and its limits without requiring another trace or a complete critical-path table | Sampling, overlapping/nested duration, protocol/status, and causal uncertainty |
| Full trace investigation | Retain useful critical-path, comparison, selection, timing, and missing-evidence details | Missing observations stay gaps; one trace does not prove population health |
| Resolved unknown-cause P3 | A genuinely abbreviated, evidence-bound postmortem with impact, key chronology, human-confirmed recovery, causal uncertainty, and owned follow-ups | No severity invention, assumed data-loss clearance, reopening, or loss of required facts |
| P1 full postmortem and knowledge closeout | Preserve full incident analysis and each distinct follow-up; enrich one record instead of duplicating actions across tables | Separate owners/statuses, unchanged evidence labels, missing checkout binding blocks `prepared`, and no invented execution/review |

The diagnosed source conflicts are unconditional output/workflow requirements: alerting always asks
for burn fields, traces always asks for a full investigation packet, the postmortem always copies
the full template, and follow-ups are restated across postmortem and knowledge-closeout sections.
This is static source evidence, not a claim that every model response exhibits the problem.

Only these output/workflow contracts and their direct consumers are in scope. No skill retirement,
frontmatter/routing change, tool grant, runtime/framework change, deployment, or publication is
authorized. The other review recommendations, including runbook rollback-template and CI-timeout
repairs, remain outside this item.

## Verification boundary

One candidate. Existing local checks and independent source review are in scope. The human was
asked separately about six matched tools-off Sonnet pairs, at most $3 in CLI estimates and 180
seconds per call, with no retries or evaluator-launched judges. No new model call is authorized
until that approval is explicitly received. Terra remains paused independently.

Shorter output alone is not success. Assessment must check retained evidence, usable next steps,
appropriate task scope, no invented work, and the full-task controls. Source-injection comparisons
do not prove native skill selection, reference loading, or end-to-end document writes. Human
acceptance of the exact candidate remains separate from implementation and testing.

## Implemented changes

- `obs-alerting`: bounded advice no longer requires a full design/readiness packet. Design work
  retains common owner/route/runbook/no-data and verification evidence; burn, freshness, and
  correlation fields apply only to their corresponding task. An untested design may be handed off
  as unverified, never presented as a verified implementation.
- `obs-traces`: supplied-span interpretation does not require retrieval, another trace, or a full
  critical-path table. Whole-trace work still carries comparison, timing, status/protocol, sampling,
  and missing-evidence details. Both paths preserve redaction and uncertainty.
- `postmortem`: the existing template now provides a common short core and full-analysis sections.
  P1/P2/full requests retain depth; P3/near-misses can use the abbreviated form unless policy or the
  owner requires full depth. Ticket drafts do not inherit repository-only metadata. Missing
  severity/evidence is not invented; unknown cause does not reopen human-confirmed resolution.
- Postmortem, advisor closeout, `operational-learning`, and `scribe` reuse one Follow-ups record.
  They enrich incoming IDs with artifact outcomes and proof, without recreating the action list in
  each section. Distinct scopes, owners, statuses, prerequisites, and evidence stay separate.
  A recipient without access to the source receives the needed rows, not an unusable pointer.
- Ordinary documentation follow-ups no longer require irrelevant production fields. A production-
  facing recommendation still requires its tier, approval, verification, and rollback/recovery.
  No `prepared` claim bypasses the verified checkout binding and actual-diff requirements.

No descriptions, invocation policies, tools, security grants, or production authority changed.
The full causal template's numbered Why skeleton was replaced while creating the conditional form,
so it now matches the existing method-selection rule rather than compelling a numbered chain.

## Verification and limits

[verified] Fresh integrated run: `python -m pytest scripts evals -q` reported **465 passed,
5 skipped, 919 subtests passed**. Focused source/asset contracts reported **51 passed,
201 subtests passed**. Generated adapters matched; Gate A passed all four structural steps;
the probe validator accepted 65 scenarios and 324 graded expectations; `git diff --check` passed.
No new validator, grader, keyword test, runtime framework, or scenario was added.

[verified] All seven task-context budgets and all three corpus weights pass unchanged. Skill
sources total 575,888 bytes, 59 fewer than baseline; agent sources total 113,990 bytes, 200 more
because scribe's direct-consumer contract changed. This is not a claim of substantial prompt-size
or model-output savings. The initial conditional-form draft exceeded the skill ceiling and was
compacted within the named files before review; no ceiling was raised.

[sourced] Independent review of the eight canonical files found no material contradiction or
regression, including a final check that method naming applies to full causal analysis rather than
requiring it for abbreviated unknown-cause write-ups. One behavioral watch remains: an action's
operational state and its later document disposition must both survive in a shared row.

[unverified] No new model calls have run. The six tasks and acceptance were frozen before source
edits; optional Sonnet approval remains outstanding. Task fit, useful brevity, deduplication, and
full-task behavior are not proved by these structural checks. The earlier incident adoption hold
is unchanged; this work does not close its selection, dispatch, or causal/timing failures.

The generic Codex skill validator is not used for this Claude-source repository: its rejection of
the supported `argument-hint` field was established previously. Repository-aware validators pass;
valid metadata was preserved. No commit, push, deployment, or new model campaign was performed.

Private cases, criteria, source snapshots and review are under `.eval-runs/task-sized-20260907/`.
Cases SHA-256: `1a717025b76316f33f9e96b2a5834fa7831c3e7798319945c92f258b49b7122a`.
Acceptance SHA-256: `2a4a52ad534b87a10108a09c32dd1e20dcac3c2fe434b14796837d003e7336b6`.

Candidate frozen at 2026-09-07 04:58:25 UTC, plugin SHA-256
`b81f345d45310584f6be63115de1187a7f5fe7ea758d58c477551424087f4b29`;
11-source snapshot `6eb7df117ad8e61ad1b1b0b3c943ef5eeaa681f158c984b8d5f950a5e4c19e6c`.
All eight reviewed hashes, eleven selected sources, cases and criteria matched at freeze. This
identifies uncommitted canonical changes over the baseline, not an accepted or published revision.

## Rescan follow-up — task scope and owner alignment

The human approved rescan items **3 (small requests inheriting large workflows)** and **4 (owner
and rollback instruction mismatches)**. Baseline: `941dc286c1e6ff88f89f3ede475d896f1c3901b2`.
The source contradictions were observed in the rescan; no model failure or improvement delta is
claimed for this follow-up. The audience remains a human SRE from first day through veteran:
bounded means relevant guidance, not missing explanations or lost evidence.

### Acceptance and implementation

| Named task / control | Required behavior and changed source |
|---|---|
| Correct a stale contact / create or revise a procedure | `runbook` and `scribe` preserve existing structure, IDs, status, history and evidence-governed dates for a bounded correction. Action/branch changes use the procedure path; new runbooks retain the full template, draft state, null dates, evidence, expected outcomes and safety checks. |
| Explain one supplied log / investigate a post-deploy error change | `obs-logs` permits a direct scoped explanation without requiring a new query or baseline. Requested query/investigation retains dialect selection, exact scope/window, query evidence, comparisons and privacy. |
| Interpret supplied metric values / construct a counter-ratio query | `obs-metrics` answers with meaning and evidence limits; missing values/time stay unknown. Query work retains type, population, reset handling, units, dialect, cadence and no-data behavior. |
| Repair one propagation boundary / design service-wide telemetry | `obs-pipeline` and its SDK reference scope verification to the affected path for a bounded fix. Full service design retains RED/USE, bounded labels, propagation/correlation and SLI checks; sampling policy/topology guidance applies when sampling is selected or changed. |
| Resolve an undecided design fork / review a proposed decision change | `eng-ladder` retains builder ownership and required senior consultation for the material fork. The caller/human senior handles the undecided choice; `reviewer` receives an actual proposal, trusted-base context, base/candidate identities and diff. No reviewer shell or Skill authority is added. |
| Document an operating procedure / change monitoring | The principal reference routes procedures to `scribe` and observability artifacts to `observability-engineer`; the caller arranges unavailable handoffs. Production execution stays with the human owner. |
| Recommend reversible change / recommend an action with irreversible effects | `sre-assistant` and the production gate agree on exact rollback where feasible, otherwise explicit non-reversibility and evidenced recovery/stop conditions. Missing recovery evidence blocks approval; recovery does not lower the tier or authorize execution. |

No descriptions, invocation policies, tool grants, encoded delegation edges, grader rules,
dependencies or runtime code changed. The Tier 0/1 actor-template issue is not part of this patch.
The rescan's diagnostic-example corrections, console-path additions and broader incident evidence
failures remain separate; this follow-up does not clear the incident acceptance hold.

### Verification boundary

Independent source review and the existing repository checks assess this patch. No prose-matching
test, new evaluator, paid judge, or model campaign is added. Behavioral response size, experience
adaptation and native routing on these new bytes remain unverified until separately authorized.

[verified] Final integrated checks: `python -m pytest scripts evals -q` reported **466 passed,
5 skipped, 923 subtests passed** (56.32s). The focused asset, runbook, agent-scope, adapter and
frontmatter suites reported **56 passed, 2 skipped, 134 subtests passed**. Regeneration and Gate A
passed; the probe validator accepted **65 scenarios / 324 expectations**; `git diff --check` passed.

[sourced] Two independent source reviews covered all ten changed canonical files, including the
scribe/gate consumers and the full-task controls. No material contradiction was found; all ten
reviewed hashes matched the integrated files. This is not a native execution or merge verdict.

[verified] All seven task-context budgets and three corpus ceilings pass without raising a limit.
Skills total **575,943 bytes** (+22 versus this follow-up's baseline); agents **114,474 bytes** (+231).
The initial combined draft exceeded the skill ceiling; redundant routing prose in the changed
`eng-ladder` section was compacted before final review. No substantial context/output saving is
claimed from these source sizes.

Final plugin-source SHA-256:
`d4fe59c06638fde289cb16d26b74a78d774101bd28fe853e826838d5cd6985f3`.
This identifies the uncommitted canonical patch over `941dc286`, not an accepted revision.
No model calls, commit, push, PR update, installation or live action were performed in this follow-up.
