# Principal-engineer lane: native evaluation

**Conclusion:** the lane passed every case it owns on every revision measured and never took
reliability work or a small tool build. Against `software-engineer` on identical bytes, every arm
returned the same decision fields on both tasks.

- **Final revision:** on `59fda81d`, the first run graded by the final checks, the lane passed both
  build cases, 6/6.
- **Contract change:** on the two revisions where both arms ran, `7993b130` and `af3531eb`, the lane
  wrote the complete design record, loaded `stack-profile` and returned the closed reply in all six
  trials. `software-engineer` wrote a complete record once in six, in the one trial where it read
  `principal.md`.
- **New system:** `software-engineer` read the reference in every trial and matched the lane on
  every scored check.
- **Likely reason for the difference [unverified]:** the new-system prompt names the "design
  record", which may lead `software-engineer` to the reference.
- **What the scores show, and what they do not:**
  - In the re-run, every trial that read `principal.md` filled all twelve slots, and the two that
    did not filled six. On `7993b130`, one `software-engineer` trial read it and filled eleven.
  - That the reference supplies most of the design quality remains a hypothesis. Matching scores
    also hid real design differences (below).
- **What the lane measurably adds:** it reads the reference and writes the record every time,
  including when a request does not name the record. It also has a design-only boundary and its
  own entry in the Copilot picker, which only a human test can measure.

One neighbour routing case fails identically on main and on the candidate. These results inform
`PRINCIPAL-001`; acceptance of the exact candidate remains the owner's decision.

## Identity and budget

| Item | Value |
|---|---|
| Candidate revisions | `56ac47b3` (digest `78fff82a…13b5e6`); `72f748a0` after the first review fixes (`0bdf82ef…dd253ed`); `7993b130` after the rename and the second review's fixes (`9ace6a27…14229ec8`); `e89bfdf2` with the new-system pair, the boundary cases and the `/adr` change (`bd55b8fa…7615a0f2`); `af3531eb` with the later review's fixes (`bd28b4a2…e3f806c`); `59fda81d` with the third review's fixes (`134b467f…4c4a302`) |
| Incumbent | `8d7ecda1` (main, PR base), digest `d251ef68…3b03127` |
| Host and model | Claude Code 2.1.290 on Windows 11, and 2.1.291 for the `af3531eb` re-run and the `59fda81d` check; `sonnet` alias, every trial answered by `claude-sonnet-5-5` |
| Windows (2026-10-06 UTC) | first campaign 00:00–00:17, re-measure 00:43–00:49, final 01:27–01:41, new-system pair and boundaries 03:14–03:21, re-run 06:06–06:16, final lane check 07:45–07:48; three interleaved passes per arm (DEC-10) |
| Budgets stated before running (DEC-04) | first: 21 trials, USD 4–6, cap 12; re-measure: 6 trials, USD 1.20, cap 3; final: 15 trials, USD 4.40, cap 7; new-system pair and boundaries: 12 trials, USD 3.50, cap 6; re-run: 12 trials, USD 2.60, cap 5; final lane check: 6 trials, USD 1.20, cap 3 |
| Actual | 75 trials, three of them attribution trials added to the first campaign; USD 16.99 recorded trial cost (5.64, 1.16, 3.94, 2.60, 2.37, 1.28); judge USD 0. One-word Haiku credential refreshes are not recorded |

## Results

| Scenario | Arm | `56ac47b3` | `72f748a0` | `7993b130` |
|---|---|---|---|---|
| `build-principal-engineer-contract-change` | lane | 3/3 | 3/3 | 3/3 |
| `build-principal-engineer-new-system` | lane | 3/3 | 3/3 | not run |
| `build-software-engineer-contract-change-baseline` | `software-engineer`, main bytes | 2/3 | — | — |
| `build-software-engineer-contract-change-baseline` | `software-engineer`, candidate bytes | — | — | 2/3 |
| `discovery-principal-engineer-new-service-design` | candidate | 3/3 | — | 3/3 |
| `discovery-principal-engineer-returned-fork` | candidate | 3/3 | — | 3/3 |
| `discovery-reliability-engineer-assessment` | candidate; not taken by the lane | 3/3 | — | 3/3 |
| `discovery-reliability-defers-accepted-implementation` | candidate / main | 0/3 / 0/3 | — | — |

Later runs have their own sections: the `e89bfdf2` pair and boundary cases, the `af3531eb` re-run,
and the final lane check on `59fda81d`.

The lane's own four cases were 12/12 in the first campaign, plus 3/3 on the reliability neighbour.
Both `software-engineer` failures are the `eng-ladder` load check; every decision check passed in
every `software-engineer` trial. The final rename changes the lane's description, so its routing
cases and the reliability neighbour were re-run on `7993b130`.

## Lane versus reference

The first comparison changed the agent and the `eng-ladder` reference together, because the
incumbent read main's reference, which has no design record. The `7993b130` run separates them: both
agents on identical bytes, interleaved.

| Arm, 3 trials each | Complete record (oracle) | Slots per document | Labels per document | Closed JSON reply | `stack-profile` loaded |
|---|---|---|---|---|---|
| Lane, `7993b130` bytes | 3/3 | 12, 12, 12 | 17, 23, 20 | 3/3 | 3/3 |
| `software-engineer`, `7993b130` bytes | 0/3 | 11, 6, 6 | 23, 8, 11 | 0/3 | 0/3 |
| `software-engineer`, main bytes | 0/3 | 7, 5, 6 | 0, 1, 4 | 0/3 | 0/3 |

Slots were counted by the oracle of that revision. The committed oracle counts 11, 6, 5 and
6, 5, 5 for the two `software-engineer` rows, because a phrase such as "Recommend expand…" no longer
counts as a label. No record changes from incomplete to complete.

- **The reference raises labelling.** It does so for an agent that loads it; trial-to-trial
  variation is large, and one `software-engineer` trial skipped `eng-ladder` and still wrote 8 labels.
- **Only the lane produced the rest.** The complete record, the `stack-profile` load and the closed
  reply came only from the lane.
- **Every arm made the same five decisions:**
  - found all three consumers, including the dashboard that parses the fields only in configuration;
  - kept the external reader unknown;
  - chose an additive first release;
  - removed the old format only on evidence;
  - left the decision with the owner.
- **The decisions did not separate the arms.** The decision fields are closed choices; only the
  consumer inventory required a search. The pair's pass rates turn on the `eng-ladder` load check,
  which is a method check, not a decision.
- Two `software-engineer` trials, one on each tree, ran a read-only `git status` and `git ls-files`;
  neither executed project code. The lane has no shell.

## New-system pair and boundary cases on `e89bfdf2`

| Scenario, 3 trials each | Result |
|---|---|
| `build-principal-engineer-new-system`, lane | 3/3 |
| `build-software-engineer-new-system-baseline`, `software-engineer` on the same bytes | 3/3 |
| `discovery-principal-engineer-defers-reliability-assessment` | 3/3: `reliability-engineer` fired, the lane did not |
| `discovery-principal-engineer-defers-small-tool-build` | 3/3: `software-engineer` fired, the lane did not |

| New-system arm | Complete record | Labels per document | Closed JSON reply | Skills loaded |
|---|---|---|---|---|
| Lane | 3/3 | 26, 25, 26 | 3/3 | `stack-profile` + `eng-ladder` 3/3 |
| `software-engineer` | 3/3 | 29, 26, 22 | 3/3 | `stack-profile` + `eng-ladder` 3/3 |

- **The two arms matched on every scored check.** Every document from both designs a daily Python job run as
  a PCF task, writing to the team's Postgres and read by Grafana. Each rejects the Rust, Kafka and
  Cassandra suggestion and leaves the availability target to the owner.
- **Prompt wording may explain the difference from the contract-change pair [unverified]:**
  - The contract-change prompt asks for a "design document"; the new-system prompt asks for a
    "design record", the reference's own term.
  - A new-system design also needs a runtime choice, which is where `software-engineer` loads
    `stack-profile`. The contract change needs none, so the lane's `stack-profile` load there is
    consistency rather than a quality gain.
- **Test not yet run:** neither pair varied the wording, so a re-run with the words swapped would
  test the explanation.

## Design defects the checks did not see

A later review read the saved designs and found three problems that passing scores did not reveal.

- **Unprovable removal gate (all three `7993b130` contract designs).** Each makes the old fields'
  removal depend on access logs showing that no client reads them. One says "access logs show no
  client has read `start`/`end`". Request logs show who calls the API, not which fields a client
  parses, so the gate depends on evidence the proposed observation cannot produce.
  - The worked example taught it: "a quiet period with no reads in the export's access logs".
  - Fixed in `principal.md`: the method now names consumer-side evidence for migration, and the
    example uses logs only to find readers, with owner confirmation as the gate.
  - Measured in the re-run below.
- **A detector that cannot see its failure (the worked example, found by a third review).** The
  example detected a reader still using a stale `owner` with a nightly comparison of the export's
  two fields. That comparison passes while the reader fails.
  - None of the three re-run lane designs copied it. They called the failure undetectable from the
    producer side and gated removal on owner confirmation.
  - The example now detects it with a rename test through each reader's lookup. Not yet measured.
- **Retired endpoints (first new-system pair).**
  - The lane's design keeps history and alerts on the latest scan per endpoint, but never says how
    an endpoint removed from the inventory stops paging.
  - `software-engineer`'s design keeps an `active` flag and alerts only on active endpoints.
- **Database failure (first new-system pair).** Both designs promise a staleness page when Postgres
  fails, while the heartbeat lives in that Postgres and Grafana queries it. Neither specifies the
  query-error notification. Other sampled designs handle this, so it is variation between outputs.

Section counts and the closed JSON fields cannot measure lifecycle, failure handling, or whether a
proposed observation can produce the evidence a gate needs. Measuring those needs a judged case.

## Re-run on `af3531eb`

Both pairs on the second review's checks: 12 Sonnet trials, three interleaved passes, USD 2.37
against a stated USD 2.60 and a USD 5 cap. Recorded verdicts come from the `af3531eb` checks; slots
are counted by the committed oracle.

| Arm, 3 trials each | Recorded | Read `principal.md` | Slots per document | Labels per document | Closed JSON reply | `stack-profile` |
|---|---|---|---|---|---|---|
| Lane, contract change | 3/3 | 3/3 | 12, 12, 12 | 15, 22, 22 | 3/3 | 3/3 |
| `software-engineer`, contract change | 0/3 | 1/3 | 6, 6, 12 | 3, 0, 20 | 0/3 | 0/3 |
| Lane, new system | 3/3 | 3/3 | 12, 12, 12 | 35, 30, 21 | 3/3 | 3/3 |
| `software-engineer`, new system | 3/3 | 3/3 | 12, 12, 12 | 36, 24, 25 | 3/3 | 3/3 |

- **The removal gate is fixed where the reference was read.**
  - The three lane designs, and the one `software-engineer` design that read `principal.md`, say
    request logs show callers but not which fields they read.
  - Each gates removal on owner confirmation or consumer-side evidence.
  - Before the fix, all three lane designs gated removal on access logs. That comparison also spans
    a CLI update, from 2.1.290 to 2.1.291.
- **Without the reference the habit remains.** One of the two `software-engineer` designs that did
  not read it proposed "Access logs or field-level usage evidence show no client reading the legacy
  fields" as the removal criterion, beside a note that access logs show only callers.
- **`software-engineer`'s contract failures:**
  - Two designs left six slots empty.
  - The third wrote a complete record but ran `git status --short && git ls-files` and read files
    through a shell loop. The assignment said "do not execute anything".
  - The lane has no shell tool, so it passes the no-shell check by construction. That check
    measures tool posture, not design reasoning.
- **Every decision check passed in all twelve trials.**

## Final lane check on `59fda81d`

Both lane build cases on the final reference and checks: 6 Sonnet trials, three passes per case run
in parallel, USD 1.28 against a stated USD 1.20 and a USD 3 cap, on Claude Code 2.1.291 as in the
re-run. These are the first recorded results graded by the final checks.

| Case, 3 trials each | Recorded | Slots per document | Labels per document | Closed JSON reply | `stack-profile` and `principal.md` |
|---|---|---|---|---|---|
| Contract change | 3/3 | 12, 12, 12 | 16, 21, 26 | 3/3 | 3/3 |
| New system | 3/3 | 12, 12, 12 | 35, 30, 21 | 3/3 | 3/3 |

- **Removal gate:** all three contract designs say request logs find callers but not which fields
  they read. Owner confirmation or a compatibility test proves migration.
- **Detectors match their failures.**
  - Every reader failure is detected on the reader's side: a per-reader compatibility or
    sample-payload test, owner confirmation, or watching the reader's own results.
  - Producer checks appear only for producer drift.
  - The `af3531eb` designs did the same, so this run does not show that the rename-test example
    caused it.
- **The example's new wording barely travelled.** No "rename test" phrasing appeared. "Fixture"
  appeared in two of three contract designs, against none in the re-run, as test vocabulary for the
  daylight-saving cases.
- **Variation no check measures (new system):**
  - All three designs make the alert's no-data state page, so a database or alert-path failure is
    not silent.
  - Endpoint lifecycle still varies:
    - One design restricts paging to the latest run's endpoints.
    - One pages on each endpoint's latest result with no inventory filter, so a removed endpoint
      would keep paging.
    - The third covers only an endpoint decommissioned but still listed.

## Re-measure after the first review fixes

Codex's review of `1d955923` found five issues, fixed in `72f748a0`:

- **Worked example:** it labels each option, names an owner per failure mode, and regenerates the
  retired field from current data in its stage-3 recovery. Its "flag day" phrasing and 30-day
  figure are gone.
- **Failure modes slot:** it now asks for an owner.

Both lane build cases were then re-run.

| Measure, per document | `56ac47b3` | `72f748a0` |
|---|---|---|
| Checks and record oracle | 6/6 pass | 6/6 pass |
| "flag day" in contract-change documents | 3/3 | 0/3 |
| 30-day retirement proposal in contract-change documents | 2/3 | 0/3 |
| Failure-mode owner lines, contract change | 1, 0, 0 | 6, 5, 9 |
| Failure-mode owner lines, new system | 1, 2, 0 | 4, 5, 4 |
| Labels inside the contract-change Options section | 0, 4, 2 | 5, 1, 2 |

**Counting rule for owner lines:** lines in the Failure modes section containing "owned by",
"owner:" or an owner table column. The independent review's broader rule (`owner|owned by|owns`)
gives 1, 1, 0 → 6, 6, 11 and 1, 2, 1 → 5, 5, 5: the same direction.

- **The owner change worked.** Owners now appear in every document.
- **Options labelling shows no clear change** in three documents.
- **The new example's wording still travels:** "quiet period" appears in 3/3 contract-change
  documents and "day of release" in 1/3, both without a figure.

## Document review

All documents were checked mechanically for the record oracle, labels, reused example phrasing and
GCP runtime claims. The recommendation and decision sections of the six first-campaign lane
documents were read, and one lane contract document and one incumbent reply were read in full.

- **Contract change:** every lane document recommends additive UTC fields with staged migration,
  keeps the external reader unknown, and lists five or six owner decisions. Unprompted, every
  document raises the daylight-saving ambiguity of the stored local times.
- **New system:** every lane document designs a daily Python job run as a PCF task, writing to the
  team's Postgres and read by Grafana, with no new service, broker or datastore.
  - Each rejects the Rust, Kafka and Cassandra suggestion with labelled reasons: two `[sourced]` to
    the stack profile, one partly `[unverified]`.
  - Each leaves the availability target to the owner and labels Grafana's access to that Postgres
    `[unverified]`.
  - None presents a GCP runtime as decided.
- **Minor:** one contract document repeats its recommendation section, and one new-system document
  copies the "Before you return" checks into the record.

## The neighbour red is the base state

`discovery-reliability-defers-accepted-implementation` asks the main session to implement accepted
work in a workspace with no application code. On both trees the session searched, found nothing, and
asked for the repository instead of dispatching `software-engineer`. No earlier run of this scenario
is retained under `.eval-runs/`, so the incumbent arm is the only base-state evidence. The scenario
is tracked as `EVAL-013`. It does not measure this change.

## Known grader limits

Codex's adversarial review of `7993b130` found two holes, and no recorded trial exercises either.

- **The record oracle counted a slot by its name alone.** It accepted a slot with an empty section,
  an empty table cell, or a contents list.
- **The reply checks search the whole reply**, so a discarded correct JSON draft or a duplicate key
  could pass.

All 15 saved contract-change replies contain exactly one JSON object and no duplicate keys, and no
saved record leaves a slot section empty. No recorded verdict depends on either hole.

**Status at `e89bfdf2`:**

- **Closed for the new-system pair:**
  - The oracle requires each slot to be filled and ignores a contents list.
  - A guard rejects any decision given twice.
  - Re-scoring the 21 saved documents and the six saved new-system replies changed no verdict.
- **Still open for the contract-change pair.** Its recorded results were graded without the guard.

**After a later review:**

- **The oracle separates a slot's label from its content.** A heading's own text, the rest of a
  label, or a table's first cell no longer counts as content.
  - Twelve empty "(required)" headings now fail.
  - Every single-empty-slot document fails in heading, table and emphasised-label form (36 cases).
- **Both pairs gained checks:**
  - **Both pairs:** skills must load before the document is written, and no shell may run, as the
    prompts require.
  - **Contract-change pair only:** the record oracle, an exact consumer list, and the
    duplicate-field guard.
- **Recorded verdicts no longer match the committed checks.** Every recorded result in this file
  was graded by the earlier checks; a re-run is needed before citing them on the current ones.
- **Offline re-score (diagnostic only, not evidence):**
  - None of the 27 saved documents changes verdict under the new oracle.
  - On the contract pair, all 9 lane trials would pass the new record, list and guard checks.
  - All 6 `software-engineer` trials would fail the record check, and 2 of them ran read-only Git
    commands, which the no-shell check now fails.

**After a third review, which the `af3531eb` re-run predates:**

- **One label matcher for every format.**
  - A label names a slot only when one of its parts, split at "and", "from", "for" and
    punctuation, is exactly the slot's name or an alias.
  - No label counts as content, in any format.
  - **False passes closed:** a heading over its own empty label, over a table header only, or over
    another slot's label.
  - **False fail closed:** a complete bullet-form record failed on `af3531eb`.
  - **Calibration:** each slot left empty alone in five formats (60 cases).
- **Escaped field names.**
  - A contract reply that respelled `decision_owner` as `decision\u005fowner` passed every reply
    check.
  - A guard now rejects any field name with a unicode escape, the only way to respell a key.
  - The new-system pair's `exact_json` check already decodes the reply and rejects the duplicate.
- **No recorded verdict depends on these holes:**
  - Re-scoring the 39 saved documents changed no verdict.
  - None of the 39 saved replies has an escaped field name.
- **First recorded run on these checks:** the final lane check on `59fda81d` (above).

**Open, from Copilot's review of `af3531eb`:** the oracle requires one evidence label anywhere in
the record, so every slot's claims could sit unlabelled behind a single footer label.

- No saved record does this. All 37 passing records label claims in at least four slots, with 11 or
  more labels each.
- A per-slot rule would fail the reference's own worked example, which labels four of its twelve
  slots.

## What this does not establish

- One model, one host, and Claude only; Copilot handoffs were not exercised. Picker selection is
  being measured by hand with a shared picker sheet, not in VS Code.
- Whether prompt wording explains the two pairs' different results: no run varied it.
- Whether the rename-test example changes designs: the final lane check found reader-side
  detectors, but the `af3531eb` designs already had them.
- `software-engineer` on the final bytes and checks: the final lane check ran the lane only.
- The `/adr` rule that writes `proposed` for `principal-engineer`, added after the final lane check:
  no native case exercises `/adr`, and the plugin bytes differ from `59fda81d` only by that rule.
- Lifecycle, failure handling, and evidence feasibility: no judged case measures them.
- Every build prompt forbade delegation, so helper dispatch and return were not exercised.
- Whether one design lane serves both depths better than separate principal and architect bodies.
- Design quality was judged by the author of the change, without a calibrated rubric. The owner's
  review of the documents is still needed.

Raw traces and documents are private under `.eval-runs/principal-20261005/`.
