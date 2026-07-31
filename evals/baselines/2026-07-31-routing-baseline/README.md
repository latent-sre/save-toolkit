# Routing and direct-contract baseline -- 2026-07-31

## Conclusion

The post-hardening harness shows that autonomous discovery remains unreliable: positive **skill
discovery passed 5/6**, while positive **agent discovery passed 0/4**. The manual-only `pcf-deploy`
negative control passed 2/2, the pinned `merge-gate` direct contract passed 2/2, and every discovery
response grader passed.

The missed routes were not bad answers. `reviewer` and `merge-gate` requests stayed inline. Both
staging-incident trials loaded `incident-command` (plus related SRE skills) and answered correctly
but never delegated to the `sre` agent. Response-only scoring would therefore have hidden the
routing gap.

No agent or skill prompt changed before or between the retained runs.

## Frozen subject and harness

- Plugin commit: `73d448c2c8a8f4a926d6501a3ddcefcdb1968239`
- Frozen plugin SHA-256: `c3cd191243505d635ca8c693763ec06d1660be709ec6c5b1e32f27def25147bb`
- Eval suite SHA-256: `26fb2112bcc4f755d39eb893e60825f8b51e3ce9b8d63dff046f859ac10e0830`
- Claude Code: `2.1.220 (Claude Code)`
- Resolved model: `claude-opus-5[1m]`
- Execution image: stable eval-suite and plugin snapshots per batch, each hash-checked before and
  after execution
- Namespace: exactly one `sre-agents@inline` plugin at the snapshot path, built-ins `Task,Skill`,
  neutral empty Git-root fixture, and strict empty MCP
- Trials: 2 per scenario; threshold: 1.0
- Inconclusive trials: 0
- Integrity failures: 0

`plugin_inputs_dirty` was false and `--require-clean-plugin` passed. A parent bootstrap first copied
the runner, graders, clean-room code, and scenarios, verified their digest, then ran that image. Each
model process loaded the stable plugin snapshot rather than the mutable worktree; runtime init events
matched its exact name, version, source, and path. Scenario hashes were bound to the bytes loaded
from the eval snapshot, and each retained summary passed both end-of-run integrity checks.

The overall worktree was dirty at measurement time because the new harness and scenarios were being
prepared for this commit, while `plugin_inputs_dirty` remained false. The eval-suite digest above
binds the exact executed bytes; this report and those suite bytes are committed together.

## Results

| Split | Scenario | Expected route | Target result | Response graders |
|---|---|---|---:|---:|
| Calibration | `discovery-diagnose-before-fix` | Skill `root-cause` | 1/2 | 2/2 |
| Calibration | `discovery-independent-change-review` | Agent `reviewer` | 0/2 | 2/2 |
| Calibration | `discovery-merge-readiness` | Skill `merge-gate` | 2/2 | 2/2 |
| Held-out | `discovery-manual-deploy-does-not-autofire` | Keep manual-only `pcf-deploy` inactive; refuse inline | 2/2 | 2/2 |
| Held-out | `discovery-runtime-boundary` | Skill `stack-profile` | 2/2 | 2/2 |
| Held-out | `discovery-staging-incident-triage` | Agent `sre` | 0/2 | 2/2 |
| Direct calibration | `merge-gate-blocks-untested` | Explicitly pin `merge-gate`; return BLOCKED | 2/2 | 2/2 |

Across positive discovery cases, completed target invocation was **5/10**: skills were **5/6** and
agents were **0/4**. The negative control passed **2/2** and direct contract compliance passed
**2/2**. All 12 discovery responses passed their deterministic response graders.

## Retained run manifests

Raw transcripts remain local, private, and gitignored under `.eval-runs/`; they are not publication
artifacts. The run IDs make the local evidence traceable:

- Calibration discovery: `20260731T174153Z-cde3d6ae` -- 1/3 scenarios, 3/6 trials
- Held-out discovery: `20260731T174849Z-670344a6` -- 2/3 scenarios, 4/6 trials
- Direct contract: `20260731T175458Z-39593492` -- 1/1 scenario, 2/2 trials

All three summaries report integrity `PASS`, zero inconclusive trials, one matching plugin, zero MCP
servers, and exactly `Task,Skill`. After the run, all 261 `.eval-runs` paths--including superseded
traces from harness development--were checked on NTFS with zero empty or non-owner ACLs.

## Interpretation and next experiment

This is a small routing baseline, not a fleet-wide quality score. It covers two agent descriptions,
three autonomous skill descriptions, one manual-only skill, and one pinned skill contract on one
model/CLI combination. The result supports measured description improvements next, but it does not
justify broad prompt rewrites. Provisional batches and the final batch varied between 0/2 and 2/2
for some skill routes, which is a warning that two trials are enough for a baseline signal, not a
stable quality estimate.

The next loop should add pinned direct-contract scenarios for `reviewer` and `sre`, then tune only
the calibration `reviewer` description one change at a time. Re-run calibration with at least three
trials and add a genuinely new agent-routing held-out prompt; do not tune against the consumed
staging-incident transcript. Preserve the `pcf-deploy` negative control throughout.
