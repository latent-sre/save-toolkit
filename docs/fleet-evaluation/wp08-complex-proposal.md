# WP-08 complex-case campaign proposal

**Status: pending human acceptance.** This amends the original easy-task selection; it does not
change that selection's recipe, results or approval. No paid trial or Docker smoke has run for
this proposal. The owner must accept the exact case bytes and run-plan amendment before execution.

[verified] The [manifest](../../evals/manifests/wp08-complex-proposal.json) contains ten cases across
eight repositories at SWE-bench Verified revision `78f471bf655a3137b2e8a75af1501690ec009ec3`.
The 500-row source has only 45 cases rated at least one hour, across eight repositories; ten distinct
repositories therefore cannot satisfy this harder difficulty filter. This proposal replaces both
the ten-repository rule and the traceback-marker balance with intrinsic complexity and subsystem
diversity. No model outcomes informed the selection. SWT's five proposed cases are disjoint.

| Original instance | Upstream difficulty | Reasoning required |
|---|---|---|
| astropy__astropy-13398 | 1–4 hours | Terrestrial coordinate transformations and observer geometry |
| django__django-13344 | 1–4 hours | Sync/async middleware and response boundaries |
| django__django-16631 | 1–4 hours | Session validation across secret-key rotation |
| pydata__xarray-6992 | >4 hours | Coordinate/index/variable invariants through state transitions |
| pylint-dev__pylint-4551 | 1–4 hours | Type annotation inference into UML attributes |
| pytest-dev__pytest-5787 | 1–4 hours | Chained exception serialization and remote presentation |
| pytest-dev__pytest-10356 | 1–4 hours | Marker merging across multiple-inheritance order |
| scikit-learn__scikit-learn-25102 | 1–4 hours | Extension dtypes through transformer output and feature selection |
| sphinx-doc__sphinx-7590 | >4 hours | C++ literal syntax handled by Sphinx's Python parser |
| sympy__sympy-13878 | >4 hours | Distribution-specific CDFs, domains and parameter limits |

[verified] [Source provenance](../../evals/manifests/wp08-complex-source.json) pins the downloaded
parquet digest, byte count and dataset card. [Licence evidence](../../evals/manifests/wp08-complex-licences.json)
pins each repository's licence at the selected base commit, including content digests. These are
source identities, not a claim that every project has the same licence. Full rows, hidden fixes,
hidden tests and downloaded licence files remain in the ignored source cache; the public manifest
contains metadata and hashes only.

Reproduce the proposal without fetching or executing code:

```bash
"$PROJECT_PYTHON" evals/swebench_repair.py propose-complex \
  --dataset .eval-runs/complex-campaigns/wp08-source/dataset.json \
  --licences evals/manifests/wp08-complex-licences.json \
  --out .eval-runs/wp08-complex-proposal.json
```

The full-row cache is the ordinary adapter envelope containing `dataset`, `revision` and `rows`.
The command always emits `admission: pending-human-acceptance`. Offline validation can inspect that
proposal; smoke/trial/batch reject it. After the owner accepts the exact proposal and amended run
conditions, record that decision and change only `admission` to `accepted`, then commit the selection
unchanged before the [operator commands](wp08-operator.md) use it. This is a cooperative human gate,
not proof of authorization inferred from a JSON field. An agent must not make that change on its own.

The existing Sonnet model, static authoring/independent verification, serial Windows Docker Desktop
host, credential proxy, spend limits and separate smoke/first-trial/batch steps still apply. Both
containers require a hard 10 GiB quota. Image IDs/digests, CLI bytes, plugin bytes, host readiness and
model availability must be bound by the operator workflow; mutable source image tags are insufficient.
The 45-minute execution bound is unchanged by this proposal. [unverified] Upstream repair-time
labels do not establish that these cases will complete under that bound or that a model can solve them.

Supported PASS/FAIL assessments are retained if unrelated cleanup or billing fails afterward.
The v1 `after_assessment` field and receipts retain those failures; the batch stops and unresolved
resources block reuse. Missing or invalid verifier identity, unsettled host processes and untrusted
artifacts still prevent a supported assessment. Human policy review and candidate acceptance remain
separate from upstream test outcomes and cleanup.
