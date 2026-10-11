# Frontend-craft integration record

## Scope and preservation

[verified] This integration installs the separately authored [frontend-craft skill](../../../skills/frontend-craft/SKILL.md) and its two references on a fresh branch from origin/main at acd99192140930a6b48a11c840a4f8a221f56b5b. The human owner authorized this integration, commit, and push after receiving the standalone draft.

[verified] The authoring snapshot remains outside the repository in the supplied authoring folder. Its ZIP SHA-256 is e01958fb3a56cc0b2a76d40a8d10703af349fa037793d6065992ec0775da56b8. It contains the complete draft, requirement mapping, sources, assumptions, proposed evaluations, and authoring validation evidence. The source draft files were not edited during integration.

[verified] The original authoring session already had automatically supplied repository guidance and historical memory. That exposure was disclosed before drafting. [unverified] A pristine-context independence guarantee is therefore unavailable. The new draft was written without deliberately opening prior frontend-craft files, and integration began only after the separate draft was preserved.

## Integration changes from the authored draft

- [verified] The description gains four quoted trigger phrases and YAML quoting to satisfy the repository's skill-discovery contract. The authored skill body is byte-identical after the closing frontmatter delimiter.
- [verified] Both supporting reference files are byte-identical to the authored draft.
- [verified] The prior bundle's three reference paths are replaced by the two authored references; generated adapters are regenerated from canonical sources.
- [verified] The ten fresh [evaluation scenarios](README.md) are copied into this proposal area. Their authoring-only validation link now points to this integration record.
- [verified] The evaluation index links to the proposal. No agent tools, delegation edges, runtime choices, or backend contracts are changed.

| Authored file | Preserved draft SHA-256 | Integrated canonical SHA-256 |
| --- | --- | --- |
| SKILL.md | db4bba0dfbe6c3ec20ee13945cccf98494a42de164e5a27b02623f88d61bad57 | 1eec6d2a92a9b58d74376dbcf13586cd51af3147cef26931698188b0a790aff6 |
| references/interaction-completion.md | cafb2165bee474d1636d78523c411854eb01a5c4ed2a26e4cacf6651c3ca71d6 | cafb2165bee474d1636d78523c411854eb01a5c4ed2a26e4cacf6651c3ca71d6 |
| references/implementation-decisions.md | 7fdb6c9562da8ea77127c6873659adc851fcad8b75f014216fd9dc88bd1ef232 | 7fdb6c9562da8ea77127c6873659adc851fcad8b75f014216fd9dc88bd1ef232 |

## Verification

[verified] Checks ran in the isolated integration worktree on Windows with CPython 3.14.7 and the constrained requirements-test.txt environment.

| Check | Actual result |
| --- | --- |
| Adapter regeneration | Exit 0; 173 adapter files generated; adapter validation passed. |
| Full repository suite: python -B -m pytest -q | Exit 0; 2,470 passed, 65 skipped, and 4,966 subtests passed in 1,509.63 seconds. |
| Structural gate: python -B scripts/gate_a.py | Exit 0; 2/2 steps passed. Ran once at the publication boundary. |
| Draft preservation and integration comparison | All eight original payload files match the preserved manifest. The skill body and both references match the independent draft. |
| Canonical/generated comparison | All three frontend-craft projection files match their canonical files byte-for-byte. |
| Scope and whitespace | Exactly 15 intended paths staged; staged whitespace check passed. |

[verified] The runtime and generated files were unchanged after these checks; this record was updated with their results. The skipped tests are not claimed as executed, and this Windows result does not establish other hosts' behavior.

[verified] The canonical bundle is 30,386 bytes versus 16,395 bytes in the integration base, a 13,991-byte increase. The 11,835-byte entrypoint covers the four product jobs, direction selection, and completion workflow; 18,551 bytes of conditional references cover interaction behavior and implementation decisions. This growth implements the broader product brief. The only increase from the preserved authored bundle is 129 bytes of discovery metadata.

[unverified] The ten proposed behavioral scenarios have not been executed. Their fixtures and applications have not been built. Structural checks, repository tests, and frontmatter compatibility do not establish visual distinctiveness, interaction quality, accessibility, performance, or live API behavior.

The proposed scenarios remain a reviewable specification. A future run needs explicit fixture preparation, host/model and budget choices, and human review of rendered work. This integration does not claim completed behavioral acceptance or authorize deployment.
