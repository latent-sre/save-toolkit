# Codex/Terra ROUTE-001 pre-canary evidence

- **Evidence date:** 2026-08-11 (America/Chicago)
- **Working branch:** `codex/full-backlog-release-routing`
- **Working-tree parent:** `b459a5d3a209d384acb2b2b7ca325aa63697113b`
- **Paired baseline:** `a39a81f33f7ad7325c52d883822bbbdd80c7ed28`
- **Status:** offline implementation verified; authenticated canary is **NO-GO** on this host
- **Authority:** preparation evidence only; no model-call, baseline, release, merge, or publication authority

## Bottom line

ROUTE-001 has been rewritten for Codex CLI 0.147.0 and `gpt-5.6-terra` at medium reasoning. The
fixed manifest contains nineteen scenarios and 48 sequential trials: five scenarios run twice at
both revisions (20 trials), while fourteen GCP/Akamai scenarios run twice at the current revision
(28 trials). The offline evaluator, trusted-bootstrap boundary, fixed canary contract, routing
graders, Git-object staging, credential lifecycle, and sanitized evidence reducers pass their tests.
Gate A passes 38/38 structural steps.

This is **not** a live routing result. No Codex credential was copied into the final harness and no
prompt was sent to OpenAI. The current Windows host does not yet provide the protected Python
runtime closure or clean effective configuration/registry/object-store boundary required by the
accepted [routing ADR](../decisions/2026-08-11-codex-terra-routing.md).

## What the evaluator can and cannot measure

- [verified] The seventeen non-root scenarios can produce observational response-grader verdicts.
  A complete non-root trial requires zero command, collaboration, and subagent-start evidence. A
  positive result means the fixed response graders passed; it does not prove an internal skill
  activation event because Codex 0.147 exposes no joinable skill-invocation receipt.
- [verified] The two root-scoped active-incident cases always return `INCONCLUSIVE` with
  `root-delegation-unobservable-v2`. Stock Codex 0.147 cannot join the encrypted V2 delegated task,
  terminal child result, and root consumption. Answer text and partial lifecycle receipts cannot
  turn those cases into `PASS` or `FAIL`.
- [verified] The one prepared authenticated canary is the non-root
  `discovery-gcp-ops-cloud-run-startup` scenario. It disables multi-agent, permits only three fixed
  linear `contains_all` graders, and rejects responses above 256 KiB total or 8 KiB per line before
  grading.
- [verified] The runner fixes `source_review = not-verified-by-runner`,
  `independent_evaluator = false`, `baseline_eligible = false`, and `release_granted = false`.
  Neither the model nor the evaluator can promote its own evidence.

## Red-first defects closed

The following contracts were demonstrated failing before their repairs and passing afterward:

1. Root-agent receipts appeared sufficient to score routing even though V2 spawn input and child
   consumption were not joinable. Root cases now short-circuit to deterministic `INCONCLUSIVE`, and
   a regression proves their response graders are not called.
2. Model-controlled output could reach unbounded regular-expression grading. The fixed canary now
   uses literal linear graders, and all non-root trials enforce total and per-line response limits
   before any grader runs.
3. The disposable auth copy could survive unexpected refresh or interruption paths. The final auth
   guard refresh now removes and verifies absence of the copy in a `finally` path before JSON,
   receipt, response, or grader processing; `RecursionError`, `KeyboardInterrupt`, and `SystemExit`
   regressions exercise that ordering.
4. A staged `__main__` entrypoint and an imported runner created distinct `TrialSpec` class
   identities. The type now lives in the shared harness and a staged-entrypoint regression exercises
   the real import boundary.
5. Mutable manifest/scenario rereads could separate approved hashes from executed bytes. Parsing is
   single-load and manifest-bound; each `TrialSpec` carries the exact scenario digest.
6. Ambient temporary directories, non-local storage, late `.git` insertion, executable drift,
   unbounded capture/receipt files, and hook-directory import shadowing had fail-open or ambiguous
   paths. The prepared bootstrap now requires an empty local fixed NTFS private root, exact
   create-only trees, bounded Job-contained processes, and pre/post byte verification.
7. Evidence labels incorrectly claimed subagent activation and a scored root-collaboration policy.
   Manifest and serialized trial labels now distinguish non-root no-model-tool evidence from
   unscored root collaboration.
8. A surprise non-root `SubagentStart` with no PostToolUse or JSONL collaboration fact could still
   pass. The focused regression failed with `PASS` before the fix and now returns
   `INCONCLUSIVE/non-root-tool-flow-observed`.

## Fresh offline verification

| Check | Result |
|---|---|
| `python evals/test_codex_harness.py` | [verified] 20/20 passed |
| `python evals/test_codex_hook_recorder.py` | [verified] 9/9 passed |
| `python evals/test_codex_model_catalog.py` | [verified] 5/5 passed |
| `python evals/test_codex_routing_grade.py` | [verified] 22/22 passed |
| `python evals/test_codex_snapshot.py` | [verified] 26/26 passed; one Windows symlink-privilege skip |
| `python evals/test_codex_trial.py` | [verified] 39/39 passed |
| `python evals/test_codex_bootstrap.py` | [verified] 32/32 passed; two Windows symlink-privilege skips |
| `python evals/test_run_codex_routing.py` | [verified] 18/18 passed |
| Eight Terra unit files combined | [verified] 171 tests passed; three privilege-dependent skips |
| `python evals/run_codex_routing.py` | [verified] manifest valid: 19 scenarios, 48 trials |
| `python evals/run_codex_routing.py --plan --current-revision b459a5d3...` | [verified] 10 before, 38 current, 48 total; no model call |
| `python scripts/check_links.py` | [verified] passed |
| `python scripts/check_plan_status.py` | [verified] passed |
| `git diff --check` | [verified] passed |
| `python scripts/gate_a.py` | [verified] 38/38 structural steps passed |

Gate A proves that the fleet and evaluator are well-formed. It does not establish the host trust
boundary, model behavior, routing correctness, or a comparable before/after baseline.

## Reviewed byte identity

The implementation/documentation surface is bound by sorted
`relative-path<TAB>file-sha256<LF>` records with manifest SHA-256
`f4153e8d0882ffc951836fbcd3205c2669d8313e5b4958f5068a5b50f70660b2`:

```text
docs/decisions/2026-08-11-codex-terra-routing.md	0e829c44238179018d5022dadd4062d82fd78f7dd61c1af1d85140a84ed2bb3b
docs/fleet-roadmap.md	de576b4cce2f50f3ed82f24bac3e8177a480c914b92da46c5e89d5d36d381cbd
evals/codex_bootstrap.py	4ff0b789fa559b52db1f11fdf9b7bb6ab2a9ece3c2b7d3123480b30ee0e9b311
evals/codex_harness.py	b3ef13a4ac72f300b4e954576cef8a9b5be538a926ecb29b4578a74b15665273
evals/codex_hook_recorder.py	c2fd5b9b3583b6dd12874850a1528eafa20b42a7d60f0c5435a1606f1105ddc8
evals/codex_model_catalog.py	08bd77d84c572dc732cb8104810c21ec4b2ebea9e90ad2a30fa973c46f5d31fd
evals/codex_routing_grade.py	b2f4d10fdd276216c304c6808b34df8bca70e207e56aa58150116c1ae8f7279f
evals/codex_snapshot.py	1c8f35fc40d31cbd3849c39497b6b33fe8f9206fbc59652816a95291448ac7b7
evals/codex_trial.py	84c94a0df59b900046ce32ad131576f1d201bab048e5cad924d89bc2f82f22c0
evals/conformance/codex-terra-evaluator-v1.json	e3ee4ea726ad2ca936bb55b00c31fa4e271ba8e9b976bfec1ac3d6a4f6a63782
evals/conformance/codex-terra-routing-v1.json	1d651a34eb570045fe7e3e6bb1054c90ce82beb69204f1650a673db1085614ba
evals/README.md	9d13d0d2d869e0b41b476eb80de1ad059fd4ba27200382f59d3d6c80df02e8e8
evals/run_codex_routing.py	3f85a8d2563e6b6b36167fe932f4b57837dd470337c2a26020287a85e26817b9
evals/test_codex_bootstrap.py	7f7c9216e44dfa0df0d3dee49d8eb4b439ce0d37241335da85dbb292fa5863e6
evals/test_codex_harness.py	68b5aa1bd9d1e035d724739e534676ad66e2d7efbd4db1b4bc7173923d866ca5
evals/test_codex_hook_recorder.py	e04d9ae2d0c71c6afb81b1aecfde52151f23892c536e8a9bd1035c98f012a8e9
evals/test_codex_model_catalog.py	30e4c26c3228a25e4621e2fe2c13d4546564cc370ebbc46bfac47de87c7a6a73
evals/test_codex_routing_grade.py	903c7f3023689062471cac440f6297bf25ffdc4ed7255781372be5ef3804c4e1
evals/test_codex_snapshot.py	7c534993686bdf0f364bff8b3b5e126f1af07baa2932ec7dc563e76c8c59243f
evals/test_codex_trial.py	44a8be82cbed27735bd3cf3a0f1aa133a122dd4ea5801044d864488009fd971e
evals/test_run_codex_routing.py	21be88bb2ed8dd18726324c5e7af0301f2f33151b7c6de20e04d084e9894062d
README.md	98a75d0966f4a281d01e5082221eb40fae63a9af8d0b970c10d2622a8d2dc939
```

The bootstrap separately binds its exact nine-file executable closure in
[`codex-terra-evaluator-v1.json`](../../evals/conformance/codex-terra-evaluator-v1.json). The review
packet is not part of that executable closure.

## Live canary prerequisites still open

The authenticated canary remains NO-GO until an independently reviewed launch packet establishes:

1. an externally verified protected copy of the exact bootstrap bytes, invoked with `-I -S -B` by
   an absolute protected Python executable whose DLL and standard-library closure are also bound;
2. a precreated empty private root on a local fixed NTFS volume, with an active same-SID compromise
   explicitly excluded or isolated through a separate OS identity;
3. a clean effective Codex configuration and registry boundary with no managed/system/project MCP,
   dynamic tools, guardian path, provider/API-route/proxy override, or Command Processor AutoRun;
4. a protected Git executable/DLL/runtime installation closure and sanitized object store with no
   repository-config includes, object alternates, replacement refs, or UNC/network resolution; the
   exact executable/archive digests prevent bad bytes from being accepted but cannot protect
   load-time dependencies or prevent pre-validation reads;
5. exact independently reviewed committed evaluator bytes and the external evaluator-manifest hash;
6. explicit owner approval for the one fixed prompt/model call and its data/cost boundary.

Only after that one-trial canary completes without an instrument or boundary failure may the 48
sequential trials run. The canary itself can never be promoted into campaign, baseline, or release
evidence.

## What was not done

- No live Terra canary or campaign was started.
- No OpenAI prompt, staged plugin content, or evaluation response was transmitted.
- No Codex auth file was copied into the final evaluator boundary.
- No current Terra before/after baseline or routing verdict exists.
- No description was tuned from historical Claude or Sol output.
- No commit, push, pull request, tag, Release, workflow dispatch, or production effect was made.
- No claim of version 1.0 was introduced; the prepared release remains beta `0.1.0`.
