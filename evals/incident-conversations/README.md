# Native incident conversation pilot

These are synthetic, authored cases. The twelve paired two-message pilot cases cover INC-01–06.
INC-05 and INC-06 are held out as complete families until candidate/model/rubric settings freeze;
loading or structurally validating them is not permission to tune against their outcomes. The two
six-message worked profiles exercise supplied helper evidence and a separately requested actual
turn-four helper. Four branching profiles cover both variants of INC-01 and INC-03. These are 18
execution profiles over six independent families, not eighteen independent incidents.

`manifest.json` pins scenario/review bytes. `review/` is harness-owned and must never be staged
into the candidate fixture, prompt, or early-turn judge context. Expected outcomes, valid alternatives,
known bad/unavailable controls and the one changed paired fact are human review material. No semantic
case or model behavior has been accepted. Structural PASS establishes runner contracts only.

The opt-in schema is `conversation.profile: incident-v1` with one null/canonical helper in `helpers`
per invocation, `partition: development|held-out`, and `manual_review: pending`. An optional
`turn_graders` list supplies one list of deterministic native text graders per invocation. Semantic
rubrics are refused until a calibrated then-visible evidence judge is implemented; use persisted
judge contexts for human review. Top-level graders/helpers are refused for this profile. Legacy
native scenarios retain their original exactly-two-message/helper behavior.

Each branch is an exact authored CHECK-line map with aliases, two useful checks, and explicit
unavailable/ambiguous replies. Advice prose is not keyword-graded to infer intent. Missing/multiple
CHECK lines yield clarification; an unknown exact form yields unavailable. The candidate receives
available forms, not their observations. Branching profiles permit a second selection to correct an
unavailable request or take the other useful check; either useful order is admissible. The human
assesses advice quality and interpretation separately from mechanically selecting a branch.

The CLI actually resumes one session and shares the scenario `max_turns` across invocations. Root
holds invocation 1; `invocations/002` onward are distinct ordered folders. `conversation.json` indexes
them. Each invocation keeps exact `input.md`, selected branch and input/trigger digests in
`release.json`, cumulative then-visible `judge-context.json`, response, raw trace and argv/boundary
metadata. Future/unchosen observations remain in the harness scenario only. Existing read boundaries
allow the neutral fixture and measured plugin image, not this repository or the evidence bundle.
This tool/read boundary is not an OS sandbox.

Wall time and the native CLI spend cap apply per invocation. They are instrument guards, not one
cumulative conversation deadline/cost cap. The shared CLI turn count is the task budget. Saved-run
regrading verifies releases, branch selection, session, model, command and evidence continuity;
v1 records link every invocation. CLI estimated spend is not provider billing. Supplied helper
text does not count as actual dispatch: only tool call/completion and parent continuation events do.

Before any model run, a human must accept exact scenario/review bytes, useful alternatives,
unavailable controls, the held-out partition, candidate/model and bounded run plan. Offline controls
and manifest validation do not grant paid execution or promote any candidate.

The proposed [run plan](run-plan.json) leaves exact candidate, runner, model, host and approved
spend unset. It selects one two-message development smoke before reviewing the six-message and
branching runs. Its 180-second wall guard is per invocation and has no live completion evidence.
Do not execute a template until the owner accepts those exact identities, case bytes and budget.
Once accepted, the native entrypoint is:

```bash
"$PROJECT_PYTHON" evals/build_probe.py run \
  --scenario incident-session-01-a --plugin-root "$APPROVED_PLUGIN_ROOT" \
  --expect-plugin-digest "$APPROVED_PLUGIN_SHA256" --model "$APPROVED_MODEL" \
  --label wp05-smoke --trials 1 --timeout 180 \
  --max-batch-usd "$APPROVED_BATCH_USD" --out .eval-runs/wp05-approved-smoke
```

The owner must set every variable from the accepted plan. `--max-batch-usd` gates scheduling the
next trial; it does not impose a cumulative hard cap inside a resumed conversation. A two-message
case has two native $0.75 invocation guards; six-message cases have six. Unknown spend stops further
scheduling. Review the raw invocation evidence and then-visible contexts before advancing the plan.

The [campaign report](../../docs/fleet-evaluation/campaign-report.md) can read saved native bundles
with `--selection evals/incident-conversations/report-selection.json --label <actual-label>`.
That selection describes all 18 execution profiles, including held-out and worked profiles; it does
not turn them into 18 independent incidents or authorize running them. Select only the approved
subset for a pilot report. Structural PASS and the trace's `semantic_assessment: UNVERIFIED` remain
separate in the report.
