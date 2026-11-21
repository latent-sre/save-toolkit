# Authoring for VS Code Copilot

Create a native workspace agent in `.github/agents/<name>.agent.md`. Use the YAML header for
selection and supported capabilities, and the Markdown body for instructions. For example:

```markdown
---
name: Glossary lookup
description: Look up a project term and report its definition with the source file.
tools: ['read', 'search']
---

Find the definition used by the component in question. If two definitions disagree, cite both
and explain which one that component uses.
```

Choose tools from the inventory available to the target client. Request only the capabilities the
task uses. The editor, the selected harness, and a delegated agent can expose different fields,
tools, or instructions. When a permission matters, inspect the effective tools on the entry point
the user will actually invoke. [Custom agent field reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference)

For a skill, package a `SKILL.md` entry file and its needed resources. Use discovery for conditional
guidance. Preload a skill when the agent needs its instructions on most assignments. For an installed
plugin, a neutral workspace lets you check that the host resolved the shipped skill and its references
without a workspace copy masking a missing file. [Agent skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)

## Porting a definition

Map each required capability to a supported target tool. Check the effect of omitted or empty tool
lists and whether invocation restrictions survive conversion. For example, exposing delegation
does not by itself limit which children the agent can invoke. When the target cannot enforce a
required restriction, use an equivalent runtime control, remove the affected capability, or report
that the restricted workflow is unsupported.

For a portable skill, use the fields defined in the [Agent Skills specification](https://agentskills.io/specification).
Host-specific fields need their own compatibility check. A parser accepting the file establishes
syntax. An observed permitted action and harmless denial can establish the tested boundary.
