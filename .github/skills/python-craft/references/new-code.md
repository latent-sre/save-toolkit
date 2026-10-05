# Building new Python code

Read when starting an implementation. Use [Writing Python](./writing-python.md) for language and
interface choices; this reference covers the decisions that precede code and how to deliver it.

## Establish the contract

Identify the actual consumer and show a realistic input/call with its expected result. Establish
material empty, invalid, and failure behavior, plus constraints such as supported runtimes, input
size, ordering, memory, and latency. Use requirements and independent examples as the test oracle.
Clarify consequential unknowns; state reasonable low-risk assumptions and continue independent work.
Do not invent requirements to justify an architecture or turn a small task into a questionnaire.

## Choose a shape that fits

| Decision | What should determine it |
|---|---|
| Script, installed CLI, library, or service | Actual consumers and delivery needs. Preserve project conventions; do not manufacture a package, service hierarchy, or plugin system for a single local operation. |
| Shared core and adapters | When multiple consumers need the same decision, expose an importable operation. Keep parsing, display, process exit, and framework details at their appropriate boundaries. |
| Materialize, stream, or index | Required access and input growth. Bounded-category aggregation can stream; global sorting needs another plan. Include index/cardinality costs in the memory model. |
| Sequential, concurrent, or async | Independent work, I/O, ordering, and resource budgets. Concurrency adds coordination and failure behavior; it is not a default marker of modern code. |
| Fail all, return per-item outcomes, or allow partial progress | The caller's contract and effects already performed. Make failures observable; choose transaction, retry, or recovery machinery only when needed. |
| Direct implementation or dependency | Compare the standard library, existing dependencies, and maintained packages against the actual capability; use [Libraries and modernization](./libraries-and-modernization.md) when adopting one. |

Make a consequential design choice explicit with its main tradeoff. Prefer the simplest design
that satisfies the complete requirement; add abstraction when actual cases reveal a shared concept.

## Deliver and verify

Build one usable path from input through validation and the core operation to its result or effect,
then complete the remaining requirements. A directory skeleton, disconnected helpers, or a happy-path
demo is not completion. Introduce test seams at real boundaries without mocking away the behavior
being tested.

Verify success, boundaries, invalid input, and relevant failure/cleanup behavior. For effects, check
whether failure can leave partial state or falsely report success. Test expected values independently
of the implementation. Exercise realistic data sizes when bounds matter; benchmark performance claims.

Check the delivered interface as consumers use it: invoke a CLI, import a library, or exercise a
service's public contract. If installation is part of delivery, check the installed artifact rather
than relying on checkout-only imports.
