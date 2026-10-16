# OpenAPI contracts

Use when the service publishes OpenAPI or its consumers need generated clients or schema-based
checks. Preserve the existing generator, specification format/location and validation pipeline.
For a new service, choose the document workflow and checks from its consumers and delivery needs.

## Keep one contract source

- Code-first services generate from typed handlers/models; spec-first services generate from the
  specification. Edit the owning source.
- Give generators, consumers and CI the same canonical document. Commit or publish a pinned
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
| Compatibility across releases | Compare the candidate with a known base; `oasdiff` is one option. Accepted breaks follow [versioning](./versioning.md). |

Use isolated test identities with the application's actual authentication integration. Test explicitly
public operations without identity, and protected operations for both refusal and intended access.
A schema gate does not establish object authorization, idempotency or crash recovery.

When using Schemathesis, supply the intended test identity; configure generated security and extra
parameters to match the service's policy. Keep stateful rejection cases explicit. FastAPI can run
in-process; another service can be tested over HTTP.

## Generator traps

- Preserve client-visible names. Configure FastAPI's `generate_unique_id_function` or Huma's
  `OperationID` when their defaults do not satisfy the selected contract.
- Name generic page models when clients require stable names. Huma drops package paths and Go
  aliases keep their target's name; check collisions in generated output.
- Choose input/output schema separation deliberately. FastAPI's
  `separate_input_output_schemas=False` merges them; a Huma contract excluding its added
  `$schema`/Link metadata needs matching configuration.
- Missing and nullable are different. A Python nullable field without a default remains required;
  Go `omitempty` can omit it. Check nil versus empty collections in serialized responses.
- Huma treats empty query values as absent; use `Resolve` when the contract rejects present-but-empty.
- Select the OpenAPI version supported by producer and consumers. Newer-only constructs need
  end-to-end support; verify stream event types in the generated client.

## CI

Wire applicable checks into the project's delivery workflow; load `ci-actions` when changing it.
For a Git-based compatibility check, fetch and verify the base revision and use the same
repository-relative document path on both sides. A first-service document absent from the base
can skip comparison; an unavailable base revision is an evidence gap.

Report the document source, checks executed and CI execution separately. Prepared workflow
configuration does not establish a remote pass.
