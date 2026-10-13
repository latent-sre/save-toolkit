# Copilot projection

How `scripts/generate_platform_adapters.py` projects this fleet's canonical agents and skills to
VS Code and GitHub Copilot, and why each lane receives the tools it does. The generator and
`scripts/test_platform_adapters.py` are the source of truth; this file records the decisions they
encode. Field-level host facts live in the
[Copilot & VS Code frontmatter reference](../skills/agent-authoring/references/copilot-frontmatter.md);
installed-host checks live in [VS Code plugin acceptance](vscode-plugin-acceptance.md).

## Adapter behavior

- No field-level equivalence is attempted; intent is preserved in each host's own vocabulary. There
  is no generated preface: a host limitation that changes what a lane may do is stated in that
  lane's own canonical body.
- A skill marked `disable-model-invocation` keeps that frontmatter in the Copilot projection.
- Stating a host authority difference (Copilot's omitted `execute`, for one) is not claiming a
  control: the omitted `execute` narrows a default the user can override and the picker can
  rewrite — read [Capability choices](#capability-choices) before citing it as authority. A fleet
  control is only as strong as the host it is proven on.
- The root manifest declares Agent Plugins 1.0, so the installed plugin reads canonical `skills/`
  and takes Copilot agents and hooks from `com.github.copilot/`. Without that schema VS Code ranks
  `.claude-plugin/plugin.json` first and loads the Claude agents instead; see
  [manifest format detection](vscode-plugin-acceptance.md#manifest-format-detection).

## Body budgets

The SRE assistant has an owner-selected working budget of 25,000 characters in its generated
Copilot body, enforced by the generator for both standard and command-preview profiles. This
repository budget leaves headroom below the provider ceiling; other agents retain the 30,000 limit.

## SRE assistant execution

`sre-assistant` deliberately receives **no** `execute` in the standard projection. Its Claude profile
uses a session-wide Bash/PowerShell guard; acceptance of the VS Code agent-scoped equivalent has
not been established, so the default retains tool absence.

The standard projection also withholds individual terminal tools. A separately exported VS Code
command preview grants only `execute/runInTerminal` and `execute/getTerminalOutput`, sets
`target: vscode`, and adds agent-scoped hooks with Windows/POSIX launchers. It is not an accepted
replacement without a human decision on its best-effort guard and installed-host evidence.
The preview's explicit `--copilot` guard mode uses agent-hook scoping, not Claude's `agent_type`.

## Capability choices

| Lane | Current Copilot capability and reason |
|---|---|
| `software-engineer`, `agent-engineer` | Read/search/edit/execute, scoped delegation, and todo; already able to build and test with the host's shell |
| `observability-engineer` | The same capability groups; already able to query Grafana through commands without a Grafana MCP, under its existing change authority |
| `reviewer` | Read/search/edit/execute, one local evidence helper, and todo; runs checks only in a scratch copy, and outside contributions only in isolated CI |
| `sre-assistant` | Read/search, researcher delegation, and selected native/MCP browser viewing interactions under read-only session controls; the command preview adds only terminal execution/output for reviewed reads |
| `repository-investigator`, `scribe` | File investigation or document edits; shell execution is outside their assignments |
| `reliability-engineer`, `principal-engineer` | Read/search/edit and three scoped evidence helpers; no execute, because design documents are their only writes and live evidence comes through `sre-assistant` |
| `researcher` | Public web access; no local files or shell. Adding exact Context7/GitHits tools needs the target host's registered tool IDs, not wildcard MCP grants. On Copilot cloud agent `web` does not apply, so researcher has no working tool there; route cited research through VS Code or Claude |

Do not broaden `execute` or use `tools: ["*"]` merely to fix a missing interpreter, credential,
or hook path. Copilot's execution tools use the configured terminal; a separate Claude PowerShell
grant is not needed to run PowerShell through Copilot. Tool presence permits execution, not
production changes or access beyond the human's assignment.

## Browser grants

Browser investigation grants are exclusive to the SRE lane. The generator derives native VS Code
`openBrowserPage`, `navigatePage`, `readPage`, `screenshotPage`, `clickElement`, `hoverElement` and
`typeInPage` from the corresponding exact canonical Playwright capabilities. Upstream
`browserChatToolReferenceNames.ts` owns these native names; installed-host availability still
needs verification. There is no wildcard, dialog, upload or page-code grant.
MCP still needs a registered server; native VS Code uses a shared integrated-browser page.
Neither frontmatter nor a viewing-only prompt enforces read-only account rights, secret masking,
origin confinement or image delivery. The
[Grafana visual reference](../skills/grafana/references/visual-verification.md) owns those
prerequisites.
