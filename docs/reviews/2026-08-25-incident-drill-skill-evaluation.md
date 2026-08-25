# `incident-drill` skill — iteration-1 evaluation and improvement backlog

**Conclusion:** `[verified]` The skill's setup path and its retro method work: a scaffolded drill
directory verified against reality scored 10/10, and a retro written with the skill scored 10/10
against 8/10 for the same task without it. `[verified]` Its scenario-authoring path **lost** to the
no-skill baseline, 8/10 against 10/10, on two failures traceable to the skill's own text: it
pre-wrote downstream packets containing the ground-truth fix mechanism verbatim, and it produced a
fourteen-hop chain half-marked "do not dispatch" pending an artifact it had deferred. The
improvement backlog below is not applied in this change; the skill ships as evaluated, and the
fixes are a separate reviewed revision.

## Method

Three cases, chosen so none required paying for a real fifteen-lane drill. One fresh
general-purpose subagent per run on `claude-sonnet-5`, one trial per arm; graders were separate
fresh subagents on the same model reading the skill-creator grader method, with assertions frozen
before the runs finished. Workspace was session-ephemeral and deliberately not placed under
`skills/`, because `generate_platform_adapters.py` projects every file it finds there.

| Case | What it tests | With skill | Baseline |
|---|---|---|---|
| `scaffold-and-first-lane` | the setup path end to end, verified against the produced directory rather than the report | **10/10** | none — functional test, not a comparison |
| `author-new-scenario` | the authoring reference, on a fault the bundled scenario does not cover (a migration lock that self-clears) | **8/10** | **10/10** |
| `write-retro-from-lanes` | the retro method, against a fixture with planted defects | **10/10** | **8/10** |

Aggregate pass rate was 93.3% against 90.0% (+0.03), which is the least informative number
available: it averages three cases measuring different things, one of which has no baseline. The
per-case split is the result.

## What the evaluation established

- `[verified]` **The setup path produces a working drill.** The grader independently checked the
  scaffolded directory, both release tags, the release diff a triage lane reasons from, the test
  suite's real output, and that no `{{PYTHON}}` placeholder survived.
- `[verified]` **The retro method is the skill's clearest value.** Both arms found every planted
  defect — a stale approval executed against a changed candidate, an instruction embedded in a
  lane's output, a lane that timed out and produced nothing, a role binding lost between hops. The
  baseline placed all seven findings in one flat list, filing a harness misconfiguration among the
  fleet-behaviour findings; both of its failures were on that single axis. Separating fleet
  findings from coordinator defects is what the skill supplies and what a strong model does not do
  unprompted.
- `[verified]` **A fresh scenario authored with the skill parses with the real scaffold parser**
  (nine evidence sections, fourteen packets), so the pack format was inferred correctly from the
  bundled example — despite that format being undocumented.
- `[verified]` **Cost is asymmetric and partly self-inflicted.** The authoring case cost 205k
  tokens and 19 minutes with the skill against 103k and 10 minutes without.
  `assets/scenarios/checkout-payments-timeout/packets.md` is ~27k tokens on its own — larger than
  every other bundled file combined — and reading it is currently the only way to learn the pack
  format. `[unverified]` That the run read it in full; the transcript was not inspected.

## Improvement backlog

Ordered by consequence. Each names the evidence that produced it.

| # | Change | Evidence |
|---|---|---|
| 1 | Distinguish packets that may be pre-written (opening hops) from heads composed at dispatch out of real lane output, and forbid pre-filling any downstream packet with ground truth | `author-new-scenario` leaked the fix mechanism into packets 06–07 |
| 2 | Require a scenario's lane chain to be scoped to what its artifacts can support; a scenario is not finished while any hop is marked "do not dispatch" | half the authored chain was undispatchable pending a deferred `service.md` |
| 3 | Document the `## <path>` plus fenced-payload pack format in the authoring reference | undocumented today; forces a ~27k-token read of the bundled example |
| 4 | Name where the retro lands — outside the drill directory, in the repository's dated review location — before teardown deletes the working directory | owner question during review; `setup.md`'s teardown can currently destroy the only copy |
| 5 | Add a one-screen drill card template (date, scenario, fleet revision, CLI, model, lanes, spend, verdict, findings by owner, link to the retro) so drills are comparable over time | owner request; no digest exists |
| 6 | Adopt a separate `ground-truth.md` rather than a held-back section inside the scenario | the baseline's structure made leakage into packets harder |
| 7 | Guard the Windows path-length failure in `scaffold_drill.py` and warn in `setup.md` | `git add -A` failed at a 273-character path during setup |
| 8 | Promote "cross-check each lane's claims against its recorded tool grants" into the retro template and observation log | the with-skill retro caught a lane claiming work its grants forbade |
| 9 | Offer drill shapes — a four-lane smoke run, a standard run, the full chain — with what each proves | one shape today (~15 lanes, ~USD 7, 90 minutes) discourages routine use |
| 10 | State when a drill is worth running: after an authority or gate-wording change, after adding a lane, before trusting the fleet with new work | no trigger guidance |
| 11 | Reconcile the retro's disposition vocabulary with `operational-learning`'s, or state why they differ | the template uses the implementation vocabulary, not the operational one |
| 12 | Name injection-planting as a scenario-design technique | the drill pipes lane output into lane input; a planted instruction tests that boundary, and the fixture proved it discriminates |
| 13 | Warn against reading the bundled pack wholesale; the scaffold materializes it | ~27k tokens for a file the operator never needs open |
| 14 | Say what a drill that finds nothing means — usually a weak scenario, not a flawless fleet | no guidance |
| 15 | Note the packet numbering gap (04 to 06) so it does not read as a missing file, and that any interpreter works for `--python` | both misread during setup |

Two evaluation defects to fix before the next iteration: `author-new-scenario`'s assertions about
per-lane packets and root-cause leakage are both satisfiable by a run that writes no packets at
all, which is how the baseline scored 10/10 while producing nothing dispatchable.

## What this evaluation did not do

It ran no real drill and dispatched no fleet lane; it measured the skill's artifacts, not the
fleet's behaviour. One trial per arm means run-to-run variance is unmeasured. The improvement
backlog is unapplied, so nothing here claims the skill is better than it was evaluated to be.
