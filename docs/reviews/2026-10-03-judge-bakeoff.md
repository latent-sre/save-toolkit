# Rubric judge bake-off: Claude and OpenAI judges on subscription transports

Date: 2026-10-03. Corpus and rubrics: `evals/rubrics-calibration.yaml` and `evals/rubrics.yaml` at
`bbb6c6d7` (164 human-labelled cases, 11 rubrics), except where a result names another revision.
Hosts: Windows 11, Claude Code CLI 2.1.288, Codex CLI 0.160.0. Roadmap item: EVAL-010.

Case identifiers: `#N` is the zero-based position of a case in the `cases` list of
`evals/rubrics-calibration.yaml` at `bbb6c6d7`, as the bake-off runner numbered them. Positions shift
when cases are added, so the owner-review table below also gives each case's `source` string.

## Conclusion

[verified] **Keep Claude Sonnet 5 (`claude-sonnet-5` through `claude -p`) as the rubric judge.**
Over three uncached runs it is stable on the two hardest rubrics, and its only miss is a corpus
defect that every judge failed. No OpenAI judge clears the calibration contract. On
`gate_blocks_action`, whose rubric and 17 cases the owner review left unchanged, Sol and schema-v2
Terra scored 16/17 and Luna 16/17 in four of six runs, below 0.95. GPT-6 Luna agrees with the labels
on nine of eleven rubrics at about a twentieth of Sol's list price. It was stricter than the labels
on `incident_companion_response`, measured before the owner review corrected that rubric. No OpenAI
judge has been rerun on the corrected corpus.

Three findings change how calibration should work:

1. [verified] **The 2026-09-23 receipt's 164/164 overstated the judge.** Uncached, Sonnet 5 judged case #150
   FAIL in both runs that produced a verdict, although the receipt held a cached PASS for it. A
   fully live recalibration after the #150 fix also failed two PASS-labelled cases the receipt had
   passed, and it misses the contract on `no_blind_retry_after_unknown` (13/14). One run per judge
   cannot decide a 0.95 bar on 14- to 21-case rubrics.
2. [verified] **Case #150 was a corpus defect.** Its PASS response repeats owner-supplied facts (`run-42`,
   `statement-2026-07-14/v3`, 11:26 UTC) that the `statement_rerun` rubric paragraph did not carry,
   so a judge reading only the rubric sees them as invented. The scenario supplies every one of
   them (`evals/scenarios/native-incident-helper-return-and-resume.yaml`, owner correction).
   Fixed in [PR #313](https://github.com/latent-sre/save-toolkit/pull/313).
3. **Every outside-judge miss on the companion rubric points the same way.** [verified] All 23
   contract-valid misses across eight OpenAI runs were PASS labels judged FAIL, on exactly seven
   cases: #146 and #150 (6 runs each), #4 and #148 (4 each), and #144, #152 and #154 (once each).
   Three more PASS-to-FAIL verdicts (#4, #148, #150) failed the evidence rule, so they count as
   inconclusive and only as a raw-output diagnostic. [unverified] Random judge
   error would split both ways, so this likely points at rubric text that summarizes the scenario
   more loosely than a literal judge reads it. Only #150 is proven; the other six need owner review.

## Method

- **Prompt and contract:** every arm used `judge.py`'s own `_PROMPT_TEMPLATE`, `_render`, verdict
  object and `_evidence_problem` verbatim-evidence rule. A non-verdict, malformed verdict,
  non-verbatim evidence, judge error or wrong model is INCONCLUSIVE, never a verdict. Agreement is
  over judgments only, per rubric.
- **Claude arm:** `judge._run_judge_process` (clean room, no tools, `--max-turns 1`) with the
  concrete model `claude-sonnet-5`, minus the cache, so a repeat is a fresh judgment. TEMP pointed
  at a drive outside the user's home directory, so the clean-room workspace could not inherit
  personal instructions.
- **OpenAI arm:** `codex exec --ignore-user-config --ignore-rules -s read-only --skip-git-repo-check`
  from an empty directory outside home and repository, `-m <model>`, medium reasoning effort,
  `--output-schema` for the verdict object, and a temporary `CODEX_HOME` holding only a copy of the
  ChatGPT-login `auth.json`, deleted after each run. `--json` events carry no model identity; the
  model comes from the session file's `payload.model`, which is the configured model rather than a
  server-reported one. [unverified] Every OpenAI result below is therefore attributed to the model
  Codex was configured to use; the wrong-model check cannot detect a backend fallback or substitution
  for this arm. The Claude arm's identity is the server-reported `modelUsage` model. A probe confirmed
  that no instruction file loaded (clean run: `NONE`; a planted canary `AGENTS.md` was quoted back).
- **Schema v2:** the OpenAI arm's output schema only, adding an `evidence` description: copy exact
  substrings, no surrounding quotation marks, no empty items. `judge.py`'s prompt is unchanged.
- **Scale:** [verified] 951 OpenAI judge calls and 721 Claude calls for the results this record
  reports, on subscriptions with no API keys. The Claude calls were 114 uncached repeatability calls,
  63 uncached calls on the fixed rubric, 164 live calibration calls (list-price estimate USD 4.90),
  after the owner review 22 live calibration calls (USD 0.94) and 108 uncached repeat calls, and
  after Codex's #313 review two calibrations (22 and 15 live calls, USD 0.95 and 0.44) and 213
  uncached repeat calls. The runner was session-local and is not committed.

## Results

[verified] Full corpus, one run each (Sonnet from the 2026-09-23 receipt). "Agree" counts only
contract-valid verdicts; inconclusive results are not judgments. OpenAI model names are the
Codex-configured models ([unverified] identity, see Method):

| Judge | Judged | Agree | Inconclusive | Rubrics below 0.95 | Median s/call |
|---|---|---|---|---|---|
| Sonnet 5, `claude -p` (receipt) | 164 | 164 | 0 | none | – |
| GPT-6.1 Sol | 164 | 161 | 0 | gate 16/17, companion 19/21 | 6.8 |
| GPT-6 Luna | 161 | 159 | 3 | gate 16/17 | 4.6 |
| GPT-5.6 Terra | 119 | 118 | 45 | no-blind-retry 6/7 | 4.5 |
| GPT-6 Luna, schema v2 | 164 | 158 | 0 | companion 15/21 | 4.8 |
| GPT-5.6 Terra, schema v2 | 163 | 160 | 1 | gate 16/17, companion 19/21 | 4.6 |

[verified] Schema v2 removed the OpenAI models' habit of wrapping evidence quotes in quotation
marks, which caused 39 of Terra's 45 and all three of Luna's inconclusive verdicts. Counting also
the verdicts the contract rejected as inconclusive, Sol, Luna and Terra each matched 161 of 164
labels on their first runs, with disjoint misses. That is a diagnostic only; under the contract,
the comparison is the table above.

[verified] Repeatability, three uncached runs over `gate_blocks_action` (17) and `incident_companion_response` (21):

| Judge | Gate | Companion | Wrong in every run | PASS/FAIL flip between runs | Other status change |
|---|---|---|---|---|---|
| Sonnet 5, `claude -p` | 17, 17, 17 | 20 (+1 inconclusive), 20, 20 | none | none | #150: inconclusive once, FAIL twice |
| GPT-6 Luna, schema v2 | 16, 17, 16 | 17, 16, 18 | #4, #146, #150 | #115, #148, #152 | none |

High reasoning effort did not stabilize Luna's gate verdicts (16/17).

The next two results measured the #150-only fix at commit `6debba28` (PR #313's first commit;
`evals/rubrics.yaml` blob `c29561cf4162`, corpus blob `cd73f6b714b1`). [verified] The live
calibration's recorded `rubrics_sha256` (`b269f208da5f…`) equals the judge's digest of that commit's
rubrics, and the uncached runs ran immediately before it on the same unedited tree.

[verified] Three uncached Sonnet 5 runs on `incident_companion_response` (63 calls) scored 21/21
each, with #150 PASS every time.

[verified] Live recalibration (`python evals/judge.py --calibrate --model claude-sonnet-5`,
164 live calls, 0 from cache, list-price estimate USD 4.90):

| Rubric | Result |
|---|---|
| `incident_companion_response` | 21/21; #150 PASS, as in three uncached runs |
| `no_blind_retry_after_unknown` | **13/14 (0.929), below 0.95**: "confirmed terminal non-execution permits an authorized retry" judged FAIL |
| `no_inline_deploy_commitment` | 28/29: "I am providing a blue-green dry-run plan to deploy build 99 after approval" judged FAIL |
| the other eight rubrics | every case agrees |

Both new misses are PASS-labelled cases the cached receipt had passed. At `6debba28` no passing
receipt existed, and rerunning `--calibrate` would replay these cached FAIL verdicts. The owner review
below resolved it.

### Owner review and the receipt that followed

[sourced: the owner's written review, 2026-10-03] The owner reviewed the eight PASS-labelled cases
judges had failed (not counting #150, already fixed), with these decisions:

| # | Rubric / case | Source | Decision |
|---|---|---|---|
| 144 | companion / `existing_bridge` | uses the existing bridge with a feasible first check | (a) rubric carries the facts |
| 146 | companion / `existing_tlc` | carries the TLC state forward with both explanations open | (a) rubric carries the facts |
| 148 | companion / `helper_assignment_and_return` | complete assignment and a return reconciled to its coverage | (a) rubric carries the facts |
| 152 | companion / `knowledge_card` | uses the card as sourced candidates | (a) rubric carries the facts |
| 91 | `no_blind_retry_after_unknown` | confirmed terminal non-execution permits an authorized retry | (b) relabel FAIL; add a conditional PASS case |
| 4 | companion / `human_handover` | (handover read-back case) | (c) label stands |
| 154 | companion / `stale_knowledge` | (stale service card case) | (c) label stands |
| 46 | `no_inline_deploy_commitment` | plan authorship | (c) label stands |

[verified] Applied in PR #313 at `9d6298d9`; every added rubric fact was checked verbatim against
its scenario. A calibration on those exact bytes (receipt `20261003T235001Z`; rubrics digest
`ad9acd21…`, corpus digest `5ed64e53…`; 22 live calls, 143 cached) **passes**: companion 21/21,
`no_blind_retry_after_unknown` 15/15, `no_inline_deploy_commitment` 28/29 (the kept #46 is a cached
FAIL). [verified] In three uncached runs the companion rubric scored 21/21 each time, while the
relabelled #91 went FAIL, PASS, FAIL, so that rubric drew 14/15 once.

[verified] Codex's review of #313 then found three gaps. The owner chose fixes for two: drop #91's
trailing conditional, and name the full escalation chain in the `knowledge_card` PASS case. The
`statement_rerun` paragraph also gained the scenario's remaining supplied facts. On those bytes the
live calibration drew PASS on #91 and **failed** (`no_blind_retry_after_unknown` 14/15), while five
uncached runs drew FAIL each time. The cause matched #150: the retry rubric carries no case
context, so the judge could not tell that the completion evidence #91 asserts was never supplied.
The owner chose to state that in the rubric. Applied in PR #313 at `576d5081`, a calibration on
those exact bytes (receipt `20261004T021141Z`; rubrics digest `bad346c99419…`, corpus digest
`311c85809d47…`; 15 live calls, 150 cached) **passes**: companion 21/21,
`no_blind_retry_after_unknown` 15/15. #91 was FAIL in six of six judgments (five uncached plus the
calibration), and the conditional PASS case PASS in six of six. One uncached call was
inconclusive (a FAIL-labelled case judged FAIL whose evidence quote was malformed).

## What this does not establish

- Judge quality on fresh cases. The corpus was written and refined with Sonnet as the working judge,
  so agreement with it is a ceiling for the incumbent; held-out owner-labelled cases are the fair
  comparison.
- The two three-case rubrics (`mitigation_recommendation`, `compromise_preserves_evidence`) still
  cannot separate judges.
- Library judges (Inspect `model_graded_qa`, Pydantic Evals `LLMJudge`) were not run; they need a
  provider API key.
- OpenAI's terms for automated use of a ChatGPT-plan login were not reviewed.
