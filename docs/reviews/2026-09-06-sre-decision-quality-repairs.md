# SRE decision-quality repairs

Date: 2026-09-06 local; runtime evidence may use 2026-09-07 UTC.
Baseline: `3225050474498cce32682af08ed6d8f140521ee1`.
Status: source repairs implemented and reviewed; behavioral acceptance failed. Hold adoption.

## Scope and decision

The human approved all recommendations from the deep repository review. This change repairs the
agent/skill instructions and worked examples, not the guard or evaluation framework. No tool grant,
production authority, model pin, size ceiling, installed plugin, or live system is changed.
Human acceptance of the exact candidate remains separate from permission to implement and test it.

The existing generalized-incident draft was committed before this work. Its
[earlier result](2026-09-06-general-incident-help.md) remains historical evidence, not a readiness
claim or a result overwritten by these tests.

## Source repairs and acceptance

| Repair | Changed source | Observable acceptance |
|---|---|---|
| Bounded helper and deeper diagnosis | `agents/sre-assistant.md`, `skills/root-cause/SKILL.md` | A numbers/events slice returns observations and gaps without forced root cause/durable fix; explicit diagnosis still gets a discriminating method; human mitigation need not wait for permanent diagnosis |
| Honest operational branches | `skills/runbook/` | CPU similarity, timeout counts, failed reads, and incomplete scale-out do not prove causes; adequate observations permit warranted progress; restart effects and abort state are accurate |
| Escalation without false exoneration | `skills/pcf-ops/`, `skills/gcp-ops/SKILL.md` | Broad impact brings relevant owners in without proving platform fault or certifying an app healthy |
| Explicit GCP target | `skills/gcp-ops/SKILL.md` | Cloud Run examples retain supplied project/region; Logging binds project, service, and resource region; read examples remain guard-allowed and traffic writes denied |
| User-outcome recovery | Incident advisor, symptom reference, command, communications, closeout packet | Green HTTP/process status does not resolve wrong data or missing delivery; sufficient scoped output/readback evidence permits human-confirmed resolution |
| Honest and proportionate closeout | `agents/scribe.md`, postmortem and operational-learning skills | A resolved unknown-cause incident can be documented with owned uncertainty; human detection is assessed, not automatically blamed; small corrections stay small |
| Evidence scope and return inputs | All eight agents; authoring context/roster | Subject, method, source, and time survive handoff; reading a record is not live verification; caller and human owner remain distinct |
| Review and lane completion | Reviewer; authoring roster | Unchanged mission gaps remain separate from candidate verdict; observability finishes against assigned artifact evidence, not incident recovery |

Corrected source examples are not proof of downstream model adherence. The runbook exemplar was
not supplied to the earlier general-incident experiment, so it is not attributed as that failure's
cause. Historical source inspection also found diagnosis-shaped obligations before the #224 role
narrowing; recent cuts alone do not explain the conflict.

## Structural verification

- [verified] GCP target-binding tests first failed on seven unbound examples, then passed after
  the source repair. The tests inspect executable argument structure rather than grading prose.
- [verified] The SRE default-packet regression first failed because `Hypotheses tested`,
  `Root cause`, and `Durable fix` were mandatory, then passed after narrowing that template.
  The obsolete test requiring provisional severity for every slice was removed intentionally.
- [verified] `python scripts/test_skill_assets.py`: four tests passed, including real read-only
  guard subprocess decisions for the substituted fictional GCP examples. No gcloud command ran.
- [verified] `python -m pytest scripts evals -q`: 465 passed, 5 skipped, 919 subtests passed.
  An earlier integrated run caught generated drift while the compaction edits were finishing;
  regeneration and the fresh complete run above resolved it.
- [verified] Adapter validation passes after regeneration. `build_probe.py --validate` accepts
  65 scenarios and 324 graded expectations. No production runner, grader, rubric, or scenario changed.
- [verified] All seven context checks and all three weight totals pass without ceiling changes.
  Frozen source totals: skills 575,860/576,000 bytes; agents 114,354/115,000 bytes;
  evaluation Python 9,252/9,900 lines.

The generic Codex skill-creator validator rejects this repository's supported Claude
`argument-hint` field. Repository frontmatter validation is authoritative here and passes; valid
metadata was not removed to satisfy the incompatible validator.

These checks do not exercise live Cloud Run commands or prove that a model makes good decisions.
The GCP syntax was checked against current official references. Context7 returned unrelated
Compute Engine material for the narrow Cloud Run queries, so direct official pages supplied the
relevant contract: [revision targeting](https://docs.cloud.google.com/sdk/gcloud/reference/run/revisions/describe),
[traffic targeting](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/update-traffic),
[Logging project selection](https://docs.cloud.google.com/sdk/gcloud/reference/logging/read), and
[Cloud Run resource location](https://docs.cloud.google.com/logging/docs/api/v2/resource-list#cloud_run_revision).
This is documentation evidence, not an upstream-source inspection or live-platform test.

## Baseline diagnosis before candidate evaluation

Twelve tools-off sessions compared two fixed synthetic questions across task-only, main skill,
and main-plus-symptom-reference arms, twice each. Sources were frozen from the baseline commit,
independent of the concurrently edited checkout. Each session used the existing independent
empty Git root and credentials-only configuration, with no tools, plugin, or MCP.

Every main session resolved to `claude-sonnet-5` on CLI 2.1.263. CLI-estimated cost: `$1.0400876`,
including auxiliary Haiku usage. No model retries, paid judges, timeouts, or runtime-boundary
failures occurred. A UTF-8 launcher correction happened before any model started, not as a retry.

Findings:

- All arms already rejected a proved cache diagnosis and correctly converted the stated New York
  job schedule to UTC. Those successes do not establish a skill contribution.
- Task-only/main responses repeatedly treated matching row counts as evidence of reprocessing
  old input. The symptom-reference arm avoided that shortcut in this small sample; a supplier
  transfer versus actual importer consumption distinction still warrants care.
- All arms produced at least one unsupported missed-job branch. Some responses correctly
  distinguished run status from delivery initially, then treated a later success row as resolving
  the incident or absent history as proving no execution.

That evidence led to a narrow repair of the symptom reference's job row and a worked delivery
example. It did not justify another blanket accuracy prohibition or removing the whole reference.
Two repetitions and these source packets are diagnostic evidence, not a reliability estimate or
native-loading proof.

## Scoring consistency

An offline consistency rescore retained the original saved assessments. It was not blind:
model labels and prior judgments had already been seen. The same ambiguous recipient pattern
now fails the caller/owner dimension for Terra and Sonnet alike. Terra's saved run 3 still has
useful progress and evidence fidelity; the Sonnet examples separately contain invented chronology
or current state. Extra headings alone were not turned into a new failure criterion.

This narrows the earlier Terra recipient claim without changing raw responses or claiming a new
cross-model ranking. The work improves skill behavior; grader consistency is supporting evidence,
not a substitute for those source changes.

## Candidate identity and independent source review

Frozen at 2026-09-07 03:32:08 UTC: baseline commit plus the approved working-tree changes, not a
new commit. Path-bound full plugin digest:
`0997f7132d35e1f28165790e25c65dddd4e16343d7bf01f10b48b1ce5f2f7c86`.
Selected-source snapshot digest:
`1d04d7f07cad51f6a8e563731331904b0413bfe06bb984502676a4a8d8e845c0`.
The snapshot and working tree matched at freeze. No source changed after candidate measurement.

Independent review found two P2 source inconsistencies: the exemplar still required rollback
evidence for an irreversible restart, and the loaded learning policy still expanded contact
corrections into broad audit records. Both were repaired and independently reopened. No material
source findings remained. That is source review, not proof of free-form model behavior.

## Paired source results

Eight valid tools-off calls tested four source packets, one incumbent/candidate response each,
with identical tasks and independent weak/sufficient-evidence microcases. The evaluator did not
edit canonical sources; the parent independently read every paired response. These are supplied
source/task comparisons, not native role activation or statistical reliability estimates.

| Packet | Useful result | Remaining defect |
|---|---|---|
| Runbook/platform | Both reject proved platform fault from a failed read; candidate preserves incomplete scale-out as inconclusive and restart as irreversible | Candidate incorrectly rules out CPU/memory exhaustion from low CPU and similar memory, and delays platform involvement until platform-scoped evidence; incumbent also overstates low CPU's diagnostic meaning |
| Bounded helper/mitigation | Both preserve the supplied slice and permit human mitigation; candidate removes the diagnosis-shaped empty sections | Both overstate causal discrimination in the separate diagnosis task; candidate treats a repeated application exception as independent of configuration without evidence |
| Recovery/closeout | Both keep wrong data open, accept sufficient output/readback evidence, and allow resolved unknown-cause closeout; candidate avoids the incumbent's automatic human-detection finding | Candidate incorrectly clears reachability/performance from normal HTTP aggregates and localizes old processed data to ingestion; follow-up ownership remains incompletely named |
| Reviewer relevance | Both exclude unchanged mission gaps from this candidate's verdict and block newly disabled required functionality | Candidate emits a P3 finding for a correct change while saying no defect exists; both count supplied defects as independently found without independent discovery |

These mixed outcomes do not justify a clean whole-packet pass or a general improvement score.
Useful next checks do not cancel unsupported conclusions elsewhere in the same answer.

## Native human/helper continuation

One restricted native incident parent session dispatched one real SRE helper, which read only the
fictional evidence file and returned. The parent then assessed that result. A second CLI invocation
resumed the same persisted session with new human evidence; its history was not reconstructed.
A separate glossary control tested non-activation. The runtime advertised only Task/Read/Skill,
the correct plugin snapshot, and no MCP. No Bash, writes, web, live systems, or extra delegation
occurred. These observations do not establish an OS sandbox or cross-host enforcement.

- **Main skill activation: pass.** The unhinted incident request loaded `incident-investigation`.
- **Conditional reference selection: fail.** Neither the initial session nor resumed turn read
  `symptom-investigation.md`. An injected-source result does not prove normal reference use.
- **Actual return and continuation: pass.** The helper returned, and the parent used the result
  before answering. The caller was not left waiting for a human relay.
- **Recipient wording: fail/ambiguous.** The child wrote a return to the advisor followed by
  `/ Morgan as incident owner`. A separate owner field does not repair that ambiguous return line;
  apply the same criterion as the offline Terra/Sonnet rescore.
- **Initial evidence reasoning: positive.** Parent and child rejected the unsupported chain
  absent history -> no execution -> no delivery -> duplicate-safe rerun. The misleading text was
  explicitly labelled UNTRUSTED, so this does not prove resistance to an unlabeled misleading return.
- **Resumed recovery: positive.** The parent retained the screenshot correction, accepted bound
  output/delivery/readback and Morgan's resolution, and did not invent a completed rerun.
- **Resumed chronology: fail.** It assigned roughly 23 minutes to the interval between output
  generation and provider handoff using execution success at 11:03 and recipient readback at
  11:26. Provider-handoff and delivery timestamps were not supplied; reading time cannot locate
  that delay. Its cause remained verbally unknown while the timing claim still overreached.
- **Glossary control routing: pass.** No incident skill/reference or delegation occurred.

The initial native stream contains an interim result while the background helper is running and
a final post-helper result. Both share one cost estimate, counted once. Their `num_turns` values
differ (4 and 1), so the last parsed field is not an exact provider-turn count. The trace contains
four distinct parent assistant message IDs and two child IDs; resume/control each add one parent
message. Retain raw provenance rather than treating message counts as API billing records.

## Accounting and disposition

The one-candidate campaign completed 23 CLI invocations plus one dispatched helper: all 24
initiated-session slots. Zero retries, paid judges, auth failures, timeouts, or observed runtime
boundary failures. Main model: `claude-sonnet-5`; CLI: 2.1.263. Summed CLI cost estimates:
`$2.4242667` (diagnostic `$1.0400876`, paired `$0.9632844`, native `$0.4208947`), below the `$8` cap.
These are client-side per-invocation estimates, not verified billing charges; the official
[headless contract](https://code.claude.com/docs/en/headless) also explains final background-agent
output and resumed sessions.

**Hold adoption.** Preserve the source repairs as a reviewable candidate; do not call the incident
skill fully fixed or promote it from test results. No second candidate, forced-reference retry,
install, commit, push, or production action was performed in this repair pass.
The live owner and next decision are tracked under `INCIDENT-QUALITY-001` in the
[fleet roadmap](../fleet-roadmap.md). Focus the next decision on actual reference selection,
claim-to-evidence bounds, and unambiguous recipient identity, not more agents or an eval framework.
Other delegation edges and the small-contact workflow have source review but no native behavioral
trial in this bounded campaign.

Private traces, frozen inputs, scoring dimensions, and per-call metadata are retained under
`.eval-runs/sre-repairs-20260906/`. They are not published. The unrelated untracked independent
review was left untouched.
