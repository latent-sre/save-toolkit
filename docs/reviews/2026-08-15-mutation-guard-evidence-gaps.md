# Mutation-guard evidence gaps — attempt-1 preparation, 2026-08-15

**Status:** preparation evidence only. No attempt is appended to the typed record, no independent
evaluation is claimed, and no promotion, merge, or monitoring is authorized by this packet. The
typed record stays `observed`.

| Field | Value |
|---|---|
| Roadmap item | [MUTATION-001](../fleet-roadmap.md) |
| Typed record | [`fi_mutation_untested_assertions`](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/evals/improvements/fi_mutation_untested_assertions/record.json) |
| Candidate revision | `82333f42c9c1f55286632f0ad4fdad3fba45a5ff` |
| Parent revision | `c556255f67a7da5e1427943a5f64ffa38fe371ef` |
| Authoring lane | `prompt-engineer` |
| Subject files | [`scripts/mutation_guard.py`](../../scripts/mutation_guard.py), [`scripts/test_mutation_guard.py`](../../scripts/test_mutation_guard.py) |

## Conclusion

`[verified]` All three control defects that the 2026-08-07 independent verification left open are
repaired at the candidate revision, each behind a regression that fails when — and only when — its
own fix is reverted. The mutation operator set is unchanged, and the narrowing of the unexercised
rule does not delete it: a genuinely unexercised inferred pair still collapses on an unbounded run,
pinned by its own test.

`[verified]` Reverting each fix in isolation fails exactly its own test class and nothing else. The
restored tree is green on the focused suite, and Gate A is green end to end.

`[unverified]` Whether these repairs are the *right* repairs, and whether the narrowed collapse rule
is well calibrated against the fleet's real corpus, has not been independently assessed. That
judgement is the evaluation this packet exists to request, not to supply.

## What was open

The verification run at `8f0c81ae992f742c1edfe272dc6b4d63746c74a9` returned `pass` on all seven
checks and, in the same run, recorded three defects in the control as found-but-not-fixed. They are
quoted verbatim in the record's `limitations` and are the whole of MUTATION-001's scope. Nothing
else in the guard was touched.

## The three repairs

### D1 — a sampled all-survivor result could claim a module is never exercised

`[sourced]` The collapse rule read `survivors and len(survivors) == tried and subject.origin ==
"literal"`. Under `--limit`, `tried` is the **sample size**, not the mutant population, so "every
mutant survived" degrades to "every mutant I happened to sample survived" — and the tool printed
`the test probably never exercises it` on that basis. Narrowing the rule to inferred subjects had
reduced the blast radius without closing the mechanism.

`[verified]` The collapse now additionally requires an unbounded run. Bounded runs report the
survivors they actually observed instead of a negative claim about mutants nobody ran. The message
itself now states the run was unbounded, so a reader cannot mistake its basis.

The regression builds a repository where a literal-origin subject is genuinely exercised — its
`pinned` function is fully contract-pinned, so an unbounded sweep kills those mutants — but whose
mutant at walk index 0 is a survivor. `--limit 1` selects exactly that index. Before the fix the
module was reported unexercised; after it, the survivor is reported as the survivor it is.

### D2 — an invalid `--limit` was indistinguishable from a refused dirty tree

`[sourced]` `parser.error()` exits 2, and `EXIT_REFUSED` is 2. In a tool whose stated design is that
a collapsed exit status cannot tell "refused to run" from "ran and proved nothing", "you typed the
flag wrong" and "this tree is dirty, I will not run" shared one status. The collision was wider than
the negative limit that surfaced it: every argparse usage error took the same path.

`[verified]` `--limit` is now parsed by a type function that rejects negatives and non-integers, and
every argparse usage exit is remapped to a distinct `EXIT_USAGE = 4`. `--help` still exits 0 — the
remap is scoped to argparse's error status, and a test pins that it does not capture help.

### D3 — the sampling docstring invited the wrong inference

`[sourced]` The docstring said a *prefix* budget would silently exclude the motivating mutant at
index 35 of 48. Stating only the prefix failure invites the reader to conclude that the evenly
spaced sample includes it.

`[verified]` It does not. Over the same 48 sites, `--limit 12` selects indices
`0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47` — bracketing 35 without ever selecting it. Both the
module docstring and the `mutants` docstring now say that a bounded sample can miss any given
mutant, the motivating one included, and that only an unbounded run tries every one. The
demonstration is executable, not prose: a regression reproduces the 48-site population and asserts
the exact chosen indices.

## Red-first evidence

Each fix was reverted in isolation against the candidate tree, the focused class re-run, and the
file restored from an unmodified copy.

| Reverted fix | Test class run | Result |
|---|---|---|
| D1 — collapse no longer requires an unbounded run | `SampledCollapseTests` | `[verified]` 2 of 4 failed |
| D2 — `EXIT_USAGE` set back to 2 | `ExitStatusTests` | `[verified]` 2 of 5 failed |
| D3 — sampling docstring restored to the prefix-only claim | `SamplingHonestyTests` | `[verified]` 1 of 3 failed |
| none (restored tree) | whole file | `[verified]` green |

`[verified]` Before any fix existed, the same suite failed in exactly these places and nowhere else:
the two `SampledCollapseTests` assertions above, the two `SamplingHonestyTests` docstring
assertions, and the four `ExitStatusTests` cases that reference the then-absent `EXIT_USAGE`.

Two of the new tests are deliberately *not* red-first, and are marked here so nobody reads them as
defect proof. `test_the_same_pair_is_provably_exercised_on_an_unbounded_run` pins the premise of the
D1 regression — if `pinned` ever stopped being contract-pinned, the module really would be
unexercised and the D1 assertion would prove nothing. `test_an_unbounded_run_still_collapses_a_
genuinely_unexercised_pair` pins that the narrowing did not delete the rule.

## Structural and mutation evidence

`[verified]` Gate A is green end to end on the candidate, run on the repo-pinned Python 3.12
interpreter. `[verified]` The focused mutation-guard suite is green on the restored tree.

### The load-bearing mutant is still killed

`[verified]` The motivating mutation the record cites is generated at the same coordinate and is
still detected at the candidate revision:

| Property | Observed |
|---|---|
| Population | 48 mutants of `skills/operational-learning/scripts/packet_drift.py` |
| Index | 35 |
| Site | `packet_drift.py:405`, `return 1 if (findings and args.fail_on_drift) else 0` |
| Operator | drop operand 0 of `And` |
| Baseline (unmutated, normalized) | `test_packet_drift.py` passes |
| Mutant | `test_packet_drift.py` fails — **killed** |
| Module afterwards | restored byte-identical |

The baseline line matters: without it a suite failing for an unrelated reason would score the mutant
killed and prove nothing. This was run as a targeted single-mutant check rather than a full sweep of
that module — the claim under test is about one named mutant, and a 48-mutant sweep across three
discovered pairs would have been a slower route to the same answer. That is a deliberate narrowing,
stated here so the evidence is not read as a full-module result.

### The guard turned on itself — discovered, not fixed

`[verified]` An unbounded sweep of `scripts/mutation_guard.py` against its own suite reported
**31 surviving mutants of 72**, exit `EXIT_SURVIVORS`. This is a measurement of the guard's own test
coverage, not a regression introduced by this candidate, and it is **not** in MUTATION-001's scope —
the item is scoped to the three recorded defects with no expansion of the operator set. Recorded
here for an owner to route, following the precedent this record already set for the earlier sweep's
findings.

Reading the survivors:

- **Equivalent or near-equivalent, no action implied:** the two `@dataclass(frozen=True)` flips, the
  `text=True` / `check=False` keywords on the subprocess call, an f-string fallback in the summary
  line, and `bool(survivors) and len(survivors) == tried`, whose guard operand is redundant whenever
  `tried > 0`.
- **Real gaps in the guard's own suite:** the mutation-generation internals and the discovery
  predicates are barely pinned, and the `unverifiable or unexercised` expression on the findings
  path has no case covering findings *and* unexercised together.
- **Not a gap:** on the no-findings reporting branch, only the `unverifiable` and `not attempted`
  operands survive. Dropping the `unexercised` operand is killed — by the test added here for the
  narrowed collapse rule. That is the operand that matters on that line.

## Ledger disposition — why no attempt is appended

`[verified]` The typed record declares `target.artifact_paths` as `AGENTS.md` and
`scripts/gate_a.py`; this candidate touches neither. The
[improvement lifecycle](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/skills/agent-authoring/references/improvement-lifecycle.md) required
that every declared target path be touched by the net candidate diff, so an attempt appended against
the current target declaration would be malformed. Re-declaring the target to name the control and
its test is a rescope, and rescoping is an owner decision, not an authoring one.

`[verified]` Independently of that, an attempt's evaluation must be a fresh evidence envelope
produced outside the authoring checkout. This packet is the author's own execution evidence. The
record's own limitations already state the standing rule: self-asserting attempt fields would be the
same bulk self-approval this fleet rejects.

So the repair is prepared and evidenced, the record's `limitations` gains an append-only entry
pointing at this packet and the candidate revision, and the transition stays where it belongs.

## What I did NOT do

- Did not promote, merge, or transition the typed record; it stays `observed` with zero attempts.
- Did not append an attempt, a review verdict, an evaluation envelope, or `actual_usage`.
- Did not rescope `target.artifact_paths`, and did not rewrite any prior limitation entry.
- Did not expand the mutation operator set, change `DEFAULT_LIMIT`, or alter the even-spacing
  sampling algorithm — only the claim the tool is willing to make from a bounded run.
- Did not fix the unrelated coverage gaps the earlier bounded sweep surfaced (`migrate_v1_to_v2.py`,
  `migrate_v2_to_v3.py`, `clean_room.py`, `evidence_envelope.py`, `graders.py`). They remain
  recorded, unowned by this record, and untouched.
- Did not make the guard a Gate A step; it remains a deliberate run, and its own test still pins
  that.

## Honest limits

- This is the author's execution evidence from the authoring checkout. It is not a fresh-context
  evaluation and carries none of that authority.
- The guard remains a sampling tool with a small operator set. A clean report still means "no
  survivor among the mutants tried". These repairs make the tool's *claims* match that limit; they
  do not remove it.
- `[unverified]` The candidate was exercised on Linux only in this session. The macOS and Windows
  Gate A jobs on the exact candidate are still owed before promotion.
- `evals/test_clean_room.py` fails on this container under Python 3.11 because
  `shutil.rmtree(onexc=...)` is 3.12+. It fails identically on an unmodified tree, is unrelated to
  this change, and passes on the pinned 3.12 interpreter.
