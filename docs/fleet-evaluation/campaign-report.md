# Saved campaign report

The standalone [reporter](../../evals/campaign_report.py) reads existing v1 evidence and prints
Markdown or JSON. It makes no model, network or Docker calls, does not rescore, and never updates
the original records. It is outside the measured runner package.

```bash
"$PROJECT_PYTHON" evals/campaign_report.py .eval-runs/wp08-approved \
  --selection evals/manifests/wp08-complex-proposal.json --label claude
"$PROJECT_PYTHON" evals/campaign_report.py .eval-runs/wp08-approved \
  --selection evals/manifests/wp08-complex-proposal.json --label claude --json
```

Use the actual accepted selection for a measured campaign. A proposal can describe expected cases
for an empty/preparation report, but does not authorize execution. Selections contain `tasks` with
unique `instance_id` values and optional positive `trials` counts. Native campaign selections can use
scenario IDs in that same small shape. Evidence bundles use `eval-<case>/<label>/run-N`; kept and
incomplete attempts stay visible. Write Markdown beside the bundle's `eval-*` directories if you
save stdout, so relative evidence links resolve. JSON links are relative to the supplied bundle.

The report separates expected, started, completed, recorded-verdict and measured PASS/FAIL slots.
Retries do not create extra denominator slots. Unselected cases and extra trial slots remain visible
with their costs, but cannot improve selected coverage or enter its verdict totals. Missing records, malformed identities, unsupported
versions, duplicate publications and inaccessible evidence are measurement gaps, not favorable
results. Incompatible candidate/model/runner/host/profile identities remain separate groups;
missing historical identity is never filled from the reporting machine.

Original verdicts, later assessment revisions, execution ending, independent verifier, cleanup and
human policy review are distinct. A supported result can coexist with a later cleanup/billing
failure; `after_assessment` is printed without erasing that result. A mechanically valid PASS does
not establish semantic correctness, policy approval or candidate acceptance.

Provider-measured spending and CLI estimates have separate totals. Known amounts are lower bounds
when any attempt is unknown, including kept or unselected attempts. Unknown spend stays unknown;
the reporter does not infer zero cost, billing completeness, key disablement or human acceptance.
Native records can retain a known judge-call subtotal even when the full judge cost is unavailable;
the report preserves that recorded spending floor.

Exit 0 means a report was produced, including any reported gaps. Exit 3 means the selection or
arguments could not be read. Neither exit code is a campaign acceptance decision.
