# Frontmatter grammar decision packet - 2026-08-18

**Status:** owner-approved and implemented in the candidate commit containing this packet. No push,
promotion, or independent review has occurred.

| Field | Value |
|---|---|
| Roadmap item | [SCRIPTS-001](../fleet-roadmap.md) |
| Subject revision | `a932e516f9a3af3fa0bec988336f7096cc58b567` |
| Compared readers before consolidation | [`check_links._frontmatter`](../../scripts/check_links.py), [`generate_platform_adapters.parse_frontmatter`](../../scripts/generate_platform_adapters.py), [`run_evals.expected_runtime_tools`](../../evals/run_evals.py) |
| Live syntax that constrains the decision | Folded `description: >-` scalars and the list-form `tools:` field in [`agents/researcher.md`](../../agents/researcher.md) |

## Conclusion

`[verified]` The approved candidate uses one deliberately small, standard-library parser with one
grammar and two error modes: strict raises on the first syntax failure; lenient collects
recoverable syntax failures. Callers retain ownership of their field allowlists, required fields,
and value-type rules.

`[verified]` The implementation uses the adapter reader's syntax as its compatibility baseline,
with two explicit choices: underscore-bearing keys are accepted because the adapter reader already
accepted them, and the adapter reader's scalar-list form is accepted because one canonical agent
uses it. Plain scalars remain strings, current quote and block-scalar decoding is preserved, and
duplicate keys fail in both modes. This keeps current adapter bytes stable without importing
PyYAML into `scripts/`.

`[verified]` The pinned PyYAML 6.0.3 dependency and the canonical direct-agent tool-reader path ran
under Python 3.12.11 during the containerized Gate A recorded below. The comparison table still
describes the third reader's broader library grammar from its `yaml.safe_load` call; the gate proves
the shipped inputs and tests, not every input PyYAML could accept.

## Pre-change grammars

| Surface | `check_links` | adapter generator | eval direct-agent boundary |
|---|---|---|---|
| Input | Caller-supplied text and path | Reads a path as UTF-8 | Reads one direct-agent path as UTF-8 |
| Opening and closing fence | First line and first later stripped `---`; missing fence becomes a collected failure | Same fence search; missing fence raises | Same fence search; failure becomes `RunnerFailed` |
| Key spelling | `[A-Za-z][A-Za-z0-9-]*` | `[A-Za-z][A-Za-z0-9_-]*` | Whatever `yaml.safe_load` accepts in a mapping |
| Comments | Only `#` in column 1 | Leading whitespace before `#` is accepted | Delegated to `yaml.safe_load` |
| Plain scalar type | Raw string; caller later validates YAML-string shape | String | Library-decoded YAML value |
| Double-quoted scalar | Caller decodes with `json.loads` | Parser decodes with `json.loads` | Delegated to `yaml.safe_load` |
| Single-quoted scalar | Caller requires both quotes and unescapes doubled apostrophes | Parser unwraps only when both quotes exist; otherwise preserves the text | Delegated to `yaml.safe_load` |
| `>`, `>-`, `|`, `|-` block | All four join nonblank indented lines with spaces | Same | Delegated to `yaml.safe_load` |
| `key:` plus indented `- item` | Each item is malformed; `key` remains an empty string | Accepted as `list[str]` | Accepted as a YAML sequence |
| Bare `key:` with no items | Empty string | Empty list | YAML null |
| Duplicate key | Collects a failure, then the later value replaces the first | Raises before replacement | Library behavior; caller has no duplicate-key check |
| Other malformed line | Collects and continues | Raises immediately | YAML error becomes `RunnerFailed` |
| Unknown field | Skill caller rejects against its allowlist | Agent validator rejects; generator itself does not | Only the presence of `tools` matters here |
| Body and raw lines | Returns body without preserving a terminal newline | Returns body with terminal-newline preservation plus raw frontmatter lines | Does not return either |
| Consumer scope | Canonical skills | Canonical agents, skills, and commands | Direct-agent evals only |

The grammar conflict is latent because the readers have different scopes. `check_links` never sees
the list-form `tools` in `agents/researcher.md`, while the generator and eval reader do. A shared
reader must not turn that scope accident into a new rejection.

## Approved grammar

| Decision | Approved contract | Reason |
|---|---|---|
| Grammar size | Keep the adapter reader's deliberately small YAML subset | Full YAML would add behavior and make the stdlib-only `scripts/` rule impractical |
| Error modes | `strict` raises first; `lenient` returns all recoverable syntax problems | Required by SCRIPTS-001 and preserves each caller's present posture |
| Key charset | Accept `[A-Za-z][A-Za-z0-9_-]*` | Preserves the generator's accepted syntax; caller allowlists still reject unsupported fields |
| Comments | Accept blank lines and whitespace-prefixed whole-line comments | Matches the generator and ordinary YAML layout without affecting values |
| Plain values | Keep strings as strings; do not infer booleans, numbers, nulls, or timestamps | Preserves generator values and leaves field typing explicit and reviewable |
| Quotes | Preserve `_yaml_scalar` behavior, including unmatched single quotes as literal text | Keeps the prerequisite quote-guard test green unchanged |
| Block scalars | Preserve the current space-folding behavior for all four accepted markers | Byte compatibility first; true literal-block semantics would be a separate behavior change |
| Lists | Accept only `key:` followed by one or more indented scalar `- item` lines | Supports the live researcher tool inventory without admitting nested YAML |
| Empty value | Preserve the adapter result: an empty list | One deterministic parse result; scalar-only callers will reject the type |
| Duplicate key | Syntax failure in both modes; retain the first value while lenient mode continues | Strict already fails; first-wins prevents an invalid later line steering secondary diagnostics |
| Flow/nested YAML | Treat non-list inline text as a plain scalar; do not add mappings, anchors, tags, or nested collections | Preserves current generator handling and keeps the parser auditable |
| Return shape | Fields, body with terminal-newline preservation, raw frontmatter lines, and problems | Covers every present consumer without reparsing source text |
| Caller policy | Keep allowed/required keys and value-type rules in each caller | A shared syntax reader must not merge skill, agent, command, and eval authority policies |
| Eval dependency | Replace only the frontmatter `safe_load`; retain PyYAML for scenario files | SCRIPTS-001 is not a scenario-format migration |

## Implementation

`[verified]` [`fleet_frontmatter.py`](../../scripts/fleet_frontmatter.py) now owns the grammar and
exposes strict and lenient parsing over the same implementation. Its result includes decoded
fields, body bytes, raw frontmatter lines, recoverable problems, and scalar style metadata needed
to preserve the skill caller's existing field policy.

`[verified]` `check_links`, the adapter generator/validator, and the direct-agent eval boundary now
use the shared reader. The eval runner still uses PyYAML for scenario documents and loads the shared
reader from the frozen plugin snapshot, so the measured direct-agent boundary cannot import a
mutable checkout copy.

`[verified]` The red-first contract was observed before implementation: the new parser suite failed
to import `fleet_frontmatter`, and the new link-check fixture failed because the former reader
reported list items as malformed top-level frontmatter. The implemented contract suite covers keys,
comments, plain and quoted scalars, all four block markers, lists, empty values, duplicates,
malformed lines, body preservation, both error modes, and the file entry point.

## Verification

`[verified]` Focused validation passed 11 shared-parser tests, 32 link-check tests, 38 adapter tests,
and 68 eval-runner tests. Direct link, adapter-byte, and fleet validation also passed. Gate A passed
all 40 structural steps in a disposable full clone containing the implementation and this final
documentation state. The validation container used Python 3.12.11 and PyYAML 6.0.3, with the source
mounted read-only, network disabled, Linux capabilities dropped, `no-new-privileges`, and a
non-root numeric user. The official base image was pinned as
`python@sha256:13c9584604a99ca134c4f41800f74ffc64ee6ac8cf555cf1e704a6087fc84f12`;
the dependency-bearing local image ID was
`sha256:2c22bac63f6ce8e12bc240e04918493f2e03c83c364972c03e7418d2190bc9cb`.

`[unverified]` Gate A proves structure, not correctness. Linux skipped the Windows-specific runtime
checks, and no independent correctness, security, or plan-conformance review has occurred. The
deliberate full-suite-per-mutant mutation guard has not run.

## What I did not do

- I did not edit canonical agents, skills, commands, or generated projections.
- I did not install PyYAML on the host or in the repository environment, or run a live model
  evaluation. PyYAML exists only in the local validation image described above.
- I did not run the mutation guard, perform an independent review, push, publish, or change any
  external configuration.

## Next gate

Independent correctness and security review belongs against the immutable commit containing this
packet. The mutation guard may then run against that clean revision if its cost is accepted.
