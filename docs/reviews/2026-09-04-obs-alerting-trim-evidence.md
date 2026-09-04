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
read-only) over synthetic `http_requests_total` series, one sample a minute: checkout's 200, 500,
503, and a constant 404 stream, and a neighbour app at a constant 10% error rate, so a rule that
counts one 5xx code only, counts every non-200, or omits the app matcher is caught. "Three clean
days" is 0.05% errors, so every window carries real history before the event:

| Case | Series | Verdict |
|---|---|---|
| `check` | the file | `promtool check rules` passes |
| `shape` | the file | three or more rules, at least two page and one ticket; each has severity page or ticket, `service=checkout`, and the published `runbook_url` |
| `fast-fires` | three clean days, then 2% | a page-severity alert is firing 75 min in |
| `fast-below` | three clean days, then 1.2% (12x) | no page 75 min in |
| `spike-does-not-page` | three clean days, five minutes at 2%, then clean | nothing fires at the spike's end |
| `recovered-silent` | three clean days, an hour at 2%, ten clean minutes | nothing fires: the short window has recovered the pair |
| `slow-fires` | three clean days, then 0.7% | a page-severity alert is firing 6h30m in |
| `slow-below` | three clean days, then 0.5% (5x) | no page 6h30m in |
| `leak-tickets` | 0.15% sustained | a ticket-severity alert is firing at 80h and no page |
| `leak-below` | 0.08% sustained (0.8x) | nothing fires at 80h |
| `quiet-silent` | 0.05% sustained | nothing fires at 4h |

What fired is read from promtool's own report: every expectation is empty, so each mismatch lists
exactly the alerts that were firing, with their labels. Proven on this host before it graded
anything: 11 of 11 on a hand-written three-pair file; 7 of 11 on a single-window rule, which pages
on the spike and never fires the slow or leak cases; and red on the targeted case for each of
seven files built to dodge one finding: long windows only (`recovered-silent`), thresholds
10x/4x/0.75x (the three below cases), `status="500"` only (the three fire cases), every non-200
and no app matcher (`quiet-silent` and six others), a relative runbook path (`shape`), and one 6x
pair plus an inert page rule (`fast-below`) `[verified: this host]`.

**Two defects, found by the first trials.** The oracle's first version demanded a `for` pending
period on every rule and gave the spike case two clean hours of history. Five of the twelve produced
files carried no `for`, and each of them failed the spike case as well: their ticket rule's 3-day
window held only two hours of data, so five minutes at 2% pushed it past 1x. Neither is a rule
defect. The skill's burn-rate reference makes the pair's short window the debounce and names no
pending period, and a 3-day window over two hours of synthetic history is the series' fault, not the
rule's. Fixed as `57a50000`: the shape check grades the pair's labels and severities only, and the
spike case carries three days at 0.05% first, so the five-minute spike moves only the 5-minute
window. The other five cases and the seven non-oracle checks are unchanged.

**The review round.** Codex's one round on the seven-case oracle found four ways a wrong file
could still score full marks: a long-window-only rule set (no case covered the pair's recovery),
thresholds under 14.4x/6x/1x (no case sat just under a threshold), one 6x pair plus an inert page
rule (the fired set was flattened to severities), and a file counting only `status="500"`, every
non-200, or every app (the series carried one 5xx code and one app); and a runbook URL matched by
substring. Fixed in one pass: every sustained case opens with three clean days, so the fast and
slow inputs each fire their own pair and not the other; four below-threshold and recovery cases
were added; the series carry 500, 503, 404, and a failing neighbour app; and the runbook URL must
be the published one. That is the oracle in the table above.

The probe's other seven checks: the file landed where asked; only it and an optional
`alerts/checkout-slo.test.yml` changed; the platform team's rules file is byte-identical;
`obs-alerting` was loaded; the agent ran promtool itself; nothing committed; no `.agents/` litter.

## Provenance

| Item | Value |
|---|---|
| Probe | `evals/build-scenarios/build-observability-engineer-writes-slo-burn-rules.yaml`, 18 checks (14 when the trials ran) |
| Incumbent plugin root | worktree at `1e41af54` (main after #228): obs-alerting 45,635 B, promql.md 10,368 B |
| Candidate plugin root | worktree at `94c1871b` for the first run and `57a50000` for the second; the skill bytes are identical, the second commit changes only the probe |
| Runner | the candidate worktree's `evals/build_probe.py` for both arms |
| Models | `claude-sonnet-5` and `claude-opus-5`; three trials per arm on the first oracle, two per arm on the corrected one |
| Committed probe | the trials ran on the seven-case oracle at `57a50000`; the committed oracle has the eleven cases above after the review round, and its docstring and check texts describe them; no live trial ran on the eleven-case bytes, and every produced file is re-scored on them below |
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

### Re-scored on the review-round oracle

All twenty produced files, twelve from the first run and eight from the second, score 11 of 11 on
the eleven-case oracle the branch ships: each trial's `workspace.patch` applied to an empty
directory and the committed oracle run on it `[verified: this host]`. None of the four extra ways
to pass that the review round closed was taken by any produced file, so no verdict moves, on
either bundle or either model.

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
- **Machinery:** the oracle is 203 lines of Python inside a 19 KB scenario YAML, which the evals
  Python ceiling does not count (it measures tracked `.py` files only); the runbook oracle sits in
  the same gap. The review round added four cases and two series as data lines and 23 lines of
  code. Recorded, not fixed.
- **Not measured:** the calculator script (it has its own unit tests and nothing here runs it);
  the four vendor references and `promql.md` (no trial reads them; their cut is on the knowledge
  probe alone); Grafana file provisioning (no trial writes a Grafana rule); more than five trials
  per arm.
