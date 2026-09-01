# AutoGen GraphFlow + A2A exact-revision verification

> **Conclusion:** `[verified local]` Exact source revision
> `ede57417026d35ff0f6a14745dff0dd35fdeb65d` passed its host boundary, pinned-image component
> suite, full six-case Docker lifecycle, cleanup checks, and Gate A on 2026-08-30 CDT. This record
> is implementation-lane verification, not independent review or owner acceptance.

## Candidate and boundary

- Branch: `work/autogen-a2a-sandbox`; source revision:
  `ede57417026d35ff0f6a14745dff0dd35fdeb65d`.
- Docker context: `desktop-linux`; daemon ID `78e193b6-71a1-4a60-9ec0-16e94dd22f62`;
  Engine `29.7.2`, Compose `v5.4.0`, Linux/amd64.
- Base image:
  `python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`.
- Built image:
  `sha256:64469af67817949dc6c74c5ab62d9a38cbefd834aa43d81c6537fa44a95f2b3e`.
  Its OCI revision label matched the complete source revision above.
- Runtime packages: `agent-framework-core==1.16.0`,
  `agent-framework-a2a==1.0.0b260821`, `autogen-agentchat==0.7.5`, and `a2a-sdk==1.1.2`.
- No model, credential, production endpoint, host port, Docker socket, host bind mount, release
  effect, or external runtime network was used. The image build accessed public package registries;
  the component suite used `--network none`, and lifecycle traffic stayed on the internal Compose
  network.

## Fresh verification

| Check | Result |
|---|---|
| `python -m unittest discover -s autogen-a2a-sandbox/tests -p "test_activation.py"` | 44 passed, one expected skip |
| `python scripts/gate_a.py` | 8/8 structural steps passed |
| `git diff --check` | passed |
| `python autogen-a2a-sandbox/activate.py build --docker-context desktop-linux --source-revision ede57417026d35ff0f6a14745dff0dd35fdeb65d` | exit 0; exact image and daemon identities above |
| Hardened `docker run --rm --network none ... python -m unittest discover -s tests -p 'test_*.py'` | 97 passed, one expected skip |

The host regression now drives both `input-required` and `canceled` through the real `_fresh`
publication branch and verifies that `runtime-terminal.json` carries the exact image and daemon
identities. It does not merely call the identity-binding helper.

## Six-case lifecycle

Each completed case ran `fresh` to the one `AWAITING_APPROVAL` boundary (exit 20), then `resume
--decision ACCEPT` on the same run (exit 0). Each non-actionable case ran `fresh` to
`terminal_without_approval` (exit 2).

| Case | Run | Observed result |
|---|---|---|
| `mission-healthy-001` | `verify-healthy-ede57417` | `DECISION_RECORDED`, `ADVANCE_CANARY` |
| `confirmed-regression-001` | `verify-regression-ede57417` | `DECISION_RECORDED`, `HALT_CANARY` |
| `stale-evidence-reconciled-001` | `verify-reconciled-ede57417` | one reconciliation, then `DECISION_RECORDED`, `ADVANCE_CANARY` |
| `checkpoint-resume-001` | `verify-checkpoint-ede57417` | saved-state continuation, then `DECISION_RECORDED`, `ADVANCE_CANARY` |
| `unresolved-contradiction-001` | `verify-input-required-ede57417` | `input-required`; no artifact or approval |
| `slow-analysis-cancel-001` | `verify-canceled-ede57417` | `canceled`; no artifact or approval |

`[verified]` Every exported record bound the complete source revision. Completed bundles bound the
same image and daemon in `environment.json`; both terminal-only records carried those identities
directly. The cancellation case emitted AutoGen's expected internal `CancelledError` diagnostic
while canceling the deliberately blocked analyzer, then published the validated `canceled` record.
It did not become a runtime failure or recommendation.

`[verified]` After all six runs, independent Docker inventories found zero `a2a-*` containers,
networks, or volumes. Raw validated bundles remain operator-local under the external revision-named
evidence root `autogen-a2a-ede57417/`; this repository retains only the bounded result.

## Remaining gates

- `[unverified]` Independent correctness and security review has not inspected this exact revision.
- `[unverified]` Save Toolkit maintainers have not accepted or rejected these exact bytes.
- Production behavior, authentication, external connectivity, multi-host durability, and framework
  production readiness remain outside this synthetic offline proof.
