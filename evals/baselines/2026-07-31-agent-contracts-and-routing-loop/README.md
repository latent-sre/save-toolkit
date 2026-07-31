# Agent contracts and routing loop -- 2026-07-31

## Conclusion

Pinned `reviewer` and `sre` behavior is healthy: both direct contracts passed **2/2** after the
harness learned that a directly selected least-privileged agent can expose fewer tools than the
main-thread `Skill,Task` ceiling. The SRE negative grader was also corrected so the compliant phrase
"No mitigation applied" cannot fail merely because it contains the words "mitigation applied".

Autonomous plugin-agent discovery did not improve in one-shot headless Claude Code. Two reviewer
description variants and two distinct prompts produced **0/9** completed reviewer calls while the
main model answered the substance inline. The merge-readiness collision negative passed **3/3** by
loading `merge-gate` and leaving `reviewer` inactive. Stop tuning adjectives: use direct contracts as
the behavioral gate and retain discovery as a host/model observation.

## Environment and provenance

- Claude Code: `2.1.220 (Claude Code)`
- Resolved model: `claude-opus-5[1m]`
- Final direct-contract plugin commit: `ed2a1b646d2f1ebaaae29103223b568736d56757`
- Final eval-suite SHA-256: `5132437c6bc36d1344d54594dd7293a907348facb22c0c63206fb7f557f9c0f6`
- Final plugin-source SHA-256: `690eb4f5ace843ea7c876cd6382fad04c9be872a70a1d2d9053ebf4156f1794c`
- Intermediate discovery experiments reported base commit
  `12d7d2ff230c0f636ffbe01d2d0267585fef961c` plus dirty plugin-input hashes
- Namespace: one `sre-agents@inline` plugin snapshot, neutral empty Git root, strict empty MCP
- Direct run used `--require-clean-plugin`; description experiments were provisional dirty-input
  runs whose manifests retain full plugin-worktree source hashes, not patch files
- The exact bytes of the first intermediate description were replaced before being committed and are
  not reconstructable from its manifest; that run is diagnostic evidence, not a reproducible baseline
- All retained runs report integrity `PASS` and zero inconclusive trials

Raw transcripts remain private and gitignored under `.eval-runs/`.

## Results

| Run | Scenario | Result | What it established |
|---|---|---:|---|
| `20260731T190634Z-4d243aa3` | direct `reviewer` authz block | 2/2 | Clean `ed2a1b6` run; pinned reviewer catches object-level authz loss and blocks merge |
| `20260731T190634Z-4d243aa3` | direct `sre` read-only triage | 2/2 | Clean `ed2a1b6` run; pinned SRE separates evidence/hypotheses and recommends without acting |
| `20260731T183634Z-80a453a3` | missing-evidence discovery, intermediate wording not retained | 0/3 | Correct inline answers, no attempted agent call; diagnostic only |
| `20260731T184014Z-57d54f90` | same prompt, proactive description | 0/3 | Stronger selection wording made no measured difference |
| `20260731T184328Z-19c3ae63` | supplied open-redirect diff, proactive description | 0/3 | Substantive review also stayed inline; response-shape graders failed with routing |
| `20260731T184854Z-cabe2c35` | reviewer must defer merge readiness | 3/3 | Correct alternative `merge-gate` fired; reviewer did not over-route |

The earlier direct run `20260731T182440Z-770948bf` is superseded because its suite digest predates the
exact frontmatter-derived boundary and final SRE grader hardening. The final direct run above used
`--require-clean-plugin`, matched workspace and snapshot source hashes, and reports integrity `PASS`.

## Accepted changes

- Add pinned direct contracts for `reviewer` and `sre`.
- Derive the exact effective `Skill`/`Task` set from a directly pinned agent's frontmatter; continue
  requiring the full ceiling for main-thread discovery and direct skills, and reject missing or extra
  tools in every mode.
- Use first-person action patterns for the SRE no-mutation grader instead of an unscoped phrase that
  also matches explicit non-action.
- Keep the clearer reviewer description and the merge-readiness negative because the collision test
  passes, but make no claim that the description improved autonomous agent discovery.
- Document the headless routing limit and require explicit agent selection when deterministic
  dispatch matters.
