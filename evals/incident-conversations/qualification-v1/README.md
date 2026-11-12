# Incident qualification v1

[sourced] This pack defines four new, two-message held-out profiles. It contains scenario definitions,
separate semantic review criteria, and a frozen one-trial native selection. It is reserved for use
after the candidate revision has been frozen; it carries no model result or candidate acceptance.

[sourced] Candidate-visible material consists only of each scenario's initial prompt, its
`evidence.md` fixture (the same initial records), and the single later release at invocation two.
The `review/` JSON files are harness-only. Do not copy them, this manifest, or this README into a
candidate fixture, prompt, tool response, or helper task. Candidate `success_criteria` are structural
only and do not contain the semantic answers.

[sourced] The author used only the assignment and the allowed native harness mechanics. The author
did not read candidate agent/skill instructions, previous model outputs, repair reports, diagnostic
cases/reviews, or earlier conversation. The author made no model/API calls and changed no candidate
instruction files. Scenario domains and expected conclusions remain in the sealed scenario/review
files rather than coordinator-facing summaries.

[sourced] `manifest.json` binds each scenario's byte SHA-256, native `case_digest`, and review byte
SHA-256, as well as the selection and this README. `report-selection.json` uses
`native-selection-v1` with one trial per profile. Git source metadata is null because this pack
binds authored files rather than a Git snapshot. The manifest separately records the reserved
frozen candidate plugin identity supplied by the coordinator before case disclosure. Do not rewrite these definitions after seeing candidate
responses; any changed definition is a different qualification pack.

[unverified] Native behavior and semantic performance have not been measured. Offline schema and
hash validation do not establish either. A structural pass must be followed by review against the
harness-only criteria using then-visible evidence. Missing runtime evidence is inconclusive;
intentional uncertainty in a causal question is part of the task, not an instrument failure.
Only human acceptance of the exact candidate revision can promote it.
