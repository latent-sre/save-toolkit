# Fleet mutation sweep — 2026-08-15

**Status:** findings only. Everything below is **discovered and not fixed**. No test was changed, no
control was repaired, no typed record was opened, and nothing here is a promotion, an approval, or
evidence that any item may close. A survivor is not automatically a defect.

| Field | Value |
|---|---|
| Revision swept | `e163d2d` |
| Command | `python3.12 scripts/mutation_guard.py --module <path>`, unbounded |
| Interpreter | Python 3.12, the repo-pinned version |
| Coverage | 6 modules completed of 24 planned; the run was stopped early |

## Why 3.12 matters

`mutation_guard` shells out with `sys.executable`. Under this container's default Python 3.11 the
`clean_room` pairs fail their baseline for an unrelated reason — `shutil.rmtree(onexc=)` is 3.12+ —
and the guard correctly but uselessly reports `UnverifiablePair`. A cost model confirmed all 38
discovered pairs pass their baseline under 3.12 before any sweeping began.

## Read the population, not just the survivor count

`[verified]` The guard's operator set is boolean-operand drop, comparison swap, not-removal, and
boolean-constant flip. Code built from anything else — string transformation, arithmetic, dict and
set construction — generates **no mutants at all**, and the guard then reports it clean while
proving nothing about it. Earlier today that produced a false clean over a function that contained a
live bypass. Every figure below therefore carries its population.

## Results

| Module | Mutants | Survivors | Rate | Exit |
|---|---|---|---|---|
| `scripts/release_contract.py` | 68 | 35 | 51% | 1 |
| `scripts/release_workflow_contract.py` | 77 | 33 | 43% | 1 |
| `scripts/readonly-guard.py` | 107 | 22 | 21% | 3 |
| `evals/graders.py` | 167 | 54 | 32% | 1 |
| `scripts/mutation_guard.py` | 72 | 31 | 43% | 1 |
| `skills/…/packet_drift.py` | 48 | targeted check only | — | — |

`scripts/validate_fleet.py` was interrupted mid-run and has no result. Eighteen planned modules were
not reached; they are listed at the end so the gap is explicit rather than implied covered.

## Finding 1 — a confirmed fail-open in the read-only guard

`[verified]` `scripts/readonly-guard.py:530` reads
`if not segments or not all(_segment_allowed(segment, agent) for segment in segments):`.
Dropping the `not segments` operand survives the suite. Because `_split_segments` already filters
empty segments, an input of only shell separators yields `segments == []`, and `all([])` is `True`,
so the mutant stops denying and the function returns `True`.

Confirmed by consequence rather than inferred from source. The guard and four mutants were copied to
a scratch directory — the repository file was never modified — and each was fed a real `PreToolUse`
payload:

| Command | pristine | drop `not segments` | drop `"/" in command` | tokenizer mutants |
|---|---|---|---|---|
| `git status` | ALLOW | ALLOW | ALLOW | ALLOW |
| `git push` | DENY | DENY | DENY | DENY |
| **`;`** (separators only) | **DENY** | **ALLOW** | DENY | DENY |
| `/bin/cat /etc/passwd` | DENY | DENY | DENY | DENY |
| `echo hi; git push` | DENY | DENY | DENY | DENY |
| `cf logs app --recent` | ALLOW | ALLOW | ALLOW | ALLOW |

`[verified]` The direction is fail-open, in a control whose whole purpose is to fail closed, and no
test pins it. `[verified]` Exploitability is low: the permitted string executes nothing. The finding
is that the boundary is unpinned, not that a live bypass exists.

### Correctly classified as NOT gaps

- `[verified]` The three `"/" in command or "\\" in command or "=" in command` survivors are
  **equivalent**. `_segment_allowed` ends in `return command in _SIMPLE_READERS`, so `/bin/cat` is
  denied by the positive allowlist regardless. The path check is deliberate defence-in-depth.
- `[verified]` The `agent`-detection survivors at 591, 599, and 600 make the guard deny **more**,
  not less. Over-denial, not fail-open.
- `[unverified]` The `shlex` tokenizer survivors (`posix=True`, `whitespace_split=True`) changed no
  verdict across 24 probes covering quoting, subshells, comments, tabs, and every separator form.
  That is evidence of equivalence, not proof, and is not claimed as proof.

## Finding 2 — the release authority contracts are largely unpinned

These are the fail-closed contracts RELEASE-001's acceptance depends on. `[verified]` The survivors
cluster on the authority checks themselves, not on incidental code.

`scripts/release_contract.py` — 35 of 68:

| Line | Unpinned contract |
|---|---|
| 78, 114 | `path.is_symlink() or not path.is_file()` — nothing proves a **symlink is rejected**; `is_file()` follows the link, so dropping the symlink operand accepts it |
| 262, 264, 266 | every **approval-expiry boundary** — `expiry <= evaluated_at`, `expiry <= issued_at`, and the `MAX_APPROVAL_LIFETIME` comparison all swap `<=`↔`<` / `>`↔`>=` unnoticed |
| 71, 228, 256 | UTC-offset and tz-aware validation on `issued_at` / `expires_at` |
| 98, 100, 106 | manifest `name == "save-toolkit"` and version-type validation |
| 335–338 | `required=True` on `--candidate-sha`, `--version`, `--run-id`, `--actor` |

`scripts/release_workflow_contract.py` — 33 of 77. The sharpest single result in the sweep:

| Line | Unpinned contract |
|---|---|
| 218, 230 | `reservation < 0 or create_tag < 0 or reservation > create_tag` — **all five mutants survive**, so the invariant that the version reservation precedes tag creation is entirely unpinned, in both the read and write variants |
| 150, 196, 202 | `cancel-in-progress: false`, `RUN_ATTEMPT: ${{ github.run_attempt }}`, and `bypassActors.length !== 1` / `excludes.length !== 0` |
| 108–113 | the block-scalar YAML reader the other checks are built on |

`[unverified]` No claim is made that any of these is exploitable, or that the workflow is wrong. The
claim is narrower and still serious: **the suite that mutation-checks the release authority boundary
is not itself mutation-proof**, so a future edit to those predicates could pass CI unnoticed.

## Finding 3 — `evals/graders.py` and `scripts/mutation_guard.py`

`[verified]` 54 of 167 and 31 of 72 respectively. Both are recorded in detail in the two packets
dated today; the `graders.py` figure is identical at `d9d3c19` and after this session's change, so
those are pre-existing gaps in the other graders rather than a regression.

## Method notes worth keeping

- `[verified]` The batch driver aborts if the tree is not clean after any module. The guard restores
  its subject in a `finally`, but a failure to restore would make every later result a measurement
  of corrupted source.
- `[verified]` Stopping the batch with a signal skips that `finally`, and the interrupted module was
  left mutated. `git restore` recovered it exactly as the guard's docstring promises, and
  `test_readonly_guard.py` passed afterwards. The documented recovery path works.
- `[verified]` Mutant consequence was checked on copies outside the repository, so the sweep in
  progress was never disturbed.

## Not reached

`validate_fleet.py` (interrupted), `validate_improvements.py`, `evidence_envelope.py`,
`verification_sandbox.py`, `clean_room.py`, `codex_routing_grade.py`, `codex_bootstrap.py`,
`codex_harness.py`, `codex_hook_recorder.py`, `codex_model_catalog.py`, `codex_snapshot.py`,
`run_codex_routing.py`, `run_evals.py`, `fleet_doctor.py`, `check_links.py`, `check_stale_names.py`,
`install_codex_agents.py`, `gate_a.py`, and the three `migrate_*` / `packet_drift` pairs.

Also never swept, and the most expensive three by far (~166 minutes combined):
`host_install_probe.py` (553 mutants), `evals/codex_trial.py` (416), and
`knowledge_update.py` (306). `host_install_probe.py` is where RELEASE-001's recorded
authority-census false pass lives, so it is the one worth running next.

## What I did NOT do

- Did not change any test, control, or contract; nothing here is repaired.
- Did not open a typed `fi_` record. The read-only guard fail-open and the release-contract gaps
  each plausibly meet the improvement lifecycle's bar for a material safety/authority failure, but
  opening records is a disposition call and the evidence above is what that call needs.
- Did not claim any finding is exploitable, or that any survivor is definitely a defect.
- Did not modify the repository copy of `readonly-guard.py` while testing its mutants.
