# archive/incident-autonomy

## 1. What this is

Byte-exact copies of the incident-autonomy machinery removed from the live tree:

- The `sre` agent's sustained-response design: it owns the technical incident
  record through recovery, using the `incident-state/v2` JSON contract.
- The `investigation-depth` mode-ladder skill that the `sre` agent used to
  scale investigation depth to incident severity.
- The evals that exercised sustained-response behavior: two scenarios and the
  three rubrics (with their calibration cases) that graded them.

Parked on 2026-09-03. The fleet's incident lane is the human-facing
`incident-investigation` advisor plus a thin, dispatched, read-only helper.
Nothing in the repository can yet drive this sustained-response machinery
unattended (see Section 4).

## 2. Source

Every copy in this folder is byte-exact from commit `8a997e68` (`main`,
2026-09-03). To prove any single file, run one of:

```
git diff --no-index <(git show 8a997e68:<source path>) <archive path>
git show 8a997e68:<source path> | diff - <archive path>
```

Both commands print nothing when the archive copy matches the commit exactly.

The two eval fixtures under `evals/` (`rubrics.yaml` and
`rubrics-calibration.yaml`) are extracted fragments, not full-file copies —
see Section 5 for what "verbatim" means for those two.

## 3. Manifest

| Source path | Archive path | Bytes |
|---|---|---|
| `agents/sre.md` | `archive/incident-autonomy/agents/sre.md` | 20032 |
| `.github/agents/sre.agent.md` | `archive/incident-autonomy/agents/sre.agent.md` | 21229 |
| `skills/investigation-depth/SKILL.md` | `archive/incident-autonomy/skills/investigation-depth/SKILL.md` | 7619 |
| `skills/investigation-depth/references/first-response.md` | `archive/incident-autonomy/skills/investigation-depth/references/first-response.md` | 3728 |
| `skills/investigation-depth/references/hypothesis-investigation.md` | `archive/incident-autonomy/skills/investigation-depth/references/hypothesis-investigation.md` | 4057 |
| `skills/investigation-depth/references/incident-handoff.md` | `archive/incident-autonomy/skills/investigation-depth/references/incident-handoff.md` | 2275 |
| `skills/investigation-depth/references/recovery-lifecycle.md` | `archive/incident-autonomy/skills/investigation-depth/references/recovery-lifecycle.md` | 5410 |
| `skills/investigation-depth/references/signal-characterization.md` | `archive/incident-autonomy/skills/investigation-depth/references/signal-characterization.md` | 3063 |
| `skills/investigation-depth/references/systemic-failure.md` | `archive/incident-autonomy/skills/investigation-depth/references/systemic-failure.md` | 3565 |
| `evals/scenarios/agent-direct-sre-owns-recovery-to-terminal.yaml` | `archive/incident-autonomy/evals/scenarios/agent-direct-sre-owns-recovery-to-terminal.yaml` | 3886 |
| `evals/scenarios/agent-direct-sre-records-unknown-recovery-progress.yaml` | `archive/incident-autonomy/evals/scenarios/agent-direct-sre-records-unknown-recovery-progress.yaml` | 4618 |
| `evals/rubrics.yaml` (3 rubrics extracted, see Section 5) | `archive/incident-autonomy/evals/rubrics.yaml` | 2666 |
| `evals/rubrics-calibration.yaml` (35 cases extracted, see Section 5) | `archive/incident-autonomy/evals/rubrics-calibration.yaml` | 14755 |

Folder total: 102261 bytes across the 13 files above, plus this README.

## 4. What a restore needs before this can run unattended

- **A trigger loop.** Nothing today invokes the agent when an alert fires or
  re-invokes it with its prior `incident-state/v2` record. The sustained-
  response design assumes an external loop that re-dispatches the agent
  across the recovery window; that loop does not exist in this repository.
- **Read paths to the team's signals.** The agent does not have read access
  to Splunk, Wavefront/PCF App Metrics, Grafana, or Apps Manager today. The
  sustained-response design assumes it can read these to characterize
  signals and track recovery; those integrations must be built first.
- **The read-only guard.** `scripts/readonly-guard.py` gates Bash by agent
  name via `GUARDED_AGENT_NAMES`. A restored agent named `sre` must be added
  back to that list, and the guard's behavior for it re-proven with
  `scripts/guard-session-preflight.py` before the agent runs against a real
  environment.

## 5. Restore steps

1. Copy the files in the manifest back to their source paths.
2. Re-add the three rubrics (`recovery_authority_held`,
   `unknown_progress_not_invented`,
   `progress_consistent_with_record`) from `evals/rubrics.yaml` in this
   folder into the live `evals/rubrics.yaml`, and the 35 calibration cases
   from `evals/rubrics-calibration.yaml` in this folder into the live
   `evals/rubrics-calibration.yaml`.
3. Apply the patches under `patches/`: `git apply archive/incident-autonomy/patches/*.patch`.
   Each is a reverse diff for one file shared with machinery that stays live, taken from the
   cut commit back to the commit before it (so they name the agent `sre-assistant`, the
   post-rename name; restoring the archived `sre` body means adding `sre` to
   `GUARDED_AGENT_NAMES` as Section 4 says). The two `evals-rubrics*` patches re-add exactly
   the fragments in step 2, so applying them makes step 2 unnecessary. The set: the fleet
   validator's conditional-handoff rule and its tests, the context-cost path entry, the
   `skill_loaded` check in the guarded-triage build probe, the forbidden-schema line in the
   read-only triage scenario, `incident-command`'s close-and-return section, `eng-ladder`'s
   description sentence, the AGENTS.md roster row, the README catalogue line, the rubric
   files, and the roadmap's ROUTE-005 item.
4. Regenerate adapters: `python scripts/generate_platform_adapters.py --write`.
5. Run `python scripts/gate_a.py` and confirm it passes.
