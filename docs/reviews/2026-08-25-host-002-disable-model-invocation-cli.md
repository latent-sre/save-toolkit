# HOST-002 F7 Claude CLI invocation-control observation

**Conclusion:** `[verified]` Claude Code 2.1.243 honored `disable-model-invocation: true` on a
disposable plugin skill. An otherwise identical unguarded control was visible and invoked through
the `Skill` tool; the guarded variant made no Skill call and returned `NOT_VISIBLE`; explicit
`/host002-canary:visibility-canary` invocation still returned the body-only marker.

This closes F7's current installed-Claude-CLI visibility gap. It does not close HOST-002's separate
VS Code invocation-authority or hook-portability criteria, and it does not turn the frontmatter flag
into the manual-only skills' load-bearing safety boundary.

## Contract and exact evidence

`[sourced]` Current official Claude Code documentation says
[`disable-model-invocation: true`](https://code.claude.com/docs/en/slash-commands) prevents Claude
from autonomously invoking a skill, removes its description from model context until triggered,
and preserves manual `/plugin:skill` invocation. The official
[`--plugin-dir` documentation](https://code.claude.com/docs/en/plugins) supports loading a local
plugin for one test session.

`[verified]` The dated
[`CLI transcript`](evidence/host-002/2026-08-25-disable-model-invocation-cli-transcript.md) binds the
run to repository revision `abb02cfd2a38f50c13e8f1e14de77d0cc65c0864`, tree digest
`3749334a1f24b8c388664eb60048fe090d522622d76b23b658c33ac5870d37da`, the exact plugin hashes,
resolved model, tool set, commands, outcomes, limitations, and reported cost. Its matching
evidence-envelope v1 record is
[`2026-08-25-disable-model-invocation-cli.json`](evidence/host-002/2026-08-25-disable-model-invocation-cli.json).

| Arm | Observable result | Verdict |
|---|---|---|
| unguarded control | `Skill(host002-canary:visibility-canary)` called; body marker injected | positive control passed |
| guarded automatic prompt | no Skill call or marker; exact `NOT_VISIBLE` result | guard honored |
| guarded explicit command | exact body-only marker returned | manual path preserved |

The unguarded Haiku control hit the operator-selected budget after the Skill call and body injection,
so its final response did not complete. That does not weaken the visibility oracle: the Skill call
and injected body are the behavior the guarded arm must prevent. A prior Sonnet calibration hit the
same post-dispatch budget behavior and is retained as cost evidence, not silently retried away.

## Remaining boundaries

- Historical Claude Code 2.1.29 and 2.1.212 observations that ignored the field remain valid for
  those builds; the new result is not backported.
- The canonical manual-only roster currently has three skills: `incident-drill`, `pcf-deploy`, and
  `service-onboarding`. Their structural fields are checked separately by repository validation.
- Body-level human approval, no-effect defaults, credentials, and host policy remain load-bearing.
- VS Code tool invocation and exact-agent Copilot hook scoping remain `[unverified]` under HOST-002.
