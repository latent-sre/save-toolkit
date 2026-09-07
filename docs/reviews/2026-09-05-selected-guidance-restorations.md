# Selected guidance restorations — 2026-09-05

## Scope and disposition

The user selected five findings from the #220–234 review: backend task-fit, human-facing systemic
investigation, operator CLI guidance, coordination choices, and SRE helper completion. These
source restorations are implemented; machinery, other findings, and production authority are
unchanged. The user subsequently authorized committing and pushing this batch to the task branch;
publication does not imply merge approval or behavioral acceptance.

The final text has independent static review and repository verification. The earlier candidate's
planning canaries exposed material CLI and helper-status errors; final wording addresses those
source gaps but was not behaviorally retested. Do not present this batch as a clean behavioral
pass or a reliable before/after improvement rate.

## What changed

| Finding | Source correction | Boundary preserved |
|---|---|---|
| Backend applies HTTP scaffolds to unrelated tasks | `backend-craft` inspects the existing task/framework/API/auth/tests first; matching new-service starters are optional; completion evidence fits workers, clients, or HTTP work. Builder's mirrored instruction is corrected too | Existing contracts/auth stay intact; no framework migration or new HTTP surface implied |
| Systemic method archived with autonomy | A conditional `systemic-analysis.md` restores shared fate, cascades, retries, poison partitions, feedback, and containment comparisons | Human advisor retains evidence, mitigation, and recovery rules; archive/autonomy machinery stays retired |
| Operator CLI detail lost | Small `operator-cli` skill, discoverable from README and the builder's normal process/on-demand list; covers streams/schema, partial outcomes, non-TTY confirmation, precedence/secrets, real dry run, bounds, interruption, and replay uncertainty | No old build pipeline, templates, new agent, tool grant, or production execution authority |
| Coordination collapsed to one default | Roster reference gives dependency-based pipeline, fan-out/synthesis, necessary barrier, independent challenge, and bounded discovery choices | Existing grants and ownership limit every pattern; no scheduler/runtime selected |
| Helper judged by recovery | Roster verifier now checks the requested target/window evidence and assignment completion rather than golden signals; missing requested work differs from an unresolved parent incident | Human owns recovery; helper returns its result rather than taking over the incident |

The relevant source hard failures were inspected at base commit
`784211a751a1fa8293b2ff6525d7c281afec90f2`: unconditional FastAPI starter installation before
reading code, the combined SRE-helper/recovery verifier row, and missing live method/CLI references.
The source corrections do not rely on claiming that every baseline model response was wrong.

## Independent review and corrections

Independent reviewers examined files they did not author. Before the first candidate calls:

- Added a loader predicate for a single repeatedly failing item/stalled partition, not just
  multi-service or post-rollback failures.
- Clarified that all-success batches exit zero; failed or UNKNOWN items cause nonzero status.
- Confirmed backend references defer to the core's existing-contract preservation rule.

After inspecting candidate responses, two narrow source corrections were made and statically
reviewed: an error status alone does not establish that a write had no effect; helper completion
is measured against its assignment, not ongoing incident impact. These final corrections have no
new live-model evidence. The systemic reference already requires establishing trigger removal;
the observed causal overstatement remains a model-behavior limitation, not silently erased evidence.

## Bounded planning canaries

Private artifacts: `.eval-runs/selected-restorations-20260905/`. Five frozen cases covered Java
queue-worker task-fit, an interactive/CI retirement CLI, a multi-service post-rollback incident,
coordination choices, and a complete helper slice during an unresolved incident.

- Incumbent digest: `99cf8467a7bb4b80b0c8a41732d501bb5469f27b409c12c0a4bb4d5a1f53356f`.
- Tested candidate digest: `20b1a8fd5b5a5374ee525974bb48396c12f7ca4bf3d03099b2f33ff448c6e6f0`.
- Final source digest after the two static corrections:
  `f0c966225835f79f74e79293729227ac60007f4efb36735d0f503dae3475776e`.
- Frozen case hash: `f72930840e2e74134bd3b7089dd48f03bc1d66b41f701412893500518b034dd4`.
- Five main calls per arm, 120 seconds per call, no judge calls or model-result retries. All ten
  returned without runtime-boundary failures. Inputs were inline, source-bound guidance and
  synthetic planning requests; runtime tools, plugins, and MCP lists were empty.
- Requested `sonnet`; initializations and assistant messages identify `claude-sonnet-5`. Usage also
  records Haiku activity of unverified purpose. This is not a claim of pure single-model API work.
- Recorded cost: USD 0.991183. These calls test source-reading/planning compatibility, not skill
  activation, an implemented CLI/API, actual delegation, or live incident response.

The first candidate process launch hit Windows' argv length limit before calling a model. The
private runner switched candidate input to stdin, with identical prompt hashes; baseline remained
argv input. The empty launch and transport variance are retained separately. No product harness,
grader, scenario, dependency, or credential changes were made to solve that transport issue.

### Findings from actual responses

| Case | What the comparison supports | Limitation |
|---|---|---|
| Backend | Both arms choose existing Java/JUnit and avoid HTTP scaffolding; candidate explicitly applies worker guidance | Source contradiction removed, not demonstrated new capability; speculative root-cause language remains |
| CLI | Candidate adds clear secret handling, UNKNOWN/network interruption, complete partial results, and confirmation distinct from production approval | It wrongly assumes a 503 proves no effect and deletion is safely idempotent without the API contract. Final source tightens this, without a new model trial |
| Systemic | Candidate uses caller attempts per request, distinguishes amplification from aggregate dependency health, and keeps mitigation conditional/human-owned | Its checkpoint overstates that rollback removed the original trigger and rules out a cause without sufficient timing/causal evidence |
| Coordination | Both arms choose compatible fan-out, dependent stages, and bounded discovery; candidate makes limits more explicit | Candidate invents a full migration/approval/smoke/deploy order beyond the supplied dependencies; no improved sequencing claim |
| Helper | Candidate preserves source labels and an unresolved incident | It calls the completed assignment partial because the incident remains open; incumbent correctly called the assignment complete. Final source explicitly separates these statuses, without a new model trial |

Independent review therefore supports the source restoration, not an all-green behavioral verdict.
No unsafe recommendation from a canary was acted on.

## Repository verification

New canonical/generated files were marked intent-to-add so tracked-file weight checks include
them. Without that registration, the initial size check omitted the new files; that preliminary
result was not used as final evidence. Redundant wording was consolidated, not a budget raised.

- Generated 125 adapters; parity and links pass.
- Gate A passes all four structural steps.
- All seven context budgets pass; the existing budgets are unchanged.
- Final weight: 570,963/571,000 skill bytes; 109,347/115,000 agent bytes; 9,252/9,900 eval Python
  lines. The small remaining skill headroom is a constraint, not an instruction to cut more work.
- Existing scenario validation remains 65 specs / 324 expectations; no grader/scenario changes.
- Final-source full suite: `python -m pytest -q -rs -p no:cacheprovider` with Git Bash tools on
  PATH — **462 passed, four skipped, 861 subtests passed**, 75.30 seconds. Three skips require
  directory symlinks; one is the CI-only shell requirement. `git diff --check` also passes.

## Deliberately left alone

Runbook causal-example bugs, frontend guidance, CI masking/scanning, ThousandEyes recipes,
Confluence paths, manifest examples, reviewer evidence wording, and the other audit findings were
not selected. The user's pre-existing independent-review document is untouched. No pipeline,
autonomy graph, language-idiom suite, or effect broker was restored.
