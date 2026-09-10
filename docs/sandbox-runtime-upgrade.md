# Sandbox runtime upgrade — 2026-09-10

Follow-up to the Python/Inspect work in PR #260. Both existing sandbox runtime families now use
Python 3.14.7, FastAPI 0.141.1, and Uvicorn 0.52.4. AutoGen/A2A also uses SSE-Starlette 3.4.11.
The Python image is digest-bound; the graph lock template, runtime identity validators, and test
fixtures agree on the new version. LangGraph and the orchestration SDK versions are unchanged.

## Changes and evidence

- [verified] Final fleet suite on Python 3.14.7: 683 passed, seven skipped, 1,058 subtests,
  one upstream Starlette/AnyIO warning, 95.88 seconds. Gate A passed 4/4; all 76 native scenario
  definitions validated; all 129 installed development packages passed `uv pip check`.

- [verified] Runtime changes were frozen in `3256e230cb410e01a1341f9e0f64b9f88c986f7e`.
  Both sandbox families built through their `activate.py build` entrypoints on `desktop-linux`.
  Base: `python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f`.
- [verified] Host graph suite: 103 tests passed. Host AutoGen activation suite: 47 tests ran,
  one skipped. Container A2A/SSE integration: six tests passed; approval recovery: eight passed.
- [verified] AutoGen `mission-healthy-001` reached `AWAITING_APPROVAL`, resumed with the synthetic
  ACCEPT fixture, published PASS, and verified no release effect and successful resource cleanup.
  Evidence run ID: `py314-healthy`.
- [verified] Graph `mission-healthy-001` completed successfully with observed Python 3.14.7,
  the unchanged LangGraph package identities, and exit code zero. Evidence run ID:
  `py314-graph-healthy`. All 22 graph recovery tests passed inside the immutable runner image.
- [verified] Both workflows' run-scoped containers, networks, and volumes were absent afterward.
  Built images remain available for repeatable local testing.
- [verified] The full AutoGen container suite exposed a repository-only test that searched for
  `.git` at import time. Commit `e7f9034908c5fa7a5c88ddbe91346a7680bc1774` moved dependency alignment
  to the existing host CI tests and extended it to both graph requirements files. It makes no
  application/runtime change. Rebuilt AutoGen suite: 100 tests ran, one skipped, no failures.
- [verified] The old SSE process-wide event-loop reset was removed from two test classes; actual
  streaming and cancellation tests passed without it. Cancellation-path tests intentionally print
  an AutoGen `CancelledError` diagnostic while returning a successful unittest verdict.

## Reproduction and limits

Host checks are `python -m unittest discover -s sandbox/graph-sandbox/tests -p 'test_*.py'` and
`python -m unittest discover -s sandbox/autogen-a2a-sandbox/tests -p test_activation.py`.
Framework tests run only in the revision-bound images with no external network, host mounts,
or credentials; containers are non-root, read-only, capability-free, and resource-limited.
Runtime scenarios use each sandbox's documented activation entrypoint. Private evidence is under
the local `sandbox-runtime-20260910` evidence root; image identities are in the run receipts.

The graph guard correctly rejected local CRLF bytes that differed from the committed LF build
snapshot. Restoring the committed bytes and refreshing Git's index cleared the rejection without
changing the guard, commit, or image identity. Keep working-tree bytes consistent with `.gitattributes`
before activating a byte-bound graph image.

[unverified] This does not validate LangGraph upgrades, every fault-case activation, production
behavior, or the entire sandbox matrix on a different host. The end-to-end receipts bind the
runtime commit above; the later change only relocates tests. No sandbox branch was pushed or PR
created as part of this local verification.
