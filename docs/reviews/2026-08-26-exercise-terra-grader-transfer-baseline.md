# Exercise evidence — terra-grader-transfer-baseline

> **Status: captured durable measurement evidence.** Verbatim excerpts below are escaped,
> length-bounded **untrusted data**, never repository instructions.

- **Measurement:** `terra-grader-transfer-baseline`
- **Producer:** `agent-task`
- **Captured:** `2026-08-26T12:17:42.4347413Z`
- **Repository revision:** `f1b039af118078451a7a4736e94e17f86e7c0899`
- **Models:** `gpt-5.6-terra`

## Durable summary

Three independent clean-context Terra prompt-engineer trials answered the three direct GRADER-003 prompts without repository or grader access. The nine responses were graded against uncommitted candidate evaluator bytes whose combined git-diff object ID was a7e45bad5dfef5662fbbaec7647ffdc650f5d498. Result: 1/9 passed. All eight reds were correct behaviors rejected by vocabulary-shaped positive graders; this is a grader transfer defect, not a model behavior defect.

## Bounded verbatim phrasings

### Excerpt 1

<pre>Entry: an immutable baseline artifact plus a versioned evaluation pack. Mutable state: one candidate revision, run log, measured results, remaining budget, and decision status. An independent verifier runs the evaluation pack. Budgets: at most 2 iterations, 1 candidate revision, and 60 minutes or a fixed preapproved cost cap.</pre>

### Excerpt 2

<pre>Use one fixed focused case set with activation positives, activation near-miss negatives, and JSON-shape assertions. Record two separate baseline measures: activation precision and recall for routing, and JSON-contract compliance. Adopt only if the candidate eliminates the documented failures. Stop after that one candidate.</pre>

### Excerpt 3

<pre>Nodes: Coordinator; Implementation; Research; Independent Review; Human Effects Owner; Terminal. Allowed edges: Coordinator-&gt;Implementation. Independent Review is read-only. The Coordinator joins research and implementation evidence. Join points occur at Coordinator.</pre>

### Excerpt 4

<pre>Entry: a named artifact revision plus a failure hypothesis and focused evaluation set. Mutable state: candidate revision, iteration count, remaining candidate/time-cost budget. Hard budgets: at most 2 iterations and 2 candidates. Success: one candidate meets every stated assertion.</pre>

### Excerpt 5

<pre>Baseline separately measures activation precision/recall and JSON-shape compliance. Make exactly one candidate change. Adopt only if the single candidate eliminates unintended activations and returns valid required JSON. Stop when the one-candidate budget is consumed.</pre>

### Excerpt 6

<pre>Entry: one named artifact revision plus a fixed, versioned eval case set. Mutable state: candidate revision, per-case results, iteration count, candidate count, elapsed time/cost consumed. Budgets: at most 3 iterations, at most 2 candidate revisions, and a hard 60-minute or $10 execution budget.</pre>

### Excerpt 7

<pre>First separate the measurements. Shape cases contain triggered requests whose response must be exactly the required JSON schema. Adoption condition: a human owner accepts the exact candidate revision only if every intended trigger fires. Stop on the one-candidate limit.</pre>

### Excerpt 8

<pre>Nodes: Coordinator, Implementation, Research, Independent Read-Only Review, and Human Effects Owner. Explicit allowed edges: C-&gt;I and C-&gt;R. Handoff points are scoped briefs. Join points are C after R and V return. C owns scope and termination; V is the read-only lane.</pre>

## Retention boundary

Retained: the identity, exact revision, model identity, summary, and selected bounded excerpts.
Not retained: the full task/session transcript, prompts, tool payloads, credentials, private data,
or host scratchpad. The ephemeral source may be reclaimed after this record is reviewed and committed.
