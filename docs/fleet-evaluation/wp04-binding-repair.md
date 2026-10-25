# WP04 downstream binding repair

[verified] The actual Scenario-102 wrong-downstream control now returns **INCONCLUSIVE**, retaining
`root_entity_at_1: 1` while leaving unsupported edge metrics unavailable. Replacing all four ad
entities with load-generator resources previously returned PASS. Passing the original poisoned
binding map directly to the scorer now produces the same unavailable result. Correct source-bound
controls still PASS. Human semantics and original upstream judging remain separate and unmeasured.

[verified] The defect was the local generator's implicit substring fallback: `re.search` matched
`ad\b` or `ad-.*` inside `load-generator`. Root-only checks did not expose this downstream failure.
The [retained rebuild helper](../../evals/itbench_adapter/bindings.py) now consumes only hash-bound
Kubernetes observations and original GT. [The shared matching policy](../../evals/itbench_adapter/core.py)
requires matching kind and supplied original namespace, exact original names where present,
then full resource-name regex matches before anchored-prefix fallback. It never expands aliases.
Genuine multiple matches remain ambiguous. The assessment boundary independently reapplies this
policy to every consumed binding; existing GT IDs alone cannot authorize a name mapping.

| Case | Before resource-name entries | After | Unsupported entries removed |
|---|---:|---:|---:|
| Scenario-7 | 5 | 5 | 0 |
| Scenario-21 | 24 | 24 | 0 |
| Scenario-24 | 5 | 5 | 0 |
| Scenario-80 | 19 | 19 | 0 |
| Scenario-102 | 16 | 12 | 4 |
| Total | 69 | 65 | 4 |

[verified] The four removed names are Deployment `load-generator`, Pod
`load-generator-57ffcd644-rwl8b`, ReplicaSet `load-generator-57ffcd644`, and Service `load-generator`,
all in `otel-demo`. Their proposed ad Deployment/Pod/ReplicaSet/Service targets did not match original
metadata. All 65 remaining entries were checked against the original source, not just these four.
There are 64 singleton bindings and one legitimate ambiguous Pod binding. Every selected root and
every required original propagation group retains a usable binding.

[verified] The [frozen metadata reference](../../evals/manifests/wp04-binding-metadata.json) preserves
original groups and edge IDs for portable offline controls, with raw GT hashes matching the selected
manifest. A real-source audit also compared this reference with the pinned raw GT files. Neither
original kind/filter/namespace fields nor any alias or propagation was changed.

[verified] Measurement identity is now `wp04-exact-entity-edge-v2`, with policy
`wp04-original-metadata-anchored-name-v1` and binding-file revision2. Known good/wrong-root/unavailable
controls preserve their supported outcomes. The added wrong-downstream counterexample changes
from the demonstrated old PASS to INCONCLUSIVE; it does not become a candidate benchmark result.
Historical v1 controls and original upstream results are not overwritten.

| Current file | SHA-256 |
|---|---|
| `wp04-bindings.json` | `6a336ff92684e3f2e51e7848badcc40538750a186b98a40cca4b7755c0e38081` |
| `wp04-binding-metadata.json` | `67577eebbdee941ee0f51916bba57f6de47f08d453fc1b7cdfe2422e38c7b535` |
| `wp04-itbench-five.json` | `475a8ef189ff60476c2b8257d0901144df017c619b3338ff7a0067e6d152a86d` |
| `wp04-run-plan.json` | `126d1ffcd9f588673c02d6afab4e6c2f098f8a33366f22bb7b995c476028c84f` |

[verified] Only assessment metadata changed in the selected manifest. Its canonical digest is now
`b9c9869928fdbbc89e74f909151063aed3ae65989f960ef6169271f601fd2e7a`; the reused native preparation
records the earlier canonical digest `6b3a395a315d9e4be310ad76cce92a21cff626787b2e9a9b23a0482f61a0b478`.
The identity receipt compares every observation asset with that native receipt and establishes they
are identical. The 458 observation assets, 441,911,602 raw bytes and 499,755,899-byte native YAML
remain unchanged. The large fixture preparation/round-trip checks were reused rather than rerun.

[verified] Fresh checks on review base `efd52266` plus the current working files: 54 focused tests,
Ruff check/format and strict mypy over the WP04 package/CLI. The red test receipt demonstrates the
false PASS before repair; green controls include original-group eligibility, wrong namespace/kind,
whole-name precedence, anchored chaos suffixes, preserved ambiguity, poisoned bindings and a
hash-bound rebuild/tamper check. No full suite, model, native trial, service or installation ran.

Private evidence under `.eval-runs/complex-campaigns/`:

- `wp04-binding-red.xml` and `wp04-binding-green.xml` / final focused JUnit receipt.
- `wp04-binding-audit-v3.json` and `wp04-binding-original-metadata-audit.json`.
- `wp04-bindings-before-p1.json`, the retained CLI rebuild and `wp04-local-controls-v3.json`.
- `wp04-binding-repair-identity.json`, including all consumed source hashes and unchanged observations.

[unverified] Human admission, exact candidate/runner identity, native Windows execution and read
isolation, model/spend approval and original judge configuration remain pending. This repair does
not accept a case or promote a candidate. Root retains integration and release decisions.
