# Building new Python code

Read when starting an implementation. Use [Writing Python](./writing-python.md) for language and
interface choices; this reference covers the decisions that precede code and how to deliver it.

## Establish the contract

Identify the actual consumer and show a realistic input/call with its expected result. Establish
material empty, invalid, and failure behavior, plus constraints such as supported runtimes, input
size, ordering, memory, and latency. Use requirements and independent examples as the test oracle.
Clarify consequential unknowns; state reasonable low-risk assumptions and continue independent work.
Do not invent requirements to justify an architecture or turn a small task into a questionnaire.

## Establish the starting environment

Inspect the project's runtime, dependency workflow, and existing test, lint, format, and type checks.
When a new project leaves those choices unset, load `stack-profile` for the team's defaults and
establish checks appropriate to the delivered component. Use [Environment and checks](./environment-and-checks.md)
to bind them to the intended interpreter; preserve an existing project's tooling.

Compose the Python guidance with `api-craft` for HTTP APIs, clients, and API-backed asynchronous work,
and `operator-cli` for a CLI's output, configuration, failure, or effect contract. Load only the
applicable layer; language-level correctness does not establish the service or operator contract.

## Choose a shape that fits

Choose the delivery form from actual consumers. State consequential tradeoffs, bound work and memory,
and preserve partial-failure semantics. For dependency adoption, use
[Libraries and modernization](./libraries-and-modernization.md).

## Deliver and verify

Deliver complete behavior through its real entrypoint; test against independent expectations.

For text protocols, establish encoding, record framing, and malformed-input policy at each real
boundary. A UTF-8 file path and redirected stdin can use different decoders; testing an in-memory
text stream does not exercise either byte boundary. When the contract rejects invalid bytes, check
them through both supported paths as well as valid non-ASCII input. Keep CLI decoding policy in the
CLI adapter; preserve borrowed streams and the core's declared text/record interface.

Check the delivered interface as consumers use it: invoke a CLI, import a library, or exercise a
service's public contract. If installation is part of delivery, check the installed artifact rather
than relying on checkout-only imports.
