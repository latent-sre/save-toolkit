# Multi-model evaluation follow-through

This execution plan implements the owner's WP-04, EVAL-005, ROUTE-007, HANDOVER-001,
WP-09 and WP-10 request from refreshed main `b4bb96a7`. Live item status remains in
the [roadmap](../fleet-roadmap.md); this is a run contract, not another backlog.

## Scope and order

1. Prepare a reusable testing block for native Sonnet and structured Codex
   GPT-6.1-Sol, GPT-6-Luna and GPT-5.6-Terra. The owner confirmed Terra explicitly.
   Use the existing runners and result formats, with exact model and source bindings.
   No replacement framework, cross-model average or claim of native Codex plugin parity.
2. WP-04: use the five frozen cases 7/21/24/80/102. The owner now requests both Linux
   and Windows execution. Preserve separate host results; neither establishes the other.
   Prove the observation/hidden-answer boundary before a model sees the evidence.
3. EVAL-005: repair demonstrated instrument defects, reproduce the fixture query,
   resolve the no-data contract, then run the bounded fixture campaign.
4. ROUTE-007: validate the completed automatic-routing selection and run it once.
   `pcf-deploy` is human-invoked only; measure explicit invocation separately rather
   than introducing an impossible automatic-discovery expectation.
5. HANDOVER-001: prepare and run two actual human tabletops with two responders and
   a facilitator. AI simulation cannot meet the human-use requirement.
6. WP-09: use the selected Docker host, exact SWT/Harbor cases, quota-bound images,
   model-free smoke and independent verifier before candidate trials.
7. WP-10: run the bounded multi-model controls, then assess the outstanding quotation,
   reliability exception-path and GCP-01 B findings against exact saved evidence.

Independent offline preparation may run concurrently. Model trials remain serial.
Native checks for routing, hooks and helper continuation remain native-only measures.

## Budget and evidence

The owner approved **USD 40 total**, shared across all requested testing, including
failed attempts, retries and any judges. No package receives a fresh USD 40 allowance.
No automatic retries or model substitution. Start with one trial per selected smoke
case and model. Preserve the full requested coverage when a schedule stops.

The initial matched testing block is eight attempts: benign/malicious log cases on
each of four models. It invokes no rubric judge; allow about one hour for reading
the eight traces. Native invocations request a USD 0.75 CLI limit; that limit may
overrun by the final response and is not a provider-side financial guarantee. Record
actual reported cost before scheduling another invocation. Stop metered scheduling
when cost is unavailable or when the remaining aggregate budget cannot cover the
next bounded invocation and its possible overrun. Reserve the majority of the budget
for WP-04 and later requested campaigns; do not exhaust it on smoke repetitions.

Codex's existing subscription adapter reports tokens and bounded time/tool calls,
but no USD cost. Its dollar cost remains unknown, never zero. The owner explicitly
selected bounded subscription runs for these models. The testing block's accounting
still exposes that gap and cannot certify an aggregate dollar total from these records;
its conservative `ready_for_further_spend` field remains false. This owner decision
permits the named bounded subscription attempts, not an unbounded schedule. No API
credential or paid fallback is introduced here; metered testing shares the USD 40 cap.

Before each run, bind the candidate plugin digest, scenario/oracle digest, runner
digest, CLI, model, host/account and invocation limits. Keep raw records private
under `.eval-runs/followthrough/`. Report mechanical, semantic, policy, cost and
cleanup results separately. Exact-candidate acceptance remains a human decision.

## Linux WP-04 boundary

`evals/wp04_linux_cli.py` is an opt-in executable wrapper for the existing native
runner. It uses an unprivileged bubblewrap namespace exposing the read-only staged
observation repository and plugin, the temporary clean-room credential directory,
system runtime files and the resolved Claude executable. Evaluator answers, the
source checkout, source cache and reviewer packet are not mounted. Network remains
available to the CLI service; this is not a network sandbox or a general execution
profile. Only the declared Read/Grep/Glob/Skill profile is accepted.

The model-free namespace control must prove an observation is readable, an external
answer file is absent and writes to the observation mount fail. Actual CLI startup,
plugin load, advertised tools, source reads and output collection remain separate
live checks. Failure of any boundary or identity check stops the pilot. The wrapper
does not change Windows behavior or authorize non-read-only native profiles.

The owner subsequently deferred Windows WP-04 and Docker-based WP-09 execution
because no Windows connection is available in this session. Their prepared packets
and required evidence remain intact; they are not completed benchmark outcomes.
The Windows run packet retains its unelevated-account and runtime-boundary checks.
Both hosts use the same manifest, observations and candidate bytes; host-specific
runtime receipts are recorded separately. A missing Windows connection or Docker
host blocks those executions, not independent offline preparation.

## Verification and completion

Use regression tests for the refusal grader, six routing cases, testing-block
identity/accounting, invocation limits and actual Linux namespace behavior. Run
focused checks first and the coordinated heavy suite once at the integration
boundary. The [multi-model testing guide](multi-model-testing.md) describes the
reusable commands. The [tabletop packet](handover-tabletops.md) supplies the human
exercise. Passing offline tests does not complete any unrun campaign or human task.

## WP-10 current-candidate continuation

Freeze executable revision `bb9e02c4`, the unchanged five continuation case digests,
plugin, shared-runner and Codex-adapter digests before launch. Use native Sonnet and
structured GPT-6.1-Sol, GPT-6-Luna and GPT-5.6-Terra on this unelevated Linux host.
These are new observations on current candidate bytes, not causal confirmation of
the historical repairs or replacement for accepted historical results.

Run three adjacent benign/malicious log-role pairs per model, three reliability
assessments per model, then one GCP-01 A/B pair per model: **11 attempts per model,
44 total**. Rotate models between repetitions; each pair stays adjacent. No automatic
retries, fallback model, rubric-judge calls or edits to the frozen candidate during
the campaign. The native and structured transports remain separate populations.
Native cases retain declared turn limits and a 300-second wall guard, with a requested
USD 0.75 invocation limit for quotation and USD 2 for reliability/GCP. Codex retains
high effort, 300 seconds and 32 fixture calls per attempt. Estimate USD 4 reported
native cost and 1.5 hours of review; the USD 40 total is shared with the USD 9.589437
already reported. Codex subscription dollars remain unknown under the owner's
bounded-run approval. Reconcile every completed native cost before scheduling more;
stop for unknown cost, identity drift, incomplete instrument evidence or insufficient
aggregate headroom. Preserve all missing slots if a schedule stops.

The unchanged cases are `build-injection-log-role-{benign,malicious}`,
`build-reliability-engineer-proportionate-options`, and `build-gcp01-startup-{a,b}`.
Treat the GCP human-review marker as its declared pending assessment, not a failed
transport. Review every reliability document and GCP response against the full
existing semantic contract, including false-return versus exception behavior,
admission placement, factual timestamps, serving-start monitoring, ownership and
recovery limits. Keep independent AI proposals separate from human acceptance.
This continuation does not, by itself, discharge unmeasured wider-lane/native
obligations or promote any candidate; audit the remaining WP-10 scope afterward.

The first phase stopped after Luna's first benign log-role attempt used a pure
literal metadata filter with `||`, which the reader incorrectly rejected despite
the unchanged prompt permitting literal name/description filters. A narrow reader
repair admits AND/OR combinations of those same bound literal predicates. It changes
no candidate prompt, tool grant, case, plugin or shared native runner. Preserve the
original INCONCLUSIVE and phase-one source bindings. Freeze a second reader phase,
then fill only the 39 unattempted slots, including the first Luna malicious arm.
The private old/new comparison proves the saved prompt and original record are
unchanged; offline reassessment is separate from the original verdict.

A third phase follows three further observed metadata-only variants: a local
catalog alias, a fixed name/description projection, and a parenthesized boolean
filter. The closed parser admits only those catalog operations, with size, token
and nesting bounds; arbitrary JavaScript and fixture-call variants remain unsupported.
The metadata-protocol paragraph now describes those forms, so phase-three prompts
are **not byte-identical** to earlier phases. Core task, cases, plugin and native
runner remain unchanged. Retain phase-specific bindings and original inconclusives;
do not pool them as an identical-condition model comparison. The first 26 attempts
are retained, and only the remaining 18 slots run under this final protocol phase.

## WP-10 repair comparison

The owner's subsequent request selects WP-10 repair and HANDOFF-002. The latter is
an offline grader repair and adds no model calls. For WP-10, compare the unchanged
plugin from integration revision `a3e5edf2` with a candidate changing only the SRE
quote/closed-schema instructions, retry-path analysis placement and Cloud Run
startup/evidence guidance, plus their generated adapters. Cases, graders, runtime,
model identifiers and the final Codex metadata protocol stay identical between arms.

Run three log-role pairs, three reliability assessments and one GCP A/B pair per
model **per arm: 88 attempts total**. Counterbalance arm order across repetitions
and models; keep each benign/malicious or GCP pair adjacent. All four named models
retain their existing native/structured transports. Use 300 seconds per invocation,
32 Codex fixture calls, high Codex effort, native requested caps of USD 0.75 for
log-role and USD 2 for reliability/GCP. There are no retries or rubric-judge calls.
Stop on incomplete instrument evidence, source/runtime/model drift or insufficient
remaining aggregate budget; retain missing slots. Native estimate is about USD 3,
within the original USD 40 shared limit and USD 10.564769 already reported. Codex
dollars remain unknown under bounded subscription use. Reserve USD 4 of headroom
before starting each invocation; do not spend the full allowance on a final response.

Freeze both exact plugin revisions/digests, the common runner and adapter digests,
case bindings and limits before execution. Independently assess all 24 reliability
documents and 16 GCP responses using opaque labels that withhold model and arm.
Apply the full existing semantic criteria and dispositions; count quotation and
output-format failures mechanically. Improvement must address the motivating
failure without regressing the paired controls. Preserve per-model/per-transport
results, uncertainty from the small sample, all failed observations and original
records. Withdraw any unsupported repair; run completion never promotes a candidate.
