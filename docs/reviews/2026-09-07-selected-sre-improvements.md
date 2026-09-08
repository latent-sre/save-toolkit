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

Pending final source review and the reserved candidate invocations. Parser tests and a well-formed
scenario do not complete this measurement or establish behavioral acceptance.

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
Context7 independently returned the documented process-scaling command; no live operation was run.

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

Implementation and focused verification are pending. The confirmed defect is that normal rubric
graders do not supply the judge's optional expected-model pin, and normal scenario/cache provenance
does not bind a calibrated judge configuration. Calibration's separate pin is insufficient evidence
that an ordinary result came from that instrument. The selected repair will explicitly bind the
normal path to an applicable calibration receipt and retain full structured judge identity.

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

Final integrated verification and total allowance are pending. Native runner/grader verification
passed 172 tests and 68 subtests before the final cost-cap predicate. The extra cost=0.76 control
then reproduced a false PASS; after repair, the focused cost/regrade checks passed two tests and
15 subtests. The native batch adds 470 evaluator lines (tests included) and 319 skill bytes. Its
ceiling adjustment is 9,900 to 10,250 evaluator lines and 579,000 to 579,300 skill bytes; later
selected changes receive their own measured allowance.

The evaluator extension adds regression coverage for false completion, ordering, session, and
runtime-boundary credit; it does not justify deleting existing checks to fit a byte/line ceiling.
Structural results and static reviews remain separate from the bounded native semantic evidence
and human acceptance.
