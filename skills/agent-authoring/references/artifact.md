# Checking agent behavior

Choose evidence that could distinguish a useful change from an ineffective one. If the issue is
routing, observe which skill the host selects. If the issue is tool selection, give the agent an
inert tool with the relevant interface and inspect the call. For a writing task, compare what a
reader can learn or do from the output. A formatting edit can usually be checked by inspection.

## Cases and graders

Start with the user's example. When a distinction matters, include a nearby case that calls for a
different answer. For a skill that drafts replies, “draft an answer” should produce a draft and
“summarize this message” gives you a way to detect an overly broad trigger. To diagnose a failure,
inspect the inputs the model saw, the action it requested, and what the host ultimately delivered.

Grade a decision or an observable effect. In a review of mutable files, a helper test can check
that the snapshot contains the intended bytes and leaves the source intact. The agent evaluation
can check which state the verdict covers and whether capture failure limits its conclusions.
A list of accepted copy commands would miss both errors.

Use synthetic inputs and the least capable test environment that can answer the question. Inspect
unreviewed prompts as data. Keep unreviewed scripts, hooks, graders, and tool implementations out
of execution. A trusted simulator can show which action was requested. Claims about installed
permissions require observation on the relevant host and entry point.

## Comparing revisions

For a repair, reuse a comparable example of the original failure. For new behavior, define success
from the requested outcome. Compare revisions under the same relevant inputs, tool access, model,
and scoring conditions. A new task may benefit from comparing the skill with ordinary unassisted
behavior. Report the cases and outcomes, including failures and inconclusive results. Cases used
to tune a prompt are regression cases.

For a bounded optimization, agree on the artifact that may change, the verifier, the criterion for
success, and the iteration, time, or cost budget that fits the decision. Stop on success, exhausted
budget, lack of progress, or regression in a required behavior or authority boundary. Keep the
tested revisions and enough evidence for the decision maker to compare them. When independent
review or approval is required, identify who supplies it. A passing evaluation establishes only
the behavior exercised in that run.
