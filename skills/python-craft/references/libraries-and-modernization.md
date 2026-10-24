# Libraries and modernization

Compare standard-library, existing and new dependencies against the maintenance/correctness benefit;
release recency alone is not quality.

## Choose and migrate

1. Check the installed and proposed APIs against current official documentation, or upstream
   source and tests when unclear, without exporting private source or credentials. State missing
   evidence instead of inventing an API; popularity does not establish compatibility.
2. Check advisories, licensing, and transitive dependencies. Preserve environment markers and
   confirm distributions exist for every target Python version and platform.
3. State the benefit and behavior differences: coercion, defaults, exceptions, serialization,
   sync/async behavior, and resource lifetime. Prefer public APIs to library internals.
4. Replace through callers under the project's dependency workflow. Keep developer tools out of
   runtime dependencies, keep the previous state installable, and remove obsolete helpers once unused.

Library adoption within an authorized improvement is ordinary implementation when it fits the
project's compatibility, licensing, dependency, and execution constraints. Seek direction for material
runtime, framework, public-contract, or external-effect changes only when not already authorized.
Verify intentional behavior changes separately from behavior-preserving restructuring.

## Examples of migration differences

These are migration traps, not a package shortlist; recheck the installed/proposed contracts.

- **Validation:** Pydantic strict and coercing modes accept different inputs. Major-version changes
  can alter missing/nullable fields and validator exception handling. Check a valid input, missing,
  null, coercible, and invalid input; strict Python-object and JSON acceptance can differ. Assert
  serialization separately; do not silently tighten accepted inputs during cleanup.
- **HTTP:** HTTPX and Requests differ in redirects, timeout defaults, and exception types. Make
  relevant choices explicit; verify changed redirect, timeout, failure, and stream cleanup paths.
  Preserve the integration's overall deadline and retry contract, not just each call's options.
- **Retries:** Tenacity's bare decorator retries exceptions indefinitely without waiting. A retry
  stop condition does not interrupt an already-blocking call. Preserve one retry owner or account
  for all physical attempts. Establish eligibility, idempotency, deadlines, and provider-specific
  retry hints. Configure the final exception behavior intentionally.

## Modernize for a benefit

Check the oldest supported Python and the runtime consumers of the affected feature. New syntax
must parse there; a backported library cannot make an older interpreter accept newer grammar.
Runtime annotation readers, class construction, serialization, and optional-dependency paths can
also constrain a change. Deferred annotation evaluation (3.14) lets unquoted forward references
work without `from __future__ import annotations` only when every supported runtime is 3.14+;
below that floor, removing the import or the quotes raises `NameError` when the definition runs.
Runtime readers see strings under that import and evaluated objects otherwise. Avoid rewriting
syntax merely because a newer spelling exists.

For semantic replacements use [refactoring](./refactoring.md); for data/async ownership use
[Writing Python](./writing-python.md). Dataclass slots or keyword-only construction need consumer
checks: inherited instance dictionaries may remain, while supported attribute access or positional
calls can break. A feature's availability does not establish equivalence.

For a Ruff upgrade preview, follow [Refactoring tools](./refactoring-tools.md) and select `UP` with
the component's actual `--target-version`. Keep optional and standard-library-only components within
their own constraints. Validate affected deployment versions rather than just the developer's runtime.
