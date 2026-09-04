# runbook trim: before/after evidence (2026-09-03)

The `runbook` skill was cut from 50,817 B to 44,748 B in the candidate the trials ran, and stands
at 45,100 B in the final tree after the import test's pinned export command was restored (not
re-measured); more to the point, it was measured for the first time against its own authoring
rules. A tools-off probe of Sonnet and Opus set the cut line;
a probe-owned oracle of eleven rules, added to the existing scribe build probe, graded every trial;
and two candidates were run, the trim alone and the trim plus two template lines, because the
baseline showed two rules that the skill states in prose were not landing. Measured on the
maintainer's Windows host. Cited by the pull request and by `CHANGELOG.md`.

## Where the cut line came from

Eight claims from the bundle, put to both models with no tools (`F:/kp`, not committed)
`[verified: the two answer files on this host, 2026-09-03]`. Both models carry the craft: why an
"Expected: OK" line fails a responder and how to rewrite it with a failure branch and a time
bound, that a placeholder needs the command that produces its value, that a rollback must
converge, view HTML over storage format and the silent loss of macro elements, imported commands
arriving unverified with provenance in References. Opus reproduced `step-craft.md`'s eight
failure modes nearly verbatim. Neither model carries the team's protocol: the words held,
contradicted, and missing that the operational-learning closeout consumes; a contradicted step
dropping the runbook to draft; `last_verified` moving only on bound rehearsal evidence; three
identical manual fixes filing an automation candidate. Sonnet would bump the date on a step that
merely worked. So the trim is the craft prose, and the protocol, the template, the exemplar, and
the importer stay.

## The oracle

`probe_runbook_slots.py`, shipped by the scribe probe through `writes:` and run after the agent has
finished, makes eleven of the skill's authoring rules mechanical: the template's frontmatter key
set with `status: draft` and both dates null; every section present; an Expected line under every
procedure step and at least one that routes a partial outcome; a source for every placeholder; a
bound and a route on every state-changing command; a rollback or an explicit nothing-to-undo with
a safe-abort; an escalation row naming a pager or channel and one carrying a time-box; a triage
tree with two routes; evidence labels; no template literal left in. Proven before any trial: 0 of
11 on a thin hand-written runbook, 11 of 11 on a complete one `[verified: this host]`. The skill's
own exemplar scored 8 of 11: two by design (a matured runbook is `active` and carries no
fresh-evidence labels) and one a real gap, its scale step had time bounds but no route when latency
does not fall, fixed in the candidate.

## Provenance

| Item | Value |
|---|---|
| Probe | `evals/build-scenarios/build-scribe-writes-only-docs.yaml`: scribe writes the runbook for a resolved incident from supplied evidence, in a fixture repo with real code beside `docs/`; 6 original checks plus the 11 rules above, 17 in all |
| Incumbent plugin root | this checkout at `b3ec12ff`, bundle 50,817 B |
| Candidate one | worktree at `322ba4c7` (`ea716ef4` + `82bc03ec` here), digest `e972b230ee8a`: `step-craft.md` deleted with its list kept in one body sentence, the runbook/playbook/SOP paragraph dropped, the Confluence export walkthrough compressed to its three team rules, the exemplar's scale step given its route, and one added sentence: a new runbook starts `status: draft`. Bundle 44,338 B |
| Candidate two | worktree at `d1aae6d8` (`30702179` here), digest `514082266fc4`: candidate one plus two lines in the template's procedure slot, the step's exit line and a note that every step carries an Expected line. Bundle 44,748 B; the final tree is 45,100 B after `77cdf135` restored the pinned export command, not re-measured |
| Models | `claude-sonnet-5` and `claude-opus-5`, three trials per arm |
| Raw runs | `.eval-runs/build/runbook-2026-09-03/` (gitignored, private) |

## Results

All rows `[verified: grading.json and the launcher logs under the raw-runs directory, this host]`.

| Arm | Checks per trial | Total | Tokens per trial | Mean tokens |
|---|---|---|---|---|
| Opus, incumbent | 14, 16, 17 of 17 | 47/51 | 245,760 · 286,231 · 194,014 | 242,002 |
| Opus, candidate one | 15, 17, 16 | 48/51 | 288,814 · 196,852 · 259,378 | 248,348 |
| Opus, candidate two | 16, 17, 17 | 50/51 | 197,133 · 196,642 · 322,693 | 238,823 |
| Sonnet, incumbent | 16, 16, 15 | 47/51 | 300,692 · 271,477 · 235,430 | 269,200 |
| Sonnet, candidate one | 16, 16, 16 | 48/51 | 269,895 · 178,428 · 209,936 | 219,420 |
| Sonnet, candidate two | 17, 17, 17 | 51/51 | 235,926 · 179,316 · 173,810 | 196,351 |

The six original checks passed in every trial. Every miss is one of the new rules:

| Rule | Incumbent misses (of 6) | Candidate one | Candidate two |
|---|---|---|---|
| a bound and a route on the state-changing step | 4 | 4 | 1 |
| an Expected line under every procedure step | 2 | 2 | 0 |
| frontmatter: a new runbook starts `status: draft` | 2 | 0 | 0 |

## What this says

- **The trim is safe** `[verified: candidate one, twelve trials]`. Nothing the incumbent passes is
  failed with 6.5 KB of craft prose removed, on either model.
- **One sentence landed six of six.** The body never said which status a fresh runbook takes;
  both models wrote `active` once in the baseline and never after the sentence was added.
- **Prose did not land two rules; the template did** `[verified: candidate two, six trials]`. The
  stop-condition rule is stated three times in the bundle and was missed in four trials of six on
  both the full and the trimmed skill. Two lines in the template's procedure slot took it to one
  miss in six, and the every-step Expected rule to none. This is the backend-craft finding again: a
  contract carried as a shape lands where a sentence does not.
- **Cost:** Sonnet's mean fell 27 percent from incumbent to candidate two; Opus is flat within
  noise. These trials are cheap, around a quarter-million tokens, because scribe runs no commands.
- **Not measured:** the exemplar's length (it was not shortened, on the evidence that examples are
  copied as shapes); the Confluence import path (the importer is software with its own tests, and
  no trial imports a page); more than three trials per arm; the one remaining Opus miss, a restart
  step with routes but no wait time, which is the rule as written.
