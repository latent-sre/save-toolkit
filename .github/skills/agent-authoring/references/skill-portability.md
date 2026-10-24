# Skill portability — which frontmatter survives off Claude Code

Use this cross-host checklist alongside the field contracts in
[Claude frontmatter](./claude-code-frontmatter.md) and
[Copilot frontmatter](./copilot-frontmatter.md). Host-specific fields may be rejected by packaging
or ignored at runtime; do not assume a control survives projection.

## The portable six

`name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`; limits and
fleet dispositions are in the Skills table of
[Copilot & VS Code frontmatter](./copilot-frontmatter.md#skills). This fleet writes `compatibility`
as one single-line scalar so the local gate measures its 500-character limit exactly.

## Claude-only fields

“Claude-only” here means outside the portable specification, not unsupported by every other host.

- `argument-hint` is used on every fleet skill; VS Code recognizes it, the portable spec does not.
- `disable-model-invocation` makes `pcf-deploy` explicit-only on Claude and VS Code; that invocation
  gate does not travel in portable metadata.
- Other nonportable fields are unused here. VS Code recognizes `user-invocable` and experimental
  `context: fork`; its `disallowedTools` and `hooks` support on agent files does not establish
  support for skill-header restrictions. See the owning host tables before adopting a field.

Portable `allowed-tools` preapproves tools; it does not restrict them. Ignored fields remove their
controls, and VS Code tool lists are user-overridable defaults, not an enforcement boundary.

## Host size limits are not interchangeable

| Host / spec | Limit | Scope |
|---|---|---|
| GitHub Copilot custom agents | 30,000 characters of Markdown below one `.agent.md` frontmatter | Per generated profile, including its host contract — not an aggregate fleet budget, not a skill-body limit; GitHub does not define "character" (code points vs UTF-16 units), so report the official contract and the counting semantics separately |
| Agent Skills specification | `description` ≤1,024 characters; `SKILL.md` recommended under 5,000 tokens and 500 lines, resources on demand | Authoring recommendations, not body validators |
| VS Code | No matching body-length check in public source | — |

## Checking a skill before publishing to the portable spec

Strip to the portable six and preserve dropped invocation/authority boundaries in the body.
Prose remains cooperative; it does not replace a host control lost during publication.
