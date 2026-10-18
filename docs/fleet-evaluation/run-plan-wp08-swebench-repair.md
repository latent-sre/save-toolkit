# WP-08 run plan: SWE-bench Verified repair, first pass

- **Status:** Draft for the owner's approval, 2026-10-18. Nothing is installed and no trial runs until
  the decisions below are approved. A change to the tasks, model, executor or cap needs a new approval.
- **Run owner:** the human owner creates the OpenRouter key and starts each step; `software-engineer`
  builds the adapter; `reviewer` checks the adapter change and the traces.
- **Purpose:** the first observation of the `software-engineer` agent repairing real repositories:
  10 SWE-bench Verified tasks on one candidate, with independent verification. It gives first evidence
  for AC-12 and AC-25 in [measurement](measurement.md#acceptance-catalog). No result accepts or rejects
  the agent; this is a pilot subset, not the benchmark.

WP-09 (SWT-Bench and Terminal-Bench) follows under its own plan after this pass.

## Decisions already made (2026-10-18)

- **DEC-13 execution:** the agent may run the task repository's code inside a disposable per-task
  container on the owner's Docker host; an independent verifier on the same host applies the patch and
  runs the hidden tests ([delivery](delivery.md)).
- **DEC-06 harness:** the official `swebench` package verifies; Harbor is a second executor (below).
- **Credential:** an OpenRouter API key with a USD spend limit and an expiry, created for this
  campaign only and disabled after it.
- **Executors, in sequence:** first a self-built adapter, then Harbor on the same 10 tasks. Both are
  verified by the same `swebench` 5.0.2 run, so their results check each other. Harbor adds roughly
  1.5 to 2 sessions of work and is the path WP-09's Terminal-Bench uses.

## Decisions for the owner

| ID | Decision | Recommendation |
|---|---|---|
| W1 | Approve this plan | Yes |
| W2 | OpenRouter key limit and expiry | USD 30 limit, expiring 14 days after creation; the owner creates it and stores it outside the repository |
| W3 | Model | Claude Sonnet 5.5 through OpenRouter, with Anthropic as the pinned first provider; the exact OpenRouter id is confirmed at setup and recorded |
| W4 | Trials | One trial per task per executor: 10 on the self-built adapter, then 10 on Harbor |
| W5 | Dependencies | Add `swebench==5.0.2` to the evaluation environment now; add `harbor==0.23.0` (the newest release older than two weeks) only for the Harbor phase |

## Task selection

The 10 tasks are drawn before any trial and recorded with the dataset revision:
`SWE-bench/SWE-bench_Verified` from Hugging Face, filtered to the annotated difficulty "<15 min fix"
and "15 min - 1 hour", grouped by repository, then `random.Random(20261018)` picks one task from each of
10 different repositories in sorted repository order. Fewer than 10 eligible repositories means the
remaining picks come from the largest repositories in the same seeded order. The selection, its
recipe and the dataset revision are committed before the first trial; no task is swapped after a
result is seen.

## Adapter design (self-built)

For each task:

1. **Container:** start the task's prebuilt SWE-bench environment image with no added capabilities,
   no privilege escalation, a memory and process cap, and the repository at its base commit. The
   test patch and the reference fix never enter this container.
2. **Agent:** install a pinned Claude Code version in the container, mount the frozen plugin
   read-only, and run `--agent software-engineer` non-interactively with the issue text as the task,
   a turn limit and a wall-clock timeout. Model environment: OpenRouter's base URL and key, an empty
   `ANTHROPIC_API_KEY`, and the plugin's `sonnet` and `haiku` aliases mapped to their OpenRouter ids,
   so subagents keep their own models.
3. **Capture:** the stream-json trace, the turn and timing data, and `git diff` against the base
   commit as the candidate patch.
4. **Verify:** a fresh `swebench` 5.0.2 evaluation of that patch in a separate container. Resolved
   means every FAIL_TO_PASS and PASS_TO_PASS test passes.
5. **Record:** a v1 record with the plugin digest, Claude Code version, resolved model, verifier
   result and spend, so the existing comparison tool reads it.

The Harbor phase runs the same tasks through Harbor's Claude Code agent with a small subclass that
adds `--plugin-dir` and `--agent`, a collection hook that writes the same `git diff`, and the same
`swebench` 5.0.2 verification. Its known differences are recorded, not corrected: Harbor maps every
model setting to the main model under a custom base URL, and it runs with `bypassPermissions`.

## Reading the results

- **Resolved / not resolved:** the verifier's result on the captured patch.
- **INCONCLUSIVE, not a failure:** an environment that would not build, a verifier that could not
  run, or a lost trace (AC-24). An empty patch after a normal run is a failure.
- **Behavior notes from the trace:** whether the agent reproduced the bug, ran tests, kept its edits
  scoped, and reported its own verification accurately. These are notes, not grades, in this pass.

## Steps and stop rules

1. **Model-free smoke:** install, then run one task's reference fix through the verifier (must
   resolve) and an empty patch (must not). This settles Windows Docker behavior before any spend.
2. **One paid trial** on the self-built adapter; confirm the trace, the patch, the verifier and that
   OpenRouter's recorded spend matches the key's usage change.
3. **The 10 tasks,** serially, then the Harbor phase on the same 10.

A run stops on an authentication failure, the key's limit, an identity mismatch, or three
consecutive environment failures. Spend is read from the OpenRouter key's usage before and after each
serial trial, because Claude Code's own cost figure is a local estimate.

## Budget

Estimated USD 0.5 to 2 per trial on Sonnet, so USD 5 to 20 per executor, under the W2 key limit for
the whole plan. Images are about 1 GB per task; the host has ample disk.

## Done means

The smoke step passes; 20 trials (10 per executor) each have a verifier result or a named
INCONCLUSIVE reason; the two executors' outcomes are compared task by task; a results record states
resolved counts, behavior notes and the executor differences; and the key is disabled.
