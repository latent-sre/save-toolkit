# GRAPH-005: current bridge acceptance evidence

[verified] The offline bridge at source revision
`41383e3dff84465d5e41923707a82eb0c6ef512c` passed a fresh image build, host activation
regressions, the in-image component/integration suite, all six lifecycle cases, and resource
cleanup on 2026-09-30. The earlier bridge review repairs are present and covered by current tests.
No runtime source repair was needed. The human owner accepted this exact offline candidate on
2026-09-30 after receiving the source identity and verification packet. This is not a new independent
security audit or production readiness approval.

The named SRE task is to assess synthetic canary evidence across SLO, deployment, and dependency
observations, reconcile at most once, and present one exact recommendation for a final human
decision. Neither acceptance of that synthetic recommendation nor this report authorizes a release.
The user reopened GRAPH-005 as part of the four-item backlog request.

## Exact candidate and execution boundary

- Source: `41383e3dff84465d5e41923707a82eb0c6ef512c`; sandbox path clean before and after execution.
- Host Python: `F:/repos/sre-agents/.venv/Scripts/python.exe`, 3.14.7.
- Docker context: `desktop-linux`; Engine 29.7.2; Compose 5.4.0; Linux/amd64.
- Daemon: `78e193b6-71a1-4a60-9ec0-16e94dd22f62`.
- Base: `python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f`.
- Built image: `sha256:eee25f145f9b51530d01ff731e7f7252317f47120549539900c98db40f4d042f`.
- Direct framework pins: Agent Framework core 1.16.0, Agent Framework A2A 1.0.0b260821,
  AutoGen AgentChat 0.7.5, A2A SDK 1.1.2.
- All lifecycle runs used `sandbox/autogen-a2a-sandbox/activate.py`. Framework/application
  execution occurred only inside the image. No host framework installation or execution occurred.
- Image build accessed public package registries. Runtime used only the internal two-container
  network; component tests used `--network none`. No ports, credentials, host mounts, Docker socket,
  cloud, model calls, or actual release effects were supplied.

Raw local bundles and logs are retained at
`C:/Users/hawkins/AppData/Local/Temp/graph005-20260930-41383e3d/`.
The coordinator also copied the public evidence tree to
`F:/repos/sre-agents/.eval-runs/graph005-20260930-41383e3d/`: all 81 files matched by SHA-256.
This archive is for inspection; replay remains bound to the original canonical evidence root.
The private activation receipts remain in activation's platform state directory; their nonces are
not copied into this report. Public hashes alone do not authenticate a bundle. The sandbox's
activation checks verified receipt/HMAC identity during publication and final replay.

## Historical finding reconciliation

[verified] PR #204 is merged; its seven review threads were read through GitHub GraphQL on
2026-09-30 and all have `isResolved: true`. Resolution flags alone are not the implementation proof.
The bridge repairs below were also inspected in current source and exercised by the current tests.

| Finding | Current mechanism and evidence |
|---|---|
| [Ambient-variable-sensitive host test](https://github.com/latent-sre/save-toolkit/pull/204#discussion_r3899846950) | The direct-runtime refusal test clears its ambient environment locally. Separate rejection tests preserve the actual credential/proxy refusal behavior. |
| [Run ID overflows artifact ID](https://github.com/latent-sre/save-toolkit/pull/204#discussion_r3899846955) | Activation limits run IDs to 105 characters; the boundary regression accepts 105 and rejects 106, preserving the artifact's 128-character limit including its prefix. |
| [Missing protocol lineage](https://github.com/latent-sre/save-toolkit/pull/204#discussion_r3899846961) | Host and producer validators require exact task/context identity on artifact and state observations. Host and integration mutations reject absent lineage. |
| [Workflow observations falsely claiming protocol fields](https://github.com/latent-sre/save-toolkit/pull/204#discussion_r3900192825) | Host and producer require all protocol fields on `workflow_working` to be null; the host regression mutates all four fields. |
| [Incorrect byte-identity claim](https://github.com/latent-sre/save-toolkit/pull/204#discussion_r3900192835) | This evidence names the newly built current revision and image; the old August image is not used as current proof. |

The other two PR threads concerned retired incident grading and plan-directory validation, outside
this bridge. Their resolved status does not constitute fresh verification of those unrelated areas.
Relevant bridge fixes came from `6f9544d3553daf6bbe8edaefda4de046018e3912` and
`9ca0d0244566c46a6d6de52a583d627145493541`; no duplicate repair was introduced.

## Fresh checks

| Check | Observed result |
|---|---|
| Host `python -m unittest discover -s sandbox/autogen-a2a-sandbox/tests -p test_activation.py` | 47 tests run; 46 passed, 1 skipped; exit 0. |
| `activate.py build --docker-context desktop-linux --source-revision 41383e3dff84465d5e41923707a82eb0c6ef512c` | Exit 0; revision-labelled image resolved to the digest above. |
| Pinned-image full `unittest` discovery | 100 tests run; 99 passed, 1 skipped; exit 0. |
| Healthy exact final replay, same `ACCEPT` | Exit 0; same authenticated final claim; no second analysis. |
| Healthy conflicting final replay, `REJECT` after `ACCEPT` | Exit 70, `runtime_evidence_invalid`, case/requested-decision binding mismatch; prior accepted evidence retained. |
| Independent Docker container/network/volume inventory | No `a2a-*` resources remaining after lifecycle and replay. |

The exact component command used no source mount:

```powershell
docker --context desktop-linux run --rm --name graph005-components-20260930 `
  --network none --read-only --user 65532:65532 --cap-drop ALL `
  --security-opt no-new-privileges:true --cpus 1 --memory 768m --pids-limit 128 `
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=134217728 --init `
  sha256:eee25f145f9b51530d01ff731e7f7252317f47120549539900c98db40f4d042f `
  timeout 180 python -m unittest discover -s tests -p 'test_*.py'
```

The component suite includes real MAF/A2A/GraphFlow integration, exact checkpoint restore,
reject decisions, same-task stream recovery, cancellation, conflicting decision writers,
artifact tampering, expiry, and publication authentication. Cancellation deliberately produces an
internal AutoGen `CancelledError` diagnostic; the expected terminal and test verdict are successful.

## Six-case lifecycle

For each case, `fresh` supplied the same revision, Docker context and external evidence root,
`--approval-fixture PENDING`, and its own run ID. Completed cases then used `resume --decision ACCEPT`
on that same run. This is the deterministic synthetic drill, not acceptance of the toolkit itself.

| Case | Run ID | Observed lifecycle |
|---|---|---|
| `mission-healthy-001` | `graph005-mission-healthy-001-20260930` | Fresh exit 20; resume exit 0; `ADVANCE_CANARY`. |
| `confirmed-regression-001` | `graph005-confirmed-regression-001-20260930` | Fresh exit 20; resume exit 0; `HALT_CANARY`. |
| `stale-evidence-reconciled-001` | `graph005-stale-evidence-reconciled-001-20260930` | Fresh exit 20; resume exit 0; exactly one reconciliation; `ADVANCE_CANARY`. |
| `checkpoint-resume-001` | `graph005-checkpoint-resume-001-20260930` | Fresh exit 20; resume exit 0; fresh-team restored state; each analyzer called once. |
| `unresolved-contradiction-001` | `graph005-unresolved-contradiction-001-20260930` | Exit 2; `input-required`; null artifact; zero approval requests. |
| `slow-analysis-cancel-001` | `graph005-slow-analysis-cancel-001-20260930` | Exit 2; `canceled`; null artifact; zero approval requests. |

An initial healthy run, `graph005-healthy-20260930`, also completed and supplied the exact/conflicting
replay checks. It was repeated under the table's run ID to capture native exit codes explicitly:
the first PowerShell wrapper represented the expected nonzero pending exit as generic failure.
This was evidence-capture correction, not retrying a failed application case.

[verified] Completed bundles bind this revision, image and daemon; one analysis invocation and
one final approval request are recorded. Initial checkpoints and terminal GraphFlow state are
present; completed analyzer counts remain one. The reconciled case has two join calls and one
reconciliation. Terminal-only evidence carries the same image/daemon/source identities, without
an artifact or approval. Final verification records report `release_effect_executed: false` and
`resource_cleanup_verified: true`; independent Docker inventories corroborate cleanup.

[verified] The root coordinator independently read the healthy verification and runtime records,
confirmed unchanged sandbox bytes against the named revision, and repeated the Docker resource
inventories with no remaining run-scoped containers, networks or volumes. This spot-check does not
replace the full lifecycle evidence or constitute a new security audit.

## Disposition and limits

The stale technical rerun prerequisite is satisfied for the exact source above. The human owner
answered **"Accept the verified offline candidate"** to the exact-revision acceptance request on
2026-09-30. The bridge source is already on main; recording the closure in the integrated roadmap
change remains pending. This packet replaces the removed August verification as current evidence
until that disposition is committed. A fresh independent review remains a distinct
claim; this author did not turn its own verification into an independent review. The root coordinator
owns repository-wide checks and any final review of the integrated backlog changes.

No source was changed, no commit or push was made, and no production platform was selected.
Any later sandbox-byte change requires a new committed source identity, build, and affected runtime
verification; this image cannot prove those changed bytes. This synthetic, single-host proof does
not establish external authentication, cloud/model connectivity, production readiness, or
multi-host/storage-failure durability. The acceptance covers only the named offline candidate.
