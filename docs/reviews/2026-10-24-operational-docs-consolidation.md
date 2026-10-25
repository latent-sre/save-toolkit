# Operational documentation consolidation

[verified] Base: `e8b8ec3d30419e439260f6e2f66e42a895716e04`. The candidate combines
`operational-learning`, `runbook`, and `postmortem` into `operational-docs`; the fleet goes from
27 skills to 25. Independent source review found no material regression. All six assets retain
their original Git blobs; the importer changes only its generated reference wording. Historical
audit findings remain unchanged, with removed-source links pinned to their recorded revisions.

[verified] Canonical bundle size is 81,525 → 80,306 bytes (1,219 removed, 1.5%). Discovery
descriptions are 1,620 → 637 bytes. The new entrypoint is 3,632 bytes and loads conditional methods;
its size alone is not the invocation cost. Shared guidance makes some individual runbook and
postmortem loads larger than their former standalone skills. The main gain is fewer overlapping
entrypoints, not a large total-content reduction.

## Verification

[verified] Focused importer, schema, asset, caller, adapter, eval and document checks: 440 passed,
1,536 subtests. The default suite initially caught one additional old template path in
`evals/test_build_probe.py`; after repair, 3,591 passed, 82 skipped and 4,272 subtests passed in
19.46 seconds. Receipt: `.git/local-test-runs/20261025T043514Z-1ddd368b/` in the common Git
directory. Ruff lint/format and mypy passed. Scenario validation reports 381 specs and 2,166
expectations. No harness, oracle, tool grant or delegation edge changed.
Gate A passed after adding its required direct links to the moved assets and converter.

## Native discovery evidence

[verified] Measured canonical plugin digest:
`ae7aa8e238af3bcb10eea9e298af32ce5886fd42d31cb529c3e3cc1db1d857a6`.
Claude Code 2.1.310 on unelevated Linux, resolved model `claude-sonnet-5-5`, one trial per case.
These are bounded smoke checks, not repeated acceptance trials or a held-out evaluation.
Private records remain under `.eval-runs/operational-docs-20261024/`.

| Case | Description-candidate label | Result |
|---|---|---|
| Resolved-incident runbook update | `operational-docs-final-runbook` | PASS 1/1 |
| Explicit postmortem request | `operational-docs-template-postmortem` | PASS 1/1 |
| Ownership lookup | `operational-docs-final-lookup` | PASS 1/1 |
| Retrospective intake | `operational-docs-template-intake` | PASS 1/1 |

[verified] Retrospective intake failed to invoke the combined skill on three earlier description
variants (`262eee8a…`, `50a50390…`, `7a4c3478…`), while the unchanged incumbent selected
`postmortem` in its one comparison run. Adding synonyms alone did not repair selection. The final
description names repository template/evidence rules and retrospective intake; that fresh trial
selected the combined skill. The earlier failures remain in their saved labels. This is a
sequential repair comparison, not proof of a stable success rate.

[verified] The fleet-failure negative remains a measurement gap: the initial combined run was
inconclusive after a denied `Glob`; a second combined run and the unchanged incumbent both hit
the three-turn limit without dispatching `agent-engineer`. Neither loaded the documentation
skill. The final description was not rerun on this negative. No permission or turn limit was
relaxed to manufacture a pass.

[unverified] Routing success establishes completed skill invocation, not conditional-reference
loading or authored quality. Restricted routing tools prevented some subsequent reads. Human
acceptance of the exact candidate and broader model adherence remain separate.

[verified] After these trials, the entrypoint gained direct asset/converter links required by
the bundle gate; description and method instructions stayed unchanged. Final source digest:
`2a5f74d2776e353049544e4454bc0cb2c211e13c2e561fb828398eac3f6160ba`.
The native trials were not repeated for that link-only packaging repair.

## Document fixture

[verified] `build-scribe-postmortem-unknown-metadata` loaded the postmortem reference and combined
skill, changed only the requested retrospective, executed no commands and made no commits (5/6
checks). The first run was inconclusive because the oracle's `python` was absent from PATH.
With the project interpreter on PATH, the next run failed the exact follow-up-row assertion:
the existing `FUP-74` gained a tracking-note suffix, and proposed `FUP-74-A/B/C` rows also matched
the oracle's ID search. The original question, owner, due date, open status and completion proof
were retained. This is a FAIL, not full artifact acceptance; neither the oracle nor candidate
method was weakened to erase it. Labels: `operational-docs-document` and
`operational-docs-document-interpreter` on the measured plugin digest. The unchanged incumbent
also failed its document fixture, on a different assertion (`fixture supplies no verified claims`;
label `incumbent-document`). These single trials establish neither equivalent authored quality
nor that the follow-up formatting difference was introduced by consolidation.
