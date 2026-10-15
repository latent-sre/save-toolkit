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
3. **Gate drift:** a test regenerates the document and compares it with the committed file, with
   an explicit update mode (`UPDATE_OPENAPI=1` for pytest, a `-update` flag for
   `go test -run TestOpenAPIDocument`). For an intended change, update from the service root, then
   review the diff before implementation under the approval rule in `SKILL.md`.
4. **Check contract rules:** assert `/v1`, unique lowerCamel `operationId`, the actual identity
   scheme except on explicitly unauthenticated operations, problem-shaped errors and version
   `3.1.0`. Drive the gates from one test fixture that supplies the real app, authenticated test
   headers, expected security schemes and explicitly public operations; they need no sample
   resource or bearer adapter. Public operations have empty effective
   security and run without identity headers. Protected operations declare problem-shaped 401
   and the integration's applicable failures (such as verifier-outage 503). Empty API documents
   fail the rules gate. Existing APIs retain their contract,
   including added routes, until an authorized migration.
5. **Exercise the document:** Schemathesis sends valid/invalid inputs and rejects undocumented
   responses and 500s. FastAPI runs in-process; Go runs the `st` CLI against the real handler
   ([FastAPI](./fastapi.md#tests-and-runtime), [Go](./go.md#data-and-tests)). Supply the app's
   test identity/session with an isolated verifier or identity fixture, never a service-wide
   static token. Disable `allow-extra-parameters` and `with-security-parameters`: extra query
   parameters are ignored, and the test supplies authentication. Explicitly test stateful
   rejections such as idempotency conflicts; schema-valid does not mean state-valid.
6. **Gate compatibility:** `oasdiff breaking --fail-on ERR base.json openapi.json` compares the
   committed candidate and base documents. Accepted breaks follow [versioning](./versioning.md).

## Generated-client shapes

- **Names are API.** Unique lowerCamel operation IDs (`listThings`): FastAPI's
  `generate_unique_id_function` replaces its default; set Huma's `OperationID` per operation.
- **Named schemas:** declare `class ThingPage(Page[Thing])` in Python, `type ThingPage Page[Thing]`
  in Go. Otherwise FastAPI names the generic `Page_Thing_`, Huma uses `PageThing`, and a Go alias
  keeps its target's name. Huma drops package paths: rename colliding types.
- **One schema per model:** FastAPI uses `separate_input_output_schemas=False` to avoid
  `Thing-Input`/`Thing-Output` splits. Huma disables its automatic `$schema` body property
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

Deliver runnable CI configuration for a new HTTP service or a separately scoped gate adoption;
local-only service delivery still includes it. Wire document drift, contract rules, response
checks and base compatibility comparison into that workflow; load `ci-actions` to write it.
Tests and comparison run from the service root. Check out with `fetch-depth: 0`, verify the base
commit (`git rev-parse --verify "origin/$BASE_REF^{commit}"`), then derive the repository-relative
document path from `git rev-parse --show-prefix` so `git show` reads the same document from the
base. A missing first-service document differs from an unavailable base revision; do not silently
skip the latter. An existing service uses its canonical specification path. Keep its existing
or equivalent drift, contract, response and compatibility checks effective.

The first document skips only the comparison when the base has no document; keep the other
gates wired. Report the workflow path, local check results and whether CI actually ran. A missing
workflow leaves delivery incomplete; a prepared workflow with no remote run remains unverified.
