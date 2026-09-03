# ADR: One eval runner, three scenario kinds

- **Date:** 2026-09-03
- **Status:** Accepted 2026-09-03
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** fleet weight review — eval harness consolidation
- **Supersedes:** nothing
- **Does not supersede:**
  [`2026-09-01-rubric-judge-evaluation-contract.md`](2026-09-01-rubric-judge-evaluation-contract.md)
  (that contract stands unchanged: structure is graded deterministically, natural-language policy is
  judged by a calibrated rubric judge, and neither promotes anything),
  [`2026-08-22-agent-discovery-calibration.md`](2026-08-22-agent-discovery-calibration.md)
  (agent-target routing remains calibration-only), or
  [`2026-08-23-retire-codex-distribution-target.md`](2026-08-23-retire-codex-distribution-target.md)

## Context

The harness had grown to roughly 14,000 lines of Python around a 51-scenario corpus and 300 KB of
agent and skill markdown. Two runners had accumulated side by side: `run_evals.py` (2,457 lines) for
routing and text contracts, and `build_probe.py` for fixture-backed outcome probes. They shared a
clean-room module, a grader registry, and a judge, but each carried its own trace parser, its own
tool-boundary check, and its own provenance.

A review of what the second runner actually spent its lines on found most of them serving provenance
ceremony rather than the reading of transcripts:

- **A parent bootstrap** copied the whole suite to a digest-verified temporary image and re-executed
  `python` against it, to guard against edits made to the suite mid-run — a condition the in-process
  digest check already detected.
- **A Windows ACL / POSIX mode verifier** spawned PowerShell and `icacls` per artifact to read back
  a permission boundary that the creation mode had just set.
- **A durable-record capture** wrote a Markdown packet into `docs/reviews/` on every run, under a
  contract (`CONTRIBUTING.md`) that a packet is kept only while something cites it. Nothing enforced
  citation, no generated packet survived in the tree, and history showed ~25 of them added and later
  deleted. Every run was producing a file the policy then required a human to remove.
- **Reference-bearing trials** — a snapshot-scoped read grant, a read-tracing pass, and an external
  denied-probe sentinel — served three of fifty-one scenarios.
- **`routing.scope: root`** and its nested-ownership lineage resolver had no user: the scenarios that
  used it were retired in the 2026-09-01 corpus cut and the code outlived them.
- **Dead fields** were recorded per trial and never read: `context_sha256` was never assigned,
  `accepted_resolved_model` had no caller including tests, `reasoning_effort` was threaded seven
  levels deep and always `None`, `fixture_sha256` was the SHA-256 of a constant string, and
  `policy_sha256` was written to results and never read back by anything in the repo.
- **`engine_adapters.py`** was a polymorphic adapter class with exactly one implementation. Codex was
  retired as a distribution target on 2026-08-23 and the multi-engine ADR was superseded; no
  `--engine` flag, no `engine:` scenario key, and the recorded engine was a hardcoded string.

The corpus had drifted from its own documentation. `evals/README.md` described the standing
regression as fifteen direct scenarios graded by one of six structural graders; the measured corpus
held eleven, and two of the six named graders were used by no direct scenario at all — each was the
sole user of one bespoke 50–190-line grader, and both of those scenarios were calibration-only.

## Decision

**One runner, `evals/build_probe.py`, grading three kinds of scenario.** The kind is decided by the
keys a spec carries, not by a `mode` field:

| Kind | Session | Graded on |
|---|---|---|
| routing | main session, `--tools Skill,Task` (a spec may widen it), no `--agent` | one check: did the named component complete a non-error invocation — or, for a negative, stay out of the way |
| contract | `agent:` pinned with `--agent`, or `skill:` pinned by instruction | `graders:` over the returned text |
| build | `agent:` pinned with its real tools pre-approved, in a seeded fixture repo | `checks:` over outcomes in code |

`run_evals.py`, `engine_adapters.py`, `scripts/capture_measurement_evidence.py`, and their tests are
deleted. What survived the adapter moved to where it is used: the empty-MCP literal and the tool
deny list to `clean_room.py` (the leaf module all callers already import), and the read-path boundary
check into the runner, where it now fires for any trial that was granted read tools.

**The grader registry is nine graders**: `rubric`, `exact_json`, `embedded_exact_json`,
`exact_fields`, `regex`, `not_regex`, `contains_all`, `contains_any`, `not_contains`. The three
bespoke graders retire. `cloud_run_rollback_packet` (191 lines) and `json_artifact_statuses` (51)
retire with their single calibration scenarios. `learning_loop_promotion` becomes `exact_json`: its
contract is fourteen exact key/value pairs, which is exactly what `exact_json` asserts, so the only
behavioural change is that the scenario prompt no longer permits a JSON fence.

The three trivial `contains_*`/`not_contains` graders stay. They are six lines each and are still
used by contract scenarios; the standing rule against keyword lists governs what new scenarios may
be *authored* with, and rewriting forty existing files to satisfy it would have been churn without a
change in what is measured.

**Routing scenarios carry no response graders.** A routing trial answers one question. Grading its
prose as well conflated "did the right lane pick this up" with "did the lane phrase its answer the
way a regex expects", and produced reds that named the wrong defect.

## Consequences

- The harness drops from 13,939 to roughly 6,000 lines of Python; the corpus from 51 to 49
  scenarios, plus the 10 build probes, under one `--validate`.
- **Equivalence was proven at trace level before the deletion, not asserted.** Six scenarios (two
  routing positives, one routing negative, and three contracts including a rubric-graded and an
  `exact_json` one) were run twice each through the old runner on Sonnet; the resulting raw traces
  were then graded through the new path. All 22 comparable check-verdicts matched, including a
  routing FAIL and an `exact_json` FAIL — both directions, not only agreement.
- The two deleted scenarios were both discovery/calibration, so the standing regression is unchanged
  by their loss.
- `--split` is no longer wired into scenario selection. It survives as a field a reader can filter
  on; selecting a slice is `--scenario <id>`. The previous behaviour let
  `--split regression --mode discovery` select eighteen routing positives that the README described
  as description-change checks — the field and the documented cadence disagreed, and the field won
  silently. Stating the cadence and dropping the selector removes the ambiguity rather than encoding
  one of the two answers.
- Provenance keeps what makes two runs comparable — model requested and resolved, plugin commit,
  input dirty state, source digest, trials, timeout, threshold, duration, cost, exact argv — and
  drops the rest. Artifacts stay owner-only under `.eval-runs/`; nothing is written to
  `docs/reviews/` automatically. A review quotes the numbers it relies on.
- The read-path guarantee is narrower than it was and now applies where reads are actually granted,
  rather than being carried by a boundary object that only one caller constructed.

## Reopen conditions

- A second engine becomes a distribution target, which would reopen the adapter question — under a
  new accepted decision naming the consumer, the regression, an owner, and a fixed budget.
- A routing regression is traced to a defect that per-scenario prose grading would have caught and
  the single routing check did not.
