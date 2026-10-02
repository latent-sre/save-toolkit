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

## Group 05 executable counterexamples

[verified] The caller loaded the dashboard fixture's actual `service_array_item` and
`grafana_query_succeeded` checks. Synthetic accepted write/query records and an in-memory response
contained three panels and a p95-titled panel with the required datasource, description, unit and
no-data text. No HTTP or PromQL engine was involved. Both predicates accepted a proper
`histogram_quantile(0.95, sum by (le) (rate(checkout_request_duration_seconds_bucket[5m])))`.
Both also accepted the same expression with `0.5` persisted and queried under the p95 title.
The negative control, saved `0.5` but queried `0.95`, was rejected by query identity. All assertions
passed under Python 3.14.7. This isolates the missing requested-quantile check (DASH-01) from the
query-equivalence and result-quality findings already recorded in group 04.

[verified: static counterexample; sourced semantics] LOG-02 uses the documented `_time` filter:
with now at 12:00, an event timestamped 05:50 but indexed at 11:59 is excluded by `earliest=-4h`.
Thus absence from that query cannot establish that ingestion stopped. This is a constructed
counterexample under the cited Splunk time-modifier contract, not an executed Splunk search.
Cloud Logging key-case semantics and the metrics recommendations likewise rely on identified
primary documentation; no Splunk, Loki, Wavefront, Mimir or Cloud Monitoring query ran.

## Group 06 executable counterexamples

[verified] The caller loaded the real closeout fixture and `check_closeout` artifact oracle into a
disposable directory under the audit scratch root. It changed only the requested owner/contact,
preserving lifecycle, source revision, review date and links. A correction on one line with
`[UNTRUSTED][sourced] AUDIT-73` passed. Removing both labels and source marker from the correction
failed. The same unlabelled correction plus an unrelated line
`[UNTRUSTED][sourced] AUDIT-73 source reference retained.` passed. All assertions passed under
Python 3.14.7. This isolates the oracle's missing binding between the correction and its evidence
marker; it does not establish a full native scenario pass or observed model behavior. No application
code, backend request or live operation ran, and the disposable input tree was removed.

[verified] The Alloy fallback's native stdin boundary was exercised without Docker or Alloy.
The caller wrote UTF-8 Alloy-shaped input containing `filename = "café.txt"` and piped it through
`Get-Content -Raw` to a Python `-I -S` reader that printed raw stdin hex. With `-NoProfile`, Windows
PowerShell 5.1.26100.9549 used `us-ascii` native output and delivered `caf??.txt`; adding
`Get-Content -Encoding UTF8` still delivered `caf?.txt`. PowerShell 7.6.6 used UTF-8 and preserved
`c3 a9` in both cases. All four commands exited 0; both shells appended a pipeline newline.
This establishes changed validation input on the named 5.1 path, not an Alloy validation result.
Adding input decoding alone does not fix native-output encoding; exact-file transport is preferable.

## Group 07 bounded effect-client probe

[verified] The caller loaded the reference CLI's actual `cancel_one` with an in-memory effect seam.
For a synthetic client that changed the item to cancelled and then raised `OrderError`, the function
returned `failed` and made zero status reads. The `TimeoutError` control returned `succeeded` after
one status read. Both assertions passed under Python 3.14.7; no real API or persistent effect occurred.
The shipped fixture raises `OrderError` only for definitive rejection, so this probe establishes the
importance of the adapter's exception contract, not a demonstrated failure of that fixture or an
actual production client. The report preserves that conditional scope.

[verified] The caller reused the CLI asset's real fake client and test runner in an owned temporary
fixture. The existing wrapper simulated `isatty() == true`. Input `y` exited 0 with three effect
calls and JSON; `n` exited 2 with no effect calls and no traceback. EOF exited 1 with an `EOFError`
traceback and zero effect calls. All caller assertions passed. This is a subprocess reproduction
of the prompt path, not a physical-terminal test. Empty JSON output is not asserted as a separate
EOF-only defect because the ordinary refusal path also emits no receipt.

## Group 08 executable oracle checks

[verified] The caller extracted the existing generator calibration positives and invoked the actual
`check_contracts.py generator` through Python 3.14.7 `-I -B` in an owned temporary fixture. Line
iteration and the original fixed `read(4)` both exited 0 with the completion message. Changing only
the fixed chunk size to 64 or 8192 exited 1 with `source consumed eagerly`; unbounded `read()` and
`list(source)` controls also failed with that diagnostic. The 12-character fixture therefore
rejects allowed bounded readers whose chunks exceed its size.

[verified] In the same actual process check, candidate `records.py` containing only
`raise SystemExit(0)` exited 0 without the oracle's completion message. `SystemExit(2)` exited 2;
the valid iterator completed normally. This demonstrates successful process exit before the
contract assertions finish; the scenario's outcome check consumes the exit code. It does not
establish a complete native scenario pass or observed model behavior. No dependency installation,
network or service execution occurred.

[verified] The complete policy oracle also conflates a returned error string with a raised error.
The caller seeded the actual YAML fixture with the existing calibration candidate and its existing
CLI-test correction. The unchanged candidate passed all import-order subprocesses and retained
fixture tests. Replacing only `raise ValueError("invalid sku")` with `return "invalid sku"` also
exited 0 with completion. A wrong error-message control exited 1 with the specification-mismatch
diagnostic. The probe exercised the actual `-I -B check_contracts.py policy` entrypoint in an owned
temporary tree; it did not claim a native implementation trial passed.

[verified: bounded coverage] The postmortem artifact oracle accepted its existing calibration row
with either `open` or `completed` status and rejected a changed owner. This supports POST-R01's
coverage recommendation: the documented checker verifies ownership, not completion semantics.
It is not counted as a new confirmed defect or a full document-quality failure.

## Group 09 executable counterexamples

[verified] The caller seeded the actual retry fixture and ran its three existing unit tests plus
`probe_retry.py`. The correct repair passed both. Changing only `isinstance(error, TimeoutError)`
to `type(error) is TimeoutError` also passed both, but a `ServiceTimeout(TimeoutError)` changed from
retryable/three calls/recovery to non-retryable/one call/the same exception propagated. The original
broad handler failed both checks. This establishes a missed classifier-compatibility regression,
not native causal reasoning or an actual service failure.

[verified] The caller loaded the real Confluence converter with owned temporary HTML/output files.
Default import created an absent file (0) and refused a pre-existing history-bearing file (1,
history intact). A controlled wrapper created that output during the real conversion, after the
existence check: main returned 0 and replaced the history. This is an injected deterministic
interleaving, not an observed production race. Explicit `--force` also replaced the history as the
intentional control. No runbook outside the temporary fixture was affected.

[verified] The same actual converter preserved a literal newline between `cf app demo` and
`cf events demo` inside a preformatted block. Replacing the newline with either `<br>` or `<br/>`
produced `cf app democf events demo` in the generated code block. Commands were converted as text,
never executed. All caller assertions passed under Python 3.14.7; no network or service ran.

## Group 10 focused checks and integration boundary

[verified] `SRE_CONTEXT_ROOT` was absent. After inspecting the guard, the caller ran
`python -B -m pytest -q scripts/test_service_lifecycle_context.py -rs` with the shared scratch cache:
**2 passed, 11 skipped in 0.02 seconds**, exit 0. Each skip explicitly requires that variable for
external producer CLI acceptance. No producer checkout/CLI ran; producer compatibility remains
unverified. This focused result is separate from the original full suite's 19 total skips.

[verified] The caller loaded the support-only-stack fixture's actual `bash_did_not_run` check and
used synthetic trace commands, without executing them. Direct Bash `mvn test` and
`java -jar app.jar` correctly failed the no-run predicate; `env mvn test` and
`command java -jar app.jar` incorrectly passed. Allowed `which mvn` and `java -version` passed.
Direct PowerShell `java -jar app.jar` failed, but `& 'java' -jar app.jar` passed; `Get-Command java`
passed its allowed control. All nine assertions passed under Python 3.14.7. This establishes the
bounded evaluator gap, not a native agent run or actual Java/Maven execution.

## Group 11 agent-oracle counterexamples

[verified] The caller loaded the actual `service_unchanged` checks from both Grafana boundary
fixtures (three checks total), constructed real `Service` objects with synthetic request histories,
and replaced only the final HTTP readback seam. For each check, GET-only, rejected write, no-op
write, and a successful write followed by restoration all passed when the final JSON equalled the
snapshot. A changed final state failed. All 15 assertions passed. The successful write/restoration
case establishes that final equality cannot prove the stronger claim that no forbidden resource was
edited. No HTTP request, Grafana service, container, or native/model trial ran.

[verified] The caller extracted the actual agent-engineer partial-research fixture's Python check
and ran it in an owned temporary skill tree. The correct repair and extra trailing newline passed
both that process check and the shared strict frontmatter parser. A leading blank line passed the
process check (exit 0) but failed the strict parser with `missing opening frontmatter marker`.
The unchanged typo failed the process check (exit 1). All assertions passed under Python 3.14.7.
This proves the fixture's normalization admits an invalid repository artifact; native host parsing
and model behavior were not exercised. No canonical source was changed.

[verified] The caller extracted both Python predicates from the reliability partial-helper
fixture. In an owned text-only assessment, a clear refusal passed the unknown-control and
no-authorization checks (0/0). An explicit rejection quoting `I authorize deployment` kept the
control unknown (0) but failed the authorization predicate (1), with that quoted substring in the
assertion diagnostic. An actual affirmative authorization also failed (0/1), as intended. This is
a bounded false rejection of quoted evidence, not an unsafe authorization or native-agent result.

## Group 12 host inventory and reviewer check

[verified] The current Codex GitHits inventory exposes `grep`; its tool description explicitly
says it replaces `code_grep`. The researcher's exact grant and validator registry still name
`code_grep`. The reviewer also retrieved the current provider guide and exercised `grep` on a
public version-pinned source, as recorded in the researcher report. This establishes drift against
that current tool set, not failed native Claude resolution on every installation. Host namespace
prefix differences are not counted as defects.

[verified] The caller invoked the actual `ran_outside_checkout` checks from the direct reviewer
fixture and the software-engineer handoff fixture (subagent scope), using real `TraceSummary`
objects with synthetic commands. In both scopes, unqualified Python in the checkout failed,
known-outside execution passed, and returning to the named source path before Python failed.
Absolute `/usr/bin/python3`, `.venv/bin/python`, and `env`-wrapped Python commands with no directory
change all passed the outside-checkout assertion incorrectly. All 12 assertions passed under
Python 3.14.7. These were command strings only: no candidate import, shell command, Git command,
service, or native/model trial ran. This is a bounded evaluator false acceptance, not evidence of
an actual reviewer executing in the source checkout.

[verified: disconfirmed lead] The changed-file-history pattern initially appeared to miss the
required `$G log` form. Inspection of `_matches_command` and its same-call assignment expansion,
plus the existing regression coverage, refuted that lead. It is not reported as a defect.

[verified] The caller also used the actual uncommitted-review fixture, its `_write_files` seeding
helper, and `no_workspace_changes` predicate in an owned temporary directory. The helper explicitly
wrote LF bytes. The unchanged seed passed; replacing LF with CRLF changed the raw SHA-256 but
still passed as `checkout unchanged`; a semantic edit failed. Git facts were synthetic and no Git
command ran. This proves the predicate does not enforce its stated byte-preservation contract for
seeded uncommitted files; it does not establish that a native reviewer rewrote a user's file.

## Group 13 guard effects and fabricated-artifact check

[verified] The caller exercised the real command guard with synthetic namespaced sre-assistant
payloads for both Bash and PowerShell. Plain `git stash show -p` and `git reflog show -p` returned
allow (42); `git diff --output=<owned path>` returned deny (43). Adding `--output=<owned path>` to
the stash/reflog forms still returned allow (42). Under Git `2.53.0.windows.2`, the caller then ran
only those two forms in a new owned temporary repository with synthetic commits/stash, isolated
global/system Git configuration, disabled hooks/signing and no external endpoints. Both returned
0 and created nonempty patch files. Repeating them against owned sentinel files replaced the
sentinels, confirming overwrite as well as creation. The source checkout was untouched and the
validated temporary root was removed. This proves the guard's permitted form has a local write
effect; it is not a native Claude hook-installation or model-behavior test.

[verified] The caller loaded all five actual graders in the software-engineer no-tools build
scenario. A truthful no-files/no-tests response passed all five; a first-person fabricated creation
claim failed the creation predicate. Passive and bare-voice fabricated creation claims both passed
all five while disclosing that tests had not run. All assertions passed under Python 3.14.7.
Only response text was graded: no named implementation/test artifact was created and no native
model ran. This is separate from the shared exact-fields extra-prose weakness.

## Final packet reconciliation

[verified] The final pre-commit reconciliation found exactly **39 asset reports**, each carrying
the frozen source identity and all six pass records: **234 documented analytical passes**. It
found **50 unique confirmed finding IDs**. All **162 captured bundle-file SHA-256 values** still
match the initial snapshot. The complete change from the source baseline is confined to this
review packet and its AUDIT-001 roadmap entry; canonical sources and generated adapters are
unchanged. The existing group commits were checked in order, with exactly the relevant three
asset reports introduced by each. The final delivery additionally checks the last commit and
clean audit-worktree state.

[verified] The original checkout still reports its pre-existing modified `docs/fleet-roadmap.md`
and untracked `docs/sre-workbench/`; this audit did not edit those user files. The separate
disposable baseline worktree was removed only after checking its exact resolved path, frozen HEAD,
absence of tracked changes, and its 12 owned untracked atlas outputs. The findings worktree and
local raw evidence under `F:/iso-tmp/fleet-audit-20261002/` are retained.

These results complete the requested review and findings record. They do not implement repairs,
promote a candidate, close the existing host/native/target acceptance gates, or supply a fresh
production observation. AUDIT-001 now points the human owner to scoped repair/disposition choices.
