# VERIFY-001 closure evidence

- **Roadmap item:** `VERIFY-001` — isolate executable verification
- **Closure date:** 2026-08-02 (America/Chicago)
- **Authority boundary:** trusted repository-controlled commands only; no model session, credential
  access, writable source mount, pull, or network access

## Merged implementation

[PR #71](https://github.com/latent-sre/sre-agents/pull/71) merged the evidence envelope,
digest-bound verification sandbox, portability fixes, documentation, and deterministic tests. The
implementation lives in `scripts/verification_sandbox.py`, with its contract in
`docs/verification-sandbox.md` and evidence shape in `schemas/evidence-envelope-v1.schema.json`.

## Acceptance disposition

The runner requires a locally present digest-pinned image, disables pulls and networking, mounts
the exact committed source read-only, uses a separate bounded scratch area, runs non-root with a
read-only root filesystem and dropped capabilities, applies resource and time limits, inspects only
its owned container identity, checks cleanup residue, and emits pass/fail/inconclusive evidence.
Negative tests cover unsafe engines, unpinned images, source indirection, Git metadata, digest drift,
timeouts, output overflow, oversized scratch, missing images, cleanup failure, foreign name
collisions, and residue.

The implementation and hosted-runner portability changes received exact-revision independent
review, and their deterministic contracts ran on Ubuntu, macOS, and Windows. This closes the
verification boundary itself. A separate verification-agent persona or durable workflow consumer is
not implied; that decision remains trigger-bound under `STATE-001`.
