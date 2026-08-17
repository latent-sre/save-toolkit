# Skills surface and parser-divergence sweep — measurements

> **Status: historical — measurement evidence for a single sweep.** Not a task list. The work it
> supports is tracked as `SKILL-001`, `ROUTE-002` and `SCRIPTS-001` in
> [`fleet-roadmap.md`](../fleet-roadmap.md).

**Date:** 2026-08-17 · **Tree:** `main` at `8394d3f` · **Python:** 3.12

This file exists because three roadmap items were first written citing an unlinked "skills sweep"
whose numbers no reader could reproduce or assess. Every load-bearing figure below is re-measured
here with the command that produces it, and labelled. Where a claim is a judgment rather than a
measurement, it says so instead of borrowing the authority of the numbers around it.

## The oversized-skill set, by a stated criterion

A skill is counted when **`SKILL.md` is at least 8,000 bytes and its `references/` total is smaller
than `SKILL.md` itself** — that is, the bulk of the content is inline and unconditional rather than
routed to on demand. The threshold is a judgment; the membership that follows from it is not.

```
python3 - <<'PY'
import pathlib
for s in sorted(pathlib.Path("skills").iterdir()):
    sk = s / "SKILL.md"
    if not sk.is_file():
        continue
    size = sk.stat().st_size
    refs = list((s / "references").rglob("*.md")) if (s / "references").is_dir() else []
    rb = sum(r.stat().st_size for r in refs)
    if size >= 8000 and rb < size:
        print(f"{s.name:24} {size:6}  refs={len(refs):2} ({rb}B)")
PY
```

`[verified]` — eight skills, of 29 total:

| Skill | `SKILL.md` | references | reference bytes |
|---|---:|---:|---:|
| `ops-tooling` | 14,607 | 2 | 7,202 |
| `pcf-ops` | 10,547 | 1 | 1,543 |
| `incident-command` | 10,542 | 0 | 0 |
| `operational-learning` | 9,434 | 1 | 7,564 |
| `ci-actions` | 9,248 | 1 | 1,620 |
| `agent-security` | 9,234 | 0 | 0 |
| `pcf-deploy` | 9,042 | 0 | 0 |
| `database-reliability` | 8,528 | 1 | 2,081 |

**Correcting the figure this sweep was first summarized with:** the roadmap initially said *eleven*
skills. That number came from a judgment table with no stated criterion and does not survive one.
`frontend-craft` (14,201 B) and `backend-craft` (11,080 B) have large cores but route 35,502 B and
17,198 B of references respectively, so they fail the second half of the criterion; several smaller
skills with zero references fall under the size threshold. Eight is the defensible set, and it is the
set `SKILL-001` now names.

`[verified]` Ten skills have zero `references/` files: `incident-command`, `agent-security`,
`pcf-deploy`, `production-change-gate`, `root-cause`, `merge-gate`, `postmortem`,
`service-onboarding`, `stack-profile`, `release-gate`. Most are short and correctly monolithic; zero
references is not on its own a defect, which is why the criterion above pairs size with routing
ratio rather than counting references alone.

## Always-resident description mass

`[verified]` Total description bytes across all 29 skills: **12,682**. These load whether or not any
skill is invoked. Largest single description: `runbook` at 575 bytes against the 600-byte cap
enforced by `check_links`.

`[unverified — judgment, not measurement]` That roughly a dozen of the 29 descriptions carry a
workflow summary alongside their triggers. This cannot be measured mechanically: the rule in
[`rules.md`](../rules.md) ("Description is a trigger only, never a workflow summary") turns on
whether a clause helps a model decide *whether to load* the skill, versus restating what the body
already contains. The judgment stands behind `SKILL-001` but the count deliberately does not appear
in that item's acceptance criteria, because a criterion nobody can reproduce cannot close an item.

## Frontmatter parser divergences

`[verified]` The two readers disagree on grammar, not merely on code. Reproduced directly:

```
python3 - <<'PY'
import pathlib, sys
sys.path.insert(0, "scripts")
import check_links as c, generate_platform_adapters as a
sample = "---\nname: probe\ntools:\n  - Read\n  - Grep\n---\n\nbody\n"
print(c._frontmatter(sample, pathlib.Path("x.md"))[2])
PY
```

| Divergence | `check_links._frontmatter` | `generate_platform_adapters.parse_frontmatter` |
|---|---|---|
| key charset | `[A-Za-z0-9-]` — `my_key` is "malformed" | `[A-Za-z0-9_-]` — accepted |
| malformed input | collects a failure and continues | raises `ValueError` |
| `key:` + `- item` list | reports two malformed lines **and** an unknown key | accepted, value typed as `list` |

The list-form divergence is the one with a live subject: `agents/researcher.md` uses that spelling
for `tools:`. `check_links` does not currently scan `agents/`, so the disagreement is latent rather
than firing — which is exactly the condition under which a consolidation would silently pick a
winner. `evals/run_evals.py` carries a third reader, not compared here.

## Trigger collision

`[sourced]` `skills/obs-logs/SKILL.md` advertises the trigger `'build a log alert'`; its ownership
map names `obs-metrics` and `obs-dashboards` and omits `obs-alerting`, which claims Splunk
saved-search alerts. `[verified]` The 66-scenario suite contains
`evals/scenarios/discovery-obs-alerting-splunk-saved-search.yaml` and no scenario asserting that
`obs-logs` defers to `obs-alerting`.

`[unverified]` Whether the collision actually misroutes anything. Establishing that needs the
clean-room runner and a live API, which is why `ROUTE-002` is `blocked` and why its acceptance
requires both a measured scenario **and** a canonical disambiguation — a scenario that passes
against today's descriptions would otherwise close the item with the ambiguity intact.
