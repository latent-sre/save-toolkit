# Independent-review fixes

Initial candidate from main at `e6702ee0`, developed on `work/address-independent-review-20260907`.
The human authorized remediation of the independent review's findings. This record describes
source fixes; it does not accept a release or claim installed-host/model behavior.

| Finding | Change and verification target |
|---|---|
| Regrade result collision | Bind retained outcomes to unambiguous assertion/scenario identities; opposite rubric results stay independent and ambiguous legacy records are inconclusive. |
| Mixed candidates and mutable input | Reject incompatible existing batches before a model call; keep full machine digests and invalidate trials whose plugin bytes change. |
| Installed helper paths | Link the bundled helper, resolve its installed absolute path, and reject unsafe generated rewrites. Run from a neutral project containing a same-named shadow script. |
| Absent Copilot guard | Qualify the credential tripwire and Bash toolbox as Claude-specific; preserve tool grants and the empty Copilot hook. |
| Misleading tests | Remove retired negative-action fixtures, test only actual offline structure, and validate dependency installation in the same job before Gate A. |
| Confluence content loss | Preserve links and image references, report uncopied attachments/unsupported content, and use h1 as the missing-title fallback. |
| Conflicting authoring rules | Separate prompt consumption from executable code, repaired failures from preserved regressions, and new behavior from a failing baseline. |
| Human GCP access | Give console views beside CLI equivalents, with unavailable-access and evidence-time rules. |

The existing dependency pins remain authoritative. `requirements-test.txt` selects pytest and
PyYAML under those constraints, so ordinary CI need not install sandbox frameworks.

The importer regressions failed on the reviewed base, then passed with the fix (16 tests,
7 subtests). The evaluator and packaging owners also captured focused failures before their fixes.

The first integrated run in a clean Python 3.12.10 environment with pytest 9.1.1 and PyYAML 6.0.3
passed 481 tests and 921 subtests in 57.48 seconds. Four skips were three unavailable Windows
directory-symlink checks and the CI-only shell requirement; Git Bash was on PATH and the actual
hook/stub-interpreter tests ran. No sandbox frameworks were installed.

Independent inspection then found a residual cross-model overwrite/regrade attribution path and
an inaccurate disk-drift claim for the judge's cached rubric definitions. The parent reproduced
the attribution defect with temporary records. Regrade now requires the saved run's complete
candidate/scenario/model identity to match before updating a summary; conflicting rows become
INCONCLUSIVE. A real file/cache-lifecycle test verifies the documented per-process rubric snapshot.
The initial green suite alone did not establish correctness.

## Final verification

- [verified] Full pinned-environment suite after the follow-up: **482 passed, 4 skipped,
  921 subtests passed**, in 59.16 seconds. Skip reasons are the same four named above.
- [verified] Gate A: **4/4 PASS**; scenario validation: **65 specs / 324 expectations**;
  regenerated adapters and link checks pass. No task-context budget changed.
- [verified] Final weight: eval Python **9,539 lines**, skills **578,305 bytes**, agents
  **114,667 bytes**. Versus the reviewed base: +287 eval lines, +2,362 skill bytes, +193 agent bytes.
  These totals include the focused tests and helper code; they are not runtime token measurements.
- [verified] An independent final source pass found **no remaining reportable findings** in patch
  `476cd703c87eac3cfbc833ebf3f9cd1d1cd6337788b93f2d70b92bec895b1fb3` against `e6702ee0`.
  The reviewer did not execute tests. Its disposition remains provisional for these uncommitted
  bytes, not merge or release approval. Only this evidence prose was completed after that review.
- [verified] The parent's independent regrade check preserved an identified FAIL/PASS pair as
  FAIL/PASS; the same legacy pair without identity became INCONCLUSIVE. No model was called.

Historical original results are retained. The compatibility change prevents ambiguous records
from being regraded or combined into newly attributed evidence; it does not rewrite prior human
acceptance decisions. Changing the measured inputs requires a fresh trial under a new label.

A metadata-only check of 499 existing private grading records found no duplicate-rubric records
or regrade FAIL-to-PASS changes. One old scratch summary under
`.eval-runs/remaining-findings-20260904/review-candidate/` mixed candidate digests; the retained
[operational-contract review](2026-09-04-operational-contract-fixes.md) uses a separate final-case
directory and already warns against combining initial variants. No private record was modified.
This inventory does not revalidate model judgments or make legacy records safe to regrade.

The skill-byte ceiling increases from 576,000 to 579,000 to accommodate conversion-loss handling
and the console/helper corrections. Other ceilings and task-context budgets are unchanged. This
is a measured repair allowance, not evidence of model quality.

## Remaining evidence

The installed VS Code version observed on this machine is 1.136.1 (`a44adf7f`), but its chat runtime
was not exercised. Use the [acceptance procedure](../vscode-plugin-acceptance.md) and the live
HOST-002/INCIDENT-QUALITY-001 items. No live model campaign, marketplace publication, versioned
release, or production action is part of these source checks. The managed security scan did not
start during the review; its coverage remains incomplete.

Claude Code 2.1.263 validates the marketplace with `claude plugin validate . --strict`. Explicit
plugin validation of `.claude-plugin/plugin.json` passes with the existing warning that root
`CLAUDE.md` is development context and is not loaded from an installed plugin. The explicit plugin
check with `--strict` therefore does not pass; do not confuse the marketplace result with it.
Those initial source checks claimed no hosted CI run or release.

## PR #237 integration

The human requested adding these fixes to the existing short-commit-ID PR. Commit `b4828007`
preserves the reviewed remediation; its integration with PR #237's `f7180d3c` preserves the
short-ID convention in routine handoffs, templates, and the importer. Machine evaluation digests
remain complete. Canonical sources merged without conflicts and the adapters were regenerated.
The [PR record](https://github.com/latent-sre/save-toolkit/pull/237) carries verification for the
combined head. The earlier numbers above remain evidence for the remediation before integration.
Publication does not close the installed-host/model or release acceptance items.
