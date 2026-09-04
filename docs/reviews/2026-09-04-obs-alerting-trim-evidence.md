# obs-alerting trim: before/after evidence (2026-09-04)

The `obs-alerting` skill was cut from 45,635 B to 36,223 B and the `obs-metrics` PromQL reference
from 10,368 B to 5,570 B, and for the first time the alerting skill was measured by what the rules it
produces do: the pinned promtool evaluated every produced rules file over synthetic series. A
tools-off probe of Sonnet and Opus set the cut line; a probe-owned oracle of seven cases on a new
observability-engineer build probe graded every trial; incumbent and candidate ran three trials per
model on the oracle's first version and two per model on the corrected one. Measured on the
maintainer's Windows host. Cited by the pull request and by `CHANGELOG.md`.

## Where the cut line came from

Twelve claims from the two bundles, put to both models with no tools (`F:/kp`, not committed)
`[verified: the two answer files on this host, 2026-09-04]`. Both models carry: the three
Workbook pairs with thresholds, budget fractions, and the AND rule; the Grafana evaluation
lifecycle (`for`, `keep_firing_for`, the Recovering state); the full-tree replacement of a
provisioned notification policy tree; Splunk's `counttype`/`relation`/`quantity` keys and the trap
that `alert_type`/`alert_comparator`/`alert_threshold` are REST names that configure nothing in the
file; ThousandEyes' BGP versus Path Visualization views and Cloud versus Enterprise Agents; PromQL's
rate-before-sum, the classic-histogram p95, and `level:metric:operations`; the `promtool test rules`
file format and what an empty `exp_alerts` asserts; and staleness alerting on a
`*_last_success_timestamp_seconds` metric with no-data treated as failure.

Neither carries reliably: the file-provisioning spellings (both wrote snake_case
`keep_firing_for` and listed `KeepLast` as a valid `noDataState`; the reference has camelCase
`keepFiringFor` and `KeepLast` absent from the enum, both sourced); the webhook
`enable_allowlist` default (Sonnet said `true`, Opus was unsure; the reference has `false`,
sourced); the Moogsoft supported release (both unsure; Sonnet also had the Sigaliser names wrong);
the native-histogram stable version and the exact remote_write defaults (Sonnet: `max_shards` 200,
not 50); Mimir 3.2.0's default changes (both unsure); and the Splunk Cloud cron timezone and the
export-JSON-versus-update-API schema (Sonnet unsure on both). So the trim removed the first set
where it was explanation, kept the second set and every team inventory table, stated the cause bar
once in the router instead of once per vendor reference, and dropped five empty inventory tables to
one per vendor.

| File | Before | After |
|---|---|---|
| `SKILL.md` | 5,689 B | 6,195 B (the cause bar moved in from the vendor references) |
| `references/burn-rate.md` | 3,048 B | 2,098 B |
| `references/grafana-alerting.md` | 9,525 B | 6,398 B |
| `references/splunk-alerting.md` | 5,048 B | 3,681 B |
| `references/moogsoft.md` | 5,729 B | 3,748 B |
| `references/thousandeyes.md` | 6,191 B | 3,698 B |
| `scripts/error_budget.py` | 10,405 B | unchanged |
| `obs-metrics/references/promql.md` | 10,368 B | 5,570 B |

## The oracle

`probe_alert_rules.py`, shipped by the new probe through `writes:` and run after the agent has
finished, runs the pinned `prom/prometheus:v3.14.0` promtool (`--network none`, workspace mounted
read-only) over synthetic `http_requests_total{app="checkout", status}` series, one sample a minute:

| Case | Series | Verdict |
|---|---|---|
| `check` | the file | `promtool check rules` passes |
| `shape` | the file | three or more rules, at least two page and one ticket; each has severity page or ticket, `service=checkout`, and a `runbook_url` naming `checkout-slo` |
| `fast-fires` | 2% errors sustained | a page-severity alert is firing at 75 min |
| `spike-does-not-page` | three days at 0.05%, five minutes at 2%, then clean | nothing fires at 72h05m |
| `slow-fires` | 0.7% errors sustained | a page-severity alert is firing at 6h30m |
| `leak-tickets` | 0.15% errors sustained | a ticket-severity alert is firing at 80h and no page |
| `quiet-silent` | 0.05% errors sustained | nothing fires at 4h |

What fired is read from promtool's own report: every expectation is empty, so each mismatch lists
exactly the alerts that were firing, with their labels. Proven before any trial and again after the
fix below: 7 of 7 on a hand-written three-pair file and 3 of 7 on a single-window rule, which
passes only the syntax check, the fast burn, and the quiet case, and pages on the spike
`[verified: this host]`. The spike case is the one that separates an AND pair from anything
weaker; the leak case fires at ticket severity during a fast burn too, which is correct, since 20x
exceeds 1x.

**Two defects, found by the first trials.** The oracle's first version demanded a `for` pending
period on every rule and gave the spike case two clean hours of history. Five of the twelve produced
files carried no `for`, and each of them failed the spike case as well: their ticket rule's 3-day
window held only two hours of data, so five minutes at 2% pushed it past 1x. Neither is a rule
defect. The skill's burn-rate reference makes the pair's short window the debounce and names no
pending period, and a 3-day window over two hours of synthetic history is the series' fault, not the
rule's. Fixed as `57a50000`: the shape check grades the pair's labels and severities only, and the
spike case carries three days at 0.05% first, so the five-minute spike moves only the 5-minute
window. The other five cases and the seven non-oracle checks are unchanged.

The probe's other seven checks: the file landed where asked; only it and an optional
`alerts/checkout-slo.test.yml` changed; the platform team's rules file is byte-identical;
`obs-alerting` was loaded; the agent ran promtool itself; nothing committed; no `.agents/` litter.

## Provenance

| Item | Value |
|---|---|
| Probe | `evals/build-scenarios/build-observability-engineer-writes-slo-burn-rules.yaml`, 14 checks |
| Incumbent plugin root | worktree at `1e41af54` (main after #228): obs-alerting 45,635 B, promql.md 10,368 B |
| Candidate plugin root | worktree at `94c1871b` for the first run and `57a50000` for the second; the skill bytes are identical, the second commit changes only the probe |
| Runner | the candidate worktree's `evals/build_probe.py` for both arms |
| Models | `claude-sonnet-5` and `claude-opus-5`; three trials per arm on the first oracle, two per arm on the corrected one |
| Committed probe | the measured `57a50000` bytes plus four lines of description (the oracle's docstring and two check `text:` fields) that still named the pending period and the two-hour spike; no logic changed, see `git diff 57a50000 -- evals/` on the branch |
| Raw runs | `.eval-runs/build/obs-alerting-2026-09-04/` and `.eval-runs/build/obs-alerting-2026-09-04-v2/` (gitignored, private) |

## Results

### First oracle, three trials per arm

| Arm | Trials at 14/14 | Misses | Mean tokens | Mean seconds | Cost |
|---|---|---|---|---|---|
| Opus, incumbent | 2 of 3 | run 1 | 816K | 501 | $4.70 |
| Opus, candidate | 1 of 3 | runs 2, 3 | 1.17M | 603 | $5.53 |
| Sonnet, incumbent | 3 of 3 | none | 1.07M | 408 | $2.18 |
| Sonnet, candidate | 1 of 3 | runs 1, 3 | 1.27M | 337 | $1.98 |

Every miss is the same two checks on a file that is otherwise 12 of 14: `shape` (no `for`) and
`spike-does-not-page` (the ticket rule firing at 125 min), the two oracle defects above and nothing
else `[verified: the five grading.json files]`.

### Re-scored on the corrected oracle

All twelve produced files score 7 of 7: each trial's `workspace.patch` applied to an empty
directory and the committed oracle run on it, seven cases each `[verified: this host]`.

### Corrected oracle, two trials per arm

| Arm | Trials at 14/14 | Mean tokens | Mean seconds | Cost |
|---|---|---|---|---|
| Opus, incumbent | 2 of 2 | 720K | 423 | $2.81 |
| Opus, candidate | 2 of 2 | 665K | 317 | $2.21 |
| Sonnet, incumbent | 2 of 2 | 1.09M | 399 | $1.35 |
| Sonnet, candidate | 2 of 2 | 801K | 286 | $1.02 |

Eight of eight, the candidate trials on `57a50000` itself `[verified: the plugin_commit in each
trial's trace summary]`. The verdict rests on these eight; the first twelve are the oracle's
calibration and agree with them once re-scored.

### What the trials exercised

Every one of the twenty trials loaded `obs-alerting` and read `burn-rate.md` and no other
reference, with two exceptions: one incumbent Opus trial also read `promql.md`, and one incumbent
Sonnet trial read the calculator script `[verified: the Read calls in each trial's trace]`. So the
promtool measurement covers `SKILL.md` and `burn-rate.md`; the four vendor references and
`promql.md` rest on the knowledge probe alone. Every trial ran promtool itself, four to ten times.
Fourteen of the twenty hit a Git Bash path-conversion error on a docker call and every one
recovered, on both bundles and both models.

## What this says

- **The trim loses nothing this oracle sees.** Both bundles, on both models, produce a correct
  three-pair AND set with the right labels and runbook link every time. The instrument is at ceiling
  on both arms, so it cannot separate them, and the knowledge probe says why: the pairs, the
  thresholds, and the AND rule are carried by both models with no tools at all.
- **No token claim either way.** On the first three trials the candidate means sat above the
  incumbent on both models (Opus 1.17M against 816K, Sonnet 1.27M against 1.07M); on the next two
  they sat below (Opus 665K against 720K, Sonnet 801K against 1.09M). Over all five, Opus 967K
  against 778K and Sonnet 1.08M against 1.08M, with single trials from 499K to 1.81M and turn
  counts from 21 to 42 in every arm. The bundle read is at most 8.3 KB either way; the spread is
  what the agent did, not what it read.
- **An oracle must be derived from the skill's contract, not from the hand solution.** Both defects
  came from grading habits of the good hand-written file (a `for` on every rule, a short synthetic
  history) that the skill never asks for. Five of twelve correct files were marked wrong before the
  trials exposed it.
- **Machinery:** the oracle is 180 lines of Python inside the scenario YAML, which the evals Python
  ceiling does not count (it measures tracked `.py` files only); the runbook oracle sits in the same
  gap. Recorded, not fixed.
- **Not measured:** the calculator script (it has its own unit tests and nothing here runs it);
  the four vendor references and `promql.md` (no trial reads them; their cut is on the knowledge
  probe alone); Grafana file provisioning (no trial writes a Grafana rule); more than five trials
  per arm.
