# Libraries and modernization

Actively evaluate supported libraries when they remove substantial custom machinery or improve
correctness, capability, clarity, or maintenance. Compare the standard library, dependencies already
present, and suitable new packages against the actual problem. Release recency alone is not quality.

## Choose and migrate

1. Name the limitation or duplicated capability. Inspect current callers, manifests, constraints,
   supported Python versions, target OS/architecture, and relevant tests.
2. Establish the documented contract for the installed and proposed APIs using current official
   documentation; inspect upstream source/tests when behavior is unclear. Use only tools available
   to the caller. A lane without external tools sends a sanitized public question to `researcher`
   through its existing delegation edge; never export private source or credentials. Missing
   evidence remains `[unverified]`, not permission to invent an API.
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

## Candidates by problem, not a universal package list

| Problem | Consider | Contract that still needs a decision |
|---|---|---|
| Named internal records | Dataclasses | Equality, mutability, defaults, construction; no general runtime type validation |
| Substantial external input validation | Existing validator or Pydantic | Coercion, missing/null, extra fields, errors, serialized output |
| Custom HTTP transport code | Existing client; HTTPX where its capabilities fit | Redirects, phase timeouts, exception hierarchy, streams, pooling, lifecycle |
| Repeated retry implementation | Existing SDK policy or configured Tenacity | Eligibility, attempt/deadline budget, cancellation, terminal exception |
| Broad deterministic input coverage | Hypothesis alongside existing tests | Meaningful invariants, independent expectations, input domain |
| Multi-keyword scanning over many texts | `pyahocorasick` over per-key substring loops | Encoding, whole-word vs substring, overlaps; stdlib `re` alternation for small sets |
| Hot JSON encode/decode | `orjson` where a binary dependency fits; stdlib `json` otherwise | Rejected types, bytes-vs-`str` output, key-order determinism |
| Human-facing CLI tables | `rich` for output only, never for decisions | Plain-text fallback for pipes/logs; no logic on rendered text |
| Parallel test execution | `pytest-xdist` (`-n auto`) for suites | Shared-state collisions; not for tests that depend on run order |
| Paths, batching, TOML reading | `pathlib`, `itertools`, `tomllib` where supported | Platform semantics, partial batches, parsing versus writing, Python floor |

These are options to evaluate, not approved additions for every project. Toolchain defaults remain
in `stack-profile`; version pins belong in the project's dependency files. Recheck package facts at
adoption rather than freezing "latest" versions into this guidance.

## Migration differences that a rename will miss

- **Validation:** Pydantic strict and coercing modes accept different inputs. Major-version changes
  can alter missing/nullable fields and validator exception handling. Check a valid input, missing,
  null, coercible, and invalid input; assert serialization separately. Do not silently tighten a
  previously accepted interface under a cleanup task.
- **HTTP:** HTTPX and Requests differ in redirects, timeout defaults, and exception types. Make
  relevant choices explicit; verify changed redirect, timeout, failure, and stream cleanup paths.
  Load `backend-craft` for the complete integration/deadline contract.
- **Retries:** Tenacity's bare decorator retries exceptions indefinitely without waiting. A retry
  stop condition does not interrupt an already-blocking call. Preserve one retry owner or account
  for all physical attempts; let `backend-craft` own eligibility, idempotency, deadlines, and
  provider-specific retry hints. Configure the final exception behavior intentionally.
- **Dependencies:** library compatibility requirements and a reproducible application environment
  serve different purposes. Preserve the project's packaging workflow; a new lock format does not
  justify replacing the package manager during unrelated work.

## Modern syntax and standard library

| Feature | Minimum version | Semantic check |
|---|---|---|
| `zip(..., strict=True)` | 3.10 | Unequal lengths now raise rather than truncate |
| `match` statement | 3.10 | Structural dispatch, not ranges; a bare name in `case` captures instead of comparing, so use dotted constants |
| `X \| None` unions at runtime | 3.10 | Earlier runtimes accept it only in postponed annotations |
| `dataclass(slots=True, kw_only=True)` | 3.10 | Slots remove the instance `__dict__`, breaking ad-hoc attributes and `cached_property`; keyword-only breaks positional callers |
| `tomllib` | 3.11 | Reads TOML; does not write it |
| `asyncio.TaskGroup` and `except*` | 3.11 | Changes task ownership, sibling failure, and cancellation; failures surface as `ExceptionGroup`, so existing `except X` handlers stop matching |
| `asyncio.timeout()` | 3.11 | One deadline over several awaits; raises `TimeoutError` outside the block |
| `datetime.UTC`, `enum.StrEnum`, `typing.Self` | 3.11 | `UTC` aliases `timezone.utc`; a `StrEnum` member's `str()` is its value |
| `type Alias = ...` / type-parameter syntax | 3.12 | Older runtimes cannot parse it; runtime annotation consumers still matter |
| `typing.override` | 3.12 | Checked by type checkers, not at runtime |
| `itertools.batched` | 3.12; `strict` in 3.13 | Decide whether the last partial batch is accepted |
| `warnings.deprecated`, `copy.replace` | 3.13 | Mark a moved public name for callers and type checkers; build a changed copy of a frozen record |
| Deferred annotation evaluation default | 3.14 | Check frameworks/tools that inspect annotations at runtime |
| `except A, B:` without parentheses | 3.14 | Older runtimes cannot parse it |

A feature's availability does not make it behavior-equivalent. Keep component-specific floors,
optional-dependency paths, and isolated standard-library entrypoints intact. Validate the actual
deployment versions, not only the developer's interpreter. For the mechanical part of an upgrade,
`ruff check --no-fix --select UP --target-version <floor> <paths>` lists the rewrites, where
`<floor>` is the oldest supported runtime (for example `py311`); review them as fixes under
Refactoring tools.

[sourced] [Pydantic migration](https://docs.pydantic.dev/latest/migration/),
[strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/),
[HTTPX compatibility](https://www.python-httpx.org/compatibility/),
[Tenacity defaults](https://tenacity.readthedocs.io/en/latest/),
[PyPA dependency contracts](https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/),
[zip](https://docs.python.org/3/library/functions.html#zip),
[tomllib](https://docs.python.org/3/library/tomllib.html),
[TaskGroup](https://docs.python.org/3/library/asyncio-task.html),
[PEP 695](https://peps.python.org/pep-0695/),
[batching](https://docs.python.org/3/library/itertools.html#itertools.batched), and
[Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html).
