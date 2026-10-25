# WP-08 SWE-bench repair implementation plan

> **For agentic workers:** Use the repository's code-work workflow with bounded file ownership,
> test-first implementation, and one integrated review. Execution status remains in EVAL-012.

**Goal:** Implement the approved static-repair adapter and credential proxy, with offline evidence
and concrete commands for the owner-started smoke and paid steps.

**Architecture:** Keep orchestration in `evals/swebench_adapter/`, outside the native probe package.
Reuse plugin staging and trace/runtime checks. The host retains the credential and verifier-only
dataset fields; the agent receives a frozen plugin, pinned CLI, problem statement, and disposable
base checkout through a fixed-target relay.

**Tech stack:** Python 3.12-compatible source, the repository's Python 3.14 development environment,
standard-library HTTP and subprocess primitives, existing Pydantic records, Docker, and the approved
`swebench==5.0.2` evaluation dependency.

**Spec:** [Approved WP-08 run plan](run-plan-wp08-swebench-repair.md).

## Global constraints

- Ten selected repositories, seed `20261018`, one trial per task; no task substitution after results.
- Claude Sonnet 5.5 first; exact model IDs, CLI bytes, plugin bytes, dataset revision and images are pinned.
- The OpenRouter key stays on the host. The agent receives a per-attempt placeholder token only.
- Agent egress reaches only the fixed model proxy. Drop capabilities and privilege escalation;
  cap CPU at 2, memory and processes, storage at 10 GiB (`size=10G`), turns at 64 and wall time at 45 minutes.
- Gold/test patches and hints never enter the agent container. Independent verification stays separate.
- Cleanup runs on every exit; unresolved cleanup prevents the next attempt.
- Model spending, owner acceptance and live execution remain governed by the approved run plan.
- Preserve old v1 records. The explicitly required optional condition changes the shared record
  model and therefore the native runner digest once; adapter additions otherwise stay outside it.
- Do not add SWE-bench pooling to the native scenario comparison. Preserve individual results.

## Review focus

1. Incoming HTTP requests must not select another upstream or expose key-management APIs.
2. Split streaming frames, redirects, authentication failures and disconnects must not leak credentials.
3. Incomplete/invalid identity or verifier evidence must not produce a passing result.
4. Setup failures, timeouts and interruption must retain cleanup evidence and stop unsafe continuation.
5. Dataset changes, task ordering, image mutation and legacy records must not silently change comparisons.

## Task 1: execution-profile compatibility

**Files:** `evals/probe/records.py`, `evals/compare_runs.py`, generated v1 schema,
`evals/test_probe_batches.py`, `evals/test_comparison.py`, expected comparison fixture.

**Interface:** Optional `conditions.execution_profile` is an object with nonempty `name` and
`authentication` strings; omitted legacy values parse as null. WP-08 uses
`static-repair-independently-verified-dec13` and `openrouter-host-proxy`.

- [ ] Demonstrate that profile-bearing records and mismatch rejection fail before implementation.
- [ ] Add the field to parsing, comparison extraction, pair/pool matching and label identity.
- [ ] Test omitted/null compatibility, differing profiles and cross-case mixed labels.
- [ ] Regenerate the schema and expected report through existing generators; preserve fixture verdicts.

## Task 2: deterministic selection and case evidence

**Files:** `evals/swebench_adapter/selection.py`, `evals/test_swebench_selection.py`.

**Interfaces:** `select_tasks(rows, revision, licences) -> dict` creates a public selection manifest;
`resolve_task(manifest, rows, instance_id) -> dict` validates the selected full dataset row;
`case_identity(task, revision, image_digest) -> dict` and `identity_digest(identity) -> str` bind evidence.
The manifest contains dataset/revision/seed and task IDs, repositories, defect labels, licences and
case-field hashes; it excludes problem text, hints, gold/test patches and verifier scripts.

- [ ] Test the seed, sorted repository order, balancing recipe, exclusions and insufficient populations.
- [ ] Implement strict revision/field validation and accept the pinned dataset's list-valued test lists.
- [ ] Reject changed selected rows and duplicate IDs; require repository licence evidence.
- [ ] Test each identity component and ensure verifier-only fields never appear in the manifest.

## Task 3: host-side model proxy

**Files:** `evals/swebench_adapter/proxy.py`, `evals/test_swebench_proxy.py`.

**Interface:** `ModelProxy(key, token, models, *, bind_host='127.0.0.1', upstream_origin=...)`
owns `start()`, `close()`, `port`, `auth_failed`, `usage()`. `usage()` returns the authenticated
key's usage/limit metadata without its credential. `read_key(path) -> str` validates protected input.
Only the host orchestrator can choose the upstream; production uses `https://openrouter.ai`.

- [ ] Use real loopback HTTP servers to prove request restrictions and incremental response delivery.
- [ ] Permit only the model Messages route, allowlisted models and the attempt token; inject the real
  bearer credential upstream, stripping caller authorization and unsafe headers.
- [ ] Reject redirects and management/absolute/traversal routes; sanitize failures and streamed secrets.
- [ ] Test chunk boundaries, disconnects, auth failures, secret-free logging and key-usage accounting.

## Task 4: bounded container execution and independent verification

**Files:** `evals/swebench_adapter/containers.py`, `evals/swebench_adapter/runner.py`,
`evals/swebench_adapter/artifacts.py`, focused `evals/test_swebench_*.py`.

**Interfaces:** Orchestration consumes Tasks 1–3. Subprocess invocations use argv arrays and bounded
timeouts. Every owned resource has a unique attempt identifier and an inspect-based cleanup receipt.
Tests replace only the external Docker/process boundary, retaining lifecycle and evidence logic.

- [ ] Test capped launch arguments, fixed-target reverse relay, no host credentials/mutable tool mounts,
  Git pruning and agent/verifier input separation.
- [ ] Implement timeout/storage monitoring and cleanup on setup failure, interrupted execution and success.
- [ ] Stage plugin bytes and pinned CLI; build strict Claude invocation and validate init model, tools and
  container-mounted plugin identity before assigning a measured result.
- [ ] Capture and screen patch/trace bytes before artifact storage; independently invoke pinned SWE-bench
  with a fresh run ID and validate instance/base/patch/image-bound verifier receipts.
- [ ] Write v1 records plus identity, billing, verifier and cleanup evidence. Cover PASS, FAIL,
  INCONCLUSIVE, invalid identity and empty-patch outcomes without a model call.

## Task 5: operator entrypoint and smoke gate

**Files:** `evals/swebench_repair.py`, `evals/swebench_adapter/__init__.py`, adapter CLI tests,
`requirements-swebench.txt`, `requirements-dev.txt`, `pyproject.toml`, WP-08 operator documentation.

- [ ] Provide `select`, `preflight`, `smoke`, `trial` and `batch` entrypoints with validated manifests
  and clear missing-prerequisite errors before resource allocation or paid calls.
- [ ] Smoke must independently discriminate reference/empty patches, exercise hook allow/deny,
  verify pruned Git reachability, egress and CPU/storage limits, and bind a successful receipt to the
  exact selection/plugin/CLI/adapter/image/configuration used by later trials.
- [ ] Prevent paid steps without matching smoke evidence; retain the USD 2 first-trial stop and serial
  batch stop rules. Do not expose credentials through arguments or output.
- [ ] Document exact setup and owner-started commands, supported evidence and unverified runtime limits.

## Verification and handoff

Run affected tests through `/home/hawkfire/save-toolkit/.venv/bin/python -m pytest -n 0` while
implementing. Run Ruff and strict mypy on changed evaluator code, then the coordinated
`scripts/local_tests.py --heavy` once on the integrated candidate. An independent review covers the
combined diff and the five review-focus cases. Record actual results and runtime blockers in EVAL-012;
do not turn offline checks into smoke, paid-run or candidate-acceptance claims.
