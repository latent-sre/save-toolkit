# WP-09 Terminal-Bench complex-five proposal

[verified] The [frozen manifest](../../evals/manifests/wp09-terminal-complex5.json) identifies five
source-coherent tasks before observing any candidate results. These are proposed cases, not accepted
benchmark results. All five parse with the actual Harbor 0.24.0 `Task` implementation. No task code,
Docker environment, reference solution or candidate model was executed during preparation.

[sourced] Source is [terminal-bench-2 at the explicit commit](https://github.com/harbor-framework/terminal-bench-2/tree/2fd12b88aafdd04a52c298e3940bcb189f9766d6)
`2fd12b88aafdd04a52c298e3940bcb189f9766d6`, under its
[Apache-2.0 license](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/LICENSE).
Each packet hashes every source file, including hidden tests and solutions; the manifest also hashes
the license. Equality with the registry label `terminal-bench@2.0` remains unverified. Use the source
commit, never that label as a substitute identity.

| Original task ID | Original difficulty | Why it is complex | Static-authoring adaptation |
|---|---|---|---|
| `terminal-bench/cancel-async-tasks` | Hard | Concurrency bounds, queued jobs, SIGINT, cancellation propagation and cleanup interact. | Author Python `/app/run.py`; the independent verifier imports and executes it. |
| `terminal-bench/llm-inference-batching-scheduler` | Hard | Cover every request exactly once while meeting a shared shape budget and several padding, cost and latency thresholds. The model is analytical; no actual model inference or GPU is needed. | Author Python generation code and `/app/submission.sh`; the independent actor creates the two output plans. |
| `terminal-bench/write-compressor` | Hard | Infer a custom format from a C decoder and create a compatible compressed stream within 2,500 bytes. | Author a Python encoder and submission script. Compilation and execution belong to the independent actor. |
| `terminal-bench/db-wal-recovery` | Medium | Recover the encrypted WAL, reconcile base and logged records, and produce complete sorted JSON. | Author a Python recovery program and submission script. This file-format exercise does not adopt SQLite as a team datastore. |
| `terminal-bench/kv-store-grpc` | Medium | Make schema, generated bindings, RPC semantics and background server lifecycle agree. | Author Python, protobuf and launch glue; the independent actor generates bindings and starts the server. |

[verified] The local IDs are `wp09-terminal-static-v1-<source-name>`. Static authoring changes the
execution profile, so these are labelled adaptations even though the upstream task files, assertions
and `tests/test.sh` remain byte-for-byte unchanged. The medium tasks remain medium. Selection uses
multi-step reasoning and source coherence, not a rewritten upstream difficulty label.

[verified] Compressor source has a significant separation trap: `environment/main.rs` contains the
reference encoder, duplicated in `solution/solve.sh`, but the source Dockerfile copies only
`decomp.c` and `data.txt`. Candidate source staging uses explicit Docker-copy input lists and excludes
that encoder, Dockerfiles, all solutions and all tests. The runtime author receives the prepared
image's `/app`, not the full source checkout. Smoke checks the expected input hashes and absence of
hidden material before admission. Source layout fidelity is not proof that an arbitrary image is safe.

[verified] Independent controls are implemented in the model-free `smoke` command: run the original
hidden `solution/solve.sh` in a fresh bounded verifier, run unchanged tests; then run the same tests
in another clean verifier with no submission. A missing reward control must remain inconclusive.
These controls are executable preparation, with live outcomes still unmeasured for every case.
Reference success is not asserted merely because a source solution exists. A failed reference or
empty control blocks the case; do not repair upstream answers to make the pilot pass.

[verified] Offline controls cover valid 1/0, unavailable/empty/nonfinite/duplicate/bool/nonbinary
rewards, real SDK parsing and verifier invocation, incomplete native authors, hidden input rejection,
unsafe archive paths, bounded subprocess collection, and preservation of supported results after
billing or cleanup failures. Those checks establish adapter behavior, not task success.

[unverified] All original task image references are mutable tags. Derived, dependency-preseeded
author/verifier images need real registry digest and local image-ID receipts before use. No image
digests are invented. Exact host smoke, native CLI/plugin operation, live reference outcomes, static
policy compliance, model availability, spending approval and human case acceptance remain gates in
the [run plan](wp09-terminal-runplan.md).
