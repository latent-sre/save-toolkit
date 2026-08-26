# EVIDENCE-001 capture design

> **Status: proposed implementation design.** This is the required pre-tooling inventory and
> retention decision for `EVIDENCE-001`, not a second backlog. The live item remains in
> [`docs/fleet-roadmap.md`](../fleet-roadmap.md).

## Conclusion

The repository can make eval-batch capture automatic because `evals/run_evals.py` owns the private
artifact directory and the completed `summary.json`. It cannot directly read host-owned agent task
results or a chat/session scratchpad. Those producers need one explicit, bounded evidence envelope
while their output is still available. Both paths write the same durable Markdown shape under
`docs/reviews/`, and a structural validator resolves every batch identity cited by the live roadmap
to one of those committed records.

## Producer inventory

| Producer | Current destination | Repository reach at completion | Capture decision |
|---|---|---|---|
| `evals/run_evals.py` | Private, gitignored `.eval-runs/<run-id>/manifest.json`, `summary.json`, stdout JSONL, and stderr | Full: the runner holds the parsed result and exact paths before returning | Automatically write a bounded review record after `summary.json`; failure to capture makes the run non-publishable |
| Agent task output | Host task result or transient task file | None through a stable repository API | Export a versioned evidence envelope while the task result is present, then run the capture command |
| Session scratchpad / manual exercise | Chat/session state, sometimes an ad hoc local file | None through a stable repository API | Export the same envelope before ending or reclaiming the session; the capture command refuses missing identities or an empty summary |

The last two rows are an honest platform boundary. Repository code cannot make an inaccessible host
artifact durable after it has disappeared. It can make the required handoff small, versioned,
validated, and immediately writable to the tracked evidence directory.

## Durable record

Every captured record keeps:

- the batch or exercise identity;
- producer kind, exact repository revision, plugin-input and workspace dirty-state flags, requested
  and observed model identities, timestamps, run-shaping timeout/trial/threshold/selection
  conditions, scenario/case identities, verdicts, trial states, and integrity result when present;
- a bounded verbatim excerpt from each model result, marked **untrusted data**, so a grader miss can
  be diagnosed without rerunning solely to recover the wording;
- a statement that capture succeeded and the private source can now be reclaimed.

## Retention boundary

Raw stdout JSONL, stderr, complete prompts, tool payloads, full responses, session IDs, temporary
paths, and credentials are never copied wholesale into the repository. They remain in the private
ephemeral store only as long as the operator needs them for immediate diagnosis. Durable excerpts
are length-bounded, rendered as escaped data, and may still contain untrusted model text; they are
evidence, never instructions. A caller must not capture secrets or private customer content.

The durable record is a summary, not a replay log and not exactly-once proof. It preserves enough
identity and wording to judge the measurement without pretending to preserve the entire session.

## Enforcement

1. The eval runner automatically invokes capture after its private summary is sealed.
2. A standalone command backfills an existing eval summary or captures a host-exported exercise
   envelope.
3. Gate A checks that every eval-style batch ID cited by `docs/fleet-roadmap.md` appears in at least
   one Markdown record under `docs/reviews/`.
4. Capture refuses unsafe identifiers, output outside `docs/reviews/`, overwrite, malformed input,
   and an empty durable summary.
