# Retire the digest-bound verification sandbox; keep its snapshot hasher

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision owner:** `latent-sre`
- **Supersedes:** `docs/verification-sandbox.md`, the live reference contract that governed
  `scripts/verification_sandbox.py`. That document and both of its files are deleted here. The
  Docker-backed local verification policy in [`AGENTS.md`](../../AGENTS.md) is **not** superseded:
  it permits a lane with existing execute authority to run a pinned image directly, which is what
  the fleet actually does.

## Context

`VERIFY-001` closed on 2026-08-02 into `docs/verification-sandbox.md`, a contract for running one
argv command inside a pinned, networkless Docker or Podman image against a digest-bound source
snapshot. The runner was implemented, specified, and tested: 25.5 KB of implementation and 15.8 KB
of tests.

Nothing ever called it. A reachability sweep on 2026-08-26 found no reference in `skills/`,
`agents/`, `commands/`, `.github/workflows/`, or `hooks/` — no lane is routed to it, no gate runs
it, and no skill names it. Its only live consumer was one line of the `HOST-002` probe instrument,
which used the `tree-digest` subcommand to record a snapshot hash as evidence. That is a hashing
utility, not the sandbox boundary.

This is the shape `RELEASE-001` and `STATE-001` were retired for: machinery built ahead of a named
consumer, then carried as maintenance. The owner directed removal on 2026-08-26.

## Decision

1. Delete `scripts/verification_sandbox.py`, `scripts/test_verification_sandbox.py`, and
   `docs/verification-sandbox.md`.
2. Move `tree_digest` and its link/reparse-point and `.git` refusals into
   [`scripts/evidence_envelope.py`](../../scripts/evidence_envelope.py) as a `tree-digest`
   subcommand. That module already owns evidence primitives, already exposes a CLI, and already
   validates envelopes carrying a `tree_digest` field.
3. Keep the digest **byte-compatible**. The `save-toolkit-verification-tree-v1` prefix and the D/F
   path framing are part of the hash, so digests already recorded in dated evidence packets still
   verify. Parity against the retired implementation was checked before deletion.
4. Repoint the `HOST-002` probe at the new command.

## Consequences

- The fleet no longer ships a digest-bound container execution boundary. A lane that needs
  containerized verification follows the `AGENTS.md` policy: pin an exact image, `--rm`,
  `--network none`, read-only mounts, no socket, no credentials, and record the resolved image
  reference, command, exit status, and what the result does and does not prove.
- The snapshot hasher keeps its safety rules and gains direct test coverage it did not have before:
  stability, content and path sensitivity, `.git` refusal, symlink refusal, non-directory refusal,
  and the CLI path.
- `docs/verification-sandbox.md` stops being a live reference contract. `docs/README.md`,
  `docs/rules.md`, `CONTRIBUTING.md`, and the `VERIFY-001` row in
  [`roadmap-closed.md`](../roadmap-closed.md) are updated in the same change.
- Dated review packets that mention `verification_sandbox.py` are left unedited. They are history,
  and `docs/rules.md` requires leaving recorded results under their original vocabulary.

## Rejected alternatives

- **Keep it against future need.** This is the argument that produced `RELEASE-001`, `STATE-001`,
  and `EVAL-001`. Git history preserves the implementation; a future consumer can restore it with a
  named requirement attached.
- **Delete `tree-digest` too and inline a hash in the probe.** That would silently change the digest
  algorithm, invalidating comparison against digests already recorded as `HOST-002` evidence.
- **Move the hasher to `fleet_doctor.py`.** The doctor is a reporting surface with its own private
  guard-bundle digest; a general snapshot hasher is an evidence primitive.

## Reopen trigger

A named consumer requires an execution boundary stronger than the `AGENTS.md` Docker policy — one
that must refuse to run against bytes whose digest was not preapproved, and must emit typed
`inconclusive` evidence when the source changes mid-run. Restore from history at that point rather
than rewriting it.
