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
but no USD cost. Its dollar cost remains unknown, never zero. The testing block's
accounting must expose that gap and cannot certify an aggregate dollar total from
these records. Bounded subscription execution versus mandatory dollar metering is
an explicit owner decision; no API credential or paid fallback is introduced here.

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
