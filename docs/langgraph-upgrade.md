# LangGraph upgrade verification - 2026-09-10

This follow-up to the [sandbox runtime upgrade](sandbox-runtime-upgrade.md) changes LangGraph
1.0.10 to 1.2.11 in canonical requirements, the runner, activation identity checks, and fixtures.
SQLite saver remains 3.1.1. It does not migrate existing checkpoint stores: the new regression
verifies that an old LangGraph fingerprint is rejected without replacing stored metadata.

## Evidence

- [sourced] The [1.2.11 release](https://github.com/langchain-ai/langgraph/releases/tag/1.2.11)
  raises constraints on langchain-core, checkpoint, prebuilt, and SDK. GitHits reported no affected
  direct or transitive packages in its upgrade comparison; this is advisory coverage, not a security verdict.
- [verified] A dry resolution of all 129 development packages succeeds on Python 3.14.7.
  It changes LangGraph to 1.2.11, prebuilt to 1.1.0, SDK to 0.4.4, and websockets from 17.1
  to 16.1.1. Upstream dependency-graph conflict signals did not reproduce in this resolver check.
- [verified] Runtime source revision: `0825c6e9d00d5c9f8ad8f0f0404823ef5dadcda4`.
  The supported activation builder produced runner image
  `sha256:8147e408ee49aec3b855711eb1a458ccc4c99e8c661eb1c3766650f156ba67cc`.
  Host contract/preflight tests: 103 passed. Hardened container recovery suite: 23 passed,
  including same-fingerprint reopen, incompatible checkpoint rejection, checkpoint write recovery,
  and effect-ledger transitions.
- [verified] Three activation cases passed on desktop-linux with observed Python 3.14.7,
  LangGraph 1.2.11, and SQLite saver 3.1.1: healthy checkout (`lg1211-healthy`),
  ambiguous-after-commit reconciliation (`lg1211-ambiguous`), and duplicate effect
  (`lg1211-duplicate`). The ambiguous case published UNKNOWN before reconciliation to SUCCEEDED.
  All three completed with exit zero; their run-scoped containers, networks, and volumes were absent
  afterward. Private receipts are under the local sandbox-runtime-20260910 evidence root.

## Remaining limits

The recovery suite emits ResourceWarning diagnostics for unclosed SQLite connections. Inspection
found connection context managers in runner/effects.py and runner/checkpoints.py that manage
transactions without explicitly closing the connection. Address connection lifetime separately;
passing recovery assertions do not establish resource hygiene.

The full shared development environment was resolved but not exercised with the downgraded
websockets package; the graph container and its dependencies were exercised. Microsoft Agent
Framework beta upgrades, every fault case, cross-version checkpoint migration, and production
behavior remain unverified. These checks do not constitute human acceptance of the candidate.
