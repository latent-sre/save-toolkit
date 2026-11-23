---
name: agent-authoring
description: >-
  Write, repair, evaluate, or security-review prompts, agents, skills, tool descriptions, graders,
  and agent workflow graphs and handoffs. Triggers: 'write a skill for this task', 'my agent chooses the wrong
  tool', 'design a bounded Loop Engineering evaluation', 'review this agent for prompt injection'.
---

# Agent authoring

Start with a request the intended user would actually make. What will they give the agent, and
what output or action would let them get on with their work? Use an example they supplied, a
correction they made, or an accepted result. For a wording edit, preserve the existing meaning
and edit directly. When drafting from scratch, ask for a missing example only if different
answers would materially change the instructions.

## Write for the decision

Identify what the agent needs to know that it could not reasonably infer. Put the condition and
the action it calls for together. For example, a release-note writer needs to know whether the
audience sees a change: “For a renamed setting, give the old name, the new name, and when users
must switch. Omit internal renames that require no user action.” A nearby case with a different
answer often teaches more than another paragraph of rules.

Write for how an LLM actually reads and reasons:

- **Explain the failure mechanism in causal prose, not telegraphic keyword lists.** Models already
  know domain terms from pretraining. A compressed list of noun phrases or slash-separated buzzwords
  (`idempotency / outbox / fencing / p99 / backpressure`) primes the model to mention those words
  superficially rather than execute the reasoning. Connect the situation the agent sees to the
  mechanism that breaks and the concrete check or artifact required—for example: “If 40 app
  instances each open a 20-connection pool and retry 3 times, a traffic spike hits the database with
  800 connections and 4× the write load; bound concurrency and retry budgets across the fleet, not
  just per process.”
- **Counter the model's default biases explicitly.** Left unguided, models tend to agree with an
  over-engineered premise in the user's prompt, summarize in abstract prose instead of inspecting
  code and writing concrete schemas or types, and trace only the happy path. Give explicit
  permission and a concrete contrast for when to push back on the premise, what calculation or code
  sketch proves a claim, and how to walk failure and rollback after live state has already changed.
- **Keep one sequential cognitive flow and state each rule once.** Repeating the same requirement
  across a triage section, a working loop, a lens checklist, and an output template splits
  attention and makes the model echo headings instead of thinking. Order the prompt chronologically—
  boundaries, how to investigate and frame, how to reason through the work, and how to shape the
  output—and put each rule in the one place where that decision happens. Keep shared fleet
  conventions (such as evidence labels) in the repository instructions or a single compact line
  rather than re-teaching them across every prompt.

Use the description to help the host select the skill. Name the task and the situations where it
applies. If a neighboring skill attracts the same requests, make the deciding difference clear.
In a portable Agent Skills package, put `name` and `description` in the frontmatter of `SKILL.md`.
Match the name to its directory. Link supporting resources directly from the entry file where
the reader needs them. Follow the destination project's conventions when they apply.

Describe a tool from the agent’s point of choice. Say when to call it, what the caller needs to
know first, and what a successful call returns or changes. When two tools look plausible for the
same request, name the detail that decides between them. Explain an argument when its meaning is
easy to guess wrong, such as whether an offset counts bytes or characters.

For a task with several valid approaches, describe the result and leave the choice to the agent.
Put a repeatable, fragile operation such as capturing a filesystem snapshot in a tested helper.
Tell the agent when to use it and how failure changes what it can conclude. Enforce permissions
where the action runs.

## Repair the part that failed

| What happened | What to change |
|---|---|
| The skill was available but never selected, or a neighbor was selected | Inspect the description the host actually presented. Try a realistic request on each side of the boundary. |
| The agent received the instruction and still chose poorly | Find the competing instruction, missing fact, or ambiguous condition. Revise it and check the case that exposed it. |
| The tool received the wrong arguments or the consumer rejected the output | Check the actual interface. Describe the ambiguous argument or required output field and validate machine-consumed structure at the boundary. |
| The agent skipped, repeated, or was allowed an action the workflow must control | Inspect the caller, tool, and runtime, including automatic retries. Put the invariant where every path to the effect passes through it. |
| The task succeeded but the grader rejected the method | Grade the observable result. Require exact text, syntax, or tool choice only when a consumer or permission boundary depends on it. |

When designing an agent handoff, identify the work the receiver owns, the state and permissions it
needs, what it must return, and who handles a partial result. Choose a separate agent when that
boundary helps. For a workflow that can pause or fan out, decide what state survives a checkpoint,
which results a join needs, and when the workflow stops. After an interrupted action, establish
whether it took effect before retrying.

## When the task needs more detail

- For a grader, a behavioral comparison, or a bounded evaluation loop, use the
  [evaluation guidance](references/artifact.md).
- For a security review or a change to tool authority, use the
  [agent security guidance](references/agent-security.md).
- For Claude Code configuration, use the [Claude Code reference](references/claude-code-frontmatter.md).
- For a VS Code Copilot custom agent, use the [Copilot reference](references/copilot-frontmatter.md).
  For another host, start with its own artifact format. Consult both hosts when porting between them.
