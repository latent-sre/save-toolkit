# Obs-skill hardening round — findings and recommendations — 2026-08-19

**Status:** prepared on branch `fix/obs-skill-hardening`; no merge, promotion, or independent
review has occurred. **Recommendations 1, 2, 3, 4, and 6 were addressed on this branch and their
outcomes are recorded below**; recommendation 5 remains proposed. The routing-eval debt is
**closed with measured before/after evidence**, and closing it surfaced a pre-existing red
scenario pair (see *Follow-up round*). This packet is evidence, not a checklist to resume.

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

## Follow-up round — how each recommendation was addressed

Commits `87cf49f` (guard, canary, conventions) and the one carrying this update.

**1. Routing-eval debt — CLOSED `[verified]`.** Both edited descriptions were measured through
`evals/run_evals.py --run` on CLI 2.1.236, 2 trials each at a 280s timeout, and the obs-logs case
was measured at the base commit `e31d04e` in a throwaway worktree for a true before/after:

| Scenario | Base `e31d04e` | Branch | Verdict |
|---|---|---|---|
| `discovery-obs-logs-defers-obs-alerting` | routing 1/2 (trial 1 wrongly fired `obs-logs`) | routing **2/2** | improvement — the ownership-map edit fixed the defect it targeted |
| `discovery-obs-alerting-splunk-saved-search` | not run | routing **2/2** (`obs-alerting` fires) | the Level-1 trim did not break triggering |

Two trials per arm is a small sample; the routing direction is clear and the content-grader
behavior is identical across arms. Offline complement, run first: all **734** `contains_all`
grader strings across every scenario were diffed between the base tree and this branch — **zero**
were present at base and absent now, so no edit moved a string a grader keys on (detector proven
with a known-present probe).

**Pre-existing red scenarios — new finding, not caused by this branch.** Both scenarios FAIL
overall at base and on the branch, for the same reason: their `contains_all` graders demand the
model emit exact `savedsearches.conf` strings (`cron_schedule = */5 * * * *`,
`dispatch.earliest_time = -5m`, `alert.suppress.fields = service,alert_type`,
`instructions_lookup`, `runbook_url`) that do exist in `obs-alerting/references/splunk-alerting.md`
but that the model does not transcribe verbatim. Two regression-split scenarios are therefore red
independent of this work. Disposition for the roadmap owner: either the graders over-specify
(verbatim config transcription as a proxy for correct alert design) or the skill under-surfaces
that reference — decide which, then fix one side.

**2. Guard widenings — DONE `[verified]`.** `promtool` is verb-gated to `{check, test}` and `alloy`
to `validate`, both observability-lane only. Tests were written first and confirmed failing (8 new
allow-cases denied) before the change. Two write vectors are gated out: `promtool test --junit FILE`
(opens `O_CREATE|O_WRONLY|O_TRUNC` per upstream `cmd/promtool/main.go`) and
`alloy validate --config.extra-args` (the `--flags-file` smuggling shape). Detector proven by
mutation: deleting the `--junit` gate makes four deny-corpus cases fail *falsely allowed*.
`error_budget.py` stays human-run — the no-code-execution stance is deliberate doctrine, not an
oversight to fix.

**3. Canary tokens — DONE `[verified]`.** `scripts/check_canary_tokens.py` enforces uniqueness
wherever tokens appear plus presence in the two fully-adopted bundles, registered in Gate A and
paired with a fixture-first suite. Mutation sweep: **1 surviving mutant**, the untestable
`if __name__ == "__main__"` guard — against **9** survivors on the mature `check_plan_status.py`,
so the new suite is stronger than the repo's existing baseline for this file class.

**4. Stamp policy — DONE.** Recorded in CONTRIBUTING.md with the canary convention: dated
verification stamps **replace** rather than accumulate.

**6. `claude plugin tag` re-probe — DONE, and it falsified the recorded guidance `[verified]`.**
On CLI 2.1.236 `claude plugin tag --dry-run` completes on a clean tree, printing the tag it would
create. The four descriptions carrying `\"` escapes hold 8 escaped-quote pairs each, byte-identical
across canonical, Copilot, and Codex form, every one decoding cleanly as a double-quoted string.
The claim that escapes "land literally in the generated projections" and require a punctuation
reword was **wrong**; `claude-code-frontmatter.md` is corrected (replacing the note, per the new
stamp policy).

**5. Agent-tail compression — still proposed.** Unchanged: an eval-gated experiment for
`agent-authoring`, never an eyeballed trim, and never touching security or evidence invariants.

## Not done / unverified

- Routing evals: run for the two edited descriptions only (2 trials per arm); the other 12
  obs-related scenarios were not exercised, and no scenario was run at more than 2 trials.
- Behavioral evals not run for body edits; edits are reference-content corrections, but the suite
  has not been exercised against them.
- Akamai verdicts rest on delegated researcher fetches of techdocs.akamai.com; Splunk .conf-key
  absence proven against a spec mirror only (official spec page blocks retrieval).
- Upstream limit defaults (Mimir/Loki/Tempo) are recorded as upstream values with explicit
  "not the tenant's limits" guards; per-tenant values remain `[unverified]`.
- Host projections were not independently re-audited (byte-synced by the adapter gate).
