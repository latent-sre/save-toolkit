# Authoring for Claude Code

For a project subagent, put a Markdown definition in `.claude/agents/`. A user-level subagent goes
in `~/.claude/agents/`. Use the description to distinguish its assignment from neighboring agents
and the body to tell it how to carry out that assignment. A project definition for a glossary
lookup could start with this header:

```yaml
---
name: glossary-lookup
description: Find a project's definition for a term and cite where it is defined.
tools: Read, Grep, Glob
---
```

Give the agent just the capabilities the task needs. An omitted `tools` field inherits the
parent's available tools. Plugin packaging, direct selection, delegation, and conversation forks
can change the effective permissions or context. For example, a main-thread coordinator can scope
delegation with `Agent(worker)`. That target list applies to the main-thread agent. Check the
effective grants of a delegated child separately. A shell grant brings the capabilities of the underlying process.
Consult the [subagent field reference](https://code.claude.com/docs/en/sub-agents#frontmatter-reference)
and [permission rules](https://code.claude.com/docs/en/permissions) for the target configuration.

For reusable instructions that run in the caller's context, use a skill directory containing
`SKILL.md`. Keep the procedure in its body and mention optional resources where they are needed.
If the skill never fires, inspect the loaded skill listing and any discovery-budget diagnostics
before rewriting its description. Use host-specific invocation or permission fields only when the
requested behavior depends on them. [Claude Code skills](https://code.claude.com/docs/en/skills)

When a change depends on isolation, inspect what the actual entry point loads from the workspace,
user settings, parent history, and tools. A fresh disposable workspace with synthetic markers can
show which sources actually reach the agent. When porting to another host, establish an equivalent
control or narrow the target capabilities. Report any required restriction the target cannot enforce.
