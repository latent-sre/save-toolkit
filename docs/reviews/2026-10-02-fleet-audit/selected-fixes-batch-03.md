# Third selected audit repair batch

Date: 2026-10-02. Human owner: the user; integration caller: `/root`.
This is evidence for `AUDIT-001`, not a separate backlog or acceptance decision.

## Scope and identity

The user selected **AA-01/02/03/04, OA-01/02/03/04, CI-01 and BC-01/02**.
The repair branch is `work/fleet-audit-selected-fixes-20261002`, in
`F:/repos/sre-agents-audit-fixes-20261002`, based on published commit
`e64e7c628d6f82dbd5647f99c3bfae9a3eb178d6`. A fresh fetch confirmed the local branch and
upstream matched before this batch. The original audit source remains `a2d2e57d`;
the [first sixteen repairs](selected-fixes.md) retain their historical evidence.
The original dirty checkout and completed audit checkout are separate and untouched.

These eleven repairs bring the selected total to **27 of 50** confirmed findings.
The remaining **23** and optional recommendations retain their original dispositions.
FA means `fleet-atlas`, the skill and CLI mapping fleet artifacts and their relationships;
FA-01/02 were explained, not selected for implementation. BC-R01 was also outside scope.

## Repairs and discriminating evidence

| Finding | Problem and repair | Evidence and limits |
|---|---|---|
| [AA-01](group-01-agent-authoring.md) | A same-suffix read from another checkout or generated copy could satisfy a required canonical reference. Bind every such read to the measured plugin root; resolve relative paths only against the known trial workspace. Save that workspace for regrading. | Actual grading/regrading rejects wrong roots, generated/workspace copies, denied reads and missing provenance; absolute and known-workspace relative positives pass. Missing saved plugin identity is inconclusive. Relative paths without a recorded workspace fail closed. |
| [AA-02](group-01-agent-authoring.md) | A positive calibration response claimed removing WebFetch prevented callbacks while Bash remained. Correct that example and a second positive making an unsupported claim about removing untrusted input. | All six positive examples inspected against the supplied toolset; 164-case corpus parses with valid parameters and retains six positive/six negative security cases. The substantive rubric is unchanged. Live judge recalibration remains unverified. |
| [AA-03](group-01-agent-authoring.md) | Skill directory/name and character-count rules were presented as generic artifact metadata rules. Scope them to skills and link the agent-specific rules. | Checked against canonical frontmatter validation and the existing reference; no prose-mirroring test. |
| [AA-04](group-01-agent-authoring.md) | The delegation reference claimed every orchestrator reaches researcher despite its explicit reviewer restriction. Delete the contradictory universal row. | No agent tools, graph edges or permissions changed. Existing fleet validation covers the authoritative graph. |
| [OA-01](group-04-obs-alerting.md) | Binary float arithmetic classified an exact inclusive burn boundary as below threshold. Preserve decimal inputs and compare the SLI directly with an exact decimal cutoff. Align the reference's wording with the existing inclusive policy. | Actual CLI checks all three pairs at, above and below threshold, including differences below float precision, mixed windows, scientific spelling and invalid input. Existing status/display arithmetic and range behavior remain. |
| [OA-02](group-04-obs-alerting.md) | The handoff checker erased PromQL `bool`, `on` and `ignoring`, changing the expression before grading. Preserve the expression so the scalar whitelist rejects unsupported modifiers. | Actual embedded predicate accepts supported two-window filters and rejects the modifier mutants, OR, raw thresholds and single-window forms. This remains a bounded scalar check; no PromQL engine or native trial ran. The fixture's explicit strict `exceed` task is unchanged. |
| [OA-03](group-04-obs-alerting.md) | A native Prometheus rules fixture claimed direct Grafana-managed file provisioning. State that the platform team loads and evaluates these rules in Prometheus. | Task, native rule schema and existing pinned promtool checker now describe the same artifact. No deployment or conversion step was added. |
| [OA-04](group-04-obs-alerting.md) | Splunk guidance contradicted its own suppression-group capability. Explain same-group, same-user ownership, with a different-owner control, and state the team's Moogsoft ownership separately. | Current official Splunk 10.4 contract supports the correction; deployed target behavior remains unverified. |
| [CI-01](group-02-ci-actions.md) | Downloading the expected artifact was credited even when `cf push` selected unrelated bytes. Bind each direct push in a selected deploy job to the download destination and reviewed manifest; reject unresolved paths and opaque mutation/rebuild forms. | Actual CLI accepts supported path/default/cwd/env forms and rejects ignored downloads, unrelated payloads, wrong manifests, replacement, rebuild and trailing opaque commands. Static path binding does not establish runtime digests or deployment readiness. |
| [BC-01](group-01-backend-craft.md) | The HMAC webhook fixture penalized the security review its task required. Remove its unconditional reviewer prohibition. | An actual parsed scoped-review trace is permitted; the routine CLI reviewer prohibition and webhook scope/commit controls remain. This repairs the fixture, without expanding agent authority. |
| [BC-02](group-01-backend-craft.md) | HTTP predicates accepted malformed cursors and incomplete problem bodies. Check the contract's media type and field types in all three independent oracles, and validate populated limit/traversal behavior. | Real HTTP boundary controls reject invalid cursors, missing request IDs, malformed fields, empty/ignored limit=1, duplicate/skipped/reordered records and bad termination. Shipped handlers, integral JSON status values and case-insensitive media types pass. |

The backend starter requires a project-owned `populated_collection_ids` fixture containing all
ordered IDs from an isolated stable collection (at least two). It seeds no datastore itself.
A separate above-cap seed remains necessary to establish a project's maximum page limit.
The three injected backend oracles remain self-contained and do not import candidate validators.

The CI predicate supports straight-line bash/sh, literal paths and environment values, checkout
and artifact-download steps, run-directory defaults, literal `cd`, and a small set of diagnostic
commands. Unsupported forms return a diagnostic rather than receiving promotion credit.
The pre-existing lexical `cf push` job-discovery rule remains: a push hidden entirely inside an
uninspected script in another job is outside this evidence. No general shell interpreter was built.

## Failure-first and affected verification

All commands used the existing Python **3.14.7** interpreter at
`F:/repos/sre-agents/.venv/Scripts/python.exe`. No dependency install or model call was needed.
Logs are under `F:/iso-tmp/fleet-audit-fixes-20261002/batch-03`.

- AA-01: before repair, **20 failing subtests** exposed wrong-root/missing-provenance acceptance.
  Focused repair: **4 tests / 40 subtests passed**. The first broader run exposed a new `ws=None`
  compatibility error; that was corrected and its failed log retained. Final affected build,
  judge, links and fleet checks: **371 passed, 1 skipped, 581 subtests passed**.
- OA-01: the original calculator failed **9 new boundary subtests**. The repaired calculator
  passed **10 tests / 31 subtests**. OA-02's original predicate accepted all four modifier mutants;
  the final combined OA checks passed **13 tests / 42 subtests**, exit 0, 5.93 seconds.
- BC-01/02: the initial regression run had **90 failures / 40 passes**; another seven pagination
  controls reproduced missing cursor/limit enforcement. Six affected suites passed **318 tests**,
  with one existing Starlette/AnyIO deprecation warning, in 202.73 seconds. A final stable-ID
  coherence adjustment passed all **38 incidents-oracle tests**.
- CI-01: the original oracle falsely accepted **25 negative subcases**. Root review then identified
  a cutoff that skipped trailing opaque commands; four actual CLI counterexamples reproduced it.
  The final predicate checks all steps in each selected job and retains supported post-push
  diagnostics. That revision's workflow/build-probe suites passed **224 tests / 394 subtests**,
  exit 0, 88.83 seconds. Independent review then found argument injection through an unchecked
  non-path option value: an unquoted buildpack variable could expand into a new `-p`. Every
  valued option now requires one supported shell word, including inline boolean values;
  unresolved, empty, multiword and glob expansions reject, with quoted controls retained.
  A hash-bound replay of the pre-correction oracle reproduced **16 false acceptances**; the
  corrected version passed all **22 controls**. The final focused calibration passed
  **8 tests / 79 subtests**. Earlier CI results came from
  tool transcripts; the later baseline-copy calibration and final green logs are retained in
  the `ci` scratch directory. The complete final suite below covers the option-value repair.

No fresh paid judge calibration was run after changing the two labeled corpus examples.
Offline parsing does not renew historical judge receipts against these new corpus bytes.
Native/model behavior and exact-candidate human acceptance remain open.

## Sourced contracts and context cost

[sourced] Context7 retrieval on 2026-10-02 supplied Python's
[decimal arithmetic documentation](https://github.com/python/cpython/blob/main/Doc/library/decimal.rst),
[PromQL operator semantics](https://prometheus.io/docs/prometheus/latest/querying/operators/),
Grafana's [alerting file schema](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/),
and Splunk Enterprise 10.4's
[savedsearches.conf contract](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.4/configuration-file-reference/10.4.0-configuration-file-reference/savedsearches.conf).
These support the OA corrections; target configuration and delivery were not exercised.

GitHits separately retrieved Prometheus v3.14.0 source showing
[retained zero-valued bool samples](https://github.com/prometheus/prometheus/blob/v3.14.0/promql/engine.go#L3427),
[label-set intersection](https://github.com/prometheus/prometheus/blob/v3.14.0/promql/engine.go#L3115),
and [alert state for returned elements](https://github.com/prometheus/prometheus/blob/v3.14.0/rules/alerting.go#L402).
The documentation and implementation evidence agree. This was source inspection, not local
execution of the Prometheus engine.

[sourced] Context7 supplied GitHub's
[artifact transfer contract](https://docs.github.com/en/actions/tutorials/store-and-share-data)
and [run-directory precedence](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/set-default-values-for-jobs).
GitHits separately corroborated single-artifact extraction in
[download-artifact](https://github.com/actions/download-artifact/blob/3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c/src/download-artifact.ts),
single-file root selection in
[upload-artifact](https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/src/shared/search.ts),
and CF's [manifest-relative fallback and path override](https://github.com/cloudfoundry/cli/blob/49cf12264a27142382ce4901779d6d74fff4fc84/actor/v7pushaction/handle_app_path_override.go).
These establish the CI resolver's modeled path semantics; no hosted job or CF deployment ran.

Relative to this batch's base, the two authoring references shrink by one byte overall.
The burn reference grows 48 bytes and the Splunk reference 550 bytes; no skill entrypoint or
agent body changes. Executable growth: reference provenance **1,084 bytes / 18 lines**;
calculator **1,459 / 28**; backend starter **1,693 / 32**; three independent backend oracles
**3,798 / 71**; CI path checker **11,290 / 190**. The latter is the largest addition because it
must resolve destinations and reject mutation/opaque shell forms before granting path evidence.
Positive compatibility and reproduced negative controls justify these mechanisms; they are
bounded checks with the limitations above, not general parsers or live-platform validators.

## Final integrated verification and disposition

[verified] Root's full repository run completed with **1,677 passed, 3,081 subtests passed,
19 skipped, one warning and 22 setup errors**, exit 1, 672.85 seconds. All 22 errors came from
the frontend module's common fixture: the caller selected a new `INCIDENTS_PAGE_SCRATCH` parent
directory without creating it. A focused reproduction confirmed `FileNotFoundError` before
any UI check executed. The caller created that scratch directory, without changing repository
bytes, and reran the entire affected frontend module: **22 passed**, exit 0, 58.90 seconds.

The combined evidence therefore covers **1,699 passing tests and 3,081 passing subtests**;
it is not represented as a single green full-suite invocation. All observed setup errors are
resolved by the targeted rerun. The failed run and reproduction remain retained. Skips are three
Windows directory-symlink cases, two shell/CI checks, eleven external-producer acceptance cases
and three opt-in Docker/Claude checks. The warning is the existing Starlette/AnyIO deprecation.

Commands, with `PYTHONDONTWRITEBYTECODE=1`, `RUN_INSPECT_DOCKER_SMOKE=0`,
`INCIDENTS_PAGE_MODE=bounded`, existing dependencies at `F:/repos/backbox-ui/frontend/node_modules`,
scratch at `F:/iso-tmp/fleet-audit-fixes-20261002/batch-03/frontend`, and no
`INCIDENTS_PAGE_ORACLE` override:

```text
python -X utf8 -B -m pytest -q -rs -o cache_dir=F:/iso-tmp/fleet-audit-fixes-20261002/batch-03/final-pytest
python -X utf8 -B -m pytest -q -rs evals/test_incidents_page_oracle.py -o cache_dir=F:/iso-tmp/fleet-audit-fixes-20261002/batch-03/frontend-final-cache
```

Logs: `batch-03/full-suite.txt`, `frontend-setup-red.txt` and `frontend-final.txt` under the
scratch root above. The frontend checks retain the earlier repair's bounded execution boundary:
actual oracle bars 1/2/3/5, a fetch transport double, existing borrowed dependencies, and no axe,
native browser or assistive-technology validation. Full MSW integration and model behavior remain
unverified. No new package, browser or container download occurred.

Scenario validation passed **193 specs / 741 expectations**; the removed webhook reviewer
prohibition accounts for the one-expectation reduction. Adapter generation, canonical links and
`git diff --check` passed. The final structural gate is recorded in the publication receipt.

Implementation identity: base `e64e7c628d6f82dbd5647f99c3bfae9a3eb178d6` plus the
**30 changed/new non-report files** in `batch-03/implementation-manifest.json`, including six
generated skill copies. Sorted path/size/SHA-256 manifest digest:
`fb231cfb98ee6ef5c3e1bae09f4458ae2b4e586b14174675517534e2e88ed671`.
Root confirmed this manifest remained unchanged through the full run and frontend recovery.
The publication readback compares each implementation blob in the final commit to this manifest.

Independent static review found the CI argument-expansion gap above; it was repaired and
re-reviewed with no remaining concrete findings in the selected implementation. The reviewer
executed no code; root owns the integrated execution evidence. Final commit and remote identity,
implementation-byte readback, exact-commit review and gate result belong to the publication receipt
at `batch-03/publication-receipt.json`.

The eleven selected findings are repaired with the verification limits above. The user authorized
commit and push on the existing repair branch; no merge, deployment or live platform operation is
part of this change. `AUDIT-001` retains owner disposition of the other 23 findings and acceptance
of the exact published candidate. Original group reports remain evidence of the audit baseline.
