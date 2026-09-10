# ADR: The grader registry is eight graders

- **Date:** 2026-09-04
- **Status:** Accepted 2026-09-04
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** fleet weight review — eval harness consolidation
- **Supersedes:** the registry list in
  [`2026-09-03-one-eval-runner.md`](2026-09-03-one-eval-runner.md) ("The grader registry is nine
  graders") — that list only.
- **Does not supersede:** anything else in that ADR. One runner, three scenario kinds, the retirement
  of the three bespoke graders, the survival of the trivial `contains_*`/`not_contains` graders, and
  the rule that routing scenarios carry no response graders all stand unchanged.

## Context

The nine-grader list named `embedded_exact_json` — a variant that pulled a JSON object out of
surrounding prose before comparing it. No scenario in the corpus used it:

```
$ git grep -c embedded_exact_json origin/main -- evals/scenarios/
$ echo $?
1
```

The same grep over the whole tree found it only in `evals/graders.py`, its own test, `evals/README.md`,
the CHANGELOG, the one-eval-runner ADR, and two already-archived scenarios under
`archive/incident-autonomy/`. It was registry surface with no caller.

## Decision

We will carry eight graders: `rubric`, `exact_json`, `exact_fields`, `regex`, `not_regex`,
`contains_all`, `contains_any`, `not_contains`. `embedded_exact_json` retired on 2026-09-04.

The maintainer's merge of PR #232 is the acceptance of this decision.

## Consequences

- A scenario that needs a JSON object read out of prose must instead say so in its prompt and use
  `exact_json`, or a new grader must be added under a new accepted decision.
- The archived incident-autonomy scenarios reference a grader the live registry no longer has. They
  are parked, not runnable, and this does not change their disposition.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>". -->
