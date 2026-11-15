# Copilot frontmatter — agents & skills

Use this reference when authoring for VS Code's default Copilot harness. Check the
[agent field reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference)
against the installed client after upgrades; a recognized header does not prove runtime enforcement.
Keep source versions and test evidence in the maintainer's review, not in agent instructions.

## Contents

- Agents
- Tool mapping and discovery
- Skill preloading
- Skills
- Host acceptance
- Portable frontmatter

## Agents

Author the fleet's canonical Claude definitions in `agents/`. Change the repository's adapter
generator, then regenerate; do not hand-edit generated files or add
Copilot-only keys to canonical Claude headers. The workspace reads `.github/agents/`; Agent Plugins
1.0 reads `com.github.copilot/agents/`. Both receive generated `<name>.agent.md` files.

The table separates available fields from this fleet's emission policy. Adding an optional field
requires its projection and checks; copying it into a canonical header does not enable it.

| Field | Copilot use and fleet disposition |
|---|---|
| `name`, `description` | Emitted identity and selection guidance. Description is required; keep procedure in the body |
| `tools` | Emitted nonempty tool names or aliases mapped from canonical grants; effective runtime availability needs observation |
| `model` | Optional scalar or ordered list of host model IDs. Fleet leaves it unset to inherit; do not copy Claude model aliases |
| `model-policy` | Optional `preferred` or `required`. VS Code enforces it for the selected chat agent, not as a runtime-wide restriction; fleet leaves it unset |
| `reasoning-effort` | Optional model-supported value. Fleet inherits; verify on the actual model before choosing an override |
| `skills` | Optional list of skill names to preload into the agent context. Fleet currently emits none; use the preload procedure below before adopting it |
| `user-invocable` | Picker visibility; default `true`. Fleet leaves it unset so humans can select every lane |
| `disable-model-invocation` | Controls whether other agents may invoke this agent; default `false`. Fleet leaves it unset. It is not a per-parent child allowlist |
| `target` | `github-copilot` selects Copilot editor interpretation. It does not switch the executing harness. Standard fleet profiles currently leave it unset |
| `hooks` | Agent-scoped hooks are forwarded, including plugin agents. Standard fleet profiles emit none and the global Copilot hook map is empty. Preserve event, input, output, identity and failure behavior together |
| `strict-tools-list` | Recognized by VS Code but not forwarded during agent conversion. Do not rely on it to suppress default tools |
| `include-custom-instructions` | Recognized but not forwarded. It cannot establish repository-instruction delivery to VS Code child agents |
| `deferred-tool-loading` | Recognized but not forwarded. It cannot establish a discovery mechanism in the converted agent |
| `github` | Recognized MCP toolsets/permissions object, not forwarded. Configure required tools through the host |
| `mcp-servers` | Recognized agent-scoped configuration, not forwarded. Configure servers through the host and verify exact tool IDs |

VS Code also does not forward `model-policy`; its selected-chat enforcement is an editor feature.
Measure repository-instruction delivery in both selected and delegated execution paths. Carry
essential lane rules in the agent body and verify their delivery.

Canonical grants use full plugin names such as `Agent(save-toolkit:reviewer)`. The generator
validates those targets and emits the `agent` alias; Copilot delegates through native `task`.
No equivalent per-parent target restriction has been established for this projection. Keep the
canonical graph in the README roster and preserve that unresolved boundary; do not substitute
visibility flags, prompt instructions, or a hook timeout fallback for enforcement.

## Tool mapping and discovery

Use the documented aliases `read`, `search`, `edit`, `execute`, `web`, `agent`, and `todo` where their
capabilities match the assignment. A tool alias is not a promise of identical tools on every client.
Keep `agent` in frontmatter; a runtime tool called `task` does not require that alias to be renamed.

For each canonical grant, identify its target mapping or intentional omission and the resulting
capability gap. Keep expected omissions explicit: `Skill` is handled through host skill discovery;
`EnterWorktree` and `ExitWorktree` have no Copilot alias and must not become `execute`. Standard
SRE deliberately omits terminal execution. The renderer rejects an empty mapped list before
replacing generated outputs: the VS Code converter turns an empty or missing list into all
session-configured tools. This is not a zero-tool profile. Unknown runtime names can also leave a
nonempty authored list without the intended capabilities; verify resolution separately.

Use qualified client references such as `browser/readPage`, `browser/clickElement`, or an
advertised `vscode/<tool>`. Preserve individual selections instead of granting a whole browser
category. Verify resolution and a representative live call on the intended host.

For MCP, bind `<server>/<tool>` to the configured server and its registered tools. A package name
or another host's identifier does not establish the Copilot identifier. Avoid
`*` and `<server>/*` as repairs for missing mappings. Do not install servers or add credentials as
an implied consequence of editing an agent.

Pair discovery instructions with a mechanism actually provided to that session; `vscode/toolSearch` is conditional on provision and
does not grant access to the tools it finds. If an integration is unavailable, report that lane's
gap and use only a permitted alternative. Update body instructions with mappings rather than
leaving an unconditional reference to an unavailable host-specific tool.

Tool availability, discovery, and authorization are separate checks. A readable schema or a
successful search result does not prove a read-only lane lacks writes or that a child inherits the
intended restrictions. Default-tool additions and selected-versus-delegated differences remain
host questions. Keep intended capability choices in the repository's `docs/copilot-projection.md`.

## Skill preloading

Agent `skills` loads named skill content into the agent's context. Use it for a core method needed
on nearly every assignment; keep conditional language, platform, and task methods on demand.
Scribe's required `operational-docs` is a candidate for a small pilot, not an enabled fleet default.

For a disposable workspace profile whose skill inventory contains `operational-docs`:

```yaml
---
name: scribe-preload-probe
description: Write the requested operational document from supplied evidence.
tools: ['read', 'search', 'edit']
target: github-copilot
skills: ['operational-docs']
---
```

Resolve the skill name from the intended host inventory. Installed plugin command names receive
a namespace, but that alone does not prove the name the preload resolver expects. Test workspace
and installed-plugin resolution independently, from a neutral workspace where local copies cannot
mask missing package resources. Test direct selection and a delegated child separately.

Verify that the skill body is delivered and that the agent follows the requested method. Linked
references are separate resources; preloading the entry file does not establish that they were
read. Preserve required reference reads. Preloading grants no tools or change approval and does
not replace the agent's authority. Keep manual-only deployment skills out of preload lists. Review
lanes must use trusted installed/base guidance, not candidate-controlled methods.

Record the context-size cost and compare the task outcome before making preload a fleet default.
Do not remove essential agent instructions merely because a skill name appears in its header.

## Skills

Workspace skill copies live under `.github/skills/`; the installed Agent Plugins 1.0 package reads
canonical `skills/`. The
[skill header reference](https://code.visualstudio.com/docs/agent-customization/agent-skills#skillmd-file-format)
and [Agent Skills specification](https://agentskills.io/specification) describe different scopes.
Keep skill names bare in their source; the plugin supplies slash-command namespacing.

Every fleet skill emits `name`, `description` (at most 1,024 characters), and `argument-hint`.
Preserve supported skill and command hints. `compatibility` states prerequisites,
not access checks. `user-invocable` stays unset so every skill remains human-invocable.

| Field | Disposition here |
|---|---|
| `disable-model-invocation` | Used by `pcf-deploy` for manual-only invocation. Combining it with `user-invocable: false` disables both entry paths |
| `allowed-tools` | Portable experimental tool preapproval with host-dependent support; it is not a restricting allowlist. Fleet does not use it |
| `context` | Forked skill execution is separate from agent preloading. Fleet leaves it unset; adopt only after checking execution ownership and returned evidence on the intended host |

## Host acceptance

Before claiming compatibility, bind the client/editor, extension and bundled runtime versions,
model, installed artifact, host configuration, and the directly selected or delegated execution path.
Check discovery, effective tools, a representative permitted call, and harmless forbidden actions
rejected before effects. For delegating roles, check allowed and forbidden child targets plus parent
continuation. Test instruction delivery and any preloads and references from the installed package.
For hooks, cover malformed input, missing interpreter, crash and timeout as well as ordinary denial.

Keep generator tests, source inspection, and installed-host results distinct. Record unavailable
checks as unverified in the maintainer's report. The standalone Copilot CLI is a separate surface;
its successful test does not qualify VS Code's default Copilot harness. A missing host does not
justify inventing tool identifiers, weakening a boundary, or treating schema acceptance as release
acceptance. COPILOT-HARNESS-001 and RELEASE-001 retain their respective native gates.

### Portable frontmatter

Host-specific fields may be rejected by packaging or ignored at runtime; do not assume a control
survives projection. The portable six are `name`, `description`, `license`, `compatibility`,
`metadata`, and `allowed-tools`. This fleet writes `compatibility` as one single-line scalar so the
local gate measures its 500-character limit exactly.

Outside the portable specification, which does not mean unsupported by every other host:

- `argument-hint` is used on every fleet skill; VS Code recognizes it, the portable spec does not.
- `disable-model-invocation` makes `pcf-deploy` explicit-only on Claude and VS Code; that invocation
  gate does not travel in portable metadata.
- Other nonportable fields are unused here; agent-file `disallowedTools` and `hooks` do not
  establish skill-header restrictions.

Portable `allowed-tools` does not establish a restricting allowlist. Ignored fields lose their
controls; evaluate effective tool restrictions on the selected host rather than inferring them
from portable metadata or another harness's results.

| Host / spec | Limit | Scope |
|---|---|---|
| GitHub Copilot custom agents | 30,000 characters of Markdown below one `.agent.md` frontmatter | Per generated profile, including its host contract — not an aggregate fleet budget, not a skill-body limit; GitHub does not define "character" (code points vs UTF-16 units), so report the official contract and the counting semantics separately |
| Agent Skills specification | `description` ≤1,024 characters; `SKILL.md` recommended under 5,000 tokens and 500 lines, resources on demand | Authoring recommendations, not body validators |

Before publishing to the portable spec, strip to the portable six and preserve dropped
invocation/authority boundaries in the body. Prose remains cooperative; it does not replace a host
control lost during publication.
