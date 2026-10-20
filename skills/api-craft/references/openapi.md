# OpenAPI contracts

Preserve the project's generator, specification format/location and validation pipeline.
For new services, choose these from consumer and delivery requirements.

## Keep one contract source

- Give generators, consumers and CI the same canonical document. Edit the owning source
  (handlers/models for code-first, specification for spec-first). Commit or publish a pinned
  artifact when consumers or reproducibility require it; its filename and location follow the project.
- Keep operation IDs stable and unique, schemas usable by the actual client generator, and
  authentication/public exceptions explicit.
- Document success and failure responses, nullability, constraints and stateful rejections.
  Schema-valid input can still conflict with current state.
- Describe the diff under the [contract-change rule](./api-contract.md#contract-changes).

## Select checks for the contract

| Need | Check |
|---|---|
| Committed generated document | Regenerate from the real app and fail on drift; provide an explicit update command. |
| Document used by clients | Validate the schema and generate/compile the actual consumer; assert required shapes and security declarations. |
| Response coverage | Exercise real handlers against documented success/error responses. Schema-based testing such as Schemathesis can broaden coverage. |
| Compatibility across releases | Compare the candidate with a known base; `oasdiff` is one option. Accepted breaks follow [contract changes](./api-contract.md#contract-changes). |

Use isolated identities from the actual authentication integration. Exercise public operations
without identity and protected operations for both refusal and intended access. With Schemathesis,
configure generated security and extra parameters to match that policy; keep stateful rejections
explicit. A schema gate does not establish object authorization, idempotency or crash recovery.

## Generator traps

- Preserve client-visible names. Configure FastAPI's `generate_unique_id_function` or Huma's
  `OperationID` when their defaults do not satisfy the selected contract.
- Name generic page models when clients require stable names. Huma drops package paths and Go
  aliases keep their target's name; check collisions in generated output.
- Choose input/output schema separation deliberately; FastAPI's
  `separate_input_output_schemas=False` merges them.
- Missing and nullable are different. In Pydantic v2, a nullable field without a default is required.
  Check omitted fields and nil versus empty collections against the actual serializer and document.
- Select the OpenAPI version supported by producer and consumers. Newer-only constructs (such as
  OpenAPI 3.2 `itemSchema`, emitted by FastAPI 0.134+/0.135+ for JSONL/SSE generators) need
  end-to-end support; verify stream event types in the generated client (for example,
  `openapi-typescript` 7.x reads `schema`, not `itemSchema`, and yields `unknown` unless `schema` is
  also present).

## CI

For a Git-based compatibility check, fetch and verify the base revision and use the same
repository-relative document path on both sides. A first-service document absent from the base
can skip comparison; an unavailable base revision is an evidence gap.
