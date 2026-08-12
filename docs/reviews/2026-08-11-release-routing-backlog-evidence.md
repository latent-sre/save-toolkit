# RELEASE-001 and ROUTE-001 preparation evidence

- **Evidence date:** 2026-08-11 (America/Chicago)
- **Working branch:** `codex/full-backlog-release-routing`
- **Reviewed base:** `65fe5c8c28da0052e3204adfac2af152e9a02475`
- **Status:** prepared, not closure evidence. Repository changes remain local to this branch; no
  push, tag, Release, workflow dispatch, or model call is authorized by this packet.

This packet binds the local verification behind the live roadmap. It records preparation and
review, not authorization to publish a release or send an eval prompt to a model provider.

## Remote and pull-request baseline

- [verified] `git fetch --prune origin` completed, after which `HEAD` and `origin/main` both resolved
  to `65fe5c8c28da0052e3204adfac2af152e9a02475`; `git rev-list --left-right --count
  HEAD...origin/main` returned `0 0`.
- [verified] `gh pr list --state open --limit 100 --json ...` returned an empty list.
- [verified] PR 102, `Pool Gate A steps, batch guard spawns, drop verified-dead code`, is merged at
  the same commit. No open Cursor-authored pull request remains.

## RELEASE-001 repository evidence

The prepared release path consists of the four version-bearing manifests, changelog, install
examples, accepted promotion ADR, release runbook, workflow, release request contract, workflow
mutation contract, and strict published-source host probe. These bytes do not create GitHub controls
or authorize workflow dispatch.

The release candidate remains pre-1.0. All four manifests now identify `0.1.0`, the changelog and
install examples name `save-toolkit--v0.1.0`, and a repository-level contract test prevents a silent
major-version jump until v1 is deliberately authorized. [verified] That test failed against the
accidental `1.0.0` state and passed after the correction. [verified] No local or remote
`save-toolkit--v*` tag existed when the correction was prepared, so `0.1.0` does not reuse a release
tag.

### Reviewed byte identity

The review base is `65fe5c8c28da0052e3204adfac2af152e9a02475`. The corrected 16-file release
surface is additionally bound by sorted `relative-path<TAB>file-sha256<LF>` records, lowercase
SHA-256, with manifest SHA-256
`c654e7de53f0b4b645352c5f4692adb86ee121f35ba3c5a2e98a45c9e2303fef`:

```text
.claude-plugin/marketplace.json	50c4d8a7a4a3324659d7a0f106d9f3f6c4ea10ff796d9bd9a182842d48f055bd
.claude-plugin/plugin.json	01f4678a009c63a2ccd7764f88bb55cdcc84beda30b6c859106f2425632faa1c
.github/workflows/release.yml	3dea37c94659a05953acd871007751caa2e4fe974493b6b164f33662a3724ce2
CHANGELOG.md	b64a372e8fecd12b87b98b441c3becb207a271c7cacced4a1193584c3f693429
docs/decisions/2026-08-11-immutable-release-promotion.md	0e1606fa480fb45aa517540150e960f2022c7b328a0d883d1aacb5f7b2bf244f
docs/release-runbook.md	18a44da7b128f3b174540a2f2636a168482423d6758e9ecb92d3a15325640ca7
evals/test_run_evals.py	2b2ff378a8b88858754c103077d2d36bdad8f4155f15bca92ada8e5e6e264484
plugin.json	fa35fa25813f6bfac3bd4b410bdbc63ddf5a76428f6a89978f32852399fbb932
plugins/save-toolkit/.codex-plugin/plugin.json	c463c0063670db6a1ede45cfefe86bfebb166c189c5ba68e58739ad693e69fa2
README.md	27108eca4906d358fcc66bc23edb23486412979191e4d5d7c9a18db69c7698c8
scripts/host_install_probe.py	1604dcb0101b7d945ebd2515de976c36666e03f705ee64ba49f15550e6f900f8
scripts/release_contract.py	70eed939d49be7b2bac9e521cc413f1fe34ea75098729cc8755821c6d2b5b364
scripts/release_workflow_contract.py	969f52e5f670373edb49c6bf0f713bc892a487f76c17a1c801cde5e376cb2e24
scripts/test_host_install_probe.py	c06bde94db637934834fab50d3d76daf2b35dd1d2feb3f9e9744fe7e9faf8ecf
scripts/test_release_contract.py	60d75f3f0706f436da44420b3261e3fa57368882fcdf3fd1052022c257e899db
scripts/test_release_workflow_contract.py	ea700a356cafd05aa56a7525c78a9bf525830c84cf1d0b2452a8b9c400e9b142
```

Earlier reviews covered the pre-beta ten-file release surface and the additive host edge-case
fixture delta; they closed the five state-machine blockers and found no P0-P2 in that host follow-up.
Their byte identities are now superseded: the beta correction changed the four manifests,
changelog, README, release-contract test, and the host/eval tests' local inventory defaults. The
16-file manifest above plus the exact corrected-commit review are the authoritative coverage for the
current candidate.

| Check | Result |
|---|---|
| `python scripts/test_release_contract.py` | [verified] 11/11 passed |
| `python scripts/test_release_workflow_contract.py` | [verified] 2/2 passed |
| `python scripts/test_host_install_probe.py` | [verified] 65 tests: 63 passed, 2 existing Windows symlink-privilege skips |
| Host-provenance sensitivity mutations | [verified] all four SHA-256, `100755`, non-blob, and case-fold mutants were caught |
| `claude plugin validate . --strict` | [verified] passed with Claude Code 2.1.227 |
| `claude plugin tag --dry-run .` | [verified] the prior clean local commit exposed the unintended `save-toolkit--v1.0.0`; no tag or Release was created. The corrected result is reported as post-packet evidence after the final commit is clean |
| `python scripts/gate_a.py` | [verified] 30/30 structural steps passed after the host and routing fixes |

A disposable local diagnostic ran Claude, Codex, and VS Code install/inventory/authority/uninstall
lifecycles with 12 pass, zero fail, zero skip, and zero inconclusive checks; its target was removed.
That run used local candidate bytes and is **not** published-artifact evidence. The strict
`--require-pass` form correctly refused the dirty worktree before target creation. A compliant
remote-tag smoke therefore remains a post-merge release-workflow requirement.

Independent inspection found no P0/P1 in the frozen release state machine and confirmed the five
earlier blockers were closed: stable rerun identity, attempt-addressed artifacts, exact timestamp
canonicalization, durable cross-dispatch reservation, and immutable Git-object provenance. The
named host edge-case follow-up received no P0-P2 finding. Its beta-fixture correction is frozen in
the 16-file manifest above and remains part of the exact-commit re-review requirement.

## ROUTE-001 offline evidence

The stream parser and root-scope grader changes are deterministic and do not call a model:

- [verified] `evals/test_run_evals.py`: 66/66 passed.
- [verified] `evals/test_clean_room.py`: 29/29 passed.
- [verified] `evals/test_graders.py`: 166/166 passed.
- [verified] `python evals/run_evals.py --validate`: 66 scenarios parsed (19 direct, 47 discovery,
  28 regression).
- [verified] Only the two active-incident negatives use `routing.scope: root`; inline, wrong-root,
  orphan, non-agent, cyclic, ambiguous, and duplicate-identity ancestry fails closed.

An independent review found that raw prompt echo passed 18/19 new response-grader sets and a
whitespace-normalized echo passed 19/19. The repair was proven red first: the new 19-case regression
passed 21/58 checks and failed the expected 37 echo-rejection checks before the YAML changes. After
the repair it passed 58/58, while every curated substantive response still passed. Prompts, targets,
routing expectations, generic graders, and runner code were unchanged. Independent review then found
three keyword-rich but behaviorally incomplete controls. Their regression was captured red at 0/3;
after the affected graders and complete fixtures were repaired, the combined focused checks passed
61/61. A final canonical-format control then exposed three fixture-shaped false negatives at 0/3;
after accepting the SRE contract's Markdown labels and equivalent alert relationships, the combined
focused checks passed 64/64 while the incomplete controls remained rejected. A reversed throttle
relationship then failed red at 0/1; binding the comparator's subject and destination closed it and
the combined focused checks passed 65/65. Two locally negated unsafe relationships then failed red at
0/2; explicit negation exclusion closed them while preserving the safe `cannot outlast` form, and the
combined focused checks passed 67/67. The 21-file oracle surface has manifest SHA-256
`974b09ff34ea8ca3ab27aa906aada2bfd0249504f8a3fa87d12db128c924e154`, computed from sorted
`relative-path<TAB>file-sha256<LF>` records.

## Prepared live campaign

No live trial was started in this preparation step.

- [verified] The last pre-expansion baseline is
  `a39a81f33f7ad7325c52d883822bbbdd80c7ed28`; the detached baseline worktree resolves to that SHA.
- [verified] The five shared description scenarios are staged once for both baseline and current;
  fourteen GCP/Akamai scenarios are current-only.
- [verified] All 25 harness files match the workspace source after the response-oracle repair.
- [verified] Both baseline and current plugin-input surfaces have zero changes under the runner's
  exact measured paths (`agents`, `skills`, `commands`, `hooks`, plugin manifest, and guard scripts).
- [verified] The paired-five harness has 8 files and manifest SHA-256
  `f8184b7da952e74ec507213f3c0aeda590c42155491c97b873688a0111a52101`; the current-fourteen harness
  has 17 files and manifest SHA-256
  `72b9c329e977cf432181f2d3c1b4788a5fb1044017c551b1387b80417f5ea96a`. Each digest uses sorted
  `relative-path<TAB>file-sha256<LF>` records and excludes Python cache files.
- [verified] The first intended paid canary was rejected before process/model execution because the
  owner has not explicitly approved transmitting the fixed prompts and isolated plugin context to
  Anthropic or incurring model usage.

If approved, the prepared contract is 5 baseline plus 5 current paired scenario executions and 14
current-only executions, each at two trials: at most **48 sequential Claude Sonnet trials**, a
300-second per-trial timeout, and a worst-case timeout envelope of about four hours plus overhead.
Stop on runner exit 2/3. Persist only sanitized digest/count/verdict/runtime evidence; private raw
traces, prompts, responses, and session identifiers remain outside the repository.

## Explicit evidence boundaries

- [unverified] No comparable before/after live routing result exists yet. Offline oracle strength is
  not a substitute for live description-routing measurement.
- [unverified] No protected release environment, release-tag ruleset, immutable-release setting, or
  separately controlled publisher App was created or inspected as closure evidence.
- [unverified] No published tag was installed, no immutable Release was created, and rollback from a
  prior published tag was not rehearsed.
- [verified] A local commit was created to freeze the prepared backlog and then reopened for this
  beta-version correction. Nothing was pushed; no tag, Release, workflow dispatch, or model call
  occurred.

One workstation caveat is unrelated to repository correctness: invoking the local `codex --version`
wrapper unexpectedly ran its maintenance hook. It reinstalled the already-current Codex CLI 0.147.0
and reported the `latent-sre` marketplace already current. No repository file changed, and that
maintenance output is not host-smoke or release evidence.

## Required next decisions

1. Before merge, retain the post-commit clean tag dry-run result and independently re-review the
   exact corrected commit. A mutable-tree verdict cannot become approval.
2. Separately decide whether to authorize the 48-trial external Claude data/cost boundary described
   above. Without explicit approval, retain ROUTE-001 as blocked.
3. After merge, separately decide whether to create the ADR's protected GitHub controls. Their plan
   and rollback must be approved before any release workflow dispatch.
