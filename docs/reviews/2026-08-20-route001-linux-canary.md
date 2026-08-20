# ROUTE-001 Linux container development canary

- **Date:** 2026-08-20
- **Branch:** `feat/route001-linux-container`
- **Base commit:** `e31d04e06d3d50e7351f0251768b11c8016c3f10`
- **Candidate state:** repaired through `cfb185173c0434a2792c5bf30270bef1e24606b1`; not independently reviewed
- **Authority:** development instrument evidence only; not campaign, baseline, release, or promotion

## Outcome

The Linux Docker arm is viable, but all three owner-approved authenticated development canaries are
**INCONCLUSIVE**. The first, under Codex 0.147.0, exited before producing a response or valid trace.
The two Codex 0.148.0 subprocesses returned `0`, but the evaluator rejected their JSONL trace or hook
receipts. Exact 0.148 source review found two evaluator mismatches: hook `permission_mode` reflects
approval policy, and `transcript_path` is nullable. Both are now repaired and covered by red-first
tests, but the nullable-path repair has not had a live retry. No attempt is a routing result, and no
48-trial campaign followed.

| Check | Evidence |
|---|---|
| Candidate image | `[verified]` `sha256:c339d945cc6d77661a836b3f81eddf0102f950fb9a43beae4529c57cb2f9047c` |
| Corrected 0.147 image | `[verified]` `sha256:0c6ae299da5088f9a93d0a968c2a95a61e6640d6b585e4740919f435afcd7287` |
| Repinned 0.148 canary image | `[verified]` `sha256:6f3f918ff7e2fddded78dfae3bc4c304440cab57182ea3f087ef1c8f7140cdaf` |
| Third 0.148 canary image | `[verified]` `sha256:861d701ba93bcf1ee098610c55a4c683688b5d1d1fdd18dc9963f653d22c764c` |
| Runtime shape | `[verified]` Linux `amd64`; non-root `65532:65532`; launcher image inspection passed |
| Focused current-repair contracts | `[verified]` 115 passed; 8 expected platform skips |
| Credential-free preflight | `[verified]` exit `0`; `credential-free-preflight-pass`; no auth or model process started |
| 0.147 development canary | `[verified]` outer exit `4`; verdict `INCONCLUSIVE`; `trace-or-hook-invalid` |
| 0.148 development canary | `[verified]` verdict `INCONCLUSIVE`; `trace-or-hook-invalid`; no retry |
| 0.148 Codex subprocess | `[verified]` exit `0` after 15,865 ms; stdout 1,684 bytes; stderr 144 bytes |
| Third Codex subprocess | `[verified]` exit `0` after 15,213 ms; stdout 1,760 bytes; stderr 144 bytes |
| Usage and cost | `[unverified]` no token, usage, billing, request, or resolved-model receipt was produced |
| Persistent run artifacts | `[verified]` `F:\route001-runs\canary-20260820` contained zero files after the run |

## Original 0.147 preflight evidence

The original immutable-image launch exercised the real evaluator setup with `--network none`, no auth mount,
read-only source, a read-only root filesystem, dropped capabilities, `no-new-privileges`, and a
private tmpfs. It verified:

- Python 3.12.10 at SHA-256
  `4dbf3143240288fb2170257ffaa7bd030cdda5d2703d1f5f30b627042267e2e3`;
- Git 2.39.5 at SHA-256
  `2540879925a6881e3877ff7e3330746ba3027b04edf16a3a12dccd1644c4f32d`;
- Codex 0.147.0 at SHA-256
  `cb0a15567e9a60a5820d54b0f6ae86d504dc3805c1eab21a47f70e3eb7b73a40`;
- exact current snapshot `b459a5d3a209d384acb2b2b7ca325aa63697113b`, tree digest
  `867f92cccb6eff6e994f27eff7301722ebb82da24b6f2adcd26be92fe2babf4a`;
- evaluator tree digest
  `a4034a47395dc1ae6ac7b60e5c13da85e2d719a812ee3585628797c27d1e811a`;
- the pinned Terra catalog, hook bundle, sanitized environment, and no-model-tools argv.

Two preflight defects were corrected before that pass: Python `-I` omitted the evaluator directory
from `sys.path`, and the image omitted the historical Windows manifest that the accepted-manifest
check resolves. A dry run then exposed that the manifest's deployment label did not equal Python's
measurable `linux-x86_64` runtime fact; that value was corrected before the final image was built.

## Canary evidence and interpretation

The canary used the fixed synthetic `discovery-gcp-ops-cloud-run-startup` scenario with
`gpt-5.6-terra`, medium reasoning, approval policy `never`, a read-only staged project, disabled
model tools, and the operator-approved existing Codex account copy inside disposable tmpfs.

The authenticated Codex subprocess returned `1` in 50 ms. Because it emitted no JSONL stdout, the
evaluator could not establish a model response, activation trace, hook receipt, routing verdict,
token usage, or cost. The raw stderr was deliberately removed with the private trial boundary; only
its byte count and digest remain. This is instrument/startup evidence, not evidence that Terra ran or
that the target skill routed correctly.

## Codex 0.148 canary evidence

`[verified]` The second canary ran from clean commit
`262dfc93daf8663b50f6175b7beb7fdfae9b15cc` using exact image
`sha256:6f3f918ff7e2fddded78dfae3bc4c304440cab57182ea3f087ef1c8f7140cdaf`,
the fixed `discovery-gcp-ops-cloud-run-startup` scenario, `gpt-5.6-terra`, medium reasoning,
approval policy `never`, read-only sandboxing, and the operator-approved existing Codex account.
The Codex subprocess returned `0` after 15,865 ms without timing out or reaching an output limit.

The evaluator then failed closed with `trace-or-hook-invalid`. That reason deliberately aggregates
failure in either JSONL trace parsing or hook-receipt loading; the sanitized result retained neither
object and the disposable raw boundary was removed. The available evidence therefore cannot identify
which parser rejected the run, establish a successful model response, grade the scenario, or recover
token/cost data. No inference that Codex 0.148 changed hook behavior is made from this single result.

## Third Codex 0.148 canary and nullable-path repair

`[verified]` A third bounded canary ran from clean commit
`0e9e7daa4cf8dab6692b80b4e3f17fa60b809068` using exact image
`sha256:861d701ba93bcf1ee098610c55a4c683688b5d1d1fdd18dc9963f653d22c764c`.
Its credential-free preflight passed first with evaluator tree SHA-256
`c1ead9f601d02ca3438cc7adb9a279f8f08c3236b65552d42a2ba5f5f5d887e7`.
The authenticated Codex process then returned `0` after 15,213 ms without timeout or output limiting,
but the evaluator again returned `INCONCLUSIVE` with `trace-or-hook-invalid`; no trace, hook packet,
verdict, usage, or billing receipt was persisted. The output root remained empty and no automatic
retry followed.

`[sourced]` Exact Codex 0.148 source defines `SessionStartRequest.transcript_path` as
`Option<PathBuf>` and serializes it through a transparent nullable-string wrapper:
[`session_start.rs`](https://github.com/openai/codex/blob/3ba0f711642a888aec92a611a3f3b2211157ff89/codex-rs/hooks/src/events/session_start.rs#L42-L50),
[`schema.rs`](https://github.com/openai/codex/blob/3ba0f711642a888aec92a611a3f3b2211157ff89/codex-rs/hooks/src/schema.rs#L40-L51), and
[`schema.rs`](https://github.com/openai/codex/blob/3ba0f711642a888aec92a611a3f3b2211157ff89/codex-rs/hooks/src/schema.rs#L483-L529).
The evaluator instead required a non-empty string for every hook receipt. A red-first regression
reproduced that rejection, and commit `cfb185173c0434a2792c5bf30270bef1e24606b1` now accepts only JSON
`null` or a non-empty string while still rejecting a missing, empty, or non-string field. The focused
bootstrap/harness/recorder/trial suite passed 115 tests with 8 expected platform skips. This repair is
not yet a live routing result.

## Offline root cause and repair

`[verified]` A network-disabled reproduction with the same credential boundary returned the same
shape as the canary — exit `1` after 50 ms, zero stdout bytes, and 213 stderr bytes — and safely
identified the startup error: Codex 0.147 rejected root configuration field
`update_plan_enabled` under `--strict-config`. The differing stderr digest was caused by the
randomized private path embedded in the message.

`[sourced]` Context7's current official Codex schema places these controls under
`[tools.update_plan]` and `[tools.experimental_request_user_input]`. GitHits confirmed the same
contract in exact tag `rust-v0.147.0`, commit
`be6e8eac029b183056b7e4402879f15d2c85f61b`: the nested structs and `enabled` fields are in
[`config_toml.rs`](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/config/src/config_toml.rs#L630-L654),
with the disabled request-input form exercised in
[`config_tests.rs`](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/core/src/config/config_tests.rs#L411-L450).

The renderer now uses the supported nested tables. Corrected image
`sha256:0c6ae299da5088f9a93d0a968c2a95a61e6640d6b585e4740919f435afcd7287`
passed the immutable-image credential-free preflight. A separate three-second startup check used
the exact `exec --strict-config` argv with `--network none` and no auth mount: it produced no stderr
or config error and remained active until the diagnostic terminated it. This proves the local
configuration defect is repaired; it is not a model, routing, or authenticated-canary result.

## Codex 0.148 repin

`[sourced]` The [OpenAI Codex changelog](https://developers.openai.com/codex/changelog) records
Codex CLI 0.148.0 on 2026-08-18. GitHits resolved exact tag
`rust-v0.148.0` to commit
[`3ba0f711642a888aec92a611a3f3b2211157ff89`](https://github.com/openai/codex/tree/3ba0f711642a888aec92a611a3f3b2211157ff89).
The tagged schema retains the nested tool controls in
[`config_toml.rs`](https://github.com/openai/codex/blob/3ba0f711642a888aec92a611a3f3b2211157ff89/codex-rs/config/src/config_toml.rs#L602-L632).

`[verified]` The no-cache build installed exact npm version 0.148.0 and accepted Linux executable
SHA-256 `ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074`.
The bundled Terra entry was rebound to source digest
`3a934e842c9b6a813dfe04ec826da0b79dcfc9b3187696d4b2c1b7110cdb811c`;
the no-local-tools transform produced entry digest
`1c03b5e12771bc6e961c0fac20830a0a2c5fcca011793ec985d24aa4d41140e9`
and catalog digest
`b5122f71336f146cb6c656167e7f3258a9e4735583b95435f808261562bb646f`.
A structural 0.147-to-0.148 comparison found no changed instruction text: 0.148 adds a null
`model_messages.multi_agent` slot, explicit false `node_repl_*` metadata, and replaces the prior
parallel-tool boolean with null. The existing transform still removes the same four model-tool
fields, and the rendered configuration still disables code mode, shell, MCP orchestration, and the
other declared model features.

`[verified]` Image
`sha256:054e5dc1deb0ed111443ffacb1616bb86261f4eefc8f8376f079e8884c906905`
inspected as Linux `amd64`, user `65532:65532`, with the fixed isolated Python entrypoint. Its
credential-free, `--network none` preflight exited `0` with
`credential-free-preflight-pass`, `authenticated_call_started=false`, and these bindings:

- evaluator tree SHA-256
  `4777f90edc78305c6420d649ca6963a3b886d7e2487e28ea6fe87de332ebd999`;
- Linux manifest SHA-256
  `de6d9d45f39dddd98dc9d1189c802be9a6f00595f64fb843c317e04d6be7871d`;
- rendered config SHA-256
  `62d87ca88c1a51bdb0d3e3ed5611331a6308e92d3f2ce9ee73d2c09f0f21d56d`;
- exact current snapshot tree SHA-256
  `867f92cccb6eff6e994f27eff7301722ebb82da24b6f2adcd26be92fe2babf4a`.

The shared nine-file Windows bootstrap manifest was refreshed with the repaired shared evaluator
modules. Its current file is 1,173 bytes with SHA-256
`fae728dfcc8da1a9b522ff61b63c4e655b9f134e36c030613a14e19b18f22fe5`.
This preserves exact-byte rejection but invalidates the older review digest; it requires a fresh
exact-byte review before any historical Windows launch could be considered.

A separate exact-command startup diagnostic used the same image with `--network none`, no auth
mount, and the rendered 0.148 strict config. Codex returned `1` without starting an authenticated
turn; stdout was empty, stderr was 30 bytes with SHA-256
`9d207bb1613f71b10fdfdc9e0bcc9c191d8f6d7084780e5d21c86e2e7af396d4`, and the bounded diagnostic
reported `config_error=false`. This is startup/configuration evidence, not a model result.

`[verified]` An earlier no-cache rebuild from the then-final normalized input closure produced
image
`sha256:6f3f918ff7e2fddded78dfae3bc4c304440cab57182ea3f087ef1c8f7140cdaf`.
The tag now resolves to that image; the earlier image is no longer present in the current Docker
daemon. The rebuilt image again inspected as Linux `amd64`, user `65532:65532`, and passed the
credential-free networkless preflight. The final newline normalization changed the evaluator tree
SHA-256 to `2d3ad45bfdc667a9d25352d02e273732e6feb25d2d16a286f250dfe82c6ed28e`;
the Codex executable, manifest, catalog, and snapshot digests remained unchanged. Its per-run
rendered-config SHA-256 was
`00f5bc9ff7e22f1e0d9bcf1caad0a584ff6fb4c195e11a60544f453dce692480`.
The Dockerfile pins the base-image digests and Codex executable but does not pin Debian package
repository contents or BuildKit provenance bytes, so the whole-image ID remains build-specific.
This observation is recorded rather than expanded into a separate dependency-pinning change.

## Exact third-canary 0.148 image input closure

Image `sha256:861d701ba93bcf1ee098610c55a4c683688b5d1d1fdd18dc9963f653d22c764c`
copies the following exact files from clean commit
`0e9e7daa4cf8dab6692b80b4e3f17fa60b809068`. This table does not include the later nullable-path
repair and makes no independent-review claim.

| Path | Bytes | SHA-256 |
|---|---:|---|
| `evals/codex_campaign.py` | 16879 | `9bfc06bf4a9f77a46382456f7f683b6e9b9e8d2db4b234815979142870921920` |
| `evals/codex_harness.py` | 33660 | `3ae3dd05990e0f54e0048d8fdd66113ca6389906da48e0abf7f82616e208eb2a` |
| `evals/codex_hook_recorder.py` | 9942 | `c2fd5b9b3583b6dd12874850a1528eafa20b42a7d60f0c5435a1606f1105ddc8` |
| `evals/codex_model_catalog.py` | 7198 | `6d7ea260d70bf3cf54add7ea9c2771995e6710eb638036a3074538ff1c32b11a` |
| `evals/codex_routing_grade.py` | 13878 | `3bfc79b547a050c7817096f531572f3d0de07e412b7a1630ccac70e522102a52` |
| `evals/codex_runtime.py` | 4683 | `6a02af5f02f53b4516a72ceb7696cb282fd7d0791974c69b38fb20a3ea31a63a` |
| `evals/codex_snapshot.py` | 33911 | `b23102b211c78acbf142091aa4ffec728875cb30e5b1f2bb8ab8f235502b5d43` |
| `evals/codex_trial.py` | 97803 | `18ead6da11978b3f57d117c9f750b05a92a22f3894829e02725bf4e0fd64f5dc` |
| `evals/graders.py` | 27013 | `cde406078548619d95f11f4c70af6010bca411043d4ee3e7a02647aab39e1ae1` |
| `evals/run_codex_routing.py` | 35409 | `6db8b0d046879fae45e90cb8bb6a62d94ca979857806f3fef1571f02894ec58a` |
| `evals/conformance/codex-terra-routing-linux-v1.json` | 7752 | `de6d9d45f39dddd98dc9d1189c802be9a6f00595f64fb843c317e04d6be7871d` |
| `evals/conformance/codex-terra-routing-v1.json` | 7495 | `d5c7c06902fe131448f6c7fb5d0e03180ccaff8eab4e4201f41315115e127887` |
| `evals/conformance/codex-terra-scenarios-v1.json` | 36415 | `640ed0da086f976b390e1f1e2c664a4181aef302c7f2dd9d7031cfe881c549cb` |
| `evals/container/route001-linux/Dockerfile` | 2656 | `26f80998798a36ecdac7d743562623ba6e912ff64190a60d6c41fc4fc00e382e` |

## Disposition

ROUTE-001 remains active and the 48-trial campaign remains **NO-GO**. The startup, hook-permission,
and nullable-transcript defects are repaired through
`cfb185173c0434a2792c5bf30270bef1e24606b1`, but the latest repair has not been rebuilt or exercised
by a live canary. Any retry requires a new exact image, credential-free preflight, and fresh owner
authorization; it remains development evidence until the campaign prerequisites are met.

The focused nullable-path repair suite passed 115 tests with 8 expected platform skips. Gate A
passed all 41 structural steps from a clean ordinary clone at the preceding committed candidate;
the snapshot contract was not weakened to accommodate the linked development worktree.

## What did not happen

- No retry followed the third development canary.
- No 48-trial campaign, baseline, promotion, release, push, or pull request occurred.
- No successful model response or routing verdict was recorded.
- No verified token or monetary-cost claim is available from any attempt.
