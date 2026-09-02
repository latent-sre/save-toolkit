# Durability and lifecycle

Read this when a run outlives a process, contains a cycle, must resume or replay, can be cancelled
or superseded, or will be migrated to a new build while in flight. Durability is a set of
identities and a recovery model, not a checkbox called "persistence".

## Contents

- Identities and durability mode
- Two recovery models
- Compatibility and migration
- Fork and supersession
- Cancellation: cooperative and durable
- Pause, resume, restart
- Cycles and termination
- Store operations
- Failure modes this section exists to catch

## Identities and durability mode

Section 10 of the artifact states:

| Field | What it must say |
|---|---|
| Run / thread / checkpoint identity | Distinct IDs; a resumed run keeps its run ID and gains a new attempt ID |
| State and checkpoint schema version | Versioned independently of the code build |
| Durability mode | `none`, `in-memory`, `persist per node`, `persist per effect boundary`, or `event history` |
| Checkpoint boundary | Whether the checkpoint lands before or after each node class — an effect node checkpointed only after dispatch is the at-least-once window |
| Last known recovery point | What a resumed run can trust and what it must re-derive |
| Resume semantics | Which nodes rerun on resume and which are skipped as complete |
| Retention and restore | How long checkpoints live and how a store is restored from backup |
| Evidence of persisted state | How the design proves a checkpoint was written, not merely scheduled |

## Two recovery models

| | Checkpoint resume | Deterministic event-history replay |
|---|---|---|
| What is stored | A snapshot of graph state at a boundary | The ordered events a workflow observed |
| What happens on recovery | Restart from the snapshot; incomplete nodes run again | Re-execute the workflow code against the recorded events; side effects are served from history |
| What must stay stable | The state schema | The code path: the same inputs must take the same decisions, or replay diverges |
| Where nondeterminism lives | Anywhere; handlers may repeat | Outside the replayed code, in activities with their own retry and idempotency |
| Typical proof | Kill-and-resume test at each boundary | Replay of recorded histories against the new build, or a shadow run |
| Common misstatement | "We replay from the checkpoint" | "The checkpoint makes activities exactly once" |

The artifact names one model per graph (or one per subgraph with an explicit boundary). A design
that mixes the vocabulary is treated as undecided, not as covering both.

## Compatibility and migration

- Pin the **code/build version** on every run and checkpoint.
- Name the **compatibility boundary**: which state or history versions the current build can
  resume or replay, and what happens to a run outside it — drain, version-gated workers that
  finish old runs on the old build, or an explicit migration step with its own verification.
- **Replay or shadow verification** precedes a build change that touches replayed code; a passing
  test suite on new inputs does not prove old histories still replay.
- **Repair policy:** who may edit persisted state or history by hand, how the edit is recorded, and
  that a repaired run carries a marker in its terminal evidence.

## Fork and supersession

- **Fork** creates a new run from an existing checkpoint with a new run ID; the parent's effects
  are not the child's, and an effect key must include enough of the run identity that a fork does
  not silently dedupe against its parent — or the design says that it deliberately does.
- **Supersession** replaces a run with a newer one for the same intent. The old run must be
  durably cancelled before the new one may dispatch effects; two live runs for one intent is the
  duplicate-effect case with a different name.

## Cancellation: cooperative and durable

State both, always:

- **Cooperative cancel** is a signal the running node observes at a named safe point. The design
  lists the safe points and the maximum time a node may run before observing one.
- **Durable cancel** persists the cancelled state so no scheduler dispatches new work for the run,
  survives a restart, and is checked at admission.
- **In-flight effects** at cancel time are waited for, or abandoned into `UNKNOWN` and reconciled;
  the design says which. Cancellation never claims to roll back a completed remote effect.
- **Late workers** that finish after cancel are quarantined with a record; their results do not
  merge.
- **Cleanup deadline:** the time by which leases are released, temporary resources freed, and the
  terminal state written, even if a worker never reports.

## Pause, resume, restart

- Pause is a durable state that stops dispatch without ending the run; resume re-checks admission,
  approval expiry, and compatibility before dispatching.
- Restart after a process loss follows the recovery model above; it does not create a new run.
- Every resumed or restarted run records the attempt lineage so an operator can see how many times
  a node ran.

## Cycles and termination

- Every cycle names its bound (iterations, elapsed time, tokens, cost) and its exit condition.
- A conditional edge back to an earlier node does not prove the exit is reachable; the design shows
  the state change that guarantees eventual exit or the hard budget that forces it.
- Section 11 of the artifact lists the termination classes with the evidence each writes: success,
  no-progress, maximum turns/iterations/time/tokens/cost, cancellation, safety stop, and detected
  unreachable exit.

## Store operations

An operable graph names the checkpoint or history store's retention, backup and restore procedure,
corrupt- or orphaned-run recovery, drift detection between run build version and current build,
replay canaries, and the disaster-recovery test that proves restore works. Existence of a backup is
not restore evidence.

## Failure modes this section exists to catch

| Defect | Symptom in the design | Correction |
|---|---|---|
| Checkpoint resume described as replay | "Deterministic replay from the last snapshot" | Pick one model; state what repeats |
| Cancel with no semantics | "The run can be cancelled" | Cooperative signal, durable state, in-flight and late-worker disposition |
| Unbounded cycle | Loop until the verifier passes | Iteration and cost bound plus a reachable exit |
| Missing terminal state | Graph ends when nothing is left to do | Named terminal nodes with required evidence |
| Two live runs for one intent | Retry submits a new run without cancelling the old | Durable cancel before supersession |
| Build drift | New build resumes an old checkpoint with a changed schema | Compatibility boundary and migration policy |
