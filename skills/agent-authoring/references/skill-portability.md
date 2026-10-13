# Skill portability — which frontmatter survives off Claude Code

A skill has two audiences. The portable Agent Skills specification
accepts six fields; Claude Code accepts those plus a Claude-only set. A Claude-only field is
**rejected** by Anthropic's packaging script when publishing to the portable spec, and silently
dropped by a host that ignores it. This fleet ships a Claude plugin *and* generates Copilot/VS Code
adapters; the generator absorbs the difference, and this file maps what it has to absorb.
`claude-code-frontmatter.md` owns what each field *does*; this file records where it is honored.

## The portable six

`name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`. Their limits
and fleet dispositions are in the Skills table of
[Copilot & VS Code frontmatter](./copilot-frontmatter.md#skills); this fleet writes `compatibility`
as one single-line scalar so the local gate measures its 500-character limit exactly.

## Claude-only fields

"Claude-only" means the portable spec, not every host; VS Code has its own Claude-dialect support.
Verify against the host you ship to.

| Field | Fleet use | Off-Claude behavior |
|---|---|---|
| `argument-hint` | Every skill | Dropped by the portable spec; recognized by VS Code |
| `disable-model-invocation` | `pcf-deploy` | Dropped by the portable spec, so the side-effect gate does **not** travel there; VS Code honors it (default `false`), which makes the Copilot copies explicit-only |
| `user-invocable` | not used | Dropped by the portable spec; recognized by VS Code (default `true`) |
| `disallowed-tools` | not used | Dropped by the portable spec and absent from VS Code's skill header; VS Code's `disallowedTools` applies only to Claude-format agent files |
| `context`, `agent`, `background` | not used | Dropped; `context: fork` exists in VS Code behind an experimental setting |
| `paths`, `shell`, `model`, `effort`, `hooks`, `when_to_use`, `arguments` | not used | Dropped by the portable spec; VS Code recognizes `hooks` on agent files |

**The portable set can only grant, never restrict.** Authority expressed through a field the target
host ignores vanishes silently at publication. A field a host happens to honor is a convenience,
never a control you may cite — VS Code's tool list is user-overridable, so even a recognized
restricting field is a default there.

## Host size limits are not interchangeable

| Host / spec | Limit | Scope |
|---|---|---|
| GitHub Copilot custom agents | 30,000 characters of Markdown below one `.agent.md` frontmatter | Per generated profile, including its host contract — not an aggregate fleet budget, not a skill-body limit; GitHub does not define "character" (code points vs UTF-16 units), so report the official contract and the counting semantics separately |
| Agent Skills specification | `description` ≤1,024 characters; `SKILL.md` recommended under 5,000 tokens and 500 lines, resources on demand | Authoring recommendations, not body validators |
| VS Code | No matching body-length check in public source | — |

## Checking a skill before publishing to the portable spec

Strip it to the portable six and confirm the body still carries the behavior any dropped field
enforced. A skill whose safety depended on `disable-model-invocation` or `disallowed-tools` must
state that boundary in its own prose — off Claude, nothing else holds it.
