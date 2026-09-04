# runbook trim: before/after evidence (2026-09-03)

The `runbook` skill was cut from 50,817 B to 44,748 B in the candidate the trials ran, and stands
at 45,955 B in the final tree after the import test's pinned export command was restored and the
review's exemplar fixes landed (measured on this host); more to the point, it was measured for the
first time against its own authoring rules. A tools-off probe of Sonnet and Opus set the cut line;
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
finished, makes eleven of the skill's authoring rules mechanical: frontmatter that parses as YAML
with the template's key set, every value filled and typed, `status: draft` and both dates null;
every section present with a body or an explicit `n/a — why`; an Expected line under every
procedure step followed by at least two routed outcome branches; a source in the sentence that
mentions each placeholder, upper- or lowercase; a bound and a route on every fallible step (any
command, any wait); a rollback entry per state change, bound to its step by number and carrying an
undo command or an explicit disposition, plus a safe-abort that says something; an escalation row
that is time-boxed and names a pager or channel on the same row; a triage tree of at least two
conditional branches; an evidence label in every step that runs a command; no template literal
left in. That is the checker after three review rounds; the trials ran under its first version,
and the re-scored table below is under the current one. Proven before any trial and again after
each tightening: 0 of 11 on a thin hand-written runbook, 11 of 11 on a complete one `[verified:
this host]`. The skill's own exemplar scores 9 of 11 under the current checker, the two misses by
design (a matured runbook is `active` and carries no fresh-evidence labels). Each tightening found
real defects in the exemplar first: a scale step with bounds but no route, read-only steps with
routes but no bound, two steps whose expected line did not take the template's `Expected:` shape,
a rollback section that numbered the scale-out as step 2 when it is step 3, a log-count pipeline
that printed a healthy zero when the platform read itself failed, and two steps whose worked
outcome had no route of its own, all fixed in this pull request.

## Provenance

| Item | Value |
|---|---|
| Probe | `evals/build-scenarios/build-scribe-writes-only-docs.yaml`: scribe writes the runbook for a resolved incident from supplied evidence, in a fixture repo with real code beside `docs/`; 6 original checks plus the 11 rules above, 17 in all |
| Incumbent plugin root | this checkout at `b3ec12ff`, bundle 50,817 B |
| Candidate one | worktree at `322ba4c7` (`ea716ef4` + `82bc03ec` here), digest `e972b230ee8a`: `step-craft.md` deleted with its list kept in one body sentence, the runbook/playbook/SOP paragraph dropped, the Confluence export walkthrough compressed to its three team rules, the exemplar's scale step given its route, and one added sentence: a new runbook starts `status: draft`. Bundle 44,338 B |
| Candidate two | worktree at `d1aae6d8` (`30702179` here), digest `514082266fc4`: candidate one plus two lines in the template's procedure slot, the step's exit line and a note that every step carries an Expected line. Bundle 44,748 B; the final tree is 45,955 B after `77cdf135` restored the pinned export command and the review's exemplar fixes landed, measured on this host |
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

## Re-scored under the tightened oracle

The review of this pull request tightened the oracle three times after the trials. Round one:
every placeholder the template carries is a literal to reject; every slot needs a body or an
explicit `n/a — why`; every procedure step's expected line must route its outcomes; every fallible
step (any command, any wait) needs a bound and a route; each state change needs a rollback line of
its own. Round two: frontmatter values may not be blank; routing counts only on the Expected line
and its outcome branches; uppercase placeholders count; a rollback entry binds to its step by
number; the time-box and the reachable contact must sit on the same escalation row; a triage tree
is conditional branches, not route phrases in prose; every command step carries its own evidence
label. Round three: the frontmatter must parse as YAML with typed values; an expected line needs at
least two routed outcome branches, so a bare success line with one failure route does not pass for
worked, partly worked, and failed; a placeholder's source must sit in a sentence that mentions it;
a rollback entry must carry an undo command or an explicit disposition, and the safe-abort must
say something. The eighteen produced runbooks were pulled from their workspace patches and
re-scored offline under the current checker, no model calls `[verified: this host, the `produced/`
directory under the raw runs]`. The six original checks are the live verdicts.

| Arm | Live (17 checks) | Re-scored (current oracle + 6 live) |
|---|---|---|
| Opus, incumbent | 47/51 | 43/51 |
| Opus, candidate one | 48/51 | 41/51 |
| Opus, candidate two | 50/51 | 46/51 |
| Sonnet, incumbent | 47/51 | 43/51 |
| Sonnet, candidate one | 48/51 | 42/51 |
| Sonnet, candidate two | 51/51 | 46/51 |

Candidate two, the one shipping, is best on both models under every version of the instrument.
Candidate one, the trim alone, rises by one point on each model under the live checks and falls
two and one points below the incumbent under the current oracle: one rule on one or two trials of
three, within what three trials can resolve, so the trim alone is read as neutral, not as better.
The round-three rules cost every arm the same two ways: frontmatter values that carry prose
evidence notes and so no longer parse as YAML (four trials), and steps whose only routed branch is
the failure, the worked path left implicit (every arm, most steps). Both are real gaps in what the
models write from this skill, and neither is on the candidate's side of the ledger alone.

## What this says

- **The trim alone is neutral** `[verified: candidate one, twelve trials]`. With 6.5 KB of craft
  prose removed the live totals rise by one on each model and the re-scored totals sit one to two
  points below the incumbent, inside three-trial noise; what ships is candidate two, above the
  incumbent on both models under every instrument.
- **One sentence landed six of six.** The body never said which status a fresh runbook takes;
  both models wrote `active` once in the baseline and never after the sentence was added.
- **Prose did not land two rules; the template did** `[verified: candidate two, six trials]`. The
  stop-condition rule is stated three times in the bundle and was missed in four trials of six on
  both the full and the trimmed skill. Two lines in the template's procedure slot took it to one
  miss in six, and the every-step Expected rule to none. This is the backend-craft finding again: a
  contract carried as a shape lands where a sentence does not. The re-score shows the next slot to
  carry that way: the template asks for worked, partly worked, and failed each with a route, and
  the models write the failure route alone.
- **Cost:** Sonnet's mean fell 27 percent from incumbent to candidate two; Opus is flat within
  noise. These trials are cheap, around a quarter-million tokens, because scribe runs no commands.
- **Not measured:** the exemplar's length (it was not shortened, on the evidence that examples are
  copied as shapes); the Confluence import path (the importer is software with its own tests, and
  no trial imports a page); more than three trials per arm; the one remaining Opus miss, a restart
  step with routes but no wait time, which is the rule as written.
