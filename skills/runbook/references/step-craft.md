# Step craft — how procedure steps fail at 3 a.m.

Read this while writing or reviewing Procedure and Triage steps. The universal rules live in
`../SKILL.md`; they win on conflict. The [worked exemplar](../assets/runbook-example.md) shows every
pattern below in place.

These are not style preferences. Each one is a way a *correct-looking* step produces a wrong action
under pressure — when the reader is tired, half-informed, and moving fast.

## The step that ran against the wrong target

`cf restart checkout` is correct in the space you had targeted while writing and destructive in the
space the reader happens to be in. Anything that depends on ambient state — a cloud project, a
kubectl context, a CF target, a working directory, an environment variable — must either name the
target in the command or make the runbook establish it up front and say that the later steps assume
it. Pick one and be consistent; a runbook that names the target in three commands and assumes it in
five teaches the reader that both are fine.

## The expected output that only describes success

"Expected: `OK`" tells the reader nothing about the case they actually hit. Under pressure the
interesting outcomes are *partial*: four of six instances came back, the command returned but the
metric did not move, the count is nonzero but small. An expected-output line earns its place when it
lets the reader sort what they see into **worked / partly worked / failed** and points each one
somewhere. The exemplar's Triage step 2 is the shape: three observed states, three destinations.

## The step the reader arrived at out of order

Decision trees exist so readers skip. A step reachable by a jump cannot assume the side effects of
the steps above it. Either re-establish what it needs, or open with the precondition it depends on
so a reader who jumped can tell they are missing something. The failure mode is silent: the command
runs, succeeds against a half-configured state, and produces a result nobody can interpret later.

## The rollback that is not idempotent

Rollbacks run under worse conditions than the forward path — later, more tired, often after a
partial failure, sometimes twice because the first attempt's output scrolled away. A rollback that
breaks when run twice, or when the forward step only half-applied, is a rollback that fails exactly
when it is needed. Prefer converging commands that state the desired end state (`cf scale checkout
-i 6`) over relative ones (`scale down by 3`). When a step genuinely cannot be undone, say so in the
step itself — "no rollback; this is one-way" is useful, and its absence reads as an oversight.

## The destructive step with no way to look first

Before a step deletes, restarts, scales down, or truncates, the reader should be able to see what it
will hit. A dry-run flag, a `--dry-run`, a matching `list` or `get` command, or simply the query
whose result the destructive command consumes. Without one, the reader's only options are to run it
blind or to stop and improvise — and at 3 a.m. they run it blind.

## The stop condition nobody wrote

The most expensive runbook failure is not a wrong step, it is a step repeated forever. "Restart the
instance" with no bound becomes three restarts and forty minutes. Any step that might not work needs
its own exit: how long to wait, how many times to try, and where to go when it does not help. The
exemplar's Procedure step 1 carries all three in two lines.

## The placeholder that does not say where to look

`<idx>`, `<pod-name>`, `<request-id>` are fine — a runbook cannot know them in advance. What makes
them work is a pointer to where the value comes from: which command printed it, which dashboard
panel, which alert field, and whether the numbering is zero- or one-based. A placeholder without a
source is a research task handed to someone who has no time for one.

## The scope that quietly grew

A runbook answers one trigger. When a step starts with "if it's actually the database…" the runbook
has begun absorbing a second failure mode, and the reader now has to decide which runbook they are
in. Route out instead — name the other runbook and stop. The exemplar does this three times
(probe-path latency, vendor degradation, crash loop), and each exit makes the remaining procedure
shorter and more certain.

## Reviewing someone else's steps

Read the procedure as the responder, not the author, and stop at the first line where you would
have to make a judgment call the runbook did not equip you for. That line is the finding. Authors
cannot see these because they hold the context the step omits — which is exactly why the
before-you-publish readback in `../SKILL.md` is written as a reader's pass, not a checklist of the
author's intentions.
