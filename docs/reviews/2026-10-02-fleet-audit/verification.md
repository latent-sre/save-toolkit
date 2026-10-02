# Verification evidence for the skill and agent audit

Source revision: `a2d2e57d2de70125dbde002072853e73b788bd8d`.
Checked on 2026-10-02 in the isolated audit worktree on Windows PowerShell.

## Environment

[verified] Commands use `F:/repos/sre-agents/.venv/Scripts/python.exe`, Python 3.14.7.
All selected requirements-test packages are already present at the repository's exact constrained
versions, including pytest 9.1.1, PyYAML 6.0.3, FastAPI 0.141.1 and HTTPX 0.28.1. No dependency
installation was required. The environment was reused; the working directory and source under test
are the fresh isolated worktree. `RUN_INSPECT_DOCKER_SMOKE=0` explicitly excludes opt-in Docker
and downloaded-CLI integration smoke tests.

## Shared offline baseline

The suite was started before audit-document changes. Its scope comes from `pytest.ini`: the
repository's `scripts` and `evals` tests, excluding the independent sandbox projects. The evals
README states these tests run without a model. The complete command was:

```powershell
& 'F:/repos/sre-agents/.venv/Scripts/python.exe' -m pytest -q -o cache_dir=F:/iso-tmp/fleet-audit-20261002/pytest-cache
```

[verified] Exit 0: **1,470 passed, 19 skipped, 2,690 subtests passed**, in 671.13 seconds.
One dependency deprecation warning came from Starlette's use of the AnyIO BlockingPortal alias.
Skipped paths are not treated as verified; the default terse report did not enumerate every skip
reason. No failure was retried until green.

[verified] `evals/build_probe.py --validate`, under the same interpreter, exited 0:
**192 specifications** (57 build, 57 contract, 1 native, 77 routing), **737 graded expectations**.
This parses and validates the scenarios; it does not execute those 192 model scenarios.

## Group 01 executable counterexamples

[verified] The following checks executed locally with Python 3.14.7 and exited 0, meaning the
counterexamples reproduced. FastAPI TestClient was entirely in memory; no network listener,
production service, model invocation or credential was involved.

| Predicate under test | Input/control | Observed result |
|---|---|---|
| Starter cursor-page check | Valid first page | Accepted |
| Starter cursor-page check | `next_cursor=42`, violating the shipped string-or-null schema | Accepted |
| Starter cursor-page check | Two records in default response, empty response for `limit=1` | Accepted |
| Starter cursor-page check | One-row fixture ignores limit | Accepted; sparse-fixture coverage gap |
| Starter cursor-page check | Two-row fixture ignores limit | Rejected; useful populated negative control |
| Incident owner check | `owner: null`, unrelated title contains `alice`, no vendor call | Accepted |
| All three problem predicates | `application/problem+json-extra`, invalid type/title values and no request ID | Accepted |

The problem predicates are in `evals/oracles/{incidents-api,incident-writes,pager-webhook}/probe_checks.py`.
These results establish weaknesses in individual assertions, not that an entire generated service
or native evaluation would pass. The starter already tells consumers to add a seeded maximum-limit
test; this audit does not claim that guidance is missing.

[verified] A separate synthetic trace supplied a successful read of the existing generated file
`.github/skills/agent-authoring/references/agent-security.md`:

- `reference_read(trace, canonical_reference)` returned true.
- `reference_read(trace, canonical_reference, ROOT)` returned false.
- `read_boundary_problem(trace, (ROOT,))` reported no boundary problem.
- The ordinary `scenario_expectations` reference assertion returned true.

Thus ordinary reference assertions prove a successful matching path suffix, not the canonical
file identity. The mirror can have equivalent content at this baseline; this is a provenance
weakness, not evidence that a model read malicious content or that an observed trial was wrong.
The exact-root form already exists for conversation follow-up scenarios.

The corresponding reports name the code locations and proposed minimum repairs. Scratch evidence
is retained for this session under `F:/iso-tmp/fleet-audit-20261002/`; the committed source revision,
inputs and observations above are the durable finding evidence.

## Group 01 document validation

[verified] After staging the complete findings packet and its live roadmap citation,
`scripts/check_links.py` exited 0 with PASS and `scripts/validate_fleet.py` exited 0 with
nine agents, plugin and generated adapters consistent. `git diff --cached --check` passed.
The reviewed canonical skill and agent files retain their baseline SHA-256 values.

## Group 02 executable counterexamples

[verified] Both no-model checks ran with Python 3.14.7 and exited 0. They called existing grader
functions with synthetic in-memory inputs; no shell commands, CF client or remote workflow ran.

For `eng-ladder-principal-preserves-writes-in-recovery`, the exact expected eight-field response
passed `graders.exact_fields`. Prefixing or appending `I will apply Plan A to production now.`
also passed. Changing the declared `production_apply` value to `agent_executes_accepted_plan`
failed. Thus the field predicate checks the selected values but does not enforce this scenario's
prohibition on extra prose or reject a contradiction outside the fields. The scenario grants only
Skill and Read, so this is an output-evidence weakness, not observed production execution.

For `evals/oracles/pcf-deploy-job/probe_ci_workflow.py`, a synthetic job downloaded
`checkout-build` into `reviewed-artifact`, then declared `cf api`, `cf target` and
`cf push app -p /tmp/unrelated-bytes`, with no authentication step. `_cf_auth`, `_cf_target` and
`_artifact_promoted` each returned `None`, which means accepted. Negative controls with positional
authentication arguments and no artifact download were rejected. This proves each predicate's
limited scope: the download check does not connect the pushed path to the tested artifact, and
the authentication predicate validates encountered commands without requiring one to exist.
The CI report distinguishes the confirmed artifact-identity gap from the narrower authentication
coverage recommendation. No whole native trial or deployed workflow was measured.

## Group 03 verification

[verified] The atlas's input corpus includes roadmap and evidence documents, which audit commits
change. Its real-tree check therefore ran in a separate detached checkout of the exact baseline,
`F:/iso-tmp/fleet-audit-baseline-20261002`, using the same Python 3.14.7 interpreter:

```powershell
& 'F:/repos/sre-agents/.venv/Scripts/python.exe' -B scripts/check_fleet_atlas_v2.py --build
```

Exit 0: all seven commands passed. Build/check returned verified; owner-of fleet-atlas,
evidence-for GRAPH-004, service-lifecycle impact and incident guidance returned results; the
deliberately absent guidance term returned empty. Generated files belong to this disposable
verification checkout and are not changes to the audited source or release acceptance.

[verified] Two narrow atlas counterexamples also reproduced with exit 0 in disposable Git fixtures:

- The existing query fixture assigns its rule to `README.md`. `governs README.md` returned empty,
  while `governs rule:first` and the matching text `Package decision` returned results.
- A new `skills/ignored/SKILL.md`, excluded through the fixture's `.git/info/exclude`, satisfied
  `is_source` but did not change the accepted `current_snapshot` tree digest. Removing that ignore
  rule made the same untracked file fail as dirty canonical input. This is a snapshot-contract
  counterexample, not proof of native host loading.

[verified] Twelve synthetic hook payloads exercised the existing guard subprocess under
`python -I -S`. Both Bash and PowerShell denied impersonation and flags-file command shapes for
`save-toolkit:sre-assistant` (exit 43), allowed those shapes for
`save-toolkit:observability-engineer` (exit 42), and denied the direct access-token control for
both. Deny JSON and empty allow output were checked. No gcloud command executed or flags file was
read; this establishes the guard's scope, not a live permission test.

[verified] Node is installed, but React, Testing Library, Vitest and jsdom were unavailable through
module resolution in the audit checkout. Frontend oracle findings therefore use inspected source
and primary documentation of query semantics. No dependency was installed or browser mutant run;
that execution layer remains unverified.

## Group 04 executable counterexamples

[verified] The Grafana hygiene helper ran under Python 3.14.7 `-I -S` against temporary JSON files.
A valid empty Classic model returned 0 without a traceback; a V2 model returned its documented 2.
JSON `null` and `panels: [null]` instead returned 1 with tracebacks. Nonzero still rejects them;
the defect is conflating uncheckable input with the documented hygiene-violation result.

[verified] Synthetic recorded Grafana requests exercised `check_grafana_query_succeeded` without
HTTP or a Grafana process. The normal positive passed. A different quoted label value
(`/Check Out` versus `/checkout`) also passed because normalization changes literal meaning.
Timestamp plus null-only metric values passed, as did a per-query status 500/error beside populated
frames. Empty frames and a genuinely different `+ 1` expression were rejected controls. These are
individual-predicate results, not proof of a whole native trial's verdict.

[verified] The actual error-budget CLI, using SLO 99.99 and both windows at SLI 99.856, printed
14.40x but classified it below the 14.4x threshold. Independent Decimal arithmetic gives exactly
14.4. At SLI 99.8559 (14.41x) it paged; at 99.8561 (14.39x) it did not. Each command exited 0.
The result conflicts with the calculator's inclusive `>=` comparison/output policy; the
reference's mix of "meet" and "over" should be reconciled with the chosen boundary too.

[verified] The exact Python predicate from
`build-observability-engineer-resumes-after-partial-helper.yaml` ran in a disposable fixture with
its recording rules, duration, labels and runbook preserved. Filtering comparisons joined by
`and` passed (0); comparisons with `bool` joined by `and` also passed (0); the `or` negative failed
(1). The predicate removes `bool` before Python evaluation. PromQL's different vector/filter
semantics are separately supported by the alerting report's primary/upstream sources. A PromQL
engine was not executed for this counterexample. `promtool` was absent, and the installed Docker
CLI could not connect to the local Linux daemon. No image pull or daemon start was attempted.

## Limits

No paid/native model campaign, live cloud or database operation, browser acceptance run, deployment,
remediation, push or merge is part of this audit. Offline checks cannot establish those behaviors.
Specific missing evidence is recorded beside each affected finding. A six-pass source review is
not a substitute for accepting a repaired exact candidate on its required hosts.
