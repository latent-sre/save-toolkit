# A passing test that asserted the opposite of its contract

**Date:** 2026-08-06
**Observed at revision:** `dc4d3e7d6b6d355e28d4f4a6cae651e8be71f4c9`
**Scope:** One verification-integrity failure found during the ADAPT-001 round, recorded as the
exact-subject evidence for fleet-improvement record `fi_mutation_untested_assertions`. This is a
dated evidence record, not a task list; the only live tracker is [`fleet-roadmap.md`](../fleet-roadmap.md).

## What happened

`scripts/test_packet_drift.py::test_fail_on_drift_turns_a_finding_into_a_nonzero_exit` carried a
comment reading "The opt-in gate must stay quiet when there is nothing to report" and then tested
none of it. Its second half:

- never passed `--fail-on-drift`;
- never reached a no-drift state — it rewrote the evidence file back to its original content, which
  adds a *second* commit, so `git log <base>..HEAD -- <path>` still returned drift; and
- asserted `assertIn("ku_checkout", clean.stdout)`, i.e. that the packet **was** reported, never
  checking the return code.

The test passed. The suite was green. The green suite was then cited as evidence the work was sound.

## How it was confirmed

The `--fail-on-drift` contract in `packet_drift.py` was mutated from

```python
return 1 if (findings and args.fail_on_drift) else 0
```

to

```python
return 1 if args.fail_on_drift else 0
```

which makes the flag fail every clean sweep. All 16 tests in the suite still reported `OK`. The
mutation was then reverted, the test split into
`test_fail_on_drift_still_exits_zero_when_there_is_nothing_to_report`, and the mutation re-applied
to confirm the replacement kills it. Both runs are recorded in the commit message of
`dc4d3e7d6b6d355e28d4f4a6cae651e8be71f4c9`.

The finding originated with the two-lane adversarial review against
`d94300a92aa2a1b3f0152476d0bcc7280db2b0de`, as finding F3 of seven. It was not found by Gate A,
which was green throughout, and it was not found by the author.

## Why it is a fleet failure and not a one-off

[`AGENTS.md`](../../AGENTS.md) line 158 already records the same class from an earlier round:

> this repo has shipped tests that silently matched nothing after a refactor moved the string they
> keyed on.

That makes this at least the second occurrence of the same normalized behaviour — a repository test
that passes while asserting nothing about the contract it names — against the same target class
(the repository's own test suite) with the same expected result (a failing assertion when the
contract breaks). The change playbook's rule already anticipates it:

> **Added or removed a validator rule** → add a fixture or mutation test that **fails without the
> change**, and confirm it fails.

The rule is written, was followed for the production code in this round, and was not followed for
the test of a script's own CLI exit contract. Nothing mechanically enforces it, and its wording
scopes it to validator rules rather than to any newly asserted contract.

## Normalized fingerprint

The record's `failure_fingerprint` is the SHA-256 of this exact ASCII string:

```text
verification-integrity|repository-test-suite|test-passes-while-asserting-non-contract|expected-failing-assertion-on-contract-break
```

Recomputing it is therefore deterministic and does not depend on this document's byte content.

## Proposed control — not applied

A deterministic check that a named contract predicate, when mutated, causes at least one test to
fail. Whether that lands as a Gate A step, a targeted mutation corpus, or a narrower rule change in
the change playbook is an open design question owned by `prompt-engineer`, and no attempt has been
made. Recording the observation is not authorization to change the fleet.

## What this record does not claim

- It does not claim the earlier occurrence in `AGENTS.md` line 158 has an incident record; it does
  not, so the recurrence rests on one precisely evidenced instance plus that documented prior.
- It does not claim any control has been designed, evaluated, or accepted.
- It does not claim Gate A is unsound; Gate A is structural by design and never asserted this.
