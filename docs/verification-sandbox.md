# Digest-bound verification sandbox

`scripts/verification_sandbox.py` runs one direct argv command inside a locally available Docker or
Podman image without granting the command ordinary host execution. It is a verification boundary,
not a general build runner and not release authorization.

## Required inputs

- A reviewed source snapshot with no `.git` metadata, symlinks, junctions, or reparse points.
- The full 40- or 64-hex revision the snapshot represents.
- A separately measured SHA-256 tree digest for those exact bytes.
- A trusted image already present locally and named as `repository@sha256:<64 lowercase hex>`.
- One direct argv command. Obvious credential-bearing flags and credentialed URLs are refused.

The runner does not create the source snapshot or decide that an image is trustworthy. Those are
caller-owned admission decisions. It hashes the source before and after execution and refuses a
pre-run mismatch; a concurrent change makes the result `inconclusive`.

## Use

Calculate the snapshot digest:

```powershell
py -3 scripts/verification_sandbox.py tree-digest C:\path\to\reviewed-snapshot
```

Then pass that exact digest to the run command:

```powershell
py -3 scripts/verification_sandbox.py run `
  --engine docker `
  --image example/verifier@sha256:<64-hex-digest> `
  --source C:\path\to\reviewed-snapshot `
  --expected-tree-digest <tree-digest> `
  --target-revision <full-revision> `
  --criterion "unit tests pass" `
  -- python -m unittest
```

The image must already exist. `--pull never` makes a missing image `inconclusive`; the runner never
downloads one. The JSON result conforms to
[`evidence-envelope-v1.schema.json`](../schemas/evidence-envelope-v1.schema.json).
`/scratch` defaults to a 256 MiB tmpfs and can be adjusted with `--scratch-size` only within the
enforced 1 MiB to 4 GiB range.

## Enforced boundary

- network mode `none` and no image pull;
- read-only container root filesystem and read-only `/workspace` source bind;
- one initially empty, size-limited `/scratch` tmpfs plus a bounded `noexec,nosuid,nodev` `/tmp`;
- non-root numeric user, all Linux capabilities dropped, and `no-new-privileges`;
- CPU, memory, PID, and wall-clock limits;
- isolated container-client home with remote Docker environment and user credentials removed;
- automatic `--rm` cleanup, or forced cleanup by an inspected, fleet-labelled container ID,
  followed by an explicit residue inspection;
- streaming stdout/stderr capture capped at 1 MiB per stream; exceeding the cap terminates the engine
  client, forces owned-container cleanup, and yields `inconclusive`; only retained-prefix hashes and
  sizes enter the envelope, never raw output.

A timeout, output-limit breach, engine failure, cleanup anomaly, residue, source drift, or unavailable
pinned image is `inconclusive`, never a pass. A nonzero command exit is `fail` only when the isolation
and cleanup checks themselves completed.

## Deliberate limits

- The digest binds bytes to the caller-supplied revision label; the runner does not execute Git in an
  untrusted checkout. The caller must create the snapshot from the reviewed revision.
- The pinned digest establishes image identity, not image trust. Use a separately reviewed image.
- Network-enabled verification is unsupported. A criterion that needs network remains
  `inconclusive` until a destination-brokered design is approved.
- Codex/Claude agent permissions do not enforce this boundary. The container engine and host OS do.
- No `verification-engineer` agent is added yet. A roster role should follow only after a measured
  workflow consumes this runner and demonstrates that a separate lane improves outcomes.
