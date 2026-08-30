# GRAPH-002 PR #193 remediation verification — 2026-08-29

## Verdict

`[verified]` Exact runtime candidate `56ebece6d34d30eaa2b6bf5725a1d4a70ecb25f9`
addresses all five unresolved PR #193 review findings with focused regressions. It passed the
host-side sandbox suite, structural gate, immutable runner and service image suites, a Linux-hosted
POSIX regression, and one real healthy Compose mission with verified evidence and complete
run-scoped teardown.

`[unverified]` GitHub CI and reviewer acceptance of this revision remain pending until the branch is
pushed. Human promotion remains separate. The earlier eight-run fault matrix and deliberately
killed live runner were not repeated at this revision; their results remain historical evidence for
`02932845fe19150166ece6d01a0959a0effbdbc0`, not current-candidate proof.

## Findings and fixes

1. **Durable wall time across process resumes.** The runner now creates an identity-bound SQLite
   deadline before event or checkpoint work, derives every process timeout from its remaining
   duration, charges only newly elapsed time, and refuses checkout dispatch when a resumed run has
   exhausted the durable budget. Contract and checkpoint-resume tests prove the original start and
   deadline survive a process boundary and that no checkout effect is dispatched after expiry.
2. **Cross-platform build test.** The fake Docker context now returns a local named pipe on Windows
   and a local Unix socket on POSIX. The focused test passed inside the pinned Linux Python image.
3. **Docker context identity through the lifecycle.** Validated Compose bytes and the captured local
   context are revalidated immediately before `up`, `ps`, `inspect`, `cp`, `stop`, and `down`,
   including PUBLISHED cleanup. A simulated context change after `up` issued no later Docker effect
   and returned fail-safe exit 125.
4. **Crash-consistent publication recovery.** Resume recognizes an installed final directory left
   by a crash between atomic publication and the claim transition, then revalidates checksums,
   runner semantics, Compose digest, context fingerprint, command journal, and host identity before
   moving the claim to `PUBLISHED` and performing cleanup only.
5. **RUNNING-claim resume.** Launch continuation now treats an already-`RUNNING` claim as the
   interrupted host state it is; only `PRELAUNCH` or `PRESERVED` transitions to `RUNNING`.

## Exact environment and images

- Docker context: `desktop-linux`; fingerprint
  `6a2bb20636775a19475ec1db0b13aed991808879ea43a62b6545b1fe5ff013c9`
- Docker Engine `29.7.2`; Compose `v5.4.0`; Linux/amd64
- Base image:
  `python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`
- Build-context digest:
  `sha256:db713cacbbf1a4a45110f776d8fa30f5bf5520c08c2fffc4b426faeeabeae9bf`
- Runner Dockerfile digest:
  `sha256:6818810a855f5f228795afd94d8c800c97177d41a2df8aebe7716e6fe227b79e`
- Runner image:
  `sha256:b9c84d5e706fae94fd9e5edddf594d03fc4a1ad9ea191a004ab00d0c6944e0b7`
- Services image:
  `sha256:5dc3ac5c6d4f84847eee5f26d896935bce18b4cedcf69eae4c0f74e83615eecd`
- Operator-local evidence root:
  `F:\repos\sre-agents\.worktrees\graph-002-pr193-evidence-56ebece6`

The exact image references above are verification output, not repository artifacts. The committed
Dockerfiles, pinned requirements, build Compose model, immutable snapshot builder, and base digest
remain the recreation recipe.

## Verification

| Check | Result |
|---|---|
| `python -m unittest graph-sandbox.tests.test_activation graph-sandbox.tests.test_preflight` | `[verified]` 81 tests passed on Windows |
| Pinned Linux Python image, focused POSIX builder-context regression | `[verified]` 1 test passed with `--network none` and a read-only minimum bind mount |
| `python scripts/gate_a.py` | `[verified]` 8/8 structural steps passed |
| Runner image contract suite | `[verified]` 21 tests passed |
| Runner image recovery suite | `[verified]` 22 tests passed |
| Runner image integration suite | `[verified]` 9 tests passed, including the resumed wall-budget guard |
| Services image contract suite | `[verified]` 10 tests passed |
| Services image integration discovery under `--network none` | `[verified]` 2 topology-dependent tests skipped as designed |
| Real Compose run `pr193-healthy-56ebece6` | `[verified]` exit 0, `SUCCEEDED`, checkout `COMPLETE`, 11 manifest artifacts, zero checksum mismatches |
| Post-run resource query | `[verified]` zero labeled containers, networks, or volumes remained |

The immutable-image test containers used `--rm`, `--network none`, read-only roots, numeric non-root
users, all capabilities dropped, `no-new-privileges`, bounded PIDs/memory/CPU, and a bounded `/tmp`
tmpfs. One initial discovery command aimed at `/app/tests` found zero tests because the three suite
directories are intentionally not packages; it was discarded and is not counted above. The
directory-scoped commands then discovered and ran all 52 runner tests.

## Remaining limits

- `[unverified]` A real process was not held for the full 120-second wall budget and killed; the
  deterministic contract and checkpoint-resume tests exercise the persistence and no-dispatch
  controls without spending that wall time.
- `[unverified]` The prior full fault matrix and live kill/resume proof were not rerun on
  `56ebece6`; no claim from the historical report is upgraded to this revision.
- `[unverified]` Production connectivity, credentials, provider behavior, telemetry delivery,
  persistence across hosts, and live Terra behavior remain outside the accepted offline boundary.
- `[unverified]` Exact-candidate acceptance, merge, and production authority remain human decisions.
