# Libraries and modernization

Actively evaluate supported libraries when they remove substantial custom machinery or improve
correctness, capability, clarity, or maintenance. Compare the standard library, dependencies already
present, and suitable new packages against the actual problem. Release recency alone is not quality.

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

Verify that real callers use the replacement. A small compatibility adapter may be necessary;
retaining a second full implementation needs a concrete reason. Count removed maintenance work,
not imports added or versions advanced.

Library adoption within an authorized improvement is ordinary implementation when it fits the
project's compatibility, licensing, dependency, and execution constraints. Seek direction for material
runtime, framework, public-contract, or external-effect changes only when not already authorized.
Verify intentional behavior changes separately from behavior-preserving restructuring.

## Worked decision: order intake validation

An API and an import tool each carry custom checks for the same order input. The agreed contract
requires a nonempty symbol and a positive integer quantity, rejecting booleans and numeric strings.
The service already uses Pydantic elsewhere.

- **Compare the work removed.** A dataclass can represent an internal order but does not replace
  runtime validation. The existing validation dependency can replace the duplicated boundary
  checks; another package would need an additional capability to justify its cost.
- **Make library behavior explicit.** Configure field constraints and coercion to match the agreed
  contract. Check the actual Python-object or JSON entrypoint being used; strict validation can
  accept different representations through those entrypoints.
- **Integrate one owner.** Put the input rules in one boundary model and expose the parsing operation
  both callers need. Keep transport-specific error responses in their adapters. Introduce a separate
  domain record only when the internal representation needs to differ from the validated input.
- **Finish the replacement.** Exercise both callers with valid, missing, empty, boolean, string,
  and nonpositive quantities as applicable; check error and serialization contracts. Remove the
  superseded validators after their callers move. Success means the duplicate rules are gone and
  the intended boundary behavior remains, not merely that the package was imported.

For a local calculation receiving already validated values, ordinary arguments or a dataclass may
be sufficient. The decision follows the capability needed and maintenance removed; it does not
make every internal object a validation model or every small check a dependency opportunity.

## Examples of migration differences

These examples illustrate what to investigate, not a package shortlist. Select candidates for the
actual problem and recheck their current contracts at adoption; keep version pins in dependency files.

- **Validation:** Pydantic strict and coercing modes accept different inputs. Major-version changes
  can alter missing/nullable fields and validator exception handling. Check a valid input, missing,
  null, coercible, and invalid input; assert serialization separately. Do not silently tighten a
  previously accepted interface under a cleanup task.
- **HTTP:** HTTPX and Requests differ in redirects, timeout defaults, and exception types. Make
  relevant choices explicit; verify changed redirect, timeout, failure, and stream cleanup paths.
  Preserve the integration's overall deadline and retry contract, not just each call's options.
- **Retries:** Tenacity's bare decorator retries exceptions indefinitely without waiting. A retry
  stop condition does not interrupt an already-blocking call. Preserve one retry owner or account
  for all physical attempts. Establish eligibility, idempotency, deadlines, and provider-specific
  retry hints. Configure the final exception behavior intentionally.
- **Dependencies:** library compatibility requirements and a reproducible application environment
  serve different purposes. Preserve the project's packaging workflow; a new lock format does not
  justify replacing the package manager during unrelated work.

## Modernize for a benefit

Check the oldest supported Python and the runtime consumers of the affected feature. New syntax
must parse there; a backported library cannot make an older interpreter accept newer grammar.
Runtime annotation readers, class construction, serialization, and optional-dependency paths can
also constrain a change. Deferred annotation evaluation (3.14) lets unquoted forward references
work without `from __future__ import annotations` only when every supported runtime is 3.14+;
below that floor, removing the import or the quotes raises `NameError` when the definition runs.
Runtime readers see strings under that import and evaluated objects otherwise. Avoid rewriting
syntax merely because a newer spelling exists.

Use the [refactoring reference](./refactoring.md) to assess control-flow, collection, and iteration
replacements. For data and async changes, [Writing Python](./writing-python.md) covers ownership and
interface differences. Features such as dataclass slots or keyword-only construction need consumer
checks: inherited instance dictionaries may remain, while supported attribute access or positional
calls can break. A feature's availability does not establish equivalence.

For a Ruff upgrade preview, follow [Refactoring tools](./refactoring-tools.md) and select `UP` with
the component's actual `--target-version`. Keep optional and standard-library-only components within
their own constraints. Validate affected deployment versions rather than just the developer's runtime.

[sourced] [Pydantic migration](https://docs.pydantic.dev/latest/migration/),
[strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/),
[HTTPX compatibility](https://www.python-httpx.org/compatibility/),
[Tenacity defaults](https://tenacity.readthedocs.io/en/latest/),
[PyPA dependency contracts](https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/),
[dataclasses](https://docs.python.org/3/library/dataclasses.html),
[PEP 695](https://peps.python.org/pep-0695/),
[deferred annotations](https://peps.python.org/pep-0649/),
[Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html), and
[Python 3.15](https://docs.python.org/3.15/whatsnew/3.15.html).
