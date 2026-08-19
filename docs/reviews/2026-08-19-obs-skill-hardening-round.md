# Obs-skill hardening round — findings and recommendations — 2026-08-19

**Status:** prepared on branch `fix/obs-skill-hardening`; no merge, promotion, or independent
review has occurred. Two description edits carry **routing-eval debt** (below) that should close
before merge. Recommendations here are **proposed** dispositions — adopting any into the live
backlog is the roadmap owner's call; this packet is evidence, not a checklist to resume.

| Field | Value |
|---|---|
| Subject revision | `d636d3f87136cecc100f7ccad5885b9fdbfebb0a` (branch `fix/obs-skill-hardening`) |
| Scope | 6 obs skills + bundles, `stack-profile`, `gcp-ops`/`akamai-edge` references, `agents/observability-engineer.md`, `agent-authoring/references/claude-code-frontmatter.md` |
| Method | 5 upstream-verification lanes + 3 review lenses (LLM-optimization, correctness corners, safety/authority), run as parallel agents over GitHits/Context7/vendor docs; guard dispositions proven by executing `scripts/readonly-guard.py` |
| Gate | `python scripts/gate_a.py` PASS 40/40 after every edit round; adapters regenerated and byte-synced each time |
| Change volume | 90 files, +1,113 / −324 (canonical + projections) |

## Conclusion

`[verified]` The obs skill set is structurally sound and lean: bodies are 85–92% role-specific
content at 17–31% of the 5k-token Level-2 budget; descriptions are 380–463 bytes against the
1,024-byte cap. The round's value was correctness and evidence quality, not restructuring: nine
wrong technical claims fixed, one material vendor-lifecycle fact recorded, four guard/command
mismatches re-attributed, and a new cross-backend "errors that are limits" teaching added with
SHA-pinned upstream evidence.

## Wrong claims fixed (each verified against upstream before editing)

- Splunk `savedsearches.conf` trigger keys: REST API names (`alert_type`/`alert_comparator`/
  `alert_threshold`) were presented as .conf keys; real keys are `counttype`/`relation`/
  `quantity`/`alert_condition` `[sourced: Alerting Manual; spec mirror]`.
- PromQL recording-rule example used `by` where upstream and the file's own prose mandate
  `without` `[sourced: prometheus/docs practices/rules.md]`.
- WQL "no `by` clause" overstated — the inner form `sum(ts(m) by (az))` is documented
  `[sourced: wavefrontHQ/docs@0492d79 query_language_aggregate_functions.md:147-151]`.
- OTel naming: blanket "counters not pluralized" contradicted semconv (unitless countables SHOULD
  pluralize); the Prometheus-exporter "applied twice" rationale contradicted the suffix-dedupe
  spec `[sourced: semconv general/naming; OTel spec sdk_exporters/prometheus]`.
- Akamai: Reporting API CP-code filter is optional, not required; DataStream 2 connection failures
  ARE retried (3×, then lost); users can reach the previous property config for minutes after
  activation phase 1; mPulse timing definitions live on `use-metrics`, not `key-concepts-terms`
  `[sourced: techdocs.akamai.com, fetched 2026-08-19]`.
- One wrong GCP citation (Ops Agent page cited for Telemetry API collector wiring) and one
  malformed heading in the agent body.

## Lifecycle facts recorded

`[sourced]` Wavefront continues as **Broadcom DX OpenExplore** — the 2025-10-31 end-of-availability
retired the VMware *Tanzu Observability* offering, not the platform (TechDocs maintains Wavefront
release notes under `dx-openexplore/saas`, Feb 2026). The tenant answers as of 2026-08-19 (UI
version 250.1) `[sourced: operator observation]`; entitlement basis remains `[unverified]` — the
stack owner records it in `stack-profile`. The OSS surface is frozen: `wavefrontHQ/docs@0492d796`
has no release notes past 2024-09.x and no "OpenExplore" string; `wavefrontHQ/wavefront-proxy` is
read-only with Proxy 14.0+ closed-source — updates and security fixes come only from Broadcom.
Also recorded: Moogsoft v9.2 as the only supported 9.x; Grafana toolchain Grizzly → `grafanactl`
(archived) → `gcx`; Traffic report discontinued 2025-11-06; mPulse CWV 2024 replaced FID with INP.

## Guard alignment (dispositions proven by executing the guard)

`[verified]` Four recommended commands the guard denies were re-attributed to explicit actors:
`promtool test rules`, the bundled `error_budget.py`, `alloy validate`, and otel-sdk.md's install
commands. Cross-agent trap recorded: the validators are allowlisted only for
`observability-engineer`, and `sre` loads the same skills. Every recommended `gcloud`/`cf` shape
passes; gcp-logging.md's structure-rule claim is true. No telemetry-as-instructions surface exists
in the 27 files reviewed.

## Ceremony / fluff assessment (measured, not eyeballed)

| Block | Size | Verdict |
|---|---|---|
| Skill bodies | 634–1,141 words | Lean; no trim warranted |
| Evidence banner | 54 words × 6, byte-identical | Safety invariant; fleet-wide; keep |
| Redaction/handoff blocks | 41–135 words | Mandated duplication (self-containment); keep |
| Canary tokens | 13 lines, two conventions | **No validator fires them** — unproven instrument |
| Dated re-check stamps | 20 added this round | Level-3 (free until read); adopt replace-not-append |
| Agent shared doctrine tail | 923 of 2,094 words (44%) | The one large repeated block; fleet doctrine |

## Recommendations (proposed — one owner decision each)

1. **Close the routing-eval debt before merge** *(blocking)*: obs-alerting (removed a body rule
   from Level-1) and obs-logs (ownership map now names obs-alerting) descriptions changed; run the
   overlapping `evals/scenarios/discovery-*obs*` scenarios through the live-API clean-room runner
   before and after per the change playbook.
2. **Decide the two guard widenings**: allowlisting `promtool test` (offline fixture evaluator)
   and a verb-gated `alloy validate` would restore agent-runnable verification paths now marked
   human-run. Each is an allowlist PR plus corpus entries per the guard playbook; if adopted,
   revert the human-run markings in obs-alerting/SKILL.md and obs-pipeline/references/alloy.md.
3. **Make canaries real or document them as manual**: two token conventions exist with no checker.
   Either add a validator (cheap: assert every obs reference carries exactly one token and the
   convention is written down in agent-authoring) or record them as a manual-drill convention.
4. **Stamp policy**: on re-verification, replace the prior dated stamp rather than appending —
   prevents evidence archaeology in reference files.
5. **Agent-tail compression experiment** *(largest potential win, eval-gated)*: the 44% shared
   doctrine tail is repeated across all 8 agents. Any trim must run `eval_behavioral.py`
   before/after — especially taint/injection scenarios — and must not touch security or evidence
   invariants. Do it once in `agent-authoring` and propagate, or not at all.
6. **Re-probe `claude plugin tag`** on the escaped-quotes divergence recorded in
   [claude-code-frontmatter.md](../../skills/agent-authoring/references/claude-code-frontmatter.md)
   before the next release.

## Not done / unverified

- Routing evals not run (live API required) — see recommendation 1.
- Behavioral evals not run for body edits; edits are reference-content corrections, but the suite
  has not been exercised against them.
- Akamai verdicts rest on delegated researcher fetches of techdocs.akamai.com; Splunk .conf-key
  absence proven against a spec mirror only (official spec page blocks retrieval).
- Upstream limit defaults (Mimir/Loki/Tempo) are recorded as upstream values with explicit
  "not the tenant's limits" guards; per-tenant values remain `[unverified]`.
- Host projections were not independently re-audited (byte-synced by the adapter gate).
