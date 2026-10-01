# Libraries and modernization

Actively evaluate supported libraries when they remove substantial custom machinery or improve
correctness, capability, clarity, or maintenance. Compare the standard library, dependencies already
present, and suitable new packages against the actual problem. Release recency alone is not quality.

## Choose and migrate

1. Name the limitation or duplicated capability. Inspect current callers, manifests, constraints,
   supported Python versions, target OS/architecture, and relevant tests.
2. Establish the documented contract for the installed and proposed APIs using current official
   documentation; inspect upstream source/tests when behavior is unclear. Research public APIs
   without exporting private source or credentials. State missing evidence instead of inventing an API.
3. Check support/maintenance, migration notes, relevant advisories, licensing fit, and direct and
   transitive dependencies. Preserve environment markers and check distribution availability for
   the target platform. Package summaries and popularity do not establish compatibility.
4. State the concrete benefit and behavior differences: inputs/coercion, defaults, exceptions,
   serialization, public interfaces, sync/async behavior, resource lifetime, and measured performance
   where material. Prefer supported public APIs to library internals.
5. Implement the replacement through its callers. Follow the project's dependency and lock/constraint workflow;
   keep developer-only refactoring tools out of application runtime dependencies. Preserve an
   installable previous code/dependency state. Remove obsolete helpers and dependencies once unused.

Verify that real callers use the replacement. A small compatibility adapter may be necessary;
retaining a second full implementation needs a concrete reason. Count removed maintenance work,
not imports added or versions advanced.

Library adoption within an authorized improvement is ordinary implementation when it fits the
project's compatibility, licensing, dependency, and execution constraints. Seek direction for material
runtime, framework, public-contract, or external-effect changes only when not already authorized.
Verify intentional behavior changes separately from behavior-preserving restructuring.

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
also constrain a change. Avoid rewriting syntax merely because a newer spelling exists.

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
[PEP 695](https://peps.python.org/pep-0695/), and
[Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html).
