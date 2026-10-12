# OpenAPI: the contract as a committed file

`../SKILL.md` owns the house contract; this file is how the document carries it. Read framework
and tool versions from the project's manifests and lockfiles, never assume them.

## The pipeline

1. **The code generates the document.** FastAPI and Huma build it from typed handlers and models.
   Nobody edits `openapi.json` by hand.
2. **The document is committed** at the service root as `openapi.json`, LF line endings. Consumers
   (the team's UIs, scripts, other services) generate clients from that file at a pinned revision.
3. **The drift test** (`test_document_matches_the_code`, `TestOpenAPIDocument`) regenerates it and
   fails on any difference. After an intended change, regenerate with `UPDATE_OPENAPI=1` or
   `-update` and review the diff as the API change.
4. **The house-rules test** fails what a generator cannot know: a path without `/v1`, a missing or
   non-lowerCamel `operationId`, an operation without security that is not listed public, an error
   response that is not `application/problem+json`, a version other than `3.1.0`.
5. **Schemathesis** drives the service from the document, with valid and invalid inputs, and fails
   on any response the document does not allow and on any 500. FastAPI runs it in-process
   (`test_schemathesis.py`); Go runs the `st` command against the real handler
   (`schemathesis_test.go`). The test token lives in the test verifier; a service never accepts a
   static token to make this work. Both run with `allow-extra-parameters` and
   `with-security-parameters` off: the test supplies the token, and a service ignores query
   parameters it does not declare, so neither an undeclared parameter nor a stripped token is
   input the document forbids.
6. **oasdiff** fails a pull request whose document breaks the base branch's:
   `oasdiff breaking --fail-on ERR base.json openapi.json`. The CI starters fetch the base
   document with `git show origin/<base>:openapi.json`.

## Shape the document for generated clients

A client generator turns names into types and functions, so the document's names are API.

- **Operation IDs** are unique lowerCamel names (`listThings`). FastAPI's default
  (`list_things_v1_things_get`) is replaced by `house.operation_id`; in Huma, set `OperationID`
  on every `huma.Operation`.
- **Schemas are named.** FastAPI names a generic `Page[Thing]` `Page_Thing_`: declare
  `class ThingPage(Page[Thing])`. Huma names `Page[Thing]` `PageThing` and an alias takes the
  target's name: declare `type ThingPage Page[Thing]`. Huma drops the package path, so two types
  named `Thing` in different packages collide; rename one.
- **One schema per model.** `separate_input_output_schemas=False` (set by `house_app`) stops
  FastAPI from splitting a model into `Thing-Input` and `Thing-Output`.
- **Nullable means present and null.** A field that is always present but may be null is required
  and nullable: Python `next_cursor: str | None` with no default, Go `NextCursor *string` without
  `omitempty`. A Go slice is nullable unless tagged `nullable:"false"`, and the handler must
  return an empty slice, never nil.
- **No framework extras in bodies.** Huma's default config adds a `$schema` property and a `Link`
  header to every body; the house config turns them off.
- **Declare what the service enforces.** Schemathesis sends every value the schema allows: a
  pattern, enum, bound or format the handler enforces but the document omits fails its
  positive-data check. An opaque cursor declares its encoding (`^([0-9a-f]{2})+$`, max 2048).
  Huma treats an empty query value as absent and skips its validation; reject a present-but-empty
  parameter in the input's `Resolve` method.

## OpenAPI 3.2-ready

3.2 is a minor release over 3.1 and the OAI states that every 3.1 document works after changing
only the version, so a document written to 3.1 is ready. FastAPI and Huma emit 3.1.0;
openapi-typescript documents 3.0 and 3.1; oasdiff, Schemathesis, Redocly CLI, Spectral and
Swagger UI 5.32 and later read 3.2. A 3.2-only construct — the QUERY method, `in: querystring`,
`itemSchema` for sequential media, tag `parent` — waits until the producing framework emits it
and every consumer's generator reads it; check both before adopting one.

Server-Sent Events are the exception already in documents: FastAPI's `fastapi.sse` declares a
stream with 3.2's `itemSchema` inside its 3.1.0 document, and openapi-typescript renders that
stream's type as `unknown` while still generating each event's data schema. The UI parses each
event's `data` as that schema (`components["schemas"]["Tick"]`) itself. Huma's `sse` package
documents a stream as an array of `oneOf` event objects instead.

## Gates in CI

The [Go](../assets/ci/api-contract-go.yml) and [FastAPI](../assets/ci/api-contract-fastapi.yml)
workflows run the tests (drift, house rules, Schemathesis), then oasdiff against the base branch.
Load `ci-actions` before changing them. An accepted breaking change follows
[versioning](./versioning.md); never weaken a gate to pass it.
