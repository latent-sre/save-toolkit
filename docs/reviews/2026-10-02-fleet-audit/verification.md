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

## Limits

No paid/native model campaign, live cloud or database operation, browser acceptance run, deployment,
remediation, push or merge is part of this audit. Offline checks cannot establish those behaviors.
Specific missing evidence is recorded beside each affected finding. A six-pass source review is
not a substitute for accepting a repaired exact candidate on its required hosts.
