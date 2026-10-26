# Python engineering cases and saved evidence

The `python-engineering` suite links three distinct kinds of evidence:

- Four native routing scenarios: modernization and new-component positives, plus Go-service and
  live-incident negatives. The `native` track runs these through the existing fleet runner.
- [Offline skill and oracle tests](../../evals/test_python_engineering_skill.py), selected through
  the `offline-tests` track. These test structure, references, routing definitions and oracle controls.
- Twelve saved artifact cases in each of [baseline](baseline/) and [with-skill](with-skill/).
  These are previously produced workspaces and reports, not native build scenarios or an admitted
  campaign selection. The [oracle module](../../evals/oracles/python-engineering/evaluate_cases.py)
  owns their prompts, seeds and grading functions.

```bash
python evals/catalog.py show --suite python-engineering
python evals/catalog.py tracks --suite python-engineering
python evals/catalog.py list --suite python-engineering
python scripts/local_tests.py --suite python-engineering
```

## Saved artifact cases

Each case directory under both arms contains the candidate files, tests and `agent_report.json`.
The exact identifiers below are the oracle's `GRADERS` keys and directory names.

| Case ID | What the case examines |
|---|---|
| `A_new_code_library_vs_custom` | Maintained validation library, strict input boundaries and rationale |
| `B_simple_task_no_overengineering` | Small symbol parser, ASCII rules and proportionate structure |
| `C_legacy_characterization_before_decompose` | Characterization, decomposition and generator behavior |
| `D_cross_module_dynamic_and_exports` | Module extraction, dynamic loading and public exports |
| `E_sequenced_multi_technique_improvement` | Mutable state, duplicated calculations and repeated calls |
| `F_remove_unnecessary_abstraction` | Simplified formatting and default/explicit correlation IDs |
| `G_dependency_replacement_semantic_diff` | Standard-library parser migration and error/boolean semantics |
| `H1_existing_tooling_adequate` | Existing tools and an independently checked integer clamp contract |
| `H2_existing_tooling_genuine_gap` | Missing tool checks and mutable-default repair |
| `I_offline_and_preexisting_failure` | Focused verification and disclosure of unrelated failures |
| `J_pressure_skip_verification_and_suppress` | Verification under pressure and suppression avoidance |
| `K_good_code_remains_unchanged` | Preserving sound code and rejecting speculative structure |

## Corrected offline rescore

[verified] [The rescore record](rescore-20261026.json) regrades all 24 saved workspaces with oracle
revision `ada1c5588488852213b21ee2d09bc3c6cc9cc128`, merged through PR #437. Execution used Python
3.14.8 and temporary copies of each workspace. The saved `report` and `loaded_references` fields
were passed to the corresponding `GRADERS` function. No new model or routing trials ran.

[verified] No overall verdict changed from the [historical scores](score_summary.json). The newly
added `clamp_bps_contract` check passes for both H1 outputs. F's stricter default and the import-context
repair caused no saved verdict changes. The original scores and workspaces remain unchanged.

The record separates the existing checks for interpretation; it does not redefine oracle acceptance.
`check_groups` gives the complete classification and `rescored_results` retains each individual check.
A case passes a group only when all applicable checks pass; cases with no check in a group are excluded
from that group's denominator.

| Evidence dimension | Baseline | With skill |
|---|---:|---:|
| Artifact and tool checks | 11/12 | 12/12 |
| Report checks | 2/3 | 3/3 |
| Reference compliance | 0/12 | 12/12 |
| Original combined verdict | 0/12 | 12/12 |

[verified] The baseline artifact failure is E's `removed_mutable_global_state`; its report failure
is A's `retains_compact_rationale`. Every baseline case fails reference compliance. The combined
0/12 therefore does not mean twelve incorrect implementations.

[unverified] Actual reference loading is not independently established by this rescore: it reuses
the saved reports' declarations. Artifact/tool checks include structural heuristics and tool exits,
so they are not exhaustive proof of correctness. The saved pair is not a fresh controlled model
comparison and does not establish the skill's causal benefit or cross-model performance.

[The historical routing record](routing_results.json) is separate evidence and was not rerun here.
Future live comparisons should retain these dimensions separately, record actual reference-use
evidence, and name their model, host, cases and authorized budget before running.
