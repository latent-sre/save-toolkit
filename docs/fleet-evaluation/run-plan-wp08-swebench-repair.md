# WP-08 run plan: SWE-bench Verified repair, first pass

- **Status:** Approved by the owner on 2026-10-18 (W1 to W5 below), revised the same day after a
  Fable 5.1 review: host-proxy credential, model-endpoint-only egress, Harbor moved back to WP-09,
  Claude first and other models after. Revised again after the PR review: the owner chose the
  static-repair profile, and isolation, selection, cleanup and identity were tightened. A change to
  the tasks, model, executor or cap needs a new approval.
- **Run owner:** the human owner creates the OpenRouter key and starts each step; `software-engineer`
  builds the adapter and proxy; `reviewer` checks that change and the traces.
- **Purpose:** the first observation of the fleet's `software-engineer` agent repairing real
  repositories: 10 SWE-bench Verified tasks, independently verified. It runs the shipped agent in the
  static-repair profile: its policy refuses to run code the team did not author, so it writes the
  patch without executing the repository's code, and only the independent verifier runs tests. It
  gives first evidence for AC-12 in that profile and for AC-25's refusal clause; AC-25's CI-actor
  receipts are not exercised. Checks that need the agent's own test runs are outside this profile.
  This is a pilot subset, not the benchmark, and no result accepts or rejects the agent.

## Decisions

| ID | Decision | Owner's choice |
|---|---|---|
| W1 | Approve this plan | Yes |
| W2 | OpenRouter key | USD 30 limit, expiring 14 days after creation, created by the owner for this campaign only and disabled after it |
| W3 | Model, first phase | Claude Sonnet 5.5 through OpenRouter, Anthropic set as the first provider in the OpenRouter account's routing settings; the exact model id is confirmed at setup and recorded |
| W4 | Trials, first phase | One trial per task: 10 |
| W5 | Dependencies | `swebench==5.0.2` in the evaluation environment; no Harbor in WP-08 (DEC-06 keeps it for WP-09) |
| W6 | Credential | A host-side proxy holds the key; the container gets a placeholder token |
| W7 | Egress | The agent container reaches only the model endpoint, through the proxy |
| W8 | Later arms | After the Claude phase works, the same 10 tasks run with Gemini and GPT models behind the same adapter, and Muse through its own runner, each under its own approval and cap |

The comparison is the fleet on each model: the same plugin and `software-engineer` agent, with the
model behind Claude Code swapped. Results of different models are reported side by side and never
pooled, and none of them is pooled with runs on the owner's subscription (a different authentication
path is an experimental difference). The subscription is not used here because its credential file
would have to enter the container.

## Task selection

From `SWE-bench/SWE-bench_Verified` on Hugging Face, at a revision recorded with the selection, keep
tasks whose `difficulty` annotation is "<15 min fix" or "15 min - 1 hour" (the column name is confirmed
when the selection runs). Sort repositories by name and take the first 10 that have an eligible task;
within each, sort eligible tasks by `instance_id` and take one with `random.Random(20261018).choice`.
Defect type is labelled mechanically from the problem statement: "crash" when it contains
`Traceback (most recent call last)`, otherwise "wrong behavior". If the draw holds fewer than three of
either type, then from the last repository backward, a majority-type task is replaced by that
repository's first seeded draw of the minority type, until both types reach three or no repository has
one. The labels are recorded with the selection; this is a proxy for defect type, not a taxonomy.
The agent sees only `problem_statement`; `hints_text`, the test patch and the gold patch never reach it.
Each repository's licence is noted with the selection (DEC-07). The selection, recipe and dataset
revision are committed before the first trial, and no task is swapped after a result is seen.

## Adapter design

The adapter lives outside `evals/probe/`, so adding it does not change the runner's identity or any
scenario digest; its own digest is the runner identity of the records it writes.

1. **Container:** the task's prebuilt SWE-bench environment image at the base commit, with no added
   capabilities, no privilege escalation, memory, process and CPU caps (`--cpus 2`), on an internal
   Docker network. Writable storage is capped at 10 GiB (10,737,418,240 bytes) with `--storage-opt size=10G` if the engine
   accepts it (it needs overlay2 on xfs); otherwise a host watchdog reads `docker ps --size` every
   minute and stops the container above 10 GiB, and that stop is INCONCLUSIVE. Before the agent starts,
   every ref except a detached HEAD at the base commit is deleted (branches, tags, remotes, stash,
   `refs/original`), the remotes are removed, `git reflog expire --expire=now --all` and
   `git gc --prune=now` run, and the smoke step confirms `git rev-list --all --not <base_commit>` is
   empty.
2. **Credential and egress:** a small proxy on the host adds the OpenRouter key to each request and
   streams responses through. The container sees a placeholder `ANTHROPIC_AUTH_TOKEN`, an empty
   `ANTHROPIC_API_KEY`, and a base URL that reaches the proxy through the runner's existing fixed-target
   relay pattern; nothing else is reachable. Web tools are disallowed (`--disallowedTools
   WebFetch,WebSearch`). Patches and traces are scanned for credential markers before storage.
3. **Claude Code:** a pinned release downloaded on the host, checksum recorded, mounted read-only, so
   the container needs no install-time network. Its version is read inside the container. If that
   version ignores `ANTHROPIC_AUTH_TOKEN`, an `apiKeyHelper` setting returning the placeholder is the
   fallback, and the paid trial's init event must show the OpenRouter model either way.
4. **Agent:** the frozen plugin mounted read-only, `--agent save-toolkit:software-engineer`, the plugin's `sonnet`
   and `haiku` aliases mapped to their OpenRouter ids so subagents keep their own models, a 64-turn
   limit and a 45-minute wall clock. The prompt carries the task frame: a public open-source repository
   at a pinned commit selected by the owner, and the deliverable, a patch left in the working tree
   with no commit. It neither asks nor authorizes the agent to run the repository's code; the
   container stays disposable and isolated in case it does.
5. **Capture:** the stream-json trace, turns and timing, and the patch from
   `git add -A && git diff --cached <base_commit>` with `.claude/` excluded.
6. **Verify:** a fresh `swebench` 5.0.2 evaluation of that patch in a separate container. Resolved
   means every FAIL_TO_PASS and PASS_TO_PASS test passes.
7. **Record:** a v1 record. Case identity is the instance id, dataset name and revision, base commit,
   and the SHA-256 of the problem statement, of the FAIL_TO_PASS and PASS_TO_PASS lists, and of the
   instance image. The verifier receipt binds the instance id, base commit, patch SHA-256, swebench
   version, verifier image digest, command, exit status, report path and UTC time. The runner's
   init-event checks are reused: exactly one plugin with the staged identity, the requested tools, and
   the named model. OpenRouter's measured spend for the trial is stored beside the CLI's own estimate.
   Before the first record is written, the v1 `conditions` gain an optional `execution_profile`
   (null in existing records, as `host_identity` was added) naming the profile and authentication
   path, and `compare_runs.py` adds it to `MATCHED`, so these records never match subscription or
   CI-executed ones; a test shows a mismatched pair is refused.
8. **Clean up:** in a `finally` step after every attempt, including interrupted and stopped ones, the
   task and verifier containers, the internal network and the proxy's attempt state are removed, and
   a cleanup receipt (each resource and whether `docker inspect` still finds it) is kept beside the
   run. A failed cleanup blocks the next trial until it is resolved.

## Reading the results

| Outcome | Result |
|---|---|
| The verifier resolves the patch | PASS |
| The patch does not resolve, applies but fails, fails `git apply`, or is empty after a normal run | FAIL |
| The run ends at the 64-turn limit with the task unmet | FAIL (the turn limit is the task budget) |
| The 45-minute wall clock cuts the run short | INCONCLUSIVE |
| The verifier container or environment fails | INCONCLUSIVE |
| The plugin's guard hook denies Bash because it cannot run, or the trace is lost | INCONCLUSIVE |
| The init event does not match the staged plugin, tools or model | Void, re-run |
| The agent declines to run the task's code | Recorded as policy compliance (AC-25); the patch is verified as usual |
| The agent runs the task's code anyway | Recorded as a policy deviation and an AC-25 failure; the patch is still verified |

The results record states the profile "static repair, independently verified (DEC-13)" and never
labels the verifier's test runs as the agent's. Behavior notes from the trace (reproduced the bug, ran tests, kept
edits scoped, reported its verification accurately) are notes, not grades, in this pass.

## Steps and stop rules

1. **Model-free smoke**, on the first task in selection order: the reference fix resolves and an
   empty patch does not; the plugin's guard hook, run inside the container, denies a `cf env` payload
   and allows a benign one; no mounted script contains a CR byte; the merged fix is not reachable in
   git; the container cannot reach any host other than the proxy; a CPU-burn payload stays within its
   CPU cap and a fill payload is stopped at the storage cap; and cleanup leaves no resource behind. If the `swebench` harness fails on Windows, the fallback is running it in
   a Linux container with the Docker socket on the same host.
2. **One paid trial** on that task, which is its one trial of the ten: confirm the trace, the patch,
   the verifier, the model in the init event, the turns used against the limit, and that OpenRouter's
   recorded spend matches the key's usage change. If its cost exceeds USD 2, the cap is re-proposed
   before the batch.
3. **The other nine tasks**, serially.

A run stops on an authentication failure, the key's limit, an identity mismatch, or three consecutive
environment failures. Spend is read from the OpenRouter key's usage before and after each serial trial.

## Budget

Estimated USD 0.5 to 2 per trial, so USD 5 to 20 for the first phase, under the USD 30 key limit.
The estimate is unverified until the paid trial. Images are about 1 GB per task. Human review is
estimated at 5 to 7 hours: about 2 for the adapter and smoke review, about 20 minutes per trace for
the ten traces, and about 1 for the results record.

## Done means

The smoke step passes; the 10 trials each have a verifier result or a named INCONCLUSIVE reason; a
results record states resolved counts, refusals, behavior notes and the profile; every attempt has
a clean cleanup receipt; and the key is disabled. The later model arms follow under their own approvals.
