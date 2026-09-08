# Selected SRE improvements — candidate evidence

The owner selected native advisor/helper/resume testing, Apps Manager mitigation guidance, one
usable critical-service context record, bounded observability work, separation of security review
from architecture escalation, judge identity binding, and the SPL error-rate denominator on
2026-09-07. This record supports the unresolved `INCIDENT-QUALITY-001` and `CONTEXT-001` decisions.
It does not reopen the other deferred campaigns or establish human acceptance.

## Revision and scope

- [verified] Base: `0450ea58d3403a56ae7cc94aef979bd033076de9`, refreshed `origin/main`.
- [verified] Candidate branch: `work/sre-incident-improvements-20260907`, isolated under
  `.worktrees/sre-incident-improvements-20260907`. Unrelated work in the main checkout was preserved.
- Canonical sources own the changes; their Copilot/VS Code projections are regenerated.
- No production operation, dashboard write, publish, push, merge, or model-judge call is part of this work.

## Native incident conversation

The incumbent runner supported individual routing/contract/build trials. The candidate adds one
actual same-session human follow-up to a native, unpinned advisor scenario, retaining raw initial
and resumed traces. A child launch acknowledgement alone is insufficient: asynchronous completion
must match the dispatched tool and task, and the parent must speak after that completion.
Reference reading must belong to the initial parent and finish before helper dispatch. Native
structural verdicts explicitly leave semantic assessment unverified.

Independent review closed five potential false-PASS paths: a wrong parent model, emitted tools
outside the advertised set, advisor loading after dispatch, an explicitly backgrounded launch with
incomplete receipt metadata, and damaged per-invocation evidence during regrade. Both live and
regrade paths apply the same native boundary checks. Missing, invalid, or over-$0.75 recorded cost
stops continuation. These are tested instrument properties, not observed runtime escapes.
The independent static recheck cleared those repairs at
`52f00e9a628a20bccd18d95df3bb70574802ef6c`. It also cleared the private candidate driver's
glossary cost/tool postconditions. Neither verdict substitutes for native semantic assessment.

The frozen comparison uses two independent synthetic daily-statement incidents per arm, each
with one helper and one owner correction, plus two fresh glossary controls per arm. The initial
prompt names neither the incident skill nor its reference. Controls offer `Skill,Read`; incidents
offer `Skill,Read,Task`. Strict empty MCP, isolated credential-only host configuration, a neutral
workspace, and a frozen plugin snapshot bound the observed tool/read surface. This is not an OS sandbox.

The fixed ceiling is 12 parent CLI invocations plus four helper children, $6 summed CLI estimates,
$0.75 per invocation, and 240 seconds per invocation. There is one candidate, no retries, and no
paid judges. The selected model is `sonnet`, with resolved parent identity `claude-sonnet-5`;
Claude Code is `2.1.263`. Raw owner-only evidence lives under
`.eval-runs/sre-improvements-20260907/`; `acceptance.md`, `native-cases.json`, and the incumbent
sampler were frozen before the candidate.

### Incumbent result

- [verified] Plugin SHA-256:
  `450f5fc1d6f9ad852559b574fc3a88e703503858eef3950ca10867bba1b15c69`.
- [verified] Six parent invocations and two helper children completed; recorded cost `$0.8358384`.
  No observed runtime/tool/read/plugin/model boundary issue was recorded in those six phases.
- [verified] Independent semantic assessment: repetition 1 met all eight frozen criteria;
  repetition 2 failed decision quality while selection, reference loading, actual helper return,
  same-session correction, recovery handling, and glossary scope passed.
- [sourced] In `native/incumbent/2/initial/stdout.jsonl`, raw line 50, the parent treated a completed
  scheduler row as narrowing the fault to delivery, and affected-recipient count as distinguishing
  delivery from execution failure. Neither observation supports that stage discrimination. It also
  misstated matching recipient readback as failing to establish whether delivery occurred at all.

The source repair keeps the routing description unchanged. A completion flag leaves processing,
publication, and delivery unconfirmed without matching output. Recipient count establishes impact
scope; either processing or delivery faults can affect one or many recipients. Matching readback
confirms receipt, while delivery time, path, and cause can remain unknown.

Repetition 1 retained two lesser overstatements: a rerun would destroy reconciliation ability, and
provider timestamps would establish the delay mechanism. Its full answer still retained the unknown
cause/timing, requested evidence through its owner, and performed no replay. Those limitations are
not erased by a PASS. Two repetitions are bounded observations, not a reliability estimate.

### Candidate result

[verified] **INCONCLUSIVE — authentication stopped the first candidate invocation.** The frozen
plugin came from clean plugin inputs at `234bafaa319cd0a99ac7337398c6df7199f9d0cc`, with SHA-256
`7e76dbc831b94b1928cae7f5ef18ef99cecd4ac4c72dcb14f5bf3472aadb0249`. Its private snapshot owns Git
commit `cfe040ea41971f6b02dd8e70edbd0e40e16b5473`; it does not inherit the enclosing main checkout's
HEAD. The outer manifest records both source and snapshot provenance.

The candidate incident uses the integrated runner with the exact frozen JSON prompt, evidence,
and correction strings. The incumbent used the retained sampler. Those instrument identities are
recorded separately; this was not an isolated causal comparison of only the prompt change.
`integrated-candidate-manifest.json` identifies the evaluator used for this attempt: its hashes
cover the final worktree harness. The older `candidate-manifest.json` records the freezer's
root-checkout harness inputs. These are different implementations and roots, not a line-ending
discrepancy; both instrument manifests hash raw file bytes. Plugin digests separately normalize
line endings. The consumed manifests and drivers remain unchanged.

The initial candidate response is:

> Failed to authenticate: OAuth session expired and could not be refreshed

Raw evidence is retained in `native/candidate/1/initial/` and the matching `integrated/` run.
It records zero model tokens, zero cost, no model-usage entries, and no tool calls or helper
dispatches. The runner stopped before the follow-up and glossary controls. Across both arms,
**seven parent invocations and two helpers** were initiated, with total CLI-reported cost
**$0.8358384**. A synthetic error response is not a candidate behavioral result.

[verified] Independent assessment of the retained initial trace, invocation metadata, and manifests
confirmed authentication failure, zero model usage, and absence of helper/resume/control evidence.
The assessor could not directly open the integrated run directory; the primary agent read its
provenance, grading, timing, and trace, which likewise record `INCONCLUSIVE`, structural-only
assessment, unverified semantics, and zero tokens/cost. The primary agent also verified byte-for-byte
identity of the retained stdout, stderr, response, and invocation files against that directory.
Neither assessment establishes candidate behavior.

The ordinary CLI still reports a saved claude.ai login; that status does not establish that the
isolated session can renew it. [sourced] The official [Claude Code error reference](https://code.claude.com/docs/en/errors#login-expired)
identifies this headless renewal failure and requires re-authentication. No credential values were
inspected or copied into this report.

### Continuation after authentication restoration

The owner subsequently reported that authentication should have been restored. The credential
file's modification time was newer than the failed attempt, and the isolated CLI reported a saved
login. [verified] The replacement invocation then reached `claude-sonnet-5` and recorded model
usage, confirming that authentication was restored for this run.

The reviewed continuation driver retained the original failed attempt and used separate
`native/candidate-after-auth/` and `integrated-after-auth/` paths. It preserved the exact candidate,
scenario, and harness identities and recorded the replacement allowance in
`candidate-after-auth-manifest.json`: at most 17 total parent/helper sessions, the same $6 ceiling,
and no further retries. The original contract and consumed drivers/manifests remain unchanged.

[verified] The first replacement conversation stopped before resume with the runner status
`INCONCLUSIVE: native tool denial/error`. The underlying error was a nonexistent file, not an
authentication or permission rejection. More significantly, the trace establishes an actual
one-helper scope violation:

- Raw line 20 dispatches an extra `Explore` helper to locate `evidence.md`.
- That child reads the supplied evidence file, then attempts `candidate-plugin/evidence.md`;
  line 29 reports that the second path does not exist. The child returns at line 33.
- Line 38 dispatches the requested `save-toolkit:sre-assistant` with the incident advisor and
  Morgan identified separately. The SRE helper reads the actual file and returns at line 50;
  the parent subsequently uses its evidence in the initial advice.

These line references are from `native/candidate-after-auth/1/initial/stdout.jsonl`, SHA-256
`0be58a6a12cbc669f566a6b2dc70a1652f3f667de70328fbe1a1f13fddf8cfa5`. The primary agent verified that
the retained stdout, stderr, response, and invocation files match the original integrated run.
The runner's zero-of-five structural summary is an inconclusive boundary result, not evidence
that advisor selection or the actual SRE return failed to occur. The extra dispatch is directly
observed noncompliance with the user's exactly-one-helper instruction.

[verified] Independent assessment of the retained trace against the frozen criteria:

| Criterion | Result | Raw evidence |
|---|---|---|
| 1. Advisor and reference before dispatch | PASS | Skill at lines 9–11; reference read at 16–17; first dispatch at 20 |
| 2. Exactly one bounded SRE helper | FAIL | `Explore` at 20, then `sre-assistant` at 38; caller/owner identity is preserved |
| 3. Successful SRE read, actual return, parent continuation | PASS | Read at 43–44; matching completion/result at 49–50; parent synthesis at 57 |
| 4. Evidence handling and feasible next checks | PASS | Parent rejects the unsupported duplicate-safe inference and preserves unresolved evidence at 57 |
| 5. Same-session correction and recovery | NOT RUN | No resume trace |
| 6. Recovery closeout and timing interpretation | NOT RUN | No follow-up response |
| 7. Bounded glossary | NOT RUN | No control invocation |
| 8. Tools, authority, helper count, and drift | FAIL | Extra child; Explore reads contents at 25–26 despite the locate-only instruction at 20 |

The SRE helper also assessed the colleague's inference at line 47 despite the extraction-only
dispatch at line 38. That is an additional assignment-scope miss. The final result at line 58
contains no permission denials; observed tools were Skill, Read, and Agent/Task, with no observed
MCP or model drift. The independent assessor used the retained copies; the primary agent's
byte comparison binds them to the integrated originals.

The continuation used one parent and two children, costing `$0.2897346`. Including the incumbent
and the earlier authentication failure, accounting is **12 total parent/helper sessions** and
**$1.125573**. No follow-up, glossary control, or second repetition ran after this boundary stop.
Same-session recovery and candidate acceptance remain unverified; authentication is no longer
the blocker. The failed conversation remains evidence, with no automatic retry or promotion.

The smallest proposed repair is to keep file resolution inside the single dispatched evidence
assignment: pass the supplied relative file and workspace context to that SRE helper, and return
a missing-file gap if necessary instead of creating a separate discovery helper. Keep the return
within its requested extraction scope, leaving assessment to the advisor. A fresh bounded candidate
must demonstrate these boundaries before the interrupted resume/recovery checks can finish.

### Helper-scope repair

[verified: source] The owner requested continuation, and `c53ed2b67d526aad1b80cc1767b36ab0e44c82ea`
repairs the two observed scope failures. The advisor counts discovery against the caller's helper
limit and sends supplied file paths/workspace directly to that helper. For extraction-only work,
the SRE helper returns the requested material and document gaps for the caller's assessment;
it does not evaluate quoted claims or select new checks. Immediate material-risk reporting,
human ownership, and tool/delegation permissions remain unchanged. Independent static review
found no conflicting return requirement or removed risk-reporting duty.

The new frozen plugin SHA-256 is
`5ee522fe03636b6f12c98445d6af724790ac5a56077b2bfe78e1e7668f5dc68c`; its private snapshot commit is
`8dce7a139bdde72d5532fc68cb4e9d1f09f1b546`. Exactly two model-input files differ from the previous
candidate: `agents/sre-assistant.md` and `skills/incident-investigation/SKILL.md`.

One new 18-line regression proves that an error-free completed `Explore` followed by a completed
SRE helper is rejected before resume. Existing enforcement already did this; the test preserves
the observed boundary independently of the previous trace's missing-file error. Native checks
passed **19 tests / 41 subtests**; skill assets and generated adapters passed **42 tests /
122 subtests**, with two Windows directory-symlink permission skips. Gate A passed **4/4**.

`helper-scope-acceptance.md` freezes this continuation: one new candidate, the same scenario,
case/evidence/correction/control strings, evaluator, CLI, model, and eight criteria. Two fresh
incident conversations and two glossary controls reserve six parents and two helpers. Including
the prior 12 sessions and `$1.125573`, the amended ceiling is 20 total sessions and the same $6
cap, $0.75 per invocation and 240 seconds each. No further retry is reserved. The old freezer's
16-session metadata is historical; the new acceptance record and run manifest govern this slice.
The comparison measures the two-rule repair together, and the incomplete baseline establishes
neither resumed behavior nor a reliability rate.

[verified] Both fresh initial conversations dispatched exactly one SRE helper. Repetition 1
completed selection, reference loading, actual helper return, and same-session resume: structural
**PASS 5/5**. Its glossary control also remained bounded. Independent semantic review nevertheless
failed criteria 4 and 6:

- Initial raw line 70 treats other recipients missing output as evidence of a shared delivery-stage
  failure. Recipient count establishes impact scope, not the failing processing/publication/delivery
  stage.
- Resumed raw line 15 treats one provider handoff timestamp as sufficient to localize the roughly
  20-minute execution-to-read gap. Actual delivery time is absent. It also invents a normal delivery
  path and certainty that a rerun would have duplicated delivery.

The same-session transition is real: initial and resumed init/terminal events match, and the
follow-up invocation explicitly resumes that ID. The parent accepted the corrected records and
Morgan's recovery decision. The SRE helper's asynchronous launch acknowledgement was followed by
a matching completed notification before parent synthesis. These mechanics passed independently
of the semantic failures. Extraction-only behavior was **not exercised** in this repetition:
the advisor explicitly asked its helper to assess the colleague's inference.

[verified] Repetition 2 completed its initial SRE exchange but stopped before resume/control with
`INCONCLUSIVE: native tool denial/error`. The advisor's raw line 25 asks the helper to check both
the actual workspace and the plugin root. The helper reads the supplied file at lines 30–31,
then tries the unnecessary plugin-root path at line 33; line 35 reports file-not-found. A single
helper does not by itself prevent speculative extra reads. The skill does contain a rough
fifteen-minute/impact-growth coordination heuristic, including sooner escalation for customer
impact or another team's help. The initial answer strengthens that into a multiple-recipient
cutoff and says coordination is not yet needed without establishing impact or criticality.
Independent review therefore fails criterion 4. It confirms that extraction-only compliance was
exercised and observed: dispatch line 25 forbids judging the colleague's inference, and return
line 38 preserves the claim without evaluating it. Gap-closing evidence suggestions were explicitly
allowed by the dispatch. The matched completion at line 41 precedes parent synthesis at line 66;
the terminal result at line 68 contains no permission denials.

Independent frozen-criterion results for the new candidate:

| Criterion | Repetition 1 | Repetition 2 |
|---|---|---|
| 1. Advisor and reference before dispatch | PASS | PASS |
| 2. One bounded helper; caller/owner preserved | PASS | PASS |
| 3. Successful child read, actual return, parent continuation | PASS | PASS |
| 4. Evidence handling and justified next steps | FAIL | FAIL |
| 5. Same-session correction and human-confirmed recovery | PASS | NOT RUN |
| 6. Recovery closeout and timing interpretation | FAIL | NOT RUN |
| 7. Bounded glossary | PASS | NOT RUN |
| 8. Tools, authority, helper count, identity | PASS | PASS |

Raw paths are `native/candidate-helper-scope/<repetition>/<phase>/stdout.jsonl`:

| Trace | SHA-256 |
|---|---|
| 1 / initial | `07c6589faca77e806cb2d5aa35d055e29b105e5a23bcb882f5095506ddf26dc3` |
| 1 / resume | `d99deb03aba36c7145d468578d715afddd87a37a0cc2d69be30ebad9cdea63c1` |
| 2 / initial | `64a543a7eed3a716e2f3d8836b1ea6b7a0be01146dc04a02730a1c8e72a37e2f` |

The primary agent verified byte-for-byte identity of each retained initial/resume stdout, stderr,
response, and invocation file against its integrated original. Source and snapshot still match the
frozen plugin digest. This candidate used **four parent invocations and two helpers**, costing
**$0.7414825**. Total campaign accounting, including the earlier failed attempts, is **12 parents
and six helpers (18 sessions)** and **$1.8670555**. Repetition 2's resume and glossary did not run;
no completion marker, further candidate, retry, or paid judge was produced.

The observed helper-count defect is absent in these two new samples; the broader incident
decision-quality criterion still fails. This is neither a reliability estimate nor acceptance of
the candidate. Further work must address exact file resolution and the unsupported conclusions
before treating another successful conversation structure as readiness.

## Apps Manager mitigation planning

The mitigation table now pairs the human's console path with the release owner's CLI/pipeline
fallback. It carries exact foundation/org/space/app identity, selected process, capability and
permission uncertainty, backout, and timestamped readback through the action decision. Missing or
unclear UI controls produce a release-owner packet; they do not require the responder to install `cf`.

[sourced] Navigation is conditional on VMware's 2023 TAS 2.12 guide, pp. 1145–1157
([versioned manual mirror](https://manuals.plus/m/f716ea2ede1f52c2fb9c9496bd199abbede3c0aa1727dab518af606551e1b71f)).
It documents Overview/process scaling, Routes, Settings variables, and revision Redeploy. Current
Broadcom pages did not provide retrievable matching procedures during this review. The older manual
does not prove this foundation's installed version, controls, permissions, or restart semantics.

[sourced] Cloud Foundry's [rolling-deployment guide](https://docs.cloudfoundry.org/devguide/deploy-apps/rolling-deploy.html)
and [cancel-deployment reference](https://cli.cloudfoundry.org/en-US/v8/cancel-deployment.html)
bound cancellation and revision interpretation. A restage is not an existing-droplet restart;
cancellation does not restore variables or service bindings. The process is preserved explicitly
with `cf scale --process`, because the [CLI default is web](https://cli.cloudfoundry.org/en-US/v8/scale.html).
The selected-instance restart also preserves `--process`; its [default is likewise web](https://cli.cloudfoundry.org/en-US/v8/restart-app-instance.html).
Whole-app restart is labeled separately. Context7 independently returned the documented
process-scaling command; the exact instance-restart syntax required the CLI reference. No live
operation was run.

[unverified] Target-foundation controls, current deployment/package state, and target readback remain
owner-supplied operational evidence. A matching current state does not time an interrupted action;
unknown outcomes require reconciliation before retry. No secret variable value enters a packet.

## One real critical service through the context contract

This item remains incomplete. The pending owner input is the critical service, environment, and
approved context-record location. A fictional checkout record cannot establish a usable real service.

[verified] The newer producer worktree
`F:\repos\sre-context\.worktrees\context001-lifecycle-review` was clean at
`be29c9428e41d957c8e889c612092bcf98538b3d` on `work/context-001-lifecycle-review`, seven commits
ahead of refreshed producer main `903ac830155059d2d357e7f446378752ea8f5a38`. The all-state PR query
for that branch returned none. This is local branch evidence, not a merged producer claim.

[verified] Its current requirements mirror matches this consumer's `v1alpha2` contract, including
freshness, forbidden paths, and optional deployment. With Python 3.12.10, PyYAML 6.0.3 and
jsonschema 4.26.0, `python -m unittest discover -s tests -q` passed **86 tests**. The offline
`sre_context.cli resolve` command consumed this candidate's exact
`skills/service-lifecycle/context-requirements.yaml` with explicit fixture selectors
`tenant-alpha / checkout-api / production`, `--allow-fixtures`, and `--as-of 2026-09-08`.
The result was `resolved/v1alpha5`, `requirements.satisfied: true`, age 15 days within `P30D`,
and optional missing `knowledge` and `pipelines`.

The producer still enforces fixture mode, `nonOperational: true`, fixture-only host/identifier
restrictions, and `actionSelection: prohibited`. Its projection contains resource references and
observability locators; it is not a complete real-service operational record. The consumer currently
uses an optional service-lifecycle sidecar, not a proven incident context loader.

After the owner supplies the service source, the smallest next slice is to identify the required
service fields and approved storage, add a versioned operational record/projection through the
existing producer contract while retaining fixture restrictions, then exercise explicit target
resolution, fresh and stale/missing records, console/telemetry navigation, ownership, and handoff
for that service. Operational context must continue to grant no execution authority. Producer
compatibility is verified; real-service onboarding and operational usability are not.

## Bounded agent work

- [verified: source] `observability-engineer` now answers a bounded explanation or health question
  with evidence and limits, then stops. Requested changes use only their matching alert, dashboard,
  or collector steps. A query repair does not initiate other design work.
- [verified: source] `software-engineer` now separates required independent security review for
  auth/input/secrets/crypto from architecture escalation. Scoped fixes remain builder-owned unless
  they also meet an above-builder trigger, consistent with the existing engineering ladder.
- [unverified] These source-alignment changes have not received separate live model comparisons.
  Tool grants, delegation edges, and the independent review boundary are unchanged.

## Judge identity binding

[verified] Implemented in `5debf2a9`. Both normal grader forms now require an explicit applicable
calibration before starting the evaluated agent. The binding covers the canonical corpus and
rubrics, recomputed agreement, concrete resolved judge model, executable arguments, timeout, and
cache selection. Execution identity controls cache eligibility; the separate receipt identity
controls run attribution. Ambient settings cannot redirect the bound call.

Complete call records retain model, response/rubric identities, verdict detail, cache status,
cost, and duration. Offline regrade keeps the original binding and judgment without reopening
receipt files or calling a model. Independent review closed two additional gaps: a bound direct
API could override the rubric text, and missing/malformed calibration inputs after a call could
be mislabeled as candidate failure while losing complete call metadata. Both have red/green
regressions and passed the independent static recheck.

[unverified] No live judge or calibration calls were run. Legacy receipts do not contain the new
execution/source evidence and cannot certify ordinary rubric trials. A fresh applicable calibration
is an explicit future operation; the runner does not initiate it. Runtime model identity still
relies on the CLI's existing `modelUsage` attribution. Frozen executable path/arguments/timeout
are not binary or host attestation, and calibration does not promote a fleet candidate.

## SPL error-rate denominator

[verified: static arithmetic] The per-class query now calculates all eligible requests by phase
before grouping by error class. One failure among 100 requests before and ten among 100 after
produce `0.01` and `0.10`. The old per-error-class denominator produces `1/1` and `10/10` when
only failed events carry the class, hiding the change. Successful requests without `error_type`
enter the phase-wide denominator before grouping.

Both query variants require equal absolute windows and one completion event per eligible request
or attempt. Missing/invalid HTTP status leaves the rate null; numeric sentinels and fractional
codes cannot masquerade as successful classification. Missing traffic or an absent phase/class
does not establish a healthy zero.

[sourced] This construction follows the official classic SPL 10.4
[eventstats](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/eventstats),
[stats](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/stats),
[conversion](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/evaluation-functions/conversion-functions),
and [conditional-function](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/evaluation-functions/comparison-and-conditional-functions)
contracts. Context7 retrieval was supplemented with the exact classic reference pages rather than
assuming returned SPL2 examples were interchangeable. [unverified] No live Splunk query was run;
field extraction, single-status semantics, request population, and coverage need target validation.

## Verification and weight

[verified] Repository checks at `234bafaa` passed **532 tests and 1,020 subtests**
in 90.02 seconds. Four checks skipped: three Windows directory-symlink cases lacked permission,
and one shell-requirement check is CI-only. Gate A passed **4/4** structural steps; scenario
validation passed **66 scenarios / 329 expectations**; whitespace and generated-adapter checks
passed. The test interpreter was Python 3.12.10 with pytest 9.1.1 and PyYAML 6.0.3, with Git Bash
available on PATH. Raw output is in `.eval-runs/sre-improvements-20260907/full-pytest-final.txt`.
The subsequent helper-scope delta has the focused verification recorded above; the 532-test
result is not represented as a fresh full-suite run on that later revision.

Native runner/grader verification passed 172 tests and
68 subtests before the final cost-cap predicate. The extra cost=0.76 control then reproduced a false
PASS; after repair, the focused cost/regrade checks passed two tests and 15 subtests. Judge
implementation checks passed 244 tests and 101 subtests before its two review repairs; the final
focused repairs passed 22 tests and 12 subtests. These unit checks were offline with model calls
mocked; the separately reported incumbent native conversations used the live CLI.

[verified] Final measured allowances on this Windows checkout:

| Total | Baseline | Candidate | Ceiling before → after |
|---|---:|---:|---:|
| Evaluator Python lines, including tests | 9,753 | 10,702 | 9,900 → 10,720 |
| Canonical skill bytes | 578,906 | 583,967 | 579,000 → 584,000 |
| Canonical agent bytes | 114,962 | 115,672 | 115,000 → 115,700 |

The native contract adds 470 evaluator lines and 319 skill bytes; judge attribution adds 461
evaluator lines, including 270 test lines. Apps Manager planning adds 2,579 skill bytes, SPL adds
1,911, and the two original agent-scope rules add 486 agent bytes. The helper-scope repair adds
18 test lines, 252 skill bytes, and 224 agent bytes. All seven existing context-cost profiles remain
within budget. These are repository weight measurements, not measured runtime token savings.

The evaluator extension adds regression coverage for false completion, ordering, session, and
runtime-boundary credit; it does not justify deleting existing checks to fit a byte/line ceiling.
Structural results and static reviews remain separate from the bounded native semantic evidence
and human acceptance.
