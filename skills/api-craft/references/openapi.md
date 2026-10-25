# OpenAPI contracts

Preserve the project's generator, document format/location and checks; choose new-service defaults for consumers.

## Keep one contract source

Edit the owning source (handlers/models or specification), not its generated copy. Generators,
consumers and CI use the same document; pin the delivered artifact when consumers need reproducibility.
Keep authentication/public exceptions and stateful rejections explicit: schema-valid input can still
conflict with current state. Compatibility changes follow the [contract rule](./api-contract.md#contract-changes).

## Select checks for the contract

| Need | Check |
|---|---|
| Committed generated document | Regenerate from the real app and fail on drift. |
| Document used by clients | Validate the schema and generate/compile the actual consumer; assert required shapes and security declarations. |
| Response coverage | Exercise real handlers against documented success/error responses. Schema-based testing such as Schemathesis can broaden coverage. |
| Compatibility across releases | Compare with a known base; `oasdiff` is one option. |

Use isolated identities with the actual authentication integration; check public access and protected
refusal/intended access. Configure Schemathesis security/parameters accordingly. A schema gate does
not establish object authorization, idempotency or crash recovery.

## Generator traps

- Preserve stable, unique operation IDs using FastAPI's `generate_unique_id_function` or Huma's
  `OperationID` when defaults do not match the client contract.
- Name generic page models when clients require stable names. Huma drops package paths and Go
  aliases keep their target's name; check collisions in generated output.
- Choose input/output schema separation deliberately; FastAPI's
  `separate_input_output_schemas=False` merges them.
- Missing and nullable are different. In Pydantic v2, a nullable field without a default is required.
  Check omitted fields and nil versus empty collections against the actual serializer and document.
- Check the emitted OpenAPI version and streaming constructs against the actual consumer generator.
  Support for ordinary `schema` does not establish support for OpenAPI 3.2 `itemSchema`; generate
  the client and verify event types rather than accepting `unknown` as a typed stream.

## CI

For Git comparisons, verify the base revision and use the same document path on both sides.
A new service with no prior document can skip comparison; an unavailable base is a gap, not that case.
