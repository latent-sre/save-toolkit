# SWT5 static reproduction proposal

[verified] The proposed five-case selection is eligible under pinned SWT-Bench's Verified
exclusion filter, has five repositories and only original Verified `1-4 hours` difficulty labels.
This is a selected reproduction pilot; the difficulty labels describe the upstream repair task,
not measured time for writing its reproduction. Human acceptance of these exact cases remains pending.

| Original instance | Intrinsic difficulty to preserve |
|---|---|
| `astropy__astropy-13579` | Coupled spatial/spectral WCS axes and dropped coordinates during slicing |
| `django__django-15957` | Per-parent sliced prefetch, ordering, window partitions and relation types |
| `sympy__sympy-17630` | Repeated block multiplication, shaped zero objects and simplification |
| `sphinx-doc__sphinx-11510` | Include directives, extension callbacks, nested sources and rendered output |
| `pylint-dev__pylint-8898` | Commas inside regex syntax versus list delimiters through configuration parsing |

The [manifest](../../evals/manifests/wp09-swt-five.json) records exact original row hashes,
base commits, source tags, test-path admission roots, source-file hashes and licence evidence.
The three original suggestions django-14011, sympy-13878 and pylint-4551 were excluded before
model results because upstream's filter excludes them. The source filter is an exclusion list,
not an inclusion list. These five cases are disjoint from the proposed complex WP08 selection.

[sourced] The adapter targets [SWT-Bench at 330a649](https://github.com/logic-star-ai/swt-bench/tree/330a649a764fab2fadaea632776eeae87272f74b)
and original [SWE-bench Verified at 78f471bf](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/tree/78f471bf655a3137b2e8a75af1501690ec009ec3).
SWT code is MIT. Each selected repository's licence text was retrieved at its exact base commit
and hashed. The pinned dataset card and file list do **not** declare a separate dataset licence;
that absence is retained in the manifest. No claim that all embedded patches inherit SWT's MIT
licence is made. Raw data and hidden patches remain private in `.eval-runs/`.

## Source and input contract

[sourced] `src/dataset.py:swe_to_swt_instance` maps original SWE `patch` to the hidden
`golden_code_patch` and `test_patch` to hidden `golden_test_patch`. Submitted tests occupy
prediction `model_patch`. The adapter exports an ordinary JSON **array**, retaining original
field roles, with `is_swt=False`. The local upstream loader bypasses `filter_swt`, so the adapter
checks the pinned exclusion list itself before export. The preformatted
`eth-sri/SWT-bench_Verified_bm25_27k_zsp@70675e4c5e43093a3e5e60cf6128f9757471ab40`
uses incompatible patch roles for this loader and is not used.

[verified] Author inputs contain only instance ID, repository, base commit and the original public
issue. Hidden code/tests, hints, expected test names, verifier scripts and receipts are separate.
The live author mounts only the frozen fleet plugin and native CLI; it receives a pruned buggy
checkout and the public issue. Test authoring is static under DEC-13. The verifier's executions
never count as author-executed reproduction or validation. Source-text/process controls are
conservative syntactic admission; indirect source inspection can still require human review.
Reading rendered output such as HTML remains allowed.

## Offline preparation

Use the repository's verified Python interpreter for offline work. An optional independent SWT
worker environment avoids changing the project environment:

```powershell
uv venv --python 3.14 .swt-venv
uv pip install --python .swt-venv\Scripts\python.exe -r requirements-swt.txt
.swt-venv\Scripts\python.exe evals/swt_pilot.py validate --dataset .eval-runs/complex-campaigns/wp08-source/dataset.json --source .eval-runs/complex-campaigns/wp09-swt-source
.swt-venv\Scripts\python.exe evals/swt_pilot.py prepare --dataset .eval-runs/complex-campaigns/wp08-source/dataset.json --source .eval-runs/complex-campaigns/wp09-swt-source --output .eval-runs/complex-campaigns/wp09-swt-prepared
```

The source checkout must be clean at the manifest's pinned revision. Preparation writes separate
`author-only/` and `verifier-only/` trees, a report selection, native CLI commands and a pending
admission template. It never accepts a candidate or runs a model/Docker. Existing destinations
are refused. Copy the [runtime template](../../evals/manifests/wp09-swt-runtime.template.json)
to a private configuration and fill it from the already chosen WP08 host, CLI, model/proxy settings
and actual immutable image identities. Null values intentionally fail validation.

[unverified] Each source row names an official SWE image using the expected `/testbed` and conda
environment. Resolve its immutable registry digest and local image Id on the accepted Windows
Docker Desktop host, record both in the config, and let the following smoke establish compatibility.
A source tag is provenance, not an immutable run identity. There is no image build or pull in the
adapter. The reference control checks a clean tracked/index baseline and exact base commit.

## Executable model-free smoke and owner gate

[verified] `smoke` is executable preparation for the live gate, not a collection of hand-entered
booleans. Run it for each selected instance, using a fresh output directory:

```powershell
.swt-venv\Scripts\python.exe evals/swt_pilot.py smoke --dataset .eval-runs/complex-campaigns/wp08-source/dataset.json --source .eval-runs/complex-campaigns/wp09-swt-source --config .eval-runs/wp09-swt-config.json --instance-id astropy__astropy-13579 --output .eval-runs/wp09-swt-smoke-astropy
```

It runs the hidden gold tests as the positive reproduction, and always-fail, pass-both and
unrelated-import negative tests through the actual independent verifier. Generated controls are
`unittest.TestCase` methods, so both Django's unittest loader and pytest collect them. Patch-text and
code-fix-as-test submissions fail admission. It reuses WP08's actual guard, Git-pruning,
network, CPU, storage-fill and cleanup probes with a local model substitute. Its two internal
verifier slots are adapted to gold tests and always-fail tests; no SWE repair score is claimed.
The worker is serial, and cleanup must be established before another control. Retain
`observations.json`, `smoke.json`, every verifier receipt and the false-by-default
`pending-admission.json`. No key is read and no provider call is made by smoke.

`pending-admission.json` names the actual `smoke.json` by a relative path and SHA-256. Keep that
file beside the admission artifact without editing it. The runner reopens it before any key read;
missing, changed, linked or escaping evidence is refused. It requires matching case and binding,
zero model calls, no smoke error, all checks and all four verifier controls with complete process
and six-container cleanup. Inline check booleans cannot replace evidence.

The owner reviews the exact manifest, source/plugin/CLI digests, model, host/engine/image binding,
observed smoke checks, budget and complexity before marking that produced admission artifact
accepted with the named owner. Bindings are per case. The combined adapter identity includes the original shared SWE/native
source-and-dependency hash, SWT adapter sources and the exact `requirements-swt.txt` bytes. That
same combined hash appears in accepted binding, published binding and record provenance.
Changing any bound input requires fresh
matching evidence. Unknown checks never become true automatically.

## Paid trial and result handling

After that exact acceptance and the existing campaign key/budget gate, run one task at a time:

```powershell
.swt-venv\Scripts\python.exe evals/swt_pilot.py run --dataset .eval-runs/complex-campaigns/wp08-source/dataset.json --source .eval-runs/complex-campaigns/wp09-swt-source --config .eval-runs/wp09-swt-config.json --instance-id astropy__astropy-13579 --output .eval-runs/wp09-swt-runs --key-file C:\private\wp09-key.txt --admission .eval-runs/wp09-swt-smoke-astropy/pending-admission.json
```

The author uses the real `save-toolkit:software-engineer` native CLI, frozen plugin/tool identity,
64 turns and 45 minutes. The host credential stays behind the proxy; the key's observed cap must
not exceed the accepted USD 30 campaign ceiling. Author and each independent verifier container
have 2 CPUs, 2 GiB memory, 256 PIDs and a mandatory 10 GiB writable-layer quota. Verifier containers
have no network or host mounts. Six variants receive fresh containers; upstream caches are bypassed.
Each variant has 600 seconds and the credential-free verifier process has 3,900 seconds total,
bounded output and owned-process cleanup. Store source/image/config identities and actual trace,
not only the prepared command. Retries and overwriting an existing attempt are refused.

[sourced] Upstream's six variants are submitted-tests/buggy, submitted-tests/repaired,
gold-tests/buggy, gold-tests/repaired, base/buggy and base/repaired. Its original parser and
`get_pred_report` report are preserved. The AC-13 assessment additionally requires an observed
FAILED-to-PASSED test that the baseline did not already reproduce; missing/error-before is not
credited. Failing gold controls are inconclusive environment evidence. Upstream success alone
cannot establish behavioral relevance.

The Windows worker keeps the same host/engine decision. Pinned upstream imports `fcntl` only for
image-build locks and `resource` only for its unused CLI limit path. The isolated worker installs
explicit import guards for those unavailable modules; reaching either operation raises. It does
not claim successful locking or emulate resource limits. The actual limits are WindowsJob,
`run_bounded` and Docker. [verified] Real pinned imports, six-variant generation, scripts, parsers
and grading run with those guards active in offline controls, including denied build/lock/resource
calls. [unverified] Native Windows/Docker Desktop execution remains part of the live smoke.

Attempts use `eval-<instance>/claude/run-1/record.json` v1. Their verifier, cleanup, billing and
policy-review sidecars feed `campaign_report.py`; original upstream outcome, mechanical result,
human relevance, execution, cleanup and provider-measured versus estimated spend remain separate.
A later cleanup/billing problem does not overwrite a supported test result. Unresolved resources
leave `swt-pending-cleanup.json` and block another trial until the owner inspects its exact names.
The report selection is the exact frozen manifest, including its `tasks` list.

A human relevance review must identify the submitted patch SHA-256, reviewer, PASS/FAIL and reason.
Use `assess --receipt <verifier-receipt.json> --patch <submitted.diff> --relevance <review.json>`
to compute that separate assessment. This does not rewrite the original v1 verdict or accept the
candidate. Review issue semantics, sensitivity to the bug, meaningful expected behavior, absence
of answer/source-text oracles, and the author's static-execution policy trace.

## Verification scope

[verified] Focused controls exercise selection/filter roles, inaccessible hidden fields, upstream
exports, patch admission, mechanical/relevance separation, native prompt/admission, v1 reporting,
quota arguments, cleanup ordering, smoke composition and Windows import guards. Four additional
controls run the actual pinned loader, scripts, parsers and grader with Docker boundary doubles.
Those four are skipped in an ordinary project environment without the optional upstream source and
dependencies; their separate successful run is recorded privately. No real repository tests,
Docker containers, models, provider billing or human acceptance were measured offline.

The focused checks are executable without Docker or a provider:

```powershell
python -m pytest -n 0 evals/test_swt_adapter.py evals/test_swt_runner.py evals/test_swt_smoke.py evals/test_swt_verifier.py
uv pip install --python .swt-venv\Scripts\python.exe -c requirements-dev.txt pytest
.swt-venv\Scripts\python.exe -m pytest -q -o addopts="" --confcutdir=evals evals/test_swt_verifier.py -k real_upstream
```

The optional controls use the pinned checkout and staged dataset at the preparation paths above.
They substitute Docker's external boundary, not the upstream transformer, six-variant generator,
evaluation scripts, log parser or grader.
