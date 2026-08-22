# Cloud Run outside-command detector repair — 2026-08-15

**Status:** preparation evidence only. No attempt is appended to the typed record, no independent
evaluation is claimed, and no canary, campaign, baseline, or promotion is authorized. The typed
record stays `observed`.

| Field | Value |
|---|---|
| Roadmap item | [ROUTE-001](../fleet-roadmap.md) |
| Typed record | [`fi_cloud_run_outside_command_continuation`](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/evals/improvements/fi_cloud_run_outside_command_continuation/record.json) |
| Parent revision | `d9d3c19` |
| Subject files | [`evals/graders.py`](../../evals/graders.py), [`evals/test_graders.py`](../../evals/test_graders.py), [`evals/conformance/codex-terra-evaluator-v1.json`](../../evals/conformance/codex-terra-evaluator-v1.json) |

## Conclusion

`[verified]` The recorded defect is repaired, and the repair covers a wider evasion class than the
record described. The detector now matches on command shape rather than one literal rendering, stays
linear on adversarial input, and still runs before the packet's own commands are accepted.

`[verified]` **Twelve** distinct evasions reached a **pass** before this work and are rejected
after it: seven found by probing the boundary, two by mutation-sweeping the repair itself, and three
by code review on the pull request. Five of the twelve — the last two groups — were live bypasses in
*versions of this repair*, not in the original detector alone. A hand-built mutant set for the
normalization, code the guard's operator set cannot reach at all, killed 3 of 9 on the first version
and kills 9 of 9 now.

An earlier revision of this packet said "ten", which matched neither its own attribution sentence
nor its table. The count is corrected here rather than left as an unsupported `[verified]` claim.

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

| Evasion | Before | After | Found by |
|---|---|---|---|
| POSIX continuation before the subcommand | accepted | rejected | the record |
| POSIX continuation at an earlier word boundary | accepted | rejected | boundary probe |
| CRLF continuation | accepted | rejected | boundary probe |
| Continuation with trailing horizontal space | accepted | rejected | boundary probe |
| Double-quoted subcommand — `services "update-traffic"` | accepted | rejected | boundary probe |
| Single-quoted subcommand | accepted | rejected | boundary probe |
| Backslash-escaped separator — `services\ update-traffic` | accepted | rejected | boundary probe |
| **Escape inside the executable name** — `gcl\oud` | **accepted** | rejected | **code review** |
| **Escape inside the subcommand** — `update\-traffic` | **accepted** | rejected | **code review** |
| **Escape inside a command word** — `serv\ices` | **accepted** | rejected | **code review** |
| Tab-separated words | rejected | rejected | boundary probe |
| **Continuation inside a word** — `serv\`+NL+`ices` | **accepted** | rejected | **mutation sweep** |
| **Continuation inside the subcommand** — `update-\`+NL+`traffic` | **accepted** | rejected | **mutation sweep** |
| Upper-case command outside the packet | rejected | rejected | mutation sweep |

The record named only the first. Six more came from probing the boundary before writing the fix.
The bold rows came later and are the serious ones — every one was a live bypass in a *version of
this repair*, not merely in the original detector. Two were found by mutation-sweeping the fix
itself (see below); three more were found by review on the pull request, after the sweep, and are
the subject of the next section.

Tab separation and the upper-case case were already handled; both are kept as fixtures so a future
narrowing of the normalization cannot silently lose them.

## The repair

`[verified]` `_shell_word_text` undoes the three word-hiding devices a shell provides — line
continuation, quoting, and backslash escape — then whitespace-normalizes, and the existing literal
search runs against that. Three single passes plus a split/join. The continuation pass substitutes
the **empty string**, matching the shell's own joining semantics; substituting a space splits words
that a continuation joins, which was the first version's bypass.

Backslash escapes are **removed, never replaced with a space**. A backslash joins — `gcl\oud` is
the word `gcloud` — so substituting a space splits precisely the words a shell would run together.
That was the defect review found; see the next-but-one section.

Two judgement calls, stated rather than buried. A backslash followed by *trailing horizontal space*
before a newline is accepted as a continuation, though a real shell would not continue that line.
And `services\ update-traffic` is a single word to a shell, so it would not invoke the traffic
command, but dropping the escape leaves a real space and the detector rejects it anyway.
Distinguishing that needs full word-splitting semantics. Both make the detector stricter than bash,
never looser.

## Mutation sweep of the repair itself

This section exists because the first version of this repair passed every fixture above and was
still wrong. Sweeping it is what found that.

### The guard cannot see this code at all

`[verified]` `mutation_guard` generates **zero** mutants for `_shell_word_text`. Its operator set is
boolean-operand drop, comparison swap, not-removal, and boolean-constant flip; the function is pure
string transformation and contains none of them. Across all of `evals/graders.py` the population is
167 mutants at both `d9d3c19` (before this work) and at the candidate — adding the function changed
the count by nothing. Exactly one mutant exists anywhere in the new code, the `In -> NotIn` swap at
the call site, and it is killed.

So "the sweep found no survivors in the new code" is a **nearly vacuous** claim, and is recorded
that way rather than as coverage. A tool reporting clean over code it cannot mutate is precisely the
false-green this repository built the guard to detect.

### Hand-built mutants for what the guard cannot reach

`[verified]` Nine mutants of the normalization written by hand, run against the focused suite. On
the first committed version of the repair **only 3 of 9 were killed**. After the defects below were
fixed and the missing fixtures added, **9 of 9 are killed**.

| Hand-built mutant | First version | Now |
|---|---|---|
| Drop line-continuation normalization | survived | killed |
| Continuation joins with a space instead of nothing | n/a — was the bug | killed |
| Continuation pattern loses `[ \t]*` tolerance | survived | killed |
| Continuation pattern no longer anchors on the newline | n/a | killed |
| Drop quote stripping (both kinds) | killed | killed |
| Drop backslash removal entirely | killed | killed |
| Backslash → space instead of removal (the reviewed defect) | n/a — was the bug | killed |
| Drop the lowercase fold | survived | killed |
| Detector reverts to the raw literal search | killed | killed |

### Defect 1 — a live bypass in the first version

`[verified]` A POSIX continuation joins its two halves with **no separator**: `serv\`+newline+`ices`
is the single word `services`. The first version substituted a *space*, splitting the word instead
of joining it, so `gcloud run serv\`+newline+`ices update-traffic ...` — a command a shell runs
verbatim — was accepted outside the packet. The normalization now substitutes the empty string.

This is why the "drop line-continuation normalization" mutant survived: with a space substitution,
the generic backslash-to-space replacement already covered every fixture, so the whole continuation
pass was doing nothing observable. The mutant that looked like a coverage gap was reporting dead
code, and the dead code was hiding a bypass.

### Defect 2 — unreachable code presented as coverage

`[verified]` The pattern carried `\r?`. The caller splits the response with `splitlines()` first,
which consumes CR, CRLF, and LF alike and drops the terminator, so no carriage return can ever reach
the pattern. No fixture could kill that mutant because no input can take the branch. It is removed,
with the reason recorded at the definition. The CRLF fixture stays, relabelled as the input a
Windows-authored response actually produces rather than as evidence of CR handling — the earlier
comment claiming it made CR tolerance load-bearing was simply false.

### Defect 3 — escapes split words the shell joins (found by review, not by me)

`[verified]` Reported on the pull request as P1 and confirmed by execution before acting on it. A
backslash before an ordinary character is an escape the shell *removes*, joining the word:
`gcl\oud` runs as `gcloud`, and `update\-traffic` as `update-traffic`. The repair replaced every
remaining backslash with a **space**, so those normalized to `gcl oud` and `update -traffic`, the
prefix search missed them, and the conflicting traffic command was accepted:

| Outside command | Before | After |
|---|---|---|
| `gcl\oud run services update-traffic …` | accepted | rejected |
| `gcloud run services update\-traffic …` | accepted | rejected |
| `gcloud run serv\ices update-traffic …` | accepted | rejected |

`[verified]` Escapes are now removed rather than space-substituted. This is the **same
space-instead-of-nothing mistake** as Defect 1, which I fixed for line continuations and left
standing in the general escape path — I fixed half the bug and the sweep could not see the other
half, because none of it is a shape the operator set can mutate.

`[verified]` One consequence, and it corrects an earlier claim in this packet. With escapes removed,
`gcloud run services\update-traffic` normalizes to `servicesupdate-traffic`, which is *not* the
guarded command — a shell would not run a traffic change — so it is now **accepted**. An earlier
revision rejected it and called that a deliberate over-rejection; that was pinning the wrong
semantics, and the fixture has moved to the accepted set. The genuine over-rejection that remains is
`services\ update-traffic`, one word to a shell but two after the escape is dropped.

### Pre-existing survivors elsewhere in the file

`[verified]` The full sweep reports **54 surviving mutants of 167** in `evals/graders.py`. The count
and the population are identical at `d9d3c19` and at the candidate, and none fall inside the new
code, so every one of them is a pre-existing coverage gap in the other graders. They are **not
fixed** here and are not owned by this record — recorded so the number is not later mistaken for a
regression from this change.

### A harness defect worth recording

`[verified]` The first hand-built mutant harness reported `SURVIVED` for mutants whose edit had
silently failed to apply — the target strings were mangled, the file was never mutated, and the
suite passed for that reason. That is the same false-green shape in the instrument rather than the
suite. The harness now validates every target string before any mutant runs and fails loudly, and
it refuses to start unless the suite passes unmutated.

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
