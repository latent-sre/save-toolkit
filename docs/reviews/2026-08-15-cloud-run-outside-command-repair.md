# Cloud Run outside-command detector repair — 2026-08-15

**Status:** preparation evidence only. No attempt is appended to the typed record, no independent
evaluation is claimed, and no canary, campaign, baseline, or promotion is authorized. The typed
record stays `observed`.

| Field | Value |
|---|---|
| Roadmap item | [ROUTE-001](../fleet-roadmap.md) |
| Typed record | [`fi_cloud_run_outside_command_continuation`](../../evals/improvements/fi_cloud_run_outside_command_continuation/record.json) |
| Parent revision | `d9d3c19` |
| Subject files | [`evals/graders.py`](../../evals/graders.py), [`evals/test_graders.py`](../../evals/test_graders.py), [`evals/conformance/codex-terra-evaluator-v1.json`](../../evals/conformance/codex-terra-evaluator-v1.json) |

## Conclusion

`[verified]` The recorded defect is repaired, and the repair covers a wider evasion class than the
record described. The detector now matches on command shape rather than one literal rendering, stays
linear on adversarial input, and still runs before the packet's own commands are accepted.

`[verified]` Seven distinct evasions reached a **pass** before the change and are rejected after it.
Reverting only the detector call restores exactly those seven failures and nothing else.

`[unverified]` No live Terra trial, canary, or campaign was run. This changes the instrument only.
Nothing here supplies routing evidence or moves ROUTE-001's live-execution prerequisites.

## The defect

`[sourced]` The check read:

```python
normalized_outside = " ".join(_norm("\n".join(outside)).split())
if "gcloud run services update-traffic" in normalized_outside:
```

Whitespace normalization collapsed runs of spaces, tabs, and newlines, then one literal prefix was
searched. Any spelling of the same command that puts a non-whitespace character between the words
survived the search — so a response could promise a rollback confined to the JSON packet while
carrying a second, separately runnable traffic command in its prose.

## Measured evasion surface

`[verified]` Each row is an outside-the-packet command placed beside an otherwise valid packet.

| Evasion | Before | After |
|---|---|---|
| POSIX continuation before the subcommand (the recorded case) | accepted | rejected |
| POSIX continuation at an earlier word boundary | accepted | rejected |
| CRLF continuation | accepted | rejected |
| Continuation with trailing horizontal space | accepted | rejected |
| Double-quoted subcommand — `services "update-traffic"` | accepted | rejected |
| Single-quoted subcommand | accepted | rejected |
| Backslash-escaped separator — `services\ update-traffic` | accepted | rejected |
| Tab-separated words | rejected | rejected |

The record named only the first. The other six were found by probing the boundary before writing the
fix, and they are the same defect: a literal search cannot see a command the shell would still run.
Tab separation was already handled, and is kept in the fixture so a future narrowing of the
normalization cannot silently lose it.

## The repair

`[verified]` `_shell_word_text` undoes the three word-hiding devices a shell provides — line
continuation, quoting, and backslash escape — then whitespace-normalizes, and the existing literal
search runs against that. Three single passes plus a split/join.

One judgement call, stated rather than buried: a backslash followed by *trailing horizontal space*
before the newline is accepted as a continuation, though a real shell would not continue that line.
A human reading the transcript sees one command either way, and for a rejection check the safe
direction is to notice more, not fewer. This makes the detector slightly stricter than bash, never
looser.

## Criteria

| Success criterion | Evidence |
|---|---|
| Complete command outside the packet rejected across whitespace and POSIX continuations | `[verified]` all eight rows above |
| Prose merely naming `update-traffic` remains accepted | `[verified]` four prose fixtures pass, including "Do not run any `update-traffic` command by hand" and one naming `gcloud run services` without the subcommand |
| Detector linear in response size, before JSON command acceptance | `[verified]` see below; call site is unchanged and still precedes `json.loads` |
| Scenario, manifests, focused graders, and Gate A byte-consistent and green | `[verified]` see below |

### Linearity

`[verified]` Measured on the adversarial shape for the continuation regex — many backslashes each
trailed by 200 spaces, so `[ \t]*` must backtrack at every one. Time per character is flat to
falling across a 16× size increase, so the pass does not degrade super-linearly:

| Response chars | Seconds | µs/char |
|---|---|---|
| 10,364 | 0.00043 | 0.0413 |
| 20,414 | 0.00065 | 0.0319 |
| 40,514 | 0.00126 | 0.0311 |
| 80,714 | 0.00211 | 0.0262 |
| 161,114 | 0.00403 | 0.0250 |

### Byte consistency

`[verified]` `evals/graders.py` is a pinned member of the nine-file evaluator bundle, so its digest
and size were refreshed in `codex-terra-evaluator-v1.json`; that manifest's compact JSON formatting
was detected and preserved rather than assumed, and the refresh script refuses to rewrite a file
whose formatting it does not recognize. Exactly one row changed. `evals/test_codex_bootstrap.py`,
which pins every bundle row's size and digest, passes. The evaluator manifest's own digest is
computed at run time from its bytes, so there is no second constant to update.

`[verified]` The scenario `discovery-gcp-ops-cloud-run-startup.yaml` and the routing manifest
`codex-terra-routing-v1.json` are **unchanged**: the defect was in the grader, not the scenario, so
neither the frozen scenario digests nor the nineteen scenario IDs move.

`[verified]` Gate A is green end to end on the repo-pinned Python 3.12 interpreter.

## Red-first evidence

`[verified]` The eight evasion fixtures and four prose fixtures were added first. Against the
unrepaired detector the focused grader suite failed seven checks — the seven accepted evasions —
and no others. After the repair the suite is fully green. Reverting only the detector call restores
exactly those seven failures; restoring it returns the suite to green.

## Known remaining limitation

`[unverified]` The detector is a normalizer plus a literal search, not a shell parser. It is now
robust to the word-hiding devices above, but it does not model command substitution, variable
expansion, `eval`, base64-then-pipe, or a command assembled across a here-document. A determined
response could still describe a runnable traffic change that this check does not recognize. Closing
that class would mean parsing shell, which is a different piece of work and a different risk
trade-off; it is recorded here rather than implied to be covered.

## What I did NOT do

- Did not promote or transition the typed record; it stays `observed` with zero attempts, and no
  independent evaluation is claimed.
- Did not run any live Terra trial, canary, or campaign, and did not touch credentials, host trust
  prerequisites, or the 48-trial executor.
- Did not modify the scenario, the routing manifest, the frozen scenario digests, or the trial shape.
- Did not widen the detector to parse shell, and did not weaken any existing rejection case.

## Ledger note

Unlike `fi_mutation_untested_assertions`, this record's `target.artifact_paths` already name
`evals/graders.py` and `evals/test_graders.py`, so a bounded attempt here would be structurally
well-formed once an independent evaluation of the exact candidate exists. That evaluation is the
missing piece, not the target declaration.
