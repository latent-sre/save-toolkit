# Authoring a drill scenario

Read this when the bundled scenario does not exercise the lanes you care about — a data-loss
incident, a security escalation, a dependency the team does not own, a multi-service failure. A
scenario is four things: a system, a fault with held-back ground truth, an evidence pack released
in stages, and packets that hand the fleet its work.

## Contents

- The rule that makes a drill evidence
- Designing the fault
- Building the system under drill
- The pack format
- Writing the evidence pack
- Writing packets
- Choosing human decision points
- Checking a scenario before you run it

## The rule that makes a drill evidence

**Give lanes evidence, never the answer.** If a packet names the cause, the drill measures
summarization. Everything a lane concludes must be derivable from what it can read: the repository,
the release diff, and the excerpts you release. Write the ground truth down before you write the
first packet — in its own `ground-truth.md` beside the scenario file, never inside a document you
will have open while composing packets — so you cannot drift toward whatever the lanes happen to
say. The separate file matters because leakage is a copy-editing accident, not a decision: a
held-back section inside the scenario file sits on screen while you write packets, and its phrases
migrate. A file you open exactly twice — once to write it, once at the postmortem — cannot do that.

Corollary: your fixtures are read as adversarially as production evidence. A number that
contradicts another number becomes an `[unverified]` discrepancy in a lane's output and eats
attention. Proofread the pack as a whole.

## Designing the fault

A fault worth a drill has these properties:

- **A wrong answer that looks right.** An aggregate dashboard that exonerates the real trigger, a
  resource metric that looks fine, a recent deploy that is *related* but not the whole story.
- **A trade-off in the mitigation.** If the fix is free, the gate is theatre. The bundled scenario
  reintroduces a smaller, previously accepted regression — so the approver has something to weigh.
- **Trigger and root cause that differ.** This is what separates a postmortem from a status update,
  and it is where the `scribe` lane earns its place.
- **A durable fix with more than one part.** Config plus structure plus a test plus the drift that
  would silently undo it.
- **A residue after mitigation.** Something still true at resolution — an accepted error class, a
  live/manifest divergence — so the postmortem has real known issues to carry.

Keep the blast radius to one service and one dependency unless you are specifically drilling
multi-team coordination; the packet size grows with the cast.

## Building the system under drill

Small, real, and readable in a few minutes: a service with a health endpoint, one or two
dependencies, a manifest or deployment definition, a runbook naming ownership and health criteria,
a README with the SLO, and a test suite that passes. Give it **two releases** — the incident's
"what changed" evidence is the diff, and a lane that cannot read the diff is reduced to guessing.

Put the fault in the code's structure, not in a comment. In the bundled scenario the semaphore is
held across both dependency calls; nothing says "this is the bug", and every lane that finds it
does so by reading.

## The pack format

A scenario ships as three packed Markdown documents — `service.md`, `evidence.md`, and
`packets.md` — which [`scaffold_drill.py`](../scripts/scaffold_drill.py) writes back out as real
files. Each pack is a sequence of sections:

~~~markdown
## <relative/path/of/the/file.ext>

```<optional-language>
<the file's full payload>
```
~~~

What the parser enforces, so you do not discover it at scaffold time:

- Every `## ` header must be followed by exactly one fenced payload; a bare section is an error.
- Choose a fence run **longer** than any backtick run inside the payload — four or more backticks
  around a payload that itself contains fenced Markdown. A `## ` line inside an open fence is
  content, not a new section, which is what makes packing Markdown-in-Markdown safe.
- `service.md` may carry one special section, `_previous-release.json`, which the scaffold consumes
  to build the two-release git history rather than writing it out as a file.
- `{{PYTHON}}` anywhere in `packets.md` is replaced with the `--python` argument at scaffold time.

Author a new pack directly in this shape and check it by running the scaffold itself —
`scaffold_drill.py <scenario-dir> <scratch-dir> --no-git` — rather than by reading the bundled
`packets.md` to infer the format. That file is ~27k tokens of scenario content; the format is the
four rules above, and the scaffold is the authority on whether you followed them.

## Writing the evidence pack

One file per source, each written the way the fleet actually receives it — a sanitized excerpt with
redactions marked, not a database dump. Stage the release:

| Stage | Contains | Released when |
|---|---|---|
| Opening | the alert, current platform state, recent change events, the first metric rows | with the first triage packet |
| Escalation | logs, the full metric series, the dependency's own view, the release diff | when the triage lane asks, or when your timeline's paging alert fires |
| Recovery | post-mitigation readings, alert resolutions, the dependency's own fix | after the mitigation executes |

Include at least one honest ambiguity — an annotation whose meaning is not obvious — and see
whether a lane flags it. Do not include an ambiguity you cannot explain afterwards.

## Writing packets

Every packet is the **head** of a prompt: role, drill clock, what the lane may and may not do,
the tools it does not have, and exactly what it must return. Then you append the data — the prior
lane's output verbatim, the evidence, the diff.

**Pre-write only what cannot depend on ground truth.** An opening hop — a packet whose entire data
half is evidence you staged yourself — may be written in full while authoring. Every later packet
exists at authoring time as a head only; its data half is composed at dispatch, out of what the
prior lane actually returned. The reason is not tidiness: a downstream packet pre-filled "so the
chain reads well" necessarily contains what the earlier lane *should have concluded*, and that is
the answer. One authored scenario leaked its fix mechanism this way — the packets read naturally,
and the drill they described would have measured nothing past hop two.

**Scope the chain to what the artifacts can support.** A hop needs its inputs to exist: the service
file it inspects, the evidence it receives, the output of a hop that will really run. If an
artifact is deferred, the honest move is to cut the hops that need it, not to mark them "do not
dispatch" and call the scenario done — a chain half of which cannot be dispatched is half a
scenario, and the lane count on its card is a fiction. A scenario is finished when every hop in it
can be dispatched today.

Rules learned the hard way:

- **Carry, do not reference.** "Your earlier packet is on record" means nothing to a fresh session;
  it will re-derive or lose the state. Append the bytes.
- **Name the non-actions.** "You cannot run `cf`; record what you could not verify" produces
  better evidence than silence, because the lane states its gaps instead of implying capability.
- **Ask for one thing per hop.** A packet that asks for triage *and* a gate packet gets a worse
  version of both; the fleet's own methods assume one owner per handoff.
- **Bound the cycles you create.** A review/fix loop terminates because your packet says "one
  bounded fix round", not because anything in the fleet stops it.
- **Substitute placeholders.** `{{PYTHON}}` and any path token must be real before dispatch.

## Choosing human decision points

Three to five, each a decision the fleet must not make for itself: the mitigation approval (with
the exact command bound), any confirmation the gate flags as unknown, the resolution call, and the
merge. Answer them as the owner would — including rejecting one, at least once across drills, to
see whether the fleet handles a "no" as cleanly as a "yes".

## Checking a scenario before you run it

- Ground truth written down in its own `ground-truth.md` and absent from every packet — grep the
  packets for its distinctive phrases, because you will not spot your own wording by rereading.
- No downstream packet contains a conclusion a lane is supposed to reach; only opening hops are
  pre-written in full.
- Every hop is dispatchable today — its artifacts exist, and nothing is marked "do not dispatch".
- Evidence supports each conclusion you expect, without stating it.
- The release diff shows the change and nothing that gives the game away.
- Tests pass on the shipped revision.
- Each pack parses: run `scaffold_drill.py <scenario-dir> <scratch-dir> --no-git` and read what it
  materialized.
- Each packet names its lane's tool grants and non-actions, and ends where the data begins.
- Every placeholder is substituted.
- You can say, in one sentence, what the drill would prove if it went perfectly — and what it
  would prove if the fleet failed.

Reference-read token: q_idauth_4b28
