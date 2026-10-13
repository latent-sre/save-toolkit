# OpenAPI: the committed contract

New HTTP services use the pipeline below. Existing services keep their framework, generator,
contract, canonical specification format/location and equivalent checks. Update that specification
when present and run applicable checks plus focused tests for changed behaviour. Missing
service-wide documentation or CI adoption is a separately scoped task; report absent contract or
compatibility evidence. Read tool/framework versions from manifests and lockfiles.

## Pipeline

1. **Generate from source:** FastAPI/Huma use typed handlers and models. Keep an existing
   spec-first workflow; never hand-edit a code-generated document.
2. **Commit one document for a new service:** `openapi.json`, LF endings, at the **service root** (module or
   `pyproject.toml` root). In a monorepo this may be `services/orders/openapi.json`. Generation,
   pinned consumer input and CI all refer to this same file.
3. **Gate drift:** `test_document_matches_the_code`/`TestOpenAPIDocument` regenerates and compares.
   For an intended change, run from the service root with `UPDATE_OPENAPI=1 python -m pytest
   test_openapi_document.py` or `go test -run TestOpenAPIDocument -update`, then review the diff
   before implementation under the approval rule in `SKILL.md`.
4. **Check contract rules:** the starters assert `/v1`, unique lowerCamel `operationId`, security
   unless explicitly public, problem-shaped errors and version `3.1.0`. In an established API,
   adapt assertions to its contract, including added routes, until an authorized migration.
5. **Exercise the document:** Schemathesis sends valid/invalid inputs and rejects undocumented
   responses and 500s. FastAPI runs in-process (`test_schemathesis.py`); Go runs `st` against the
   real handler (`schemathesis_test.go`). Use the test verifier's token, never a service-wide
   static token. Disable `allow-extra-parameters` and `with-security-parameters`: extra query
   parameters are ignored, and the test supplies authentication. Explicitly test stateful
   rejections such as idempotency conflicts; schema-valid does not mean state-valid.
6. **Gate compatibility:** `oasdiff breaking --fail-on ERR base.json openapi.json` compares the
   committed candidate and base documents. Accepted breaks follow [versioning](./versioning.md).

## Generated-client shapes

- **Names are API.** Unique lowerCamel operation IDs (`listThings`): FastAPI's house
  `operation_id` replaces its default; set Huma's `OperationID` per operation.
- **Named schemas:** declare `class ThingPage(Page[Thing])` in Python, `type ThingPage Page[Thing]`
  in Go. Otherwise FastAPI names the generic `Page_Thing_`, Huma uses `PageThing`, and a Go alias
  keeps its target's name. Huma drops package paths: rename colliding types.
- **One schema per model:** house FastAPI uses `separate_input_output_schemas=False` to avoid
  `Thing-Input`/`Thing-Output` splits. House Huma disables its automatic `$schema` body property
  and `Link` header.
- **Present and nullable:** Python `next_cursor: str | None` without a default; Go `NextCursor
  *string` without `omitempty`. Go slices need `nullable:"false"` and an empty, non-nil return.
- **Schema-declarable validation belongs in the document:** patterns, enums, bounds and formats.
  Opaque cursors declare encoding (`^([0-9a-f]{2})+$`, max 2048). Huma treats empty query values
  as absent: reject present-but-empty parameters in `Resolve`. Stateful rejection belongs in
  documented responses and behavioural tests, not fictitious input restrictions.

## OpenAPI 3.2-ready

The OAI states 3.1 documents work as 3.2 after changing only the version. FastAPI/Huma emit 3.1.0;
openapi-typescript documents 3.0/3.1. oasdiff, Schemathesis, Redocly CLI, Spectral and Swagger UI
5.32+ read 3.2. A 3.2-only construct (`QUERY`, `in: querystring`, sequential-media `itemSchema`,
tag `parent`) waits for both the producing framework and every consumer's generator.

SSE is the existing exception: FastAPI's `fastapi.sse` emits 3.2 `itemSchema` inside 3.1.0;
openapi-typescript types that stream as `unknown` but generates event-data schemas. The UI parses
each event's `data` as its schema (`components["schemas"]["Tick"]`). Huma's `sse` package documents
an array of `oneOf` event objects.

## CI

For a new service or a separately scoped gate adoption, load `ci-actions` when adapting
[Go](../assets/ci/api-contract-go.yml) or
[FastAPI](../assets/ci/api-contract-fastapi.yml) workflows. Set `SERVICE_DIR` to the service root
(`.` for a single-service repository); tests and comparison run there. The starters verify the
base commit, then derive the repository-relative document path from the service's Git prefix, so
`git show` reads the same document from the base. A missing first-service document differs from an
unavailable base revision; do not silently skip the latter. The starters assume `openapi.json`;
adapt their paths and commands to an existing service's canonical specification. Keep its existing
or equivalent drift, contract, response and compatibility checks effective.
