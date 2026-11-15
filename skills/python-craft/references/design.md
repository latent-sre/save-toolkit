# Design and dependencies

## Choosing a library

Prefer a maintained library to homegrown validation, configuration, HTTP, retries, persistence,
CLI parsing, serialization, and data processing. Assess in proportion to the commitment: fit to the
actual problem, API quality, maintenance, support for the Python floor and deployment platforms,
typing, license, and dependency or runtime cost.

- One library per role: use the project's existing HTTP client, validator, or CLI framework or
  replace it everywhere; never run two.
- Wrap a library only where the wrapper owns domain vocabulary, a policy, or a substitution seam.
- A one-line rationale covers an ordinary choice.

## Technique selection

| Problem | Use, and the trap |
|---|---|
| Data crossing a trust boundary | A validating model at the boundary, plain typed values inside. Annotations, dataclasses, and `TypedDict` validate nothing at runtime |
| Invalid states are representable | Enums, tagged unions matched exhaustively (`assert_never`), `NewType` identifiers, generics instead of `Any`, frozen dataclasses. `frozen=True` does not freeze contained collections |
| A caller needs substitution | A `Protocol` owned by the consumer, the dependency passed in. No substitution need, no interface |
| Function, class, or composition | Functions for stateless behavior; a class when it owns state with invariants or a lifecycle; compose collaborators rather than inherit |
| Decisions tangled with I/O | A core returning decisions as values; I/O and orchestration at the edge, depending on the core and never the reverse; one responsibility per module |
| Something acquired must be released | Context managers, `ExitStack` for dynamic sets; owners close, borrowers do not. A generator returned from inside `with` outlives the resource |
| Shared clients, pools, settings | Construct in the entrypoint and pass down. Module-level singletons and import-time I/O hide ownership |
| The workload outgrows the simple version | Stream and batch unbounded input, index repeated lookups, vectorize numeric volume, cache repeated pure computation. Fix the algorithm first |

## Concurrency

Add it for a real need: threads for blocking libraries, `asyncio` with `TaskGroup` for I/O
fan-out, processes or a native library for CPU-bound work. Make explicit:

- **Bound:** a semaphore, pool size, or bounded queue. `TaskGroup` and `gather` limit nothing.
- **Deadline:** one for the whole operation (`asyncio.timeout`), a timeout on every network call.
- **Cancellation:** clean up, then re-raise.
- **Failure:** `TaskGroup` cancels siblings and raises `ExceptionGroup`, which `except ValueError`
  misses; use `except*`. No unowned tasks, no blocked event loop.

## Services and automation

- **Idempotency:** decide what a second run does; use keys, upserts, or recorded progress.
- **Retries:** transient failures of idempotent calls only, bounded attempts under a total
  deadline, jittered backoff, one retry owner per call path.
- **Partial failure:** stop, continue with per-item outcomes, or compensate; report it in the
  result and exit status. When requirements do not settle the policy, ask.
- **Diagnostics:** errors name the operation, item, and cause. Never log a failure and return
  success.
- **Operator mutations:** compute a plan, then apply it. `--dry-run` prints that same plan with
  writes disabled, never a parallel code path.
