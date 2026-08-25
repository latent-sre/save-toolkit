# HOST-002 F7 Claude CLI visibility-canary transcript

- Run ID: `host-002-f7-20260825-130506`
- Task: `HOST-002 / F7`
- Probe checkout: `F:\repos\sre-agents-host-002`
- Revision: `abb02cfd2a38f50c13e8f1e14de77d0cc65c0864`
- Snapshot tree digest: `3749334a1f24b8c388664eb60048fe090d522622d76b23b658c33ac5870d37da`
- Observation window: `2026-08-25T13:05:06Z` through `2026-08-25T13:09:24Z`
- Installed CLI: Claude Code `2.1.243`
- Host: Microsoft Windows 11 Pro, build `26200`, x64
- Repository status before the run: clean
- Live systems touched: Anthropic model API through the already-authenticated local Claude CLI;
  no production, staging, cloud resource, or repository mutation

## Criterion

On the installed Claude CLI, a plugin skill with `disable-model-invocation: true` must be absent
from model-triggerable skill context while remaining available through explicit
`/plugin:skill` invocation.

The paired control and guarded plugins were created outside the repository under
`C:\Users\hawkins\AppData\Local\Temp\host-002-f7-20260825-130506`. Both used plugin name
`host002-canary`, skill name `visibility-canary`, and body-only marker
`HOST002_F7_BODY_6B61BEE9`. Their manifests were byte-identical at SHA-256
`92714e72ff6c5edaa2d7ec2974ac469433ef6045a5710d2c36b56ca63ec5cd7e`. The skill files differed
only by this guarded-variant line:

```yaml
disable-model-invocation: true
```

Control skill SHA-256:
`467cf2057a42bd6ef9ac29bf8bce5780dad0cbd8cf1595f5366f30d0498d02eb`.
Guarded skill SHA-256:
`0e3bc92f06fdca5bde085d642c73a214bb6b2fffb790df948335947e04420190`.
`claude plugin validate` passed both variants with the same non-blocking missing-author warning.

## Shared automatic-discovery prompt

```text
Show the HOST002 F7 visibility canary. Use the matching plugin skill if it is available. Do not
read files or use any other tool. If no matching skill is available, reply exactly NOT_VISIBLE.
```

The paired Haiku arms used the same trusted empty workspace and these controls:

```text
--model haiku
--tools Skill
--permission-mode dontAsk
--setting-sources project
--strict-mcp-config --mcp-config {"mcpServers":{}}
--no-session-persistence
--output-format stream-json --verbose
```

The resolved model was `claude-haiku-4-5-20251001`; the init record reported only `Skill` in the
tool list and no MCP servers.

## Observations

### Unguarded control

- The init record registered `host002-canary:visibility-canary`.
- The model called `Skill` with `skill=host002-canary:visibility-canary`.
- The synthetic skill-body event contained the body-only marker.
- The call then ended `error_max_budget_usd`: the operator-set `$0.02` cap was checked after the
  first request cost had reached `$0.023742`, before the model printed its final response.
- Result for the visibility criterion: positive control passed; the Skill call and injected body
  are the public-boundary events under test. Final-response completion failed for budget reasons.

### Guarded automatic-discovery arm

- The init record still registered the guarded skill as a slash command, proving the plugin loaded.
- The model made no `Skill` call, the body marker never entered context, and the final result was
  exactly `NOT_VISIBLE`.
- The call completed successfully in one turn at `$0.0107564`.

### Guarded explicit-invocation arm

- Prompt: `/host002-canary:visibility-canary`.
- The final result was exactly `HOST002_F7_BODY_6B61BEE9`.
- The call completed successfully in one turn at `$0.0094014`.

### Aborted Sonnet calibration

Before fixing the paired model, a Sonnet control resolved to `claude-sonnet-5`, called the same
Skill, and received the body marker. Its 21,276-token startup cache creation exceeded the
operator-set `$0.05` budget after dispatch; the CLI reported `$0.086931` and
`error_max_budget_usd`. This was an environment/cost limitation, not a guard result, and was not
used as the paired baseline. The cap was chosen by the operator; it was not a repository or user
requirement. Total reported cost across all four calls was `$0.1308308`.

## Verdict and limits

`[verified]` On Claude Code 2.1.243, `disable-model-invocation: true` was honored for the disposable
plugin skill: it prevented model-triggered visibility/invocation while preserving explicit manual
invocation. This is direct installed-runtime evidence and supersedes the current `[unverified]`
state for that exact CLI build.

The result does not erase the historical CLI 2.1.29 and 2.1.212 counter-evidence, prove another
version or host, make the flag portable, or replace the three manual-only skills' body-level human
approval and no-effect boundaries. It also does not establish VS Code `execute` authority, Copilot
managed-policy enforcement, or hook payload identity.
