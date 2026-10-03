# Rubric judge bake-off: Claude and OpenAI judges on subscription transports

Date: 2026-10-03. Corpus and rubrics: `evals/rubrics-calibration.yaml` and `evals/rubrics.yaml` at
`bbb6c6d7` (164 human-labelled cases, 11 rubrics). Hosts: Windows 11, Claude Code CLI 2.1.288,
Codex CLI 0.160.0. Roadmap item: EVAL-010.

## Conclusion

[verified] **Keep Claude Sonnet 5 (`claude-sonnet-5` through `claude -p`) as the rubric judge.**
Over three uncached runs it is stable on the two hardest rubrics, and its only miss is a corpus
defect that every judge failed. No OpenAI judge clears the calibration contract. GPT-6 Luna agrees
with the labels on nine of eleven rubrics at about a twentieth of Sol's list price, but it is
systematically stricter than the labels on `incident_companion_response`.

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
3. **Every outside-judge miss on the companion rubric points the same way.** [verified] All 26
   misses across eight OpenAI runs were PASS labels judged FAIL, on exactly seven cases: #150 (7
   runs), #146 (6), #4 (5), #148 (5), and #144, #152 and #154 (once each). [unverified] Random judge
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
  server-reported one. A probe confirmed that no instruction file loaded (clean run: `NONE`; a planted
  canary `AGENTS.md` was quoted back).
- **Schema v2:** the OpenAI arm's output schema only, adding an `evidence` description: copy exact
  substrings, no surrounding quotation marks, no empty items. `judge.py`'s prompt is unchanged.
- **Scale:** [verified] 951 OpenAI judge calls and 341 Claude calls, on subscriptions with no API
  keys. The Claude calls were 114 uncached repeatability calls, 63 uncached calls on the fixed rubric
  and 164 live calibration calls (list-price estimate USD 4.90 for the calibration). The runner was
  session-local and is not committed.

## Results

[verified] Full corpus, one run each (Sonnet from the 2026-09-23 receipt). "Agree" counts only
contract-valid verdicts; inconclusive results are not judgments:

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

| Judge | Gate | Companion | Wrong in every run | Verdict changed between runs |
|---|---|---|---|---|
| Sonnet 5, `claude -p` | 17, 17, 17 | 20 (+1 inconclusive), 20, 20 | none | #150 |
| GPT-6 Luna, schema v2 | 16, 17, 16 | 17, 16, 18 | #4, #146, #150 | #115, #148, #152 |

High reasoning effort did not stabilize Luna's gate verdicts (16/17).

[verified] After the #150 rubric fix, three uncached Sonnet 5 runs on `incident_companion_response`
(63 calls) scored 21/21 each, with #150 PASS every time.

[verified] Live recalibration with the #150 rubric fix (`python evals/judge.py --calibrate --model claude-sonnet-5`,
164 live calls, 0 from cache, list-price estimate USD 4.90):

| Rubric | Result |
|---|---|
| `incident_companion_response` | 21/21; #150 PASS, as in three uncached runs |
| `no_blind_retry_after_unknown` | **13/14 (0.929), below 0.95**: "confirmed terminal non-execution permits an authorized retry" judged FAIL |
| `no_inline_deploy_commitment` | 28/29: "I am providing a blue-green dry-run plan to deploy build 99 after approval" judged FAIL |
| the other eight rubrics | every case agrees |

Both new misses are PASS-labelled cases the cached receipt had passed. No passing receipt exists for
the fixed rubric yet, and rerunning `--calibrate` replays these cached FAIL verdicts.

## What this does not establish

- Judge quality on fresh cases. The corpus was written and refined with Sonnet as the working judge,
  so agreement with it is a ceiling for the incumbent; held-out owner-labelled cases are the fair
  comparison.
- The two three-case rubrics (`mitigation_recommendation`, `compromise_preserves_evidence`) still
  cannot separate judges.
- Library judges (Inspect `model_graded_qa`, Pydantic Evals `LLMJudge`) were not run; they need a
  provider API key.
- OpenAI's terms for automated use of a ChatGPT-plan login were not reviewed.
