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
  name via `GUARDED_AGENT_NAMES`, which already lists `sre-assistant` — step 1
  restores the agent under that name, so nothing here needs adding. Re-prove
  the guard's behavior for it with `scripts/guard-session-preflight.py` before
  the agent runs against a real environment.

## 5. Restore steps

1. Copy `agents/sre.md` from this folder over `agents/sre-assistant.md` and set
   its frontmatter to `name: sre-assistant`. The rename stays: a second agent
   named `sre` beside `sre-assistant` fails the fleet validator's roster check,
   and restoring the old name means reversing commit 122070f5 across the guard
   roster, the generator roster, the validator's `EXPECTED_AUTHORITY` and
   `EXPECTED_DELEGATION`, the manifests, and the tests.
2. Copy `skills/investigation-depth/` and the two scenarios from this folder
   back to their source paths.
3. Apply the name token to the restored files: replace the whole word `sre`
   (not inside `sre-assistant`, `sre-ladder`, `sre-context-resolver`, or a
   domain such as `sre.google`) with `sre-assistant` in the restored skill and
   both scenarios. They predate the rename, and the shared handoff `## Rules`
   block test compares bytes across agents.
4. `git apply archive/incident-autonomy/patches/*.patch`. The two
   `evals-rubrics*` patches re-add the three rubrics and their 35 cases, so the
   YAML fragments in this folder are reference copies, not a step.
5. `python scripts/generate_platform_adapters.py --write`.
6. Raise `agents_bytes` and `skills_bytes` in `scripts/weights.json` to the
   measured totals in the same diff. The 2026-09-03 dry run of these steps
   measured 119,023 B of agents and 641,444 B of skills against ceilings of
   115,000 and 640,000.
7. `python scripts/gate_a.py` (PASS 4/4 in the dry run), `python -m pytest
   scripts evals -q` (445 passed), `python evals/build_probe.py --validate` (61
   specs).
