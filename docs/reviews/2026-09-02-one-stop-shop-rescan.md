# One-stop-shop rescan of the Save Toolkit fleet

Date: 2026-09-02. Scanned revision: `a5db765d` (branch `work/fleet-weight-round5`, which includes main through PR #214).

## Status of this document

**Every finding below is UNVERIFIED.** The review ran as a workflow of twelve reading agents,
each of which was to be followed by two independent refuters per finding: one checking the
evidence, one checking that a real person on the team benefits. The twelve readers finished. The
verification and synthesis stages hit the account session limit and never ran, so 12 of 174
planned verdicts exist and none are included here. Treat this as a list of leads to check, not a
list of defects. Prior experience on this repo is that roughly a third of unverified findings do
not survive an evidence refuter.

The review lens was the owner's: the plugin exists to help the humans on one SRE team do their
whole job as a one-stop shop. Each reader was given the team's stack facts (PCF operated through
the Apps Manager web UI with many SREs lacking the cf CLI; Splunk primary for incident logs;
Wavefront and PCF App Metrics for app metrics) and the owner's standing rules (7,500-byte skill
screen, incident stack edited screen by screen only, extend before adding, prefer deleting).

Raw machine-readable output sits beside this file as `scans_labeled.json`. To finish the
verification when the limit resets, resume the workflow: the twelve reads replay from cache.

```
Workflow({scriptPath: 'C:/Users/hawkins/.claude/projects/F--repos-sre-agents--worktrees-round5/06229b0e-1ff7-453e-b54e-ca7b0cdd50de/workflows/scripts/one-stop-shop-rescan-wf_31dc3f13-457.js', resumeFromRunId: 'wf_31dc3f13-457'})
```

## Shape of the result

| Measure | Count |
|---|---|
| Reading agents completed | 12 of 12 |
| Findings returned | 87 |
| Verdicts completed | 12 of 174 |
| High severity | 28 |
| Medium severity | 44 |
| Low severity | 15 |
| Small effort | 80 |
| Medium effort | 7 |
| Large effort | 0 |

## Themes that recurred across independent readers

These are the claims that more than one reader reached separately, which makes them the first
things worth verifying.

1. **The team's own screens are named almost nowhere.** Apps Manager and PCF App Metrics appear
   in no skill body outside `stack-profile`, and in no skill or agent description, so PCF checks
   are given as cf commands to a team where many people have no cf CLI.
2. **The incident advisor is hard to reach.** `incident-command`, `postmortem`, and `root-cause`
   route to the `sre` agent, and the always-loaded fleet guide never names
   `incident-investigation`, so a paged human can land on the bounded helper instead of the
   advisor the owner chose.
3. **Alert tuning stops short of the team's alerting system.** `obs-alerting` advertises the
   noisy-alert trigger but carries no Wavefront alerting and no procedure for tuning and then
   proving the noise went away.
4. **Team-specific inventories are still placeholders.** Splunk indexes, metric names, and saved
   searches are `<placeholder>`, so a correct query shape still needs the human to supply the
   parts only the team knows.
5. **Some support surfaces are written for a machine caller.** The reviewer, researcher, and
   repository-investigator hand a developer packets and untrusted-input rituals rather than an
   answer.

## Findings by area

Each finding carries the reader's evidence, its proposed change, and the human it claims to help.
Severity and effort are the reader's own estimates.

### Incident stack (incident-investigation, investigation-depth, root-cause, incident-command, postmortem)

**Reader's verdict.** For the responder inside incident-investigation this is a genuinely useful advisor — the per-turn order, the "choose the check whose predictions differ" rule, the pressure-and-trap table, and the board give a mid-incident SRE judgment they did not have — but the team's own screens (Apps Manager, Wavefront, PCF App Metrics) are named nowhere in the five skills, so every "look here" is a Splunk search, a Grafana panel, or a cf command, and the phase table that promises a tool and a healthy/unhealthy result per ask delivers neither. From the command side the human advisor is unreachable: no file outside its own directory references incident-investigation, and incident-command, postmortem, and root-cause still hand triage, recovery confirmation, and the postmortem seed to the sre agent — so the fix is a handful of one-line routing and tool-name edits, not a rewrite.

#### incident-stack 1. incident-investigation names Grafana as the incumbent and never Apps Manager or Wavefront

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/incident-investigation/SKILL.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/incident-investigation/SKILL.md:43 "Splunk and Grafana are the incumbents, and the search you name must be in the dialect the team actually queries"; :64 "The one Splunk search, Grafana panel, or command whose results differ between the top candidates". Contradicts skills/stack-profile/SKILL.md:39-41 "Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes, and Wavefront and PCF App Metrics for application metrics. Grafana with Mimir, Loki, and Tempo is the additive stack". grep -i for apps manager|wavefront|app metrics across the five incident skills: 0 hits (same grep found Splunk at :16).
- **Proposed change:** Replace lines 42-44 with: "If the service card does not say where its logs and metrics live: Apps Manager (the app's page — instance state, Events, last-minutes log tail) for what changed, Splunk for logs beyond the last minutes, Wavefront or PCF App Metrics for app metrics; Grafana only for a service already instrumented into it. `stack-profile` has the detail." Change line 64's tool list to "The one Apps Manager view, Splunk search, Wavefront / App Metrics chart, or command whose results differ". Net size roughly neutral.
- **Who it helps:** The on-call SRE who has Apps Manager and Wavefront open gets the next check named in the screen in front of them, instead of a Grafana panel that does not exist for their PCF app.

#### incident-stack 2. The Examine row promises a tool and a healthy/unhealthy result per ask and delivers neither

- **Kind / severity / effort:** gap · high · small
- **Files:** `skills/incident-investigation/SKILL.md`, `skills/obs-logs/references/query-catalog.md`, `skills/obs-metrics/references/metrics.md`
- **Evidence:** skills/incident-investigation/SKILL.md:85-86 "each ask names the tool, what it does, and what a healthy and an unhealthy result look like" versus :92 "| Examine | the golden signals as time series (latency, traffic, errors, saturation); logs for one failing request; the service's own exposed state (thread dump, pool and queue metrics); what changed, with times |" — no tool, no healthy shape. The pieces already exist: skills/obs-logs/references/query-catalog.md:98-110 "Where did one request fail across services?" with "Healthy looks like: every expected hop present, terminating in a success status"; skills/obs-metrics/references/metrics.md:11-16 candidate Wavefront names for request rate, latency, errors, memory.
- **Proposed change:** Rewrite the Examine row as four asks, each with its screen and healthy shape: "what changed → Apps Manager app page → Events (crash, restart, scale, update lines with times; `cf events` fallback) — healthy is nothing since the last known-good deploy; golden signals → Wavefront / App Metrics chart of request count, latency, errors, memory, split by instance (`obs-metrics` metrics reference) — healthy is flat at baseline, unhealthy is a bend with a time; one failing request → Splunk catalog entry 'Where did one request fail across services?' (`obs-logs`) — healthy is every hop present ending in success; exposed state → thread dump / pool metrics from the app's own endpoint, captured before any restart". Adds about 250 bytes to a file already past the screen; the owner's screen-by-screen pass decides where it lands.
- **Who it helps:** The responder mid-incident gets four concrete open-this-look-for-that instructions in Apps Manager, Wavefront, and Splunk, and the SPL the team already wrote down becomes reachable from the incident skill.

#### incident-stack 3. incident-command never routes to incident-investigation and hands technical diagnosis to the sre agent

- **Kind / severity / effort:** route · high · small
- **Files:** `skills/incident-command/SKILL.md`
- **Evidence:** skills/incident-command/SKILL.md:7 "Not for technical diagnosis (sre), resolved-incident documentation"; :19-20 "The typed `sre` agent owns technical triage and root-cause hypotheses; a human release owner owns remediation." grep for incident-investigation across agents/ skills/ commands/ AGENTS.md excluding its own directory: 0 hits (the same grep found investigation-depth's five references in agents/sre.md and eng-ladder).
- **Proposed change:** Line 7: "Not for technical diagnosis (`incident-investigation` advises the responder; the `sre` agent takes a bounded read-only look)". Lines 19-21: "The responder owns triage and hypotheses with `incident-investigation`; the `sre` agent takes bounded read-only looks; a human release owner owns remediation."
- **Who it helps:** The incident commander who asks "what should our responder check" is sent to the advisor that prompts a human, instead of to an agent whose cf reads may not exist on this team; the human advisor becomes reachable from the command side at all.

#### incident-stack 4. Recovery confirmation and the resolution update are assigned to the sre agent, not the human watching the chart

- **Kind / severity / effort:** edit · medium · small
- **Files:** `skills/incident-command/SKILL.md`, `skills/incident-command/references/command-and-communications.md`
- **Evidence:** skills/incident-command/SKILL.md:53 "Resolve only after the typed `sre` investigator confirms that user impact has ended and the same golden signals have remained at baseline"; :58 "After terminal resolution, `sre` sends the resolution update and returns the authoritative timeline"; skills/incident-command/references/command-and-communications.md:81 "Resolve only after the typed `sre` investigator confirms that user impact has ended". The sre agent has no Wavefront access and (stack-profile:23-25) may have no cf CLI where it runs.
- **Proposed change:** In both places: "Resolve only when the responder — or the `sre` agent, if it has been watching — confirms user impact has ended and the recovery signal named in the Do-now line (the Wavefront / App Metrics chart or Grafana panel they have been watching) has stayed at baseline for the stated window." Line 58: "the commander (or the comms owner) sends the resolution update".
- **Who it helps:** The IC watching the recovery chart can resolve on what they see, the comms owner knows the resolution update is theirs, and closing a human-run incident no longer waits on an agent that cannot see the metrics.

#### incident-stack 5. Mitigation table is cf-CLI-only for a release owner who acts in Apps Manager

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `skills/incident-command/references/mitigation-selection.md`
- **Evidence:** skills/incident-command/references/mitigation-selection.md:16 "The commands below are planning examples, not current-foundation evidence."; :25 "`cf restart <app>` or `cf restart-app-instance <app> <i>`"; :26 "`cf set-env <app> KEY <old>` then `cf restage <app>`"; :27 "`cf scale <app> -i <more>`". stack-profile:24-25 "Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback."
- **Proposed change:** Add one sentence above the table: "The release owner usually acts in Apps Manager — restart, scale, and environment-variable edits sit on the app's page and revision rollback in its Revisions view [unverified: confirm each view on the foundation]; route remap and cancel-deployment are cf-CLI actions. The cf commands below are the CLI equivalent." Keep the table unchanged.
- **Who it helps:** The release owner executing a P1 rollback is told which view they will actually use, and the approval packet can name a screen they can screenshot into the timeline instead of a command they cannot run.

#### incident-stack 6. investigation-depth's description invites the human SRE into the agent's method skill

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/investigation-depth/SKILL.md`
- **Evidence:** skills/investigation-depth/SKILL.md:4 "Help an SRE choose the investigation depth for an active alert or incident"; :6-7 "Triggers: 'what incident mode is this', 'is first response still enough', 'does this need systemic analysis'"; :12 "# Incident investigation" (same H1 as the human-facing skill); :79-80 "the responder receives what was selected, not the machinery". Only agents/sre.md and skills/eng-ladder/SKILL.md reference it; lines 95-121 are ownership/support-span and incident-state/v2 contract text for the sre agent.
- **Proposed change:** Rewrite the description: "Loaded by the `sre` agent to pick the depth of a bounded evidence slice (first response, hypothesis, systemic) and the recovery-record contract. A human asking what to check next belongs in `incident-investigation`." Drop the three human-phrased triggers and rename the H1 to "# Investigation depth".
- **Who it helps:** The SRE who types "is first response still enough" lands in the advisor that prompts them, not in the ownership-span and JSON-record text that only the agent needs.

#### incident-stack 7. postmortem seeds from the sre agent's evidence and does not know the closeout packet exists

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/postmortem/SKILL.md`, `skills/incident-investigation/assets/closeout-packet.md`, `agents/scribe.md`
- **Evidence:** skills/postmortem/SKILL.md:81 "Seed this from the supplied incident timeline and typed `sre` agent's root-cause evidence so it is accurate while memory is fresh." versus skills/incident-investigation/assets/closeout-packet.md:4 "It is the source for the postmortem and the knowledge closeout" and skills/incident-investigation/SKILL.md:190-192 "fill the [closeout packet] ... and route it to `scribe` — postmortem mode first". agents/scribe.md:89 postmortem mode step 1 likewise gathers "technical findings from `sre`" and never names the packet.
- **Proposed change:** Replace line 81 with: "Seed this from the closeout packet the responder filled in `incident-investigation` — its Timeline, Cause, Mitigation, Worked / slow, and Ledger lines map onto the template's sections — plus `incident-command`'s timeline if one was kept; `sre` agent evidence packets are supporting sources." (Companion one-liner for agents/scribe.md:89 if the maintainer wants the same fix on the agent side.)
- **Who it helps:** The responder who just closed an incident hands one document to scribe and the postmortem skill recognizes it; nothing from the board is re-asked or lost between mitigated and written up.


### Platform (stack-profile, pcf-ops, pcf-deploy, gcp-ops, akamai-edge)

**Reader's verdict.** An SRE on this team who works in Apps Manager, Splunk, and PCF App Metrics opens pcf-ops or pcf-deploy today and gets only cf CLI commands (zero Apps Manager mentions in either skill, against stack-profile's own "first checks as Apps Manager views" rule), no pointer to Splunk for log history or to App Metrics for memory-over-time, and no way to check quota headroom; gcp-ops and akamai-edge triage well, but the two everyday edge jobs — cache purge and edge-certificate (CPS) expiry — get no answer at all. The interpretive content is genuinely good and should stay (137-vs-OOM, the X-Cf-RouterError table, restart-vs-restage, the Cloud Run traffic model, Reference # decoding, the 60-minute fast-fallback window); the gap is the surface the human actually clicks, and every fix below is a small table or sentence edit that fits inside the 7,500-byte screen.

#### platform 1. pcf-ops leads with four cf reads and never names Apps Manager

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/pcf-ops/references/foundations.md`
- **Evidence:** skills/pcf-ops/SKILL.md:18-20 "**One-shot triage — run these four reads directly:** `cf target` → `cf app <app>` → `cf events <app> | head -n 25` → `cf logs <app> --recent | tail -n 120`." and :8 "compatibility: Requires the cf CLI v8 and access/auth to the target PCF foundation" — versus skills/stack-profile/SKILL.md:23-25 "many SREs do not have the `cf` CLI installed. Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback". grep -i 'apps manager' over skills/pcf-ops returns 0 (the same grep hits stack-profile and README).
- **Proposed change:** Replace the lines 18-26 blockquote with a four-row table `First check | Apps Manager | cf equivalent`: (1) right foundation/org/space — the foundation's Apps Manager URL and org/space picker | `cf target`; (2) instance state, memory/CPU/disk, routes — the app's Overview page | `cf app <app>`; (3) what changed — the app's Events view (crash, restart, scale, push audit entries with timestamps) | `cf events <app>`; (4) last minutes of logs — the app's Logs tab | `cf logs <app> --recent`. Keep the cf column verbatim so evals/scenarios/discovery-gcp-ops-defers-pcf.yaml:22 (`contains_all: cf target, cf app checkout, …`) stays green; shrink the triage.sh/triage.ps1 paragraph to one sentence to fund the bytes; change `compatibility:` to 'Apps Manager access to the foundation; cf CLI v8 for the equivalents'; add an `Apps Manager URL` column to the foundations.md:11-15 table. Mark the exact tab labels `[unverified]` on the team's TAS version until the owner confirms them.
- **Who it helps:** The on-call SRE without the cf CLI (the majority, per the owner) currently receives four commands they cannot run; with the table they get the screen to open and paste back from, in the order the incident advisor asks for.

#### platform 2. Log history beyond the buffer is routed to the sre agent, not to Splunk

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/pcf-ops/SKILL.md`
- **Evidence:** skills/pcf-ops/SKILL.md:77-79 "For history beyond the buffer, capture the timestamp and correlation ID and hand the evidence to the `sre` agent for the configured log backend." — versus skills/stack-profile/SKILL.md:39-40 "Splunk for logs beyond the last minutes". grep -i splunk over skills/pcf-ops returns 0.
- **Proposed change:** Replace that sentence with: 'Beyond the last minutes, Splunk is primary: take the timestamp and correlation ID to `obs-logs` — its Splunk catalog entries "Which errors started at the same time as the impact?" and "Where did one request fail across services?" — and search the RTR lines by status, response time, and `x_cf_routererror`.' (The catalog has no PCF/RTR-specific entry — grep -i 'rtr|cf_app|pcf' on skills/obs-logs/references/query-catalog.md returns 0 while grep -i splunk returns 4 — so name the fields here rather than promise a catalog row.)
- **Who it helps:** The responder reading pcf-ops learns the next tool is the Splunk they already have open, not a handoff to an agent that has no log backend access either.

#### platform 3. Per-instance memory/CPU history never points at PCF App Metrics or Wavefront

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/pcf-ops/references/application-crashes-and-health-checks.md`
- **Evidence:** skills/pcf-ops/SKILL.md:107-108 "`/v3/apps/<guid>/processes` lists processes, not instances. Per-instance cpu/mem/disk/state comes from the process `/stats` endpoint." and references/application-crashes-and-health-checks.md:17-18 "memory versus quota (`cf app`, or `/v3/apps/<guid>/processes/web/stats` -> `usage.mem` vs `mem_quota`)" — versus skills/stack-profile/references/observability-stack.md:13 "the live metrics UI for PCF applications today, with PCF App Metrics". grep -i 'wavefront|app metrics' over skills/pcf-ops returns 0.
- **Proposed change:** Add one line at the top of the 'Drill in (read-only)' section (SKILL.md:96): 'Per-instance CPU/memory/disk **over time** — was memory climbing before the 137, or did it spike? — is PCF App Metrics for the app (events overlaid), or Wavefront via the `obs-metrics` WQL reference; `cf curl …/stats` is only a point-in-time snapshot.' Mirror the same clause after 'memory versus quota' in application-crashes-and-health-checks.md:17.
- **Who it helps:** For the most common crash question (leak vs spike vs undersized) the SRE is sent to the history view they already have instead of a snapshot that cannot answer it.

#### platform 4. Everyday deploy-skill jobs (scale, env, rollback, quota) have only cf forms and no quota check at all

- **Kind / severity / effort:** gap · medium · small
- **Files:** `skills/pcf-deploy/references/configuration-and-scaling.md`, `skills/pcf-deploy/references/rolling-canary-and-revisions.md`
- **Evidence:** skills/pcf-deploy/references/configuration-and-scaling.md:10-13 "cf set-env checkout KEY value && cf restart checkout … cf scale checkout -i 5 / cf scale checkout -m 2G -k 2G"; rolling-canary-and-revisions.md:21 "Confirm quota for that extra capacity." and :44 "cf rollback checkout --version <n>". grep -i quota over skills/pcf-deploy hits 5 lines, none of which names a view or command that shows the quota.
- **Proposed change:** In configuration-and-scaling.md turn the 'Planning commands' block into a table `Task | Apps Manager | cf`: scale instances — app Overview → Scale | `cf scale -i`; memory/disk — same dialog (restarts instances) | `cf scale -m/-k`; env var — Settings → Environment Variables, then Restart or Restage per the section below | `cf set-env` + restart/restage; quota headroom before any of the above — the org/space page quota usage | `cf org <org>`, `cf space <space>`, `cf space-quota <name>`. In rolling-canary-and-revisions.md:44 add beside `cf rollback`: 'Apps Manager: the app's Revisions tab → redeploy the prior revision (same limits: droplet must still exist; scale, routes, and bindings are not restored).' Label the UI labels `[unverified]` on the team's TAS version.
- **Who it helps:** The release owner asked to scale or roll back at 02:00 who works in Apps Manager gets the click path with the same rollback-truth caveats, and can see quota headroom before an instance bump fails mid-change.

#### platform 5. akamai-edge has no cache purge anywhere

- **Kind / severity / effort:** gap · high · small
- **Files:** `skills/akamai-edge/SKILL.md`, `skills/akamai-edge/references/property-config.md`
- **Evidence:** skills/akamai-edge/SKILL.md:44-56 defines exactly three lanes — "Triage is read-only, portal-first", "Delivery config is change-managed work", "WAF policy changes are security changes" — and property-config.md:24-31 covers rollback only as "Fast Fallback … revert to the most recent previously-active version". grep -i purge over skills/akamai-edge returns 0 (grep -i expir in the same tree returns 2).
- **Proposed change:** Add a 'Purge — the other live edge change' subsection to property-config.md (about 12 lines) and one matching row in SKILL.md's 'Read the reference' table (:60-64): Fast Purge from Control Center (Publish → Purge cache), the Fast Purge API v3, or the `akamai purge` CLI; scope by URL, CP code, or cache tag; **invalidate** (object revalidated against origin on next request — the safe default) vs **delete** (removed; origin must be able to serve or users get errors); when it is the mitigation (users still see the old JS/HTML after a deploy, wrong content cached, or after a fast fallback — reverting the property does not evict objects the bad version cached); blast radius = origin load from the miss storm, and there is no un-purge, so a CP-code purge is a production change under `production-change-gate`. Mark completion time and API path `[unverified]` until checked against techdocs, matching the reference's existing sourcing convention.
- **Who it helps:** "We deployed and users still see the old bundle" is the most common edge request an SRE gets; today the skill answers nothing, and the existing rollback section silently leaves stale objects in cache after a fallback.

#### platform 6. gcp-ops answer shape carries grader apparatus that means nothing to an SRE

- **Kind / severity / effort:** cut · medium · small
- **Files:** `skills/gcp-ops/SKILL.md`
- **Evidence:** skills/gcp-ops/SKILL.md:24-26 "Keep causal claims `[unverified]` until outputs exist and preserve the caller's requested output shape. Never add a fenced block the caller did not permit." and :35-36 "Preserve every exact value and output shape the caller requested for the forward and inverse traffic commands". These mirror evals/scenarios/discovery-gcp-ops-cloud-run-startup.yaml:55-56 ("That packet must be the only fenced code block anywhere in your reply"), and that eval's own comment at :46 calls it "a constraint no real caller imposes".
- **Proposed change:** Delete the sentence 'preserve the caller's requested output shape. Never add a fenced block the caller did not permit.' from slot 1 and the phrase 'Preserve every exact value and output shape the caller requested for' from slot 4, leaving 'Substitute the caller's exact service, region, and project in these read-only commands' and 'Give the forward and inverse traffic commands with exact revision names; recommend them, never run them or claim that traffic moved.' The eval prompt already states the fence constraint (EVAL-006 option a), so the grader keeps enforcing it without the skill teaching it; the scenario is calibration split, so no regression gate flips.
- **Who it helps:** The SRE reading the Cloud Run startup/rollback shape sees four steps about their outage instead of two sentences about a test harness.

#### platform 7. Cloud Run reads and traffic rollback have no console equivalent

- **Kind / severity / effort:** route · low · small
- **Files:** `skills/gcp-ops/SKILL.md`
- **Evidence:** skills/gcp-ops/SKILL.md:10 "compatibility: Requires the gcloud CLI and viewer access to the target GCP project"; :27-30 the four reads are gcloud only; :102 "gcloud run services update-traffic <service> --to-revisions <previous-revision>=100". grep -i 'console|manage traffic' over skills/gcp-ops returns 0.
- **Proposed change:** Add a parenthetical console path to each of the four reads and the rollback: services describe → Cloud Run › the service › Details/YAML; revisions list → the Revisions tab (creation time and % traffic per revision, which is the 'what changed' view); logs read → the Logs tab; update-traffic → Revisions tab › Manage traffic (set the prior healthy revision to 100%, note whether 'serve latest' was on so it can be restored). Label the exact menu names `[unverified]` and keep the gcloud forms verbatim because the startup eval's graders match them. Inference, not a sourced fact: the population that lacks the cf CLI is likely to lack gcloud too — the owner should confirm before treating the console as primary.
- **Who it helps:** An SRE with console viewer access but no gcloud can still do the revision-vs-onset sweep and can describe the exact rollback click to the release owner.


### Observability (obs-logs, obs-metrics, obs-traces, obs-dashboards, obs-alerting, obs-pipeline)

**Reader's verdict.** The dialect references are the strongest part of the fleet for an SRE: spl.md and wql.md give paste-ready shapes with the real traps named (unextracted fields, streamstats contamination, the fabricated WQL `by` clause), and the 2026-09-02 stack facts are recorded where the skills can read them. But the routers in front of those references are still OTel/Grafana-first — no obs skill names Apps Manager, PCF App Metrics, or the Loggregator-to-Splunk path, obs-alerting has no Wavefront alerting and no "too noisy" procedure despite advertising the trigger, and every team-specific inventory (indexes, metric names, saved searches) is still `<placeholder>`, so a responder gets a correct query shape today but must still supply the index, the metric name, and the alert-history check themselves.

#### observability 1. obs-pipeline has no PCF-to-Splunk path; 'logs are not showing up in Splunk' routes a PCF app into Alloy debugging

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/obs-pipeline/SKILL.md`
- **Evidence:** skills/obs-pipeline/SKILL.md:16 "app → SDK/agent → collector/Alloy → backend"; :21 "| Structured logs | approved JSON fields plus trace/span correlation | OTLP or file receiver → redact/filter/batch → route | Loki; Splunk where required |"; :6 trigger "'logs are not showing up in'". stack-profile/SKILL.md:39-41 makes Splunk the primary log store for PCF apps.
- **Proposed change:** Add one row to the signal table after line 23: "| PCF app logs | stdout/stderr (no SDK) | Loggregator → Splunk nozzle or syslog drain — record which the foundation uses | Splunk |", and one line under 'Where a missing signal gets lost': "PCF app: the line is in Apps Manager → app → Logs but not in Splunk → the drain/nozzle boundary (platform team); in neither → the app never wrote it (boundary 1)." Also change line 21's "Loki; Splunk where required" to "Splunk (incumbent); Loki for OTel-instrumented services".
- **Who it helps:** The SRE whose PCF app's logs stopped appearing in Splunk gets a two-check split (Apps Manager tail vs Splunk) that names the owner, instead of an Alloy receiver/exporter walk that does not exist on that path.

#### observability 2. 'This alert is too noisy' is a trigger with no procedure and no way to prove the tuning worked

- **Kind / severity / effort:** gap · high · small
- **Files:** `skills/obs-alerting/SKILL.md`, `skills/obs-alerting/references/grafana-alerting.md`, `skills/obs-alerting/references/splunk-alerting.md`
- **Evidence:** skills/obs-alerting/SKILL.md:6 "Triggers: 'define an SLO', 'this alert is too noisy', 'what should page'" — the body's sections (SLI/SLO, reference table, scheduled work, verify, don't, handoff) never mention an existing noisy alert. The knobs exist only per backend: grafana-alerting.md:45 "**Pending period (`for`)**" / :55 "**Recovery threshold**"; splunk-alerting.md:47 "alert.suppress.fields = service,alert_type". No file counts fires before and after a change.
- **Proposed change:** Add a compact table to SKILL.md between 'Scheduled work' and 'Verify' titled 'Too noisy — pick the symptom': rows (symptom | knob | prove it): flaps around the threshold → Grafana recovery threshold + `for`/`keep_firing_for`, or the Wavefront alert's fire-minutes/resolve-minutes; the same service re-pages every cycle → Splunk `alert.suppress.fields`, Wavefront resolve minutes; many alerts, one cause → Moogsoft signature/Recipe (not per-alert throttling); fires and nobody acts → demote to ticket. 'Prove it' column, one line: count fires 7 days before vs 7 days after — Splunk `index=_internal sourcetype=scheduler savedsearch_name="<alert>" alert_actions=* | timechart span=1d count` [unverified], Grafana rule History tab, Wavefront alert firing events.
- **Who it helps:** The on-call engineer paged fourteen times overnight gets the one knob for their symptom and a search that shows the page count actually dropped, instead of a design lecture on burn rates.

#### observability 3. obs-alerting covers Grafana, Splunk, Moogsoft, and ThousandEyes but not Wavefront — the backend that pages PCF apps today

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/obs-alerting/SKILL.md`, `skills/obs-metrics/references/wql.md`
- **Evidence:** skills/obs-alerting/SKILL.md:36-44 reference table has rows for Grafana 13, Splunk, Moogsoft, ThousandEyes, and graph-sandbox; the only Wavefront mention in the skill is the placeholder moogsoft.md:83 "| `<Wavefront>` | `<integration name>` | `<fields>` | `<owner / metric alerts>` |". wql.md:175 already carries the no-data condition "mcount(5m, ts(app.http.requests.count, app=\"checkout\")) < 5" but no alert shape around it. stack-profile/SKILL.md:40-41: "**Wavefront and PCF App Metrics** for application metrics".
- **Proposed change:** Extend wql.md's 'Missing data' section into 'Alert conditions': the condition is a WQL expression that evaluates true (`... > <threshold>`), plus the alert's fire-after-N-minutes and resolve-after-N-minutes settings, severity, and target (the Moogsoft webhook); verify by forcing the condition on a non-prod app and reading the alert's firing events, and use the mcount() shape already on line 175 for no-data. Add one prose row to obs-alerting SKILL.md's table: "| Wavefront alert condition, fire/resolve minutes, or no-data | `obs-metrics` WQL reference, 'Alert conditions' |" (prose, not a cross-skill link, so check_links containment holds).
- **Who it helps:** The SRE writing or tuning the alert that actually pages them for a PCF app gets a condition, fire/resolve settings, and a verification path in the product they use, instead of promtool instructions for a rule engine that alert does not run in.

#### observability 4. obs-metrics never names PCF App Metrics and its Wavefront inventory invents app-emitted names when platform metrics already exist for every app

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `skills/obs-metrics/SKILL.md`, `skills/obs-metrics/references/metrics.md`
- **Evidence:** skills/obs-metrics/SKILL.md:5 "Backends: Wavefront (WQL), Mimir/Prometheus (PromQL), and Cloud Monitoring on GCP" and the dialect table :77-83 has no App Metrics row; grep for 'app metrics' across skills/obs-* returns nothing. metrics.md:13 "| request rate | `<app.http.requests.count>` | `app`, `env`, `instance` |" — every Wavefront name is a placeholder the app would have to emit.
- **Proposed change:** Add a first row to SKILL.md's table: "| One PCF app's CPU/memory/disk or request latency, no query needed | PCF App Metrics (from Apps Manager); Wavefront when you need to compare or alert |". In metrics.md add a 'PCF integration metrics (present for every app, no instrumentation)' row: `pcf.container.memory_bytes` / `pcf.container.memory_bytes_quota` / `pcf.container.cpu_percentage`, tag `applicationName`, with one paste query `100 * ts(pcf.container.memory_bytes, applicationName="<app>") / ts(pcf.container.memory_bytes_quota, applicationName="<app>")` labelled [unverified: confirm names in Wavefront's metrics browser].
- **Who it helps:** The SRE asking 'is checkout near its memory quota' gets a place to look without a CLI and a query to paste, instead of a placeholder metric the app never emitted.

#### observability 5. obs-logs has no Apps Manager row; the responder's first log look for a PCF app is not in the router

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `skills/obs-logs/SKILL.md`, `skills/obs-logs/references/indexes.md`
- **Evidence:** skills/obs-logs/SKILL.md:76-83 dialect table rows are Splunk, Loki, Cloud Logging, inventory, catalog, graph-sandbox — no PCF row; grep for 'Apps Manager' across skills/obs-* returns nothing. stack-profile/SKILL.md:39-40: "Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes".
- **Proposed change:** Add a first row to the table at line 78: "| The last few minutes of one PCF app, or its crash/restart events | Apps Manager → app → Logs and Events tabs (`cf logs --recent` / `cf events` equivalent); Splunk for anything older |". In indexes.md's 'Correlation fields' add one line: "PCF platform fields (`cf_app_name`, `cf_space_name`, `cf_org_name` if ingested by the Splunk nozzle; syslog-drain fields differ) — record which ingest path applies."
- **Who it helps:** The SRE at the 'app just restarted' moment is sent to the tab that shows the crash reason in seconds, and knows which Splunk field scopes a PCF app before writing `index=`.

#### observability 6. graph-sandbox rows sit in the SRE's dialect tables but serve only the fleet's synthetic drill

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/obs-logs/SKILL.md`, `skills/obs-metrics/SKILL.md`, `skills/obs-alerting/SKILL.md`
- **Evidence:** skills/obs-logs/SKILL.md:83 "| A verified synthetic graph bundle or failure-plane lineage | graph-sandbox failure-plane view (`./references/graph-sandbox.md`) |"; obs-metrics/SKILL.md:83 and obs-alerting/SKILL.md:44 carry the same row. obs-metrics/references/graph-sandbox.md:3 "Use only for the synthetic `checkout-payments-timeout-drill/v1` graph"; obs-alerting/references/graph-sandbox.md:3-4 "It has no Grafana UID, contact point, notification-policy entry, production route, or pager integration." plus a 21.9 KB evaluator script.
- **Proposed change:** Delete the three graph-sandbox rows from the SKILL.md tables and link the three reference files (and graph_sandbox_alerts.py) from graph-sandbox/AGENTS.md instead, so the GRAPH-003 producer/consumer contract is untouched but leaves the human-facing router.
- **Who it helps:** Every SRE reading the three routers sees only rows they might pick, and each SKILL.md gains ~150 bytes of screen headroom for the Apps Manager, App Metrics, and Wavefront-alert rows above.

#### observability 7. obs-dashboards answers 'add a panel for my PCF app' with a Grafana API loop that may have no Wavefront data source

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `skills/obs-dashboards/SKILL.md`
- **Evidence:** skills/obs-dashboards/SKILL.md:82-83 "Wavefront and Splunk data-source plugins require Enterprise entitlement." and :84-85 "Confirm edition, entitlement, and `GET /api/plugins` on the target" — the skill stops there. references/wavefront-legacy.md:14-15 "Wavefront is the live metrics UI for this team's PCF applications today"; :13 support against the tenant is "[unverified]".
- **Proposed change:** Append one sentence to the paragraph ending at SKILL.md:85: "If `grafana-wavefront-datasource` is absent on the target, build the PCF app's chart in Wavefront itself (start from its PCF integration dashboards) and say so; do not hold today's question on an entitlement check."
- **Who it helps:** The SRE who asked for a chart of checkout memory gets one today in the tool that has the data, instead of a preflight that ends at 'plugin entitlement unverified'.

#### observability 8. obs-traces sends a PCF-only SRE hunting Tempo for traces that do not exist

- **Kind / severity / effort:** stack-truth · low · small
- **Files:** `skills/obs-traces/SKILL.md`
- **Evidence:** skills/obs-traces/SKILL.md:6 "Backends: Tempo (TraceQL) and Cloud Trace on GCP." and :30 "## Enter through one of two doors" — neither door says the app may have no trace at all. stack-profile/references/observability-stack.md:14 "| Traces | — (new capability) | Tempo (TraceQL) |".
- **Proposed change:** Add one line before 'Enter through one of two doors': "A PCF app not yet exporting to Tempo has no trace. Answer 'where did the latency go' with the Splunk correlation search (obs-logs catalog, 'Where did one request fail across services?') using `latency_ms` per hop, and hand the instrumentation gap to obs-pipeline."
- **Who it helps:** The SRE asking 'where did the latency go' for a PCF app is pointed at the search that will actually return rows, and the missing-trace finding is filed rather than mistaken for a sampling problem.


### Knowledge and documents (runbook, operational-learning, service-lifecycle)

**Reader's verdict.** The templates are present and fillable, the runbook exemplar is genuinely good teaching material, and the loop from incident advisor to closeout packet to scribe to runbook Incident-history row exists end to end. But the runbook surface still teaches cf-CLI-first shapes to a team that operates PCF through Apps Manager, the service card lacks the one slot the incident advisor reads it for (where logs and metrics live), the retire mode's body refuses the read-only inventory its own description promises, and the per-step held/contradicted/missing outcomes the living-runbook protocol depends on have no slot in the packet that feeds closeout.

#### knowledge-docs 1. Runbook template, exemplar, and worked excerpt are cf-CLI-first on an Apps Manager team

- **Kind / severity / effort:** stack-truth · high · medium
- **Files:** `skills/runbook/assets/runbook-template.md`, `skills/runbook/assets/runbook-example.md`, `skills/runbook/SKILL.md`
- **Evidence:** skills/runbook/assets/runbook-template.md:28 "- Tools: <cf CLI v8, Splunk, Wavefront, …>"; skills/runbook/assets/runbook-example.md:39 "- Access: `cf` CLI v8 authenticated to the `payments` org, `prod` space"; skills/runbook/SKILL.md:132 "**First checks**: `cf app checkout` → expect `6/6 running`"; versus skills/stack-profile/SKILL.md:23-25 "many SREs do not have the `cf` CLI installed. Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback". A case-insensitive grep for "apps manager" across skills/ hits only stack-profile/SKILL.md.
- **Proposed change:** In runbook-template.md replace line 28 with "- Tools: Apps Manager (<org/space>), Splunk (<index / saved search>), Wavefront or PCF App Metrics; `cf` v8 only where installed" and line 32 with "1. Confirm impact: Apps Manager → <org/space> → <app> (instances, crash events, last-minutes logs) · Splunk <saved search> · Wavefront <chart>. `cf` fallback: `<command>`"; then make the exemplar's Triage step 2 and SKILL.md:132 lead with the Apps Manager instances view ("6/6 running") and give `cf app checkout` as the fallback line.
- **Who it helps:** The on-call SRE without the cf CLI can run a runbook's first checks from the browser; today the exemplar's Prerequisites (line 39) stop them before step 1, and every runbook copied from the template inherits the same dead end.

#### knowledge-docs 2. Retire without a plan: description promises an audit, body says "inventory nothing"

- **Kind / severity / effort:** edit · high · small
- **Files:** `skills/service-lifecycle/SKILL.md`
- **Evidence:** skills/service-lifecycle/SKILL.md:8-9 "Onboard and retire need an approved plan named in the request; without one the skill audits and lists what the plan must contain." versus SKILL.md:28 (Retire row, Otherwise cell) "Stop and name what is missing; inventory nothing." The Onboard row one line above says "Stop, name what is missing, and audit what exists instead".
- **Proposed change:** Replace the Retire row's Otherwise cell with "Stop, name what is missing, and audit what exists instead — read-only inventory of consumers, dependencies, datastores, alerts, and records; disposition and remove nothing. Missing ownership, an unknown consumer, an unclassified datastore, or an unproven recovery path is `BLOCKED`." This keeps both retire evals green: discovery-service-lifecycle-decommission-request grades refusal to remove plus naming the missing plan, not refusal to inventory.
- **Who it helps:** The SRE told to decommission an app gets the consumer/dependency/datastore inventory the retirement plan must contain, instead of a refusal that sends them to build that inventory by hand before the skill will talk to them.

#### knowledge-docs 3. Per-step held/contradicted/missing outcomes have no slot in the closeout packet, and living-runbooks names an intake that does not exist

- **Kind / severity / effort:** gap · medium · small
- **Files:** `skills/runbook/references/living-runbooks.md`, `skills/incident-investigation/assets/closeout-packet.md`
- **Evidence:** skills/runbook/references/living-runbooks.md:27-29 "The `sre` agent's closeout dispositions (\"missing, contradicted, or newly required runbook → `scribe` prepares or proposes the update\") are the intake"; but agents/sre.md:100-102 "Do not classify those candidates as learning dispositions, assign artifact statuses, or load `operational-learning`." The human advisor's packet, skills/incident-investigation/assets/closeout-packet.md:18, carries only "Knowledge repo: <root> · read: <paths> · missing or stale: <paths>" — no per-step outcome — while evals/scenarios/discovery-runbook-incident-update.yaml:9-11 assumes those outcomes arrive as input.
- **Proposed change:** Add one line to closeout-packet.md after line 18: "Runbook used:     <path · version used · each step: held / contradicted / missing; or none existed>", and rewrite living-runbooks.md:27-29 to name that packet line as the intake (dropping the `sre` dispositions sentence). One added slot, no restructure.
- **Who it helps:** The responder records which runbook steps held or failed while it is fresh, and scribe fills the Incident-history row from a slot instead of reconstructing it from the Ledger — the lesson from the incident lands in the runbook the next responder opens.

#### knowledge-docs 4. Service card has no "where logs and metrics live" slot; alert card's backend hint omits Splunk and Wavefront

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `skills/operational-learning/assets/service-card-template.md`, `skills/operational-learning/assets/alert-card-template.md`
- **Evidence:** skills/operational-learning/assets/service-card-template.md:49-51 "- SLI/SLO: <definition link or explicit gap> / - Health signal: … / - Dashboard: <link or explicit gap>" (nothing for logs); skills/incident-investigation/SKILL.md:42-43 "If the service card does not say where its logs and metrics live, load `stack-profile`"; skills/operational-learning/assets/alert-card-template.md:25 "- Backend and signal type: <Grafana/Moogsoft/ThousandEyes/etc. + metric/log/synthetic>" while stack-profile/SKILL.md:39-41 names Splunk and Wavefront/PCF App Metrics as the incident tools.
- **Proposed change:** Under service-card "Reliability and observability" add "- Logs: <Splunk index + saved search; Apps Manager tail covers only the last minutes>" and "- Metrics: <Wavefront / PCF App Metrics chart; Grafana for GCP or OTel services>"; in alert-card line 25 change the hint to "<Splunk / Wavefront / Grafana / Moogsoft / ThousandEyes + metric/log/synthetic>".
- **Who it helps:** The responder (or the advisor reading on their behalf) opens the service card at 3 a.m. and gets the Splunk index and metric chart directly, instead of a second lookup into stack-profile; every card the closeout writes captures the fact the advisor is built to read.

#### knowledge-docs 5. The synthetic graph-sandbox runbook is a maintainers' lab artifact linked as a live runbook from the SRE-facing skill

- **Kind / severity / effort:** cut · low · small
- **Files:** `skills/runbook/SKILL.md`, `skills/runbook/references/graph-sandbox.md`
- **Evidence:** skills/runbook/SKILL.md:27 "The current synthetic graph runbook is graph-sandbox run needs action (`./references/graph-sandbox.md`)."; graph-sandbox.md:119 escalates to "`sre`" and :121 to "`observability-engineer` / `scribe`", and :126-127 "This synthetic runbook creates no channel, contact point, or pager route." — contradicting the skill's own readback rule at SKILL.md:84 "**Does the escalation row reach a human at 3 a.m.?**". Grep for the path over scripts/ and evals/ finds nothing; only docs/reviews/2026-08-30-graph-003-current-runtime-evidence.md:23 links it.
- **Proposed change:** Delete SKILL.md line 27 and move references/graph-sandbox.md to docs/reviews/evidence/ (or the graph-sandbox/ tree), updating the single docs/reviews link. The obs-* skills keep their own graph-sandbox references; nothing else pins this path.
- **Who it helps:** An SRE learning the runbook shape from this skill sees one exemplar whose escalation reaches a human, not a Docker-lab runbook whose escalation table names agents and which the team will never operate.

#### knowledge-docs 6. Confluence import commits to Atlassian Cloud endpoints; the stack profile never records Cloud vs Data Center

- **Kind / severity / effort:** stack-truth · low · small
- **Files:** `skills/runbook/references/confluence-import.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/runbook/references/confluence-import.md:21-22 "curl --fail-with-body --user \"user@example.com\" --output page.json \\ \"https://<site>.atlassian.net/wiki/api/v2/pages/<page-id>?body-format=view\""; skills/stack-profile/SKILL.md:70 "Confluence still holds operational documentation" — a case-insensitive grep of skills/stack-profile for "confluence" returns only lines 70-78, none naming the edition. Which edition the team runs is [unverified] from this review.
- **Proposed change:** Add one owner-filled line to stack-profile "Documentation home": "Confluence is <Cloud | Data Center vX>." If Data Center, change export path 1 in confluence-import.md to `https://<host>/rest/api/content/<page-id>?expand=body.view` (the jq `.body.view.value` extraction is unchanged).
- **Who it helps:** The SRE draining a Confluence runbook into the repo gets an export command that works first time instead of a 404 against a v2 path their Confluence may not serve.


### Change and craft (production-change-gate, backend/frontend-craft, language-idiom, ops-tooling, ci-actions, database-reliability, eng-ladder)

**Reader's verdict.** A Java engineer shipping to PCF gets real, team-sourced help here: ci-actions carries environment-secrets-not-OIDC, RHEL self-hosted runners and a cf deploy job; the Spring Boot reference explains actuator probes and VCAP on PCF; the Java idiom file explains the buildpack memory calculator; and the gate's three checklists are tables a human can walk. But the ship-to-production path still assumes a cf CLI most of the team does not have (the only worked approval example is cf-only), says nothing about who applies a schema migration on a PCF rolling deploy, hands a JVM-first team a Python-only CI starter, has no Cloud Run deploy shape at all, and merge-readiness quotes this toolkit repo's ruleset as if it were the reader's; ops-tooling's plan/packet/counter apparatus and frontend-craft's design-language essay are the least load-bearing pieces for a person on this team.

#### change-craft 1. The only worked approval packet is cf-CLI-only on an Apps Manager team

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/production-change-gate/references/tier-2-approval-example.md`, `skills/production-change-gate/SKILL.md`
- **Evidence:** skills/production-change-gate/references/tier-2-approval-example.md:13 "**Exact command**: `cf scale checkout -i 6`" and :17 "**Verification**: `cf app checkout` shows `6/6 running`"; SKILL.md:7 trigger "'can I run this cf command in prod'"; skills/stack-profile/SKILL.md:24-25 "Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback". grep -i 'apps manager' across the eight change-craft skills: 0 hits.
- **Proposed change:** In the example, make the exact action the Apps Manager path with cf as the fallback — "**Exact action**: Apps Manager → `checkout` (prod space) → Scale → Instances 4 → 6 → Apply; cf fallback `cf scale checkout -i 6`" and "**Verification**: the app's Instances panel shows 6 running; 502 rate in Wavefront / PCF App Metrics drops within 5 min". In SKILL.md, extend the "Plan shown" row with one clause: "a UI action is recorded as screen → control → value plus the expected post-state", and add the trigger 'can I apply this in Apps Manager' beside the cf one.
- **Who it helps:** The release owner approving a scale-up (and the SRE preparing the packet) gets a command they can actually execute and verify from the UI they use, instead of a cf string they cannot run.

#### change-craft 2. Nobody says who applies a schema migration on a PCF rolling deploy

- **Kind / severity / effort:** gap · high · small
- **Files:** `skills/database-reliability/SKILL.md`, `skills/production-change-gate/references/release-readiness.md`, `skills/backend-craft/references/spring-boot.md`
- **Evidence:** skills/database-reliability/SKILL.md:37-39 "Use **expand → contract** when running code depends on the schema: expand with the compatible shape; backfill in bounded batches"; skills/backend-craft/references/spring-boot.md:47 "Migrations run at startup by default."; skills/production-change-gate/references/release-readiness.md:11 "Migrations | Schema and configuration migrations are backward-compatible, ordered before the code that needs them". grep 'run-task' across skills/: 0 hits (detector proven: grep -i flyway found 2 files).
- **Proposed change:** Add one bullet under "Migration safety" in database-reliability SKILL.md: "**Who applies it on PCF.** Startup-run Flyway/Alembic applies the migration from the first new instance mid-rolling-deploy while old instances still serve, so it must be expand-only and a failure stalls the deploy with the schema possibly half-applied. To satisfy 'ordered before the code', run the migration first as a one-off task against the pushed artifact (`cf run-task <app> "<migrate command>"`; Apps Manager: the app's Tasks tab [unverified here]) with startup migration disabled on serving instances, then push the code."
- **Who it helps:** The engineer shipping a Spring Boot or FastAPI schema change to PCF decides the migration runner and ordering before the push, instead of discovering a half-applied schema during a stalled rolling deploy.

#### change-craft 3. Merge readiness quotes this toolkit repo's ruleset as if it were the reader's

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `skills/production-change-gate/references/merge-readiness.md`
- **Evidence:** skills/production-change-gate/references/merge-readiness.md:20-21 "This repository's ruleset requires a pull request and zero approvals, so this checklist never claims independent review is enforced" — a fact about sre-agents, read by an engineer gating a merge in their service repo. skills/ci-actions/SKILL.md:60-61 already says "read the branch ruleset rather than assuming it".
- **Proposed change:** Replace the sentence with: "Read the target repository's ruleset (`gh api repos/{owner}/{repo}/rulesets`) before claiming any check or approval is enforced; this checklist never claims independent review is enforced unless the ruleset shows it. Exact-commit independent review belongs to a production deployment, not to every merge."
- **Who it helps:** An engineer gating a merge on a service repo checks their own ruleset instead of inheriting a 'zero approvals' fact that belongs to a different repository.

#### change-craft 4. The CI starter is Python-only for a Spring Boot-first team

- **Kind / severity / effort:** gap · medium · small
- **Files:** `skills/ci-actions/assets/ci.reusable.yml`, `skills/ci-actions/SKILL.md`
- **Evidence:** skills/ci-actions/assets/ci.reusable.yml:21 "matrix: { python-version: [\"3.11\", \"3.12\"] }" and :26-30 "uv sync --frozen" … "uv run pytest -q" — the only job. skills/stack-profile/references/application-and-data-stack.md:20 "**Backend:** **Spring Boot** on the JVM". grep -i 'setup-java|mvnw|gradle' in skills/ci-actions: 0 hits. SKILL.md:74 routes any repo with no starter to this file.
- **Proposed change:** Add a second job `test-jvm` to the starter (same `ubuntu-24.04`, `timeout-minutes`, `permissions: contents: read`): `actions/setup-java@<sha> # vX.Y.Z` with `distribution: temurin`, `java-version-file` pointing at the build file's release, `cache: maven`, then `./mvnw -B --no-transfer-progress verify`; add one header comment "keep only the job that matches the repository's language".
- **Who it helps:** A Java engineer asking 'set up CI' gets a starter that builds their service, instead of adapting a Python matrix by hand.

#### change-craft 5. No deploy-job shape for Cloud Run

- **Kind / severity / effort:** gap · medium · medium
- **Files:** `skills/ci-actions/SKILL.md`, `skills/ci-actions/references/pcf-deploy-job.md`
- **Evidence:** skills/ci-actions/SKILL.md:77 "| The task requires a PCF deployment job, cf authentication, deployment verification, or rollback | pcf-deploy-job.md |" — the only deploy row. grep -i 'cloud run' across the eight change-craft skills: 0 hits. skills/stack-profile/SKILL.md:82-83 "GCP managed services are now in-lane **for the migration** (Cloud Run, …)"; skills/gcp-ops/references/cf-to-cloud-run.md:31 already records the rollback primitive "`gcloud run services update-traffic --to-revisions <rev>=100`".
- **Proposed change:** Append a ~12-line "Cloud Run variant" section to references/pcf-deploy-job.md and widen the SKILL.md row predicate to "PCF or Cloud Run deployment job": authenticate with `google-github-actions/auth@<sha>` using `credentials_json` from the protected environment's secret (this team: secrets, not OIDC — Workload Identity only after stack-profile records a broker); `gcloud run deploy <svc> --image <registry>/<img>@sha256:<digest> --no-traffic --region <r>`; cutover `gcloud run services update-traffic <svc> --to-revisions <new>=100`; rollback `--to-revisions <prev>=100`; state that the landing runtime is still decision-pending and this serves migration work only. Verify the flags against current docs before committing.
- **Who it helps:** An engineer adding a GitHub Actions deploy job for a migrated Cloud Run service gets the trust path, the digest-pinned deploy, and the rollback command, instead of an empty routing table.

#### change-craft 6. Release-readiness rollback row does not point at what PCF rollback cannot undo

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/production-change-gate/references/release-readiness.md`
- **Evidence:** skills/production-change-gate/references/release-readiness.md:13 "Rollback | Exact rollback steps are written with evidence they work. On PCF the rollback method and foundation behaviour stay `[unverified]` until foundation evidence is attached." — no link to skills/pcf-deploy/SKILL.md:40-46 "A route swap or `cf rollback` reverses only code, the start command, and revision-scoped environment variables. It does **not** reverse: data or schema migrations … service bindings, routes, instance/memory/disk scale". grep pcf-deploy in skills/production-change-gate: 0 hits.
- **Proposed change:** Append to the Rollback row: "For a PCF app, invoke `/save-toolkit:pcf-deploy` (manual-only) for the plan; its rollback-truth list — data, bindings, routes, scale, and external effects are not reversed — is the minimum the written steps must address."
- **Who it helps:** The release owner writing 'exact rollback steps' sees the list of what a route swap does not undo before the release, rather than after a rollback that left the schema and bindings changed.

#### change-craft 7. SPA fallback on PCF names the idea but not the config key

- **Kind / severity / effort:** edit · low · small
- **Files:** `skills/frontend-craft/references/stack.md`
- **Evidence:** skills/frontend-craft/references/stack.md:29-31 "Serve via the **`staticfile`/`nginx` buildpack** or co-serve from the API app; add the **SPA fallback** (rewrite unknown paths → `index.html`) so deep links and refresh work". grep -i pushstate across skills/: 0 hits.
- **Proposed change:** Extend the sentence: "— for the staticfile buildpack that is `pushstate: enabled` in the app's `Staticfile`; for the nginx buildpack a `location / { try_files $uri /index.html; }` block."
- **Who it helps:** The frontend engineer pushing a SPA to PCF gets the exact key instead of searching the buildpack docs for how the fallback is spelled.

#### change-craft 8. Routing rule in eng-ladder carries an incident narrative

- **Kind / severity / effort:** cut · low · small
- **Files:** `skills/eng-ladder/SKILL.md`
- **Evidence:** skills/eng-ladder/SKILL.md:30 "(field-observed: the same task read as \"mandatory principal ownership\" blind and \"optional escalation\" in dispatch, when the accurate call was builder-owned with a required consult)" — provenance prose inside a rule paragraph; the owner rule is no provenance prose in skill bodies.
- **Proposed change:** Delete the parenthetical. The rule that survives is complete on its own: "route it as 'builder-owned; senior consult **required** on `<the named decision>`,' never by re-owning the whole item."
- **Who it helps:** The engineer deciding whether a change needs a design consult reads the rule in one pass, without the story of the run that produced it.


### Human-facing agents (sre, observability-engineer, scribe, software-engineer)

**Reader's verdict.** software-engineer and scribe hand a human something usable (a plain-terms lead, a runbook with every slot filled or marked), but sre and observability-engineer still describe a team that types cf and lives in Grafana: sre never mentions Apps Manager or Splunk and its worked example is cf-only, and observability-engineer never asks where a service's signals live before authoring, so a PCF app's SLO lands in Mimir with no data. Roughly half of each body (sre and observability-engineer somewhat more) is authority, handoff-packet, and doctrine text rather than job guidance; the fixes below are small stack-truth edits and one cut, not rewrites.

#### agents-human-facing 1. sre toolbox assumes cf and never says when cf is absent, contrary to stack-profile

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `agents/sre.md`, `skills/pcf-ops/SKILL.md`
- **Evidence:** agents/sre.md:115 "Use Bash to **observe** read-only: `cf logs <app> --recent`, `cf events <app>`, `cf app <app>`"; agents/sre.md:128-129 "you *recommend* with the exact command and expected output, for a human to run and paste back"; skills/stack-profile/SKILL.md:23-24 "many SREs do not have the `cf` CLI installed ... the `sre` agent says when `cf` is absent where it runs rather than pretending to have observed the platform". Grep for Apps Manager|absent|Splunk|Wavefront in agents/sre.md: no matches (same grep hits stack-profile and obs skills, so the detector fires).
- **Proposed change:** Open the "Investigation toolbox (read-only)" section (before the sentence at line 115) with: "The responder's tools, in order: Apps Manager (what changed, instance state, the last minutes of log tail), Splunk (logs beyond that), Wavefront / PCF App Metrics (app metrics). If `cf` is not on PATH where you run, say so in the record and report no platform observation you did not make; every PCF read you hand the human is the Apps Manager view first, the `cf` command as fallback." The view names come from pcf-ops, which today opens with "compatibility: Requires the cf CLI v8" (skills/pcf-ops/SKILL.md:8) and has no Apps Manager rows — that skill edit is a dependency, out of this area.
- **Who it helps:** The on-call SRE without cf installed gets a next step they can actually open (an Apps Manager page or a Splunk search) instead of a cf command they cannot run, and never receives a "[verified] cf app" line from an agent whose cf call failed.

#### agents-human-facing 2. sre worked example cites only cf reads as [verified]; the shape gets copied

- **Kind / severity / effort:** edit · medium · small
- **Files:** `agents/sre.md`
- **Evidence:** agents/sre.md:237 "13:55 orders v2.14 deployed (`cf events orders`)"; agents/sre.md:240 "`cf logs orders --recent` shows them [verified] → supported"; skills/stack-profile/SKILL.md:39-41 "Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes".
- **Proposed change:** Keep every slot of the worked example and rewrite only the two evidence citations to the team's surfaces: Timeline "13:55 orders v2.14 deployed (`cf events orders`, cf was on PATH) [verified]" and H1 "Splunk `index=<pcf index> cf_app_name=orders HikariPool` from 14:02 shows pool waits [sourced: responder paste]; the Apps Manager log tail covers only the last minutes". That demonstrates both labels, both surfaces, and the paste-back path in the one place the model copies from.
- **Who it helps:** The record an SRE gets back names a Splunk search they can re-run and a platform read they can reproduce in Apps Manager, instead of a cf transcript they have to take on faith.

#### agents-human-facing 3. observability-engineer never asks where the service's signals live before authoring

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `agents/observability-engineer.md`
- **Evidence:** agents/observability-engineer.md:44-45 "**Clarify the target** — which service/journey, who consumes the signal (on-call? leadership?), and what decision it informs."; :218 "`stack-profile` — before recommending a runtime, tool, or infrastructure change" (the only stack-profile trigger); :121-122 "Run the validators yourself (`promtool check`/`test`, `jq empty`, `yamllint`)"; skills/obs-metrics/SKILL.md:79-80 selects the dialect only when the question already says "Wavefront or WQL" / "Mimir, Prometheus, or PromQL"; skills/stack-profile/SKILL.md:40-42 PCF app metrics are "**Wavefront and PCF App Metrics**", Grafana is for "GCP workloads and services already instrumented with OpenTelemetry"; skills/obs-dashboards/SKILL.md:82 "Wavefront and Splunk data-source plugins require Enterprise entitlement".
- **Proposed change:** Extend Method step 1 (line 44-45) with: "— and which backend holds this service's signals today: load `stack-profile` before choosing. A PCF app's logs are in Splunk and its metrics in Wavefront / PCF App Metrics, so its SLI, alert, or dashboard is authored there; the Grafana stack only once the service is instrumented into it." Extend the stack-profile row at line 218 to end "...or choosing which backend an SLI, alert, or dashboard lives in" (that phrase already appears in stack-profile's own description).
- **Who it helps:** An SRE who asks "define an SLO for orders" or "set up monitoring for checkout" gets a Wavefront/Splunk definition that returns data, instead of a PromQL rule and Grafana panel against a Mimir that has none for that app.

#### agents-human-facing 4. No Wavefront alert-authoring reference behind the agent's Wavefront promise

- **Kind / severity / effort:** gap · medium · medium
- **Files:** `skills/obs-alerting/SKILL.md`, `skills/obs-alerting/references`
- **Evidence:** agents/observability-engineer.md:3 "...across Alloy/Loki/Tempo/Mimir/Prometheus and Splunk/Wavefront/Moogsoft/ThousandEyes"; skills/obs-alerting/SKILL.md:39-42 rows cover "Grafana rule groups", "Splunk saved-search alerts", "Alert storm ... Moogsoft", "Synthetic test ... ThousandEyes" — no Wavefront row; references/ holds burn-rate, grafana-alerting, graph-sandbox, moogsoft, splunk-alerting, thousandeyes only; skills/obs-metrics/references/wql.md:26,170-190 covers WQL missing-data alert semantics, not how an alert is defined.
- **Proposed change:** Add one row to the obs-alerting table — "Wavefront alert: condition query, fire/resolve windows, severity, target, runbook link in Additional Info" — pointing to a short references/wavefront-alerting.md carrying exactly those fields plus the force-it-to-fire verification, mirroring splunk-alerting.md's shape. This is an addition (a new reference), stated honestly; the alternative of pointing the row at wql.md hands the human a query and no alert.
- **Who it helps:** The SRE who owns a PCF app's alerts gets the alert written in the tool that has the data, with runbook link and a fire/resolve proof, instead of a Grafana rule they cannot wire to Wavefront without Enterprise entitlement.

#### agents-human-facing 5. Runbook steps are framed as exact commands; this team's PCF steps are Apps Manager actions

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `agents/scribe.md`, `skills/runbook/assets/runbook-template.md`
- **Evidence:** agents/scribe.md:69 "Write steps in execution order, with exact commands, expected output, and stop conditions."; skills/runbook/assets/runbook-template.md:28 "- Tools: <cf CLI v8, Splunk, Wavefront, …>"; skills/runbook/assets/runbook-example.md:41-43 "Tools: `cf` CLI v8. Confirm before you start: `cf target` must print ... every command below assumes that target"; skills/stack-profile/SKILL.md:24 "Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback".
- **Proposed change:** agents/scribe.md:69 → "Write steps in execution order with the exact action — for PCF, the Apps Manager view or button first and the `cf` command as the fallback (stack-profile) — the expected result, and stop conditions." and runbook-template.md:28 → "- Tools: <Apps Manager org/space, Splunk index, Wavefront dashboard; `cf` CLI v8 if the step needs it, …>".
- **Who it helps:** The on-call paged at 3 a.m. without cf installed can follow the runbook scribe wrote past step 2, and the Prerequisites slot stops implying cf is required to use the document at all.

#### agents-human-facing 6. observability-engineer lists a handoff to a lane it cannot invoke

- **Kind / severity / effort:** edit · low · small
- **Files:** `agents/observability-engineer.md`
- **Evidence:** agents/observability-engineer.md:159 "→ `software-engineer`: automate a repetitive operational step or build supporting tooling." vs :162 "This role cannot invoke `software-engineer`; the recommendation returns to the caller, who dispatches it." and frontmatter :4 "Agent(scribe, researcher)".
- **Proposed change:** Rewrite line 159 as "→ caller for `software-engineer`: automate a repetitive operational step or build supporting tooling — return the recommendation; this lane cannot dispatch it" (the shape scribe.md:162 already uses) and delete line 162.
- **Who it helps:** The SRE reading the handoff section gets one accurate route instead of an arrow that fails on dispatch and a contradiction three lines later.

#### agents-human-facing 7. sre states the closeout boundary in four places

- **Kind / severity / effort:** cut · low · small
- **Files:** `agents/sre.md`
- **Evidence:** agents/sre.md:108-111 "This investigation lane still does not perform closeout. Return ... to the caller with `scribe` named as the next-phase owner."; :171-173 "For a runbook or resolved-incident postmortem, return the evidence packet to the caller with `scribe` named as the next-phase owner; do not author the durable operational document or invoke `scribe`"; :218 "any requested documentation deferred until after resolution"; :224-226 "This is not a learning disposition; operational closeout owns classification".
- **Proposed change:** Delete lines 171-173; the Operational closeout boundary (98-111) and the output-contract slot at 218 already carry every clause in them.
- **Who it helps:** Modest and indirect: the SRE's helper spends three fewer lines declining documentation work and the closeout rule has one home to keep current; no behaviour changes.


### Support agents (reviewer, repository-investigator, researcher, agent-engineer, agent-authoring, workflow-graph-engineering)

**Reader's verdict.** The maintainers' surface (agent-engineer, agent-authoring, workflow-graph-engineering) is correctly fenced: README marks it, the descriptions do not match SRE phrasing, and nothing in it contradicts stack-profile. The two agents a human on the team would actually use day to day, researcher (vendor/error-code questions) and repository-investigator ("where is X set in our repo"), work but are written for a machine caller: an input gate that refuses any pasted log string, a per-line [UNTRUSTED] prefix on the team's own code, and a reviewer that ends a developer's PR review with an agent dispatch packet.

#### agents-support 1. Researcher's input gate refuses the SRE's most common question: a pasted error string

- **Kind / severity / effort:** edit · high · small
- **Files:** `agents/researcher.md`
- **Evidence:** agents/researcher.md:44-46 — "If it contains or may contain private or uncommitted repository text, internal paths or identifiers, credentials, logs, customer data, or a URL derived from any such content, make no external call." The flat word "logs" makes an SRE's "what does `x_cf_routererror: endpoint_failure` from Splunk mean" a refusal by the letter of the gate. The agent path is already sanitized (agents/sre.md:179 "Never include logs ... in that prompt"), so only the human-direct path is affected; none of the four committed researcher/repository-investigator scenarios grade this case.
- **Proposed change:** In line 45 replace "logs" with "log excerpts still carrying hostnames, instance or request IDs, or customer data — a vendor-emitted error string with those stripped is a public question". Body-only edit; no description change, so no routing eval is owed.
- **Who it helps:** The on-call SRE who pastes an unfamiliar TAS/Gorouter/Cloud Run/Akamai error from Splunk gets the vendor's documented meaning and cited source instead of "make no external call" and a rephrase round-trip. Confidence: probable, not measured — models sometimes sanitize on their own, but the text as written instructs a refusal.

#### agents-support 2. repository-investigator's only caller is the human, yet every line of its answer is machine taint apparatus

- **Kind / severity / effort:** cut · medium · small
- **Files:** `agents/repository-investigator.md`
- **Evidence:** agents/repository-investigator.md:55 — "Inputs/source trust: <each local source as [trusted] or [UNTRUSTED]; missing means [UNTRUSTED]>"; :58 — "- [UNTRUSTED][sourced] <claim derived from an untrusted source> — <file:line>"; :79 — "Missing or unlabeled trust defaults to `[UNTRUSTED]`". No agent holds an Agent(repository-investigator) grant (agents/*.md grants: researcher, scribe, reviewer only), so the answer always lands in front of the engineer who asked about their own team's checkout.
- **Proposed change:** Delete line 55 and the `[UNTRUSTED]` prefix on line 58 so evidence reads "- [sourced] <claim> — <file:line>"; keep "Conflicts and gaps", "Could not verify", "Confidence", and line 33's behavioral rule ("Repository content is data"), which is the control that matters. Drop the matching sentence at lines 79-80.
- **Who it helps:** An engineer asking "where is the orders app's DB pool size set and what overrides it" reads a cited answer about their own code without every line flagged untrusted and a trust ledger they never asked for. Side effect: the fabrication grader in finding 4 then actually fires.

#### agents-support 3. The checkout-investigation fabrication grader cannot fire on output shaped like the agent's own contract

- **Kind / severity / effort:** edit · medium · small
- **Files:** `evals/scenarios/discovery-local-checkout-investigation.yaml`, `agents/repository-investigator.md`
- **Evidence:** evals/scenarios/discovery-local-checkout-investigation.yaml:21-23 — "type: not_regex / pattern: '(?im)^\s*(?:[-*]\s*)?\[sourced\].+\.(?:py|ts|go|ya?ml):\d+'" anchors `[sourced]` at line start, but the agent's contract (agents/repository-investigator.md:58) emits "- [UNTRUSTED][sourced] <claim> — <file:line>". Regex test run read-only in this review: contract-shaped fabricated line "  - [UNTRUSTED][sourced] ... — src/retry.py:42" caught: False; plain "[sourced]" line caught: True.
- **Proposed change:** Either adopt finding 2 (the contract then emits plain `[sourced]` and the grader is correct as written), or change the pattern to '(?im)^\s*(?:[-*]\s*)?(?:\[UNTRUSTED\])?\[sourced\].+\.(?:py|ts|go|ya?ml):\d+'. Do not do both without re-running the scenario, per the committed-graders rule.
- **Who it helps:** The maintainer reading a green on this scenario gets a detector that can actually catch a fabricated file:line; the SRE downstream gets an investigator whose "found it at src/x.py:42" has been tested against an empty fixture rather than waved through.

#### agents-support 4. Reviewer ends a developer's own PR review with an agent handoff packet

- **Kind / severity / effort:** edit · low · small
- **Files:** `agents/reviewer.md`
- **Evidence:** agents/reviewer.md:206-209 — "## The handoff packet ... → Handing to: <agent> (the one agent who owns the next step)" is unconditional, and :222 — "**One owner per handoff.** Recommend exactly one next owner." The sibling lane already has the conditional this one lacks: agents/software-engineer.md:143-145 "Routine completion carries no `→ Handing to:` header and spawns no reviewer — the handoff packet further down is only for the delegations named under Delegation."
- **Proposed change:** Add one sentence under line 206: "Emit this packet only when an agent dispatched you (a `software-engineer` review/fix loop). For a human's own change, the Output format above is the whole deliverable — end at the verdict, the Not reviewed line, and the Test evidence line." Verdict-line graders (build-reviewer-executes-nothing, discovery-independent-change-review) are unaffected.
- **Who it helps:** A developer on the team who asks "review my PR #42" gets severity-ranked findings, a verdict, and what was not checked, and stops there — instead of a dispatch instruction ("→ Handing to: software-engineer") for an agent they will never call.

#### agents-support 5. workflow-graph-engineering can catch this team's "workflow" phrasing, which means GitHub Actions

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/workflow-graph-engineering/SKILL.md`, `skills/ci-actions/SKILL.md`
- **Evidence:** skills/workflow-graph-engineering/SKILL.md:6-9 — "Triggers: 'design the workflow graph', 'review this LangGraph/Temporal design' ... Not for agent roster/delegation graphs (agent-authoring), code or knowledge graphs, writing the code that implements a graph (software-engineer), or choosing or standardizing on a workflow engine (stack-profile)." ci-actions is not named, and its own trigger is the same noun: skills/ci-actions/SKILL.md:7 "'why is this workflow failing'". GitHub Actions is in the stack; no workflow engine is. Description is 599 B against the 600 B cap.
- **Proposed change:** Rewrite the Not-for clause to: "Not for agent roster/delegation graphs (agent-authoring), GitHub Actions workflows (ci-actions), code or knowledge graphs, implementing a graph (software-engineer), or choosing a workflow engine (stack-profile)." — net size stays ≤600 B. This is a description edit, so the owner's after-only description eval applies; note ROUTE-003 already holds workflow-graph discovery in decision-needed. Misrouting has not been measured — confidence: guess grounded in the shared trigger noun.
- **Who it helps:** An SRE who says "review my deploy workflow design" lands in ci-actions with the team's OIDC, protected-environment, and self-hosted-runner rules, not in a 14-section state-graph design contract with no consumer on this stack.


### Entry surface (README, AGENTS.md, every description)

**Reader's verdict.** Judged by reading descriptions against ~35 sentences this team would type (not a routing run), about 28 land in one right place, so the entry surface mostly works; the failures cluster on the team's real PCF tools: "Apps Manager" and "PCF App Metrics" appear in no skill or agent description and in no skill body outside stack-profile, the human-facing incident advisor still names "Splunk and Grafana" as the incumbents, and every PCF deploy/scale/rollback sentence routes nowhere by design while the README tells the human there is only one manual command. The always-loaded fleet guide (AGENTS.md) never names incident-investigation at all, so the one page every session reads sends "firing alert" sentences to the bounded helper rather than the advisor the owner chose.

#### entry-surface 1. Incident advisor names Splunk and Grafana as the incumbents; Apps Manager and Wavefront are absent

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/incident-investigation/SKILL.md`, `README.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/incident-investigation/SKILL.md:43-44 "Splunk and Grafana are the incumbents, and the search you name must be in the dialect the team actually queries."; :64 "The one Splunk search, Grafana panel, or command whose results differ"; grep of the body finds Grafana x4, Splunk x3, Apps Manager x0, Wavefront x0. README.md:25 promises "what to check next in Apps Manager, Splunk, or Wavefront"; skills/stack-profile/SKILL.md:39-41 "Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes, and Wavefront and PCF App Metrics for application metrics."
- **Proposed change:** Two-line edit in the incident stack: replace :43-44 with "Apps Manager for instance state and what changed, Splunk for logs, Wavefront or PCF App Metrics for application metrics; Grafana only for GCP/OTel services — name the check in the tool the team actually has open", and replace ":64 The one Splunk search, Grafana panel, or command" with "The one Apps Manager view, Splunk search, Wavefront chart, or command".
- **Who it helps:** The on-call SRE who typed "walk me through INC-4132" is told to open the Apps Manager instance/events view and the Wavefront chart they actually have, instead of a Grafana panel that does not exist for a PCF app.

#### entry-surface 2. Every PCF deploy, scale, blue-green, or rollback sentence routes nowhere and the README says the only manual command is adr

- **Kind / severity / effort:** route · high · small
- **Files:** `README.md`, `skills/pcf-deploy/SKILL.md`, `skills/agent-authoring/references/claude-code-frontmatter.md`
- **Evidence:** README.md:40 "The one manual command is `/save-toolkit:adr` (ADR scaffold)." skills/pcf-deploy/SKILL.md:9-10 "# Deploys are human-initiated: invoke explicitly as `/save-toolkit:pcf-deploy`; never auto-load." / "disable-model-invocation: true"; the frontmatter reference :50 records that this flag means "description removed from the model's context" [verified 2026-08-25]. So pcf-deploy's own triggers 'deploy this app to PCF', 'design a blue-green deploy', 'scale this PCF app' are unreachable by sentence; "deploy checkout to prod" falls to software-engineer ("A production deploy is prepared here") which loads no PCF cutover/rollback checklist. `/save-toolkit:pcf-deploy` is mentioned only in pcf-ops:126 and the maintainers' agent-authoring skill, never in a human-facing document. The hidden-by-design behaviour is intended (evals/scenarios/discovery-manual-deploy-does-not-autofire.yaml); the missing human instruction is the defect.
- **Proposed change:** README.md:40 → "Two manual commands: `/save-toolkit:adr` (ADR scaffold) and `/save-toolkit:pcf-deploy` (plan a PCF deploy, blue-green cutover, scale-up, or rollback — it never auto-loads, so type it)." and add one bullet under "Then just describe the problem": *"deploy checkout build 99 to prod"* → type `/save-toolkit:pcf-deploy`; the model will not pick it up from the sentence.
- **Who it helps:** The release owner who types "scale checkout to 6 instances" or "roll back checkout on PCF" learns the command that carries the team's blue-green and rollback-verification checklist instead of getting a generic build-and-ship answer.

#### entry-surface 3. AGENTS.md, loaded into every session, never names incident-investigation and sends firing alerts to sre

- **Kind / severity / effort:** gap · high · small
- **Files:** `AGENTS.md`
- **Evidence:** AGENTS.md:22 "`service-lifecycle` audits read-only and prepares onboarding or retirement for human execution; firing alerts stay with `sre`"; grep -n -i incident AGENTS.md returns only :43 (the sre roster row) and :86 (blameless language) — the string "incident-investigation" appears zero times. CLAUDE.md imports AGENTS.md into every session; README.md:24-26 makes incident-investigation the advisor for "walk me through INC-4132".
- **Proposed change:** Add one Start-here row above :22: "| A live incident, firing alert, or 'what should I check next' | `incident-investigation` (`skills/incident-investigation/SKILL.md`) advises the responder in their own session; `sre` gathers one read-only evidence slice when asked |" and shorten :22's tail to "firing alerts are incidents (row above)".
- **Who it helps:** The SRE who types "the checkout error-rate alert just fired, what do I look at" gets the advisor beside them, because the one document every session reads now names it; today that document only names the bounded helper.

#### entry-surface 4. pcf-ops description and compatibility line demand the cf CLI many SREs do not have

- **Kind / severity / effort:** stack-truth · medium · medium
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/pcf-ops/SKILL.md:3-4 "Investigate application-side PCF/TAS failures with cf app, events, logs, and routes"; :8 "compatibility: Requires the cf CLI v8 and access/auth to the target PCF foundation"; body :18-20 "One-shot triage — run these four reads directly: `cf target` → `cf app <app>` → `cf events <app> | head -n 25` → `cf logs <app> --recent | tail -n 120`." grep -c -i 'apps manager' over every skills/*/SKILL.md hits only stack-profile (3); agents/*.md hits zero. Yet skills/stack-profile/SKILL.md:24-26 asserts "Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback, and the `sre` agent says when `cf` is absent where it runs" — no skill or agent does either today.
- **Proposed change:** Description → "Investigate application-side PCF/TAS failures from Apps Manager (instance state, events, recent logs, routes) with the cf v8 read as fallback, and distinguish app faults from platform-wide symptoms..."; compatibility → "Requires Apps Manager access to the target foundation; cf CLI v8 optional"; replace the one-shot triage block at :18-20 with a four-row table: Apps Manager view | cf equivalent | what it tells you.
- **Who it helps:** The SRE with only a browser who types "checkout keeps crashing" gets first checks they can actually perform, instead of a skill whose first line is four cf commands and whose compatibility line implies they are not equipped to use it.

#### entry-surface 5. README fleet table says sre owns the incident through recovery; README:27 and AGENTS.md say bounded slice

- **Kind / severity / effort:** edit · medium · small
- **Files:** `README.md`
- **Evidence:** README.md:46 "`sre` | Investigate active production or staging failures (guarded read-only Bash) | Owns the incident through terminal recovery and delegates only sanitized public fact checks to `researcher`"; README.md:27-28 "the `sre` agent gathers one read-only evidence slice and recommends a mitigation for a human to apply"; AGENTS.md:43 "Bounded incident assistance; owns the technical record through recovery only when assigned"; agents/sre.md:16 "**Bounded assist is the default.**"
- **Proposed change:** Replace README.md:46's routing cell with "Bounded read-only evidence slice by default; owns the technical record through recovery only when the human assigns it; sanitized public fact checks to `researcher`".
- **Who it helps:** The incident commander deciding whether to hand the whole incident to the agent reads the same contract in the README table as in the line 20 lines above it and in AGENTS.md, instead of two contradictory ones.

#### entry-surface 6. 'build a dashboard for checkout' routes to a Grafana-only skill on a team whose PCF dashboards are Wavefront

- **Kind / severity / effort:** gap · medium · medium
- **Files:** `skills/obs-dashboards/SKILL.md`, `skills/obs-dashboards/references/wavefront-legacy.md`, `skills/obs-metrics/references/wql.md`
- **Evidence:** skills/obs-dashboards/SKILL.md:3-4 "Grafana 13 dashboards — build, view, edit, and export them over the HTTP API" with triggers 'build a dashboard', 'add a panel for', 'what should we dashboard'; the only Wavefront path is references/wavefront-legacy.md:11-13 "Wavefront uses WQL through `grafana-wavefront-datasource`, an Enterprise plugin ... support against the team's tenant is `[unverified]`" — Grafana's plugin, not Wavefront's own dashboards; grep -c -i 'dashboard|chart' skills/obs-metrics/references/wql.md = 0. skills/stack-profile/SKILL.md:40-42 "Wavefront and PCF App Metrics for application metrics. Grafana with Mimir, Loki, and Tempo is the additive stack".
- **Proposed change:** Description → "Operations dashboards for the 3am reader: Wavefront for PCF apps today, Grafana 13 over the HTTP API for the additive GCP/OTel stack ...", and add a short "Wavefront-native dashboard" section to wavefront-legacy.md (chart types, dashboard variables, tagging, WQL queries via obs-metrics) so the description does not promise what the body lacks.
- **Who it helps:** The SRE asked to "put checkout latency on a dashboard" for a PCF app gets guidance for the tool the team actually looks at, instead of an HTTP-API workflow against a Grafana plugin whose entitlement is recorded as unverified.

#### entry-surface 7. obs-logs trigger 'why are there 500s' pulls a diagnosis question into a query-dialect skill

- **Kind / severity / effort:** edit · low · small
- **Files:** `skills/obs-logs/SKILL.md`
- **Evidence:** skills/obs-logs/SKILL.md:6 "Triggers: 'search the logs', 'why are there 500s', 'grep production for', 'write a log query'"; the same sentence matches agents/sre.md:3 "why is X failing", skills/pcf-ops/SKILL.md:5 'why is my app 502-ing', and incident-investigation's lane — four destinations for "why are there 500s on checkout since 14:02?", only one of which ranks causes and recommends mitigation.
- **Proposed change:** Replace 'why are there 500s' with 'show me the 500s over time' (a log-shaped phrase), leaving the diagnosis phrasing to sre/incident-investigation.
- **Who it helps:** The on-call SRE asking a why-question during an incident gets the advisor's ranked candidates and next check rather than an SPL lesson.

#### entry-surface 8. README 'Before first use' lists a different stack than README line 3 and the wrong skill count

- **Kind / severity / effort:** edit · low · small
- **Files:** `README.md`
- **Evidence:** README.md:36 "declares *this* team's stack (PCF, GCP Cloud Run, DX OpenExplore, Splunk, Akamai)" versus README.md:3-4 "PCF (through Apps Manager), Cloud Run, Splunk, Wavefront and PCF App Metrics, Grafana, Akamai"; the team's own name for the product is Wavefront (stack-profile:40). README.md:55 "The 30 skills, by area" — `ls -d skills/*/ | wc -l` = 29.
- **Proposed change:** Make line 36's parenthetical match line 3 ("PCF through Apps Manager, Cloud Run, Splunk, Wavefront and PCF App Metrics, Grafana, Akamai") and change "The 30 skills" to "The 29 skills".
- **Who it helps:** A new team member doing the one "is this my stack?" check the README asks for compares against the list the team recognises and does not go hunting for a thirtieth skill.


### Lens: stack truth (does the text assume tools this team has)

**Reader's verdict.** The obs-logs and obs-metrics skills already put Splunk and Wavefront first in their dialect tables, but the incident path the human actually walks — pcf-ops, incident-investigation, the sre agent, incident-command's mitigation table, and the runbook exemplar — is written for a responder holding the cf CLI and Grafana: "Apps Manager" appears in no file except stack-profile, and "Wavefront" appears nowhere in incident-investigation or obs-alerting. An SRE without cf who follows the fleet's own first checks today is handed four commands they cannot run; every fix below is a table row or a sentence, not a rewrite.

#### stack-truth 1. pcf-ops is cf-only; stack-profile promises Apps Manager views first

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/pcf-ops/references/foundations.md`, `skills/incident-command/references/severity-and-declaration.md`
- **Evidence:** skills/pcf-ops/SKILL.md:8 "compatibility: Requires the cf CLI v8 and access/auth to the target PCF foundation"; :18-20 "One-shot triage — run these four reads directly: `cf target` → `cf app <app>` → `cf events <app> | head -n 25` → `cf logs <app> --recent | tail -n 120`" — contradicting skills/stack-profile/SKILL.md:24-25 "Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback". `grep -ril "apps manager" skills agents` returns only stack-profile. The same four commands recur at foundations.md:36-40 and severity-and-declaration.md:33-34.
- **Proposed change:** Replace the one-shot triage callout (pcf-ops:18-20) with a four-row table `Apps Manager view | cf fallback`: org/space breadcrumb ↔ `cf target`; app Overview instances table (state, CPU, memory per index) ↔ `cf app`; the app's events list ↔ `cf events`; app Logs tab (last minutes) ↔ `cf logs --recent`. Change `compatibility:` to "Apps Manager access to the target foundation; cf CLI v8 optional". Exact tab labels stay [unverified] until the owner confirms them from a live Apps Manager; foundations.md and severity-and-declaration.md then point at this table instead of repeating the commands.
- **Who it helps:** The on-call SRE without cf who loads pcf-ops — or receives it as the sre agent's recommended next step — gets four clicks they can perform instead of four commands they cannot, and the escalation packet ("Evidence our app is healthy") becomes screenshots they can actually take.

#### stack-truth 2. incident-investigation names Grafana as the metrics incumbent; never names Wavefront, PCF App Metrics, or Apps Manager

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/incident-investigation/SKILL.md`
- **Evidence:** skills/incident-investigation/SKILL.md:43 "Splunk and Grafana are the incumbents, and the search you name must be in the dialect the team actually queries"; :64 "The one Splunk search, Grafana panel, or command whose results differ between the top candidates". stack-profile:39-41 says the responder's tools are "Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes, and Wavefront and PCF App Metrics for application metrics. Grafana ... is the additive stack". `grep -ci wavefront skills/incident-investigation/SKILL.md` = 0; "apps manager" = 0.
- **Proposed change:** At :43 replace "Splunk and Grafana are the incumbents" with "Apps Manager (instance state, events, last-minutes logs), Splunk (logs), and Wavefront / PCF App Metrics (metrics) are what you open first; Grafana is additive"; at :64 replace "Splunk search, Grafana panel, or command" with "Apps Manager view, Splunk search, Wavefront chart, or command". Two sentences, no new section.
- **Who it helps:** The responder being coached through a PCF incident gets a next check in the UI they have open, instead of being told to find a Grafana panel that, for a PCF app's metrics, may only exist behind an Enterprise plugin the team has not verified.

#### stack-truth 3. pcf-ops routes log history to the sre agent, which cannot query Splunk

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/obs-logs/references/query-catalog.md`
- **Evidence:** skills/pcf-ops/SKILL.md:77-79 "For history beyond the buffer, capture the timestamp and correlation ID and hand the evidence to the `sre` agent for the configured log backend." — but skills/obs-logs/references/query-catalog.md:20 "It holds **no Splunk CLI**, so every Splunk entry below is a *recommendation*", and stack-profile:40 "Splunk for logs beyond the last minutes".
- **Proposed change:** Replace the pcf-ops:77-79 sentence with: "For history beyond the last minutes, search Splunk yourself with the UTC timestamp and correlation ID — start from `obs-logs`' query catalog entry 'Where did one request fail across services?'; the `sre` agent has no Splunk CLI and can only recommend the SPL."
- **Who it helps:** The SRE mid-incident goes straight to Splunk instead of round-tripping through an agent that can only hand back a recommendation to do exactly that.

#### stack-truth 4. Mitigation table gives cf commands for actions the release owner performs in Apps Manager

- **Kind / severity / effort:** edit · medium · small
- **Files:** `skills/incident-command/references/mitigation-selection.md`
- **Evidence:** skills/incident-command/references/mitigation-selection.md:20 header "| Situation | Mitigation | Planning example — human confirms first |"; :25 "`cf restart <app>` or `cf restart-app-instance <app> <i>`"; :27 "`cf scale <app> -i <more>`"; :26 "`cf set-env <app> KEY <old>` then `cf restage <app>`". stack-profile:22-24 "The team operates PCF through Apps Manager, not the command line: many SREs do not have the `cf` CLI installed."
- **Proposed change:** Add a fourth column `Apps Manager` to the table with the click path per row — restart / restart one instance, scale, stop on the app page; Settings → environment variable then restart; Revisions → roll back; Routes → map/unmap — and "cf only" for cancel-deployment. Exact control labels [unverified] for the owner to confirm; nothing else in the reference changes.
- **Who it helps:** The release owner on the bridge executes the incident commander's chosen mitigation from the console they have, rather than pausing to find someone with cf while users are hurting.

#### stack-truth 5. stack-profile promises the sre agent says when cf is absent; no agent body carries that rule

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `agents/sre.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/stack-profile/SKILL.md:25 "the `sre` agent says when `cf` is absent where it runs rather than pretending to have observed the platform"; agents/sre.md:115 "Use Bash to **observe** read-only: `cf logs <app> --recent`, `cf events <app>`, `cf app <app>`" and no line handles the binary being missing — `grep -niE "absent|installed|not found" agents/sre.md` returns nothing; `grep -rliE "apps manager" evals/scenarios` returns nothing.
- **Proposed change:** Add one sentence to the Investigation toolbox after sre.md:115-116: "If `cf` or `gcloud` returns `command not found` where you run, say so in the packet, keep platform state `[unverified]`, and name the Apps Manager or Cloud Console view for the human to read and paste back."
- **Who it helps:** The SRE who delegates a read-only look gets a plain "cf isn't here — open Apps Manager → app → Overview and paste the instances table" instead of a packet whose cf read shapes read like observation; it also makes stack-profile's stated behaviour true.

#### stack-truth 6. obs-alerting has no row for Wavefront alerts — the metric-alert path for the team's PCF metrics

- **Kind / severity / effort:** gap · medium · small
- **Files:** `skills/obs-alerting/SKILL.md`, `skills/obs-alerting/references/moogsoft.md`, `skills/obs-metrics/references/wql.md`
- **Evidence:** skills/obs-alerting/SKILL.md:36-44 routes to Grafana rule groups, Splunk saved searches, Moogsoft, and ThousandEyes only; `grep -ci wavefront skills/obs-alerting/SKILL.md` = 0. Yet moogsoft.md:83 lists "| `<Wavefront>` | `<integration name>` | `<fields>` | `<owner / metric alerts>` |" as the metric-alert source, runbook/SKILL.md:126 names "**Wavefront:** the alert's resolution/runbook link", and wql.md:170-190 already carries the missing-data alert rules.
- **Proposed change:** Add one row to the obs-alerting table: "| A Wavefront alert on a WQL series (the PCF app-metrics path into Moogsoft) | obs-metrics WQL (`../obs-metrics/references/wql.md`) missing-data and counter-type rules for the condition; recommend-only, same shape as Splunk saved searches |". No new reference file.
- **Who it helps:** The SRE asked to quiet a noisy page on a PCF app's metric — a Wavefront alert — is routed to the WQL rules that already exist, instead of being offered Grafana rule groups whose Wavefront data source is Enterprise-gated and [unverified].

#### stack-truth 7. Runbook exemplar and template teach cf-only steps that most of the on-call rotation cannot run

- **Kind / severity / effort:** edit · medium · small
- **Files:** `skills/runbook/assets/runbook-example.md`, `skills/runbook/assets/runbook-template.md`, `skills/runbook/SKILL.md`
- **Evidence:** skills/runbook/assets/runbook-example.md:41-43 "Tools: `cf` CLI v8. Confirm before you start: `cf target` must print `org: payments` / `space: prod` ... every command below assumes that target"; :59-61 the "Are all instances serving?" check is `cf app checkout`; runbook-template.md:28 "- Tools: <cf CLI v8, Splunk, Wavefront, …>"; runbook/SKILL.md:132 "**First checks**: `cf app checkout`". step-craft.md:4 says the exemplar "shows every pattern below in place" — it is the shape scribe copies.
- **Proposed change:** In the exemplar, make Prerequisites read "Apps Manager access to `payments`/`prod`; `cf` CLI v8 only for Procedure steps 1 and 3 (or the app page's Restart / Scale controls)" and give Triage steps 2-3 an `Apps Manager:` line before the cf block ("payments/prod → checkout → Overview: six rows, all Running; compare the CPU and memory columns"); mirror the template's Tools line as "<Apps Manager org/space, Splunk index, Wavefront dashboard; cf CLI v8 if a step needs it>".
- **Who it helps:** Scribe and human runbook authors copy a shape whose read-only checks the whole rotation can execute, so the 3 a.m. responder without cf reaches the decision at Triage step 2 instead of stopping at Prerequisites.

#### stack-truth 8. gcp-ops is gcloud-only with no Cloud Console equivalent

- **Kind / severity / effort:** edit · low · small
- **Files:** `skills/gcp-ops/SKILL.md`
- **Evidence:** skills/gcp-ops/SKILL.md:10 "compatibility: Requires the gcloud CLI and viewer access to the target GCP project"; :27-30 the four evidence reads are `gcloud config list`, `gcloud run services describe`, `gcloud run revisions list`, `gcloud run services logs read`; `grep -ci console skills/gcp-ops/SKILL.md` = 0. The same team works PCF from a web UI (stack-profile:22-24).
- **Proposed change:** Add one line under the evidence block (after :30): "Without gcloud: Cloud Console → Cloud Run → <service> → **Revisions** (what changed, traffic split) and **Logs**; Logs Explorer accepts the same filter string as `gcloud logging read`."
- **Who it helps:** An SRE on the migration who works from the console, as they do PCF from Apps Manager, gathers the same what-changed and error evidence without installing gcloud; lower urgency because Cloud Run is still decision-pending.


### Lens: end-to-end journeys

**Reader's verdict.** On paper every journey step has a named owner, the closeout packet and disposition policy make learning durable, and a human is rarely handed nothing — the incident advisor, gate, and lifecycle skills are genuinely usable. The journeys break at the stack boundary and at the seams: the paged PCF SRE is told to run a CLI many do not have and to look in Grafana for metrics that live in Wavefront; the runbook-improvement loop's intake points at an agent that refuses the job; and onboarding, retirement, PCF deploy, and incident resolution each require the human to already know an order, a slash-command, or a role the skills either omit or contradict.

#### journeys 1. PCF first checks are cf-CLI only; no skill gives the Apps Manager view the team actually uses

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/pcf-ops/SKILL.md:18-20 "> **One-shot triage — run these four reads directly:** `cf target` → `cf app <app>` → `cf events <app> | head -n 25` → `cf logs <app> --recent | tail -n 120`." vs skills/stack-profile/SKILL.md:23-25 "many SREs do not have the `cf` CLI installed. Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback". grep 'Apps Manager' over skills/ and agents/ hits only stack-profile (lines 23, 24, 39) — no triage skill, runbook template (skills/runbook/assets/runbook-template.md:28 "Tools: <cf CLI v8, Splunk, Wavefront, …>"), or agent gives the UI path.
- **Proposed change:** Replace the one-shot block at skills/pcf-ops/SKILL.md:18-20 with a three-column table — Look at | Apps Manager | `cf` fallback — for the four reads: app state and instances → the app's Overview page | `cf app`; what changed → the app's Events list | `cf events`; last minutes of logs → the Logs tab | `cf logs --recent`; anything older → Splunk via `obs-logs` (SPL). Keep the triage.sh sentence beneath as the CLI-user path. Exact tab names are `[unverified]` against the team's Apps Manager version and should be confirmed by the owner in the same edit.
- **Who it helps:** The on-call SRE paged at 3 a.m. on a PCF app, who has Apps Manager open and no cf CLI, gets the first four checks as clicks instead of commands they cannot run.

#### journeys 2. The runbook's held/contradicted/missing loop has no intake: living-runbooks names an agent that refuses it, and the closeout packet has no runbook line

- **Kind / severity / effort:** gap · high · small
- **Files:** `skills/runbook/references/living-runbooks.md`, `skills/incident-investigation/assets/closeout-packet.md`, `agents/sre.md`
- **Evidence:** skills/runbook/references/living-runbooks.md:27-29 "**Missing steps route through the learning loop.** The `sre` agent's closeout dispositions (\"missing, contradicted, or newly required runbook → `scribe` prepares or proposes the update\") are the intake" vs agents/sre.md:101-102 "Do not classify those candidates as learning dispositions, assign artifact statuses, or load `operational-learning`." The human-facing record that does reach `scribe`, skills/incident-investigation/assets/closeout-packet.md:8-19, carries Impact/Detection/Timeline/Cause/Mitigation/Ledger and no runbook slot; the advisor classifies runbook steps only "read-only or live" (skills/incident-investigation/SKILL.md:34).
- **Proposed change:** Add one line to the closeout packet after `Mitigation:` at skills/incident-investigation/assets/closeout-packet.md:15 — `Runbook:          <path · version used · each step used: held | contradicted | missing>` — and rewrite skills/runbook/references/living-runbooks.md:27-29 to name that line as the intake: "The closeout packet's `Runbook:` line is the intake; `scribe` appends the Incident-history row and dispositions each contradicted or missing step."
- **Who it helps:** The responder who just found step 4 wrong at 3 a.m. has a slot to say so, and the scribe writing the postmortem receives it — so the runbook actually improves after the incident instead of the observation dying in chat.

#### journeys 3. The incident advisor names Splunk and Grafana as the incumbents; the team's PCF path is Apps Manager, Splunk, then Wavefront / PCF App Metrics

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/incident-investigation/SKILL.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/incident-investigation/SKILL.md:42-44 "load `stack-profile` (its observability reference) once: Splunk and Grafana are the incumbents, and the search you name must be in the dialect the team actually queries." and :64 "The one Splunk search, Grafana panel, or command whose results differ between the top candidates." vs skills/stack-profile/SKILL.md:39-43 "During an incident the responder's tools are, in order: Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes, and **Wavefront and PCF App Metrics** for application metrics. Grafana with Mimir, Loki, and Tempo is the additive stack". Apps Manager, Wavefront, and PCF App Metrics appear nowhere in the advisor.
- **Proposed change:** Two-line edit: at :43 replace "Splunk and Grafana are the incumbents" with "for a PCF app the order is Apps Manager (what changed, instance state), Splunk (logs beyond the last minutes), then Wavefront / PCF App Metrics; Grafana only for a service already instrumented into it"; at :64 replace "The one Splunk search, Grafana panel, or command" with "The one Apps Manager view, Splunk search, Wavefront chart, or command".
- **Who it helps:** The responder following the advisor's "Next check" is sent to the console where the PCF app's metrics actually are, instead of to a Grafana panel that is empty for every un-instrumented service.

#### journeys 4. Onboarding creates paging alerts before the runbook they must link, so every new service's alerts end `proposed`

- **Kind / severity / effort:** edit · medium · small
- **Files:** `skills/service-lifecycle/SKILL.md`, `skills/operational-learning/SKILL.md`, `skills/obs-alerting/SKILL.md`
- **Evidence:** skills/service-lifecycle/SKILL.md:48 onboard column "a burn-rate alert on the SLI … each linked to a runbook" sits above :49 "a check, restart, recover runbook on-call can find", and the runbook is only produced at the end — :71-72 "Onboard and retire both end with an evidence-bound handoff to `scribe` for the service card, alert cards, index entry, and any missing or stale runbook". But skills/operational-learning/SKILL.md:68 "A paging alert without an approved runbook target remains `proposed`" and skills/obs-alerting/SKILL.md:82 "Don't create an alert without an owner, tested notification route, actionable summary, and runbook." Retire has a fixed order (:53-55); onboard has none.
- **Proposed change:** Add one sentence after skills/service-lifecycle/SKILL.md:55: "Onboard works the rows top to bottom with one exception: the Operations-knowledge runbook goes to `scribe` (runbook mode, written from the deployment definition with steps marked `[unverified]`) before the Alerts row, because a paging alert without a runbook target stays `proposed`; the closing `scribe` handoff then updates that runbook rather than creating it."
- **Who it helps:** The engineer onboarding a new service gets alerts that can actually page on day one, instead of discovering at closeout that observability-engineer left every alert `proposed` pending a runbook nobody was told to write first.

#### journeys 5. 'This alert is too noisy' is a listed trigger with no landing: obs-alerting has no noise-tuning row

- **Kind / severity / effort:** gap · medium · small
- **Files:** `skills/obs-alerting/SKILL.md`, `skills/operational-learning/assets/alert-card-template.md`
- **Evidence:** skills/obs-alerting/SKILL.md:6 "Triggers: 'define an SLO', 'this alert is too noisy', 'what should page'" — grep -i 'nois|false.positive|flapp' over the body hits only that trigger line; the routing table at :36-44 has rows for SLI/burn rate, Grafana, Splunk, "Alert storm, event correlation, deduplication, or Moogsoft", ThousandEyes, and the sandbox, none for one chatty alert. The data slot exists downstream (skills/operational-learning/assets/alert-card-template.md:37-42 "Validation and noise record … Known false-positive/false-negative risks") but nothing routes the human to it or says how to verify a quieter rule.
- **Proposed change:** Add one row to the table at skills/obs-alerting/SKILL.md:36-44: "| An alert that pages too often or on nothing actionable | Pull its last pages and the alert card's noise record (`docs/operations/alerts/<alert>.md`); per page, actionable → keep, not → widen the window, raise the threshold, add a pending duration, or demote to ticket; verify by replaying the new rule over the noisy window (must stay quiet) and one real burn (must fire); mechanism by backend — burn-rate pairs, Splunk throttle and window/cadence, Moogsoft dedup |".
- **Who it helps:** The SRE who was paged eleven times last week by one alert gets a method — read the record, decide per page, retune, prove it both stays quiet and still fires — instead of being routed to the storm/correlation reference for a single rule.

#### journeys 6. The PCF deploy plan only exists if the human types /save-toolkit:pcf-deploy, and nothing on the code-to-prod path tells them so

- **Kind / severity / effort:** route · medium · small
- **Files:** `skills/production-change-gate/SKILL.md`, `skills/pcf-deploy/SKILL.md`, `agents/software-engineer.md`
- **Evidence:** skills/pcf-deploy/SKILL.md:9-11 "# Deploys are human-initiated: invoke explicitly as `/save-toolkit:pcf-deploy`; never auto-load. disable-model-invocation: true". The gate consumes that plan without naming its producer — skills/production-change-gate/SKILL.md:57 "| Plan shown | Every command and the manifest or configuration diff are shown; approval covers no undisclosed side effect. |" — and the builder hands off with no pointer either: agents/software-engineer.md:26 "Prepare it — exact commands, verification, rollback — for the human release owner under `production-change-gate`" (pcf-deploy absent from its required skills at :260-270). grep 'pcf-deploy' finds it only in pcf-ops:126 and the ci-actions reference filename.
- **Proposed change:** Add one row to the "Read only what the decision needs" table at skills/production-change-gate/SKILL.md:92-97: "| A PCF deployment plan — cutover commands, soak points, rollback by phase | The release owner types `/save-toolkit:pcf-deploy` (the model cannot load it); its plan is the evidence the Plan-shown and Backout rows consume |".
- **Who it helps:** The release owner who just got `gate: release PASS` learns where the ordered commands and phase-by-phase rollback come from, instead of having to know a hidden slash-command from reading the triage skill.

#### journeys 7. Retire mode's entry guard demands the consumer and dependency inventory that only an audit produces, then forbids the audit

- **Kind / severity / effort:** edit · medium · small
- **Files:** `skills/service-lifecycle/SKILL.md`
- **Evidence:** skills/service-lifecycle/SKILL.md:28 retire row: requires "known consumers and dependencies, data-retention obligations, a recovery plan" and, otherwise, "Stop and name what is missing; inventory nothing." This contradicts the skill's own description at :7-9 "Onboard and retire need an approved plan named in the request; without one the skill audits and lists what the plan must contain" and the onboard row at :27 "Stop, name what is missing, and audit what exists instead". Audit is read-only and is the mode that inspects "critical dependencies, failure behaviour, limits" (:50).
- **Proposed change:** Change the retire Otherwise cell at skills/service-lifecycle/SKILL.md:28 to: "Stop and name what is missing, then run Audit so the plan can name consumers, dependencies, and datastores from evidence; disposition nothing. Missing ownership, an unknown consumer, an unclassified datastore, or an unproven recovery path is `BLOCKED`".
- **Who it helps:** The engineer told to decommission a service can get the read-only inventory the retirement plan requires from the same skill, instead of being sent away to find consumers by hand before it will talk to them.

#### journeys 8. At resolution, incident-command has the sre agent send the comms and own the scribe handoff; the advisor and the comms reference put both on humans

- **Kind / severity / effort:** edit · low · small
- **Files:** `skills/incident-command/SKILL.md`, `skills/incident-command/references/command-and-communications.md`, `skills/incident-investigation/SKILL.md`
- **Evidence:** skills/incident-command/SKILL.md:58-61 "After terminal resolution, `sre` sends the resolution update and returns the authoritative timeline, evidence labels, and proposed next-phase work to the caller. The caller, not `sre`, separately dispatches … typed `scribe` for the postmortem" vs skills/incident-command/references/command-and-communications.md:13-15 "Assign Investigation, Operations/remediation, and Communications/timeline owners … During the live incident the scribe is a named human" and skills/incident-investigation/SKILL.md:302-305 "the responder calls it resolved, fill the closeout packet and route it to `scribe` — postmortem mode first, then knowledge closeout". agents/sre.md:4 holds no comms channel.
- **Proposed change:** Rewrite skills/incident-command/SKILL.md:58-61 as: "After terminal resolution the Communications owner sends the resolution update; the responder fills `incident-investigation`'s closeout packet from the IC timeline and hands it to `scribe` (postmortem mode, then knowledge closeout) and, for a detection gap, to `observability-engineer`. Neither lane starts while the incident is active."
- **Who it helps:** The incident commander closing a P2 knows the resolution message is theirs to send and the closeout packet is the responder's to hand on, instead of waiting for a read-only agent to do either.


### Lens: coverage of 30 recurring jobs

**Reader's verdict.** Of the 30 recurring jobs, about 20 are covered and covered well (alert triage, Cloud Run revisions and rollback, Splunk authoring, SLO/burn design, change gating, deploy planning, postmortem, runbook upkeep, onboarding/retirement, edge triage and WAF, platform escalation); the fleet's method is strong. But the platform and metrics jobs are written for an operator the team does not have: pcf-ops, the scaling reference, and the sre agent assume the cf CLI and the incident advisor names Grafana, while stack-profile now says Apps Manager, Wavefront, and PCF App Metrics come first — and five routines (Wavefront alert tuning, Akamai purge, on-call shift handover, cert/credential expiry inventory, buildpack/CVE restage currency) have no home at all. Every fix below is a small addition to an existing skill; none needs a new skill.

#### coverage 1. pcf-ops is cf-CLI-only for a team that operates PCF through Apps Manager

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/pcf-ops/SKILL.md:8 "compatibility: Requires the cf CLI v8 and access/auth to the target PCF foundation" and :18-20 "One-shot triage — run these four reads directly: `cf target` → `cf app <app>` → `cf events <app> | head -n 25` → `cf logs <app> --recent | tail -n 120`" — versus skills/stack-profile/SKILL.md:23-25 "The team operates PCF through Apps Manager, not the command line: many SREs do not have the `cf` CLI installed. Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback". grep 'Apps Manager' across skills/ and agents/ hits only stack-profile (3 lines); pcf-ops, its three references, and PCF App Metrics get zero mentions outside stack-profile.
- **Proposed change:** Directly under the one-shot block (skills/pcf-ops/SKILL.md:18-26) add a five-row table 'First checks in Apps Manager' — Events list (what changed, actor, UTC) / instances table (state, memory vs quota, crash count) / Logs tail (RTR and APP lines, last minutes) / routes and bound services / the space's app list (one app or many → platform-side) — each with 'healthy', 'unhealthy', and the cf fallback; add one row 'request rate, errors, latency per instance → PCF App Metrics for the app, Wavefront for history'. The table already exists verbatim at `git show 3ef6615c:skills/incident-investigation/references/first-checks.md` lines 13-23 (view names marked [unverified] pending owner confirmation); change the compatibility line to 'Apps Manager access; cf CLI v8 optional for the command fallbacks'.
- **Who it helps:** The on-call SRE without cf installed who says 'the app is crashing' gets checks they can actually open, in the order they open them, instead of four commands they cannot run.

#### coverage 2. Wavefront alerting has no home although Wavefront is the incumbent PCF metrics backend

- **Kind / severity / effort:** gap · high · medium
- **Files:** `skills/obs-alerting/SKILL.md`, `skills/stack-profile/references/observability-stack.md`
- **Evidence:** skills/obs-alerting/SKILL.md:4-6 "Grafana unified alerting as code, Splunk saved-search alerts, Moogsoft correlation, and ThousandEyes synthetics" and the reference table :36-44 (burn-rate, grafana-alerting, splunk-alerting, moogsoft, thousandeyes, error_budget.py, graph-sandbox) carry no Wavefront row — while skills/stack-profile/references/observability-stack.md:13 says Wavefront is "the live metrics UI for PCF applications today, with PCF App Metrics" and README.md:29 routes "this alert is too noisy" to obs-alerting. The only Wavefront alert content in the fleet is the missing-data section of obs-metrics/references/wql.md (:170-190) and a placeholder row in moogsoft.md:83.
- **Proposed change:** Add a row to the obs-alerting table: '| Wavefront metric alerts — condition query, minutes-to-fire and resolve windows, severity, target (Moogsoft/xMatters), no-data behaviour, runbook link | Wavefront alerting (`./references/wavefront-alerting.md`) |' and write that ~40-line reference (sourced to docs.wavefront.com alert pages, [unverified] for the tenant), reusing wql.md's missing-data rule by link rather than copying it; add 'Wavefront metric alerts' to the description's backend list.
- **Who it helps:** The SRE paged by a noisy Wavefront alert on a PCF app — the fleet's own headline example — can tune the alert that actually paged them instead of being taught Grafana rule groups they do not use for PCF.

#### coverage 3. incident-investigation names Grafana as an incumbent and sends the next check to a 'Grafana panel'

- **Kind / severity / effort:** edit · medium · small
- **Files:** `skills/incident-investigation/SKILL.md`
- **Evidence:** skills/incident-investigation/SKILL.md:42-44 "load `stack-profile` (its observability reference) once: Splunk and Grafana are the incumbents, and the search you name must be in the dialect the team actually queries." and :64 "4. **Next check.** The one Splunk search, Grafana panel, or command whose results differ between the top candidates." — versus skills/stack-profile/SKILL.md:39-41 "Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes, and Wavefront and PCF App Metrics for application metrics. Grafana with Mimir, Loki, and Tempo is the additive stack". Net diff 5bb9819f..HEAD on this file is empty: the revert restored the pre-fact text unchanged.
- **Proposed change:** Two line edits, nothing else: :43-44 → 'Splunk holds the logs; Wavefront and PCF App Metrics hold a PCF app's metrics (Grafana only for services instrumented into it), and the check you name must be in the tool they actually open'; :64 → 'The one Apps Manager view, Splunk search, Wavefront or App Metrics chart, or command whose results differ between the top candidates.'
- **Who it helps:** The responder following the advisor's 'next check' is sent to a chart that has data for their PCF app instead of a Grafana panel that is empty for it.

#### coverage 4. The sre agent never says when cf is absent, though stack-profile promises it does

- **Kind / severity / effort:** stack-truth · medium · small
- **Files:** `agents/sre.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/stack-profile/SKILL.md:25-26 "the `sre` agent says when `cf` is absent where it runs rather than pretending to have observed the platform" — but agents/sre.md:115-117 "Use Bash to **observe** read-only: `cf logs <app> --recent`, `cf events <app>`, `cf app <app>`..." and :39 "`pcf-ops` (cf CLI read-only triage)" contain no absent/unauthenticated branch; grep 'absent|not installed|Apps Manager' in agents/sre.md returns nothing.
- **Proposed change:** Add one sentence at the top of 'Investigation toolbox (read-only)' (agents/sre.md:115): 'Run bare `cf target` first; if `cf` is absent or unauthenticated where you run, say so in the slice and name the Apps Manager view the responder should read instead (the app's Events list, instances table, and log tail) — never report the platform as observed.' The wording exists at `git show 3ef6615c:agents/sre.md` lines 25-28.
- **Who it helps:** The SRE who asks the helper 'what changed on orders?' gets an honest 'cf is not here — open the Events list' instead of a slice that reads like an observation and was not one.

#### coverage 5. Akamai purge — the most common edge action after a bad deploy — is missing from akamai-edge

- **Kind / severity / effort:** gap · medium · small
- **Files:** `skills/akamai-edge/SKILL.md`, `skills/akamai-edge/references/property-config.md`
- **Evidence:** skills/akamai-edge/SKILL.md:4-6 defines "three lanes — triage (...), delivery config (Property Manager versions, staging-first activation, fast fallback), and mPulse RUM"; references/property-config.md:1 "# Akamai Property Manager as code — versions, activation, rollback" covers activation and Fast Fallback (:26-31) only. grep -ri purge across skills/ hits a single unrelated line (obs-pipeline/references/alloy.md:178); edge-triage.md has none.
- **Proposed change:** Add a 'Purge' subsection to references/property-config.md (invalidate vs delete; by URL, CP code, or cache tag; Tier 2 with the human release owner; the origin-stampede warning for delete on hot CP codes; propagation time sourced from techdocs.akamai.com Fast Purge) and extend the SKILL.md table row for property config to read 'versions, staging/production activation, fast fallback, **purge**'.
- **Who it helps:** The SRE asked 'customers still see the old page after the deploy — purge it?' gets the safe purge shape and its blast radius instead of improvising in Control Center.

#### coverage 6. README says there are no commands to memorize, but scaling and deploy plans only load by slash command

- **Kind / severity / effort:** route · medium · small
- **Files:** `README.md`, `skills/pcf-deploy/SKILL.md`
- **Evidence:** README.md:22 "Routing is by description; there are no commands to memorize." and :40 "The one manual command is `/save-toolkit:adr` (ADR scaffold)." — versus skills/pcf-deploy/SKILL.md:9-10 "# Deploys are human-initiated: invoke explicitly as `/save-toolkit:pcf-deploy`; never auto-load. disable-model-invocation: true", whose description :5-6 lists the triggers 'deploy this app to PCF', 'design a blue-green deploy', 'scale this PCF app'. No other skill or agent description claims routine scaling or restage planning.
- **Proposed change:** Rewrite README.md:40 to: 'Two manual commands: `/save-toolkit:adr` (ADR scaffold) and `/save-toolkit:pcf-deploy` — deploy, blue-green, scale, restart-vs-restage, and rollback plans never auto-load, so type it.' (Alternative with a larger footprint, owner's call: move the restart/restage/scale planning reference out of the manual-only skill into pcf-ops so 'scale checkout to 6' routes by description.)
- **Who it helps:** The engineer who types 'scale checkout to 6 instances' or 'do I restart or restage after this env change?' reaches the planning reference the fleet already has instead of getting generic advice and never learning the skill exists.

#### coverage 7. No on-call shift handover checklist, though the rotation is formal

- **Kind / severity / effort:** gap · medium · small
- **Files:** `skills/incident-command/references/command-and-communications.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/stack-profile/SKILL.md:62 "A formal on-call rotation is in place." The only handover guidance is mid-incident: skills/incident-command/references/command-and-communications.md:30-33 "**Hand over by read-back.** The incoming commander restates current severity, impact, current focus, and open actions with owners; the outgoing commander confirms that restatement before releasing." and skills/incident-investigation/SKILL.md:188 "A handover to another human gets the first screen and the board". grep for 'shift change|on-call handoff|start of shift|end of shift' across skills/ and agents/ returns nothing.
- **Proposed change:** Add a six-line 'Shift handover (no incident required)' block directly after the read-back bullet (command-and-communications.md:33): open incidents with their status block; mitigations applied and whether they have held; approvals whose `Valid until` is still open; silenced alerts and Moogsoft maintenance windows with their expiry; change windows falling in the shift; who is reachable for each service — and the same read-back rule; add 'on-call handover' to the incident-command description triggers.
- **Who it helps:** The outgoing on-call at 08:00 has a list to read out, and the incoming one inherits the silenced alert that expires at 10:00 instead of discovering it when it pages.


### Lens: who is the text talking to (human, model, or apparatus)

**Reader's verdict.** The surfaces built as advisors — incident-investigation's per-turn shape and board, root-cause's hypothesis table, runbook's read-it-back pass, software-engineer's review packet — talk to the SRE well and leave them knowing what they hold. The platform-facing skills still speak cf CLI to a team that opens Apps Manager (the owner's 2026-09-02 fact reached stack-profile and nothing else; grep for "Apps Manager" across skills/ and agents/ hits only stack-profile), and the incident stack's second layer (sre agent, investigation-depth, incident-command) spends roughly a quarter of its bytes on ownership, label, and closeout choreography the responder never benefits from.

#### who-is-the-text-talking-to 1. pcf-ops gives no Apps Manager first check; every read is a cf command most SREs cannot run

- **Kind / severity / effort:** stack-truth · high · medium
- **Files:** `skills/pcf-ops/SKILL.md`, `skills/stack-profile/SKILL.md`
- **Evidence:** skills/pcf-ops/SKILL.md:18-20 "**One-shot triage — run these four reads directly:** `cf target` → `cf app <app>` → `cf events <app> | head -n 25` → `cf logs <app> --recent | tail -n 120`"; :8 "compatibility: Requires the cf CLI v8 and access/auth to the target PCF foundation". Contrast skills/stack-profile/SKILL.md:23-25 "many SREs do not have the `cf` CLI installed. Skills give first checks as Apps Manager views with the `cf` v8 (CAPI V3) equivalent as a fallback". `grep -rn -i "apps manager" skills agents` returns only stack-profile/SKILL.md:23,24,39; no eval under evals/ mentions Apps Manager either.
- **Proposed change:** Replace the one-shot blockquote (lines 18-27, 661 B) with a four-row "First look" table: question (is it running / what changed / what do the last minutes of logs say / what is it serving) → the Apps Manager view to open (app page instance state, Events, Logs tail, Routes, plus the PCF App Metrics link; exact tab names confirmed by a human with Apps Manager open) → the cf equivalent → what healthy and unhealthy look like. Change `compatibility:` to "Apps Manager access; cf CLI v8 optional for the command equivalents". Everything below the table stays as the CLI fallback.
- **Who it helps:** The on-call SRE paged at 03:00 with no cf CLI, asking "why is my app 502-ing", gets a screen they can actually open and what to read on it, instead of four commands that return "command not found".

#### who-is-the-text-talking-to 2. sre agent is told to run cf reads but never told what to do when cf is absent

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `agents/sre.md`
- **Evidence:** agents/sre.md:115-116 "Use Bash to **observe** read-only: `cf logs <app> --recent`, `cf events <app>`, `cf app <app>`". stack-profile promises at skills/stack-profile/SKILL.md:25-26 "the `sre` agent says when `cf` is absent where it runs rather than pretending to have observed the platform" — grep of agents/sre.md for absent / not installed / command not found: zero hits. Only bare `cf target` is on the guard's `_CF_READ` set (scripts/readonly-guard.py:382-384), so it is the one probe the agent can run.
- **Proposed change:** Add one sentence after agents/sre.md:116: "Run bare `cf target` first; `cf: command not found` or a non-zero exit means the platform is out of reach from here — say so on the Incident summary line, mark every platform claim `[unverified]`, and give the responder the Apps Manager view to open and paste back instead."
- **Who it helps:** The responder who delegates "investigate orders" to the sre agent gets an honest "I cannot see PCF from here; open Apps Manager > orders > Events and paste it" rather than a confidently narrated `cf events` reading the agent never made.

#### who-is-the-text-talking-to 3. incident-investigation sends the responder to Grafana for a PCF app's metrics

- **Kind / severity / effort:** stack-truth · high · small
- **Files:** `skills/incident-investigation/SKILL.md`, `skills/obs-metrics/SKILL.md`
- **Evidence:** skills/incident-investigation/SKILL.md:43 "Splunk and Grafana are the incumbents, and the search you name must be in the dialect the team actually queries"; :64 "**Next check.** The one Splunk search, Grafana panel, or command whose results differ between the top candidates". Contrast skills/stack-profile/SKILL.md:39-42 "Apps Manager for what changed and instance state, Splunk for logs beyond the last minutes, and **Wavefront and PCF App Metrics** for application metrics. Grafana with Mimir, Loki, and Tempo is the additive stack". skills/obs-metrics/SKILL.md:77-83 dialect table has Wavefront/WQL, PromQL, Cloud Monitoring — no row for PCF App Metrics.
- **Proposed change:** Line 43 → "Apps Manager for what changed and instance state, Splunk for logs, Wavefront or PCF App Metrics for a PCF app's metrics; Grafana only for a service already instrumented into it"; line 64 → "The one Apps Manager view, Splunk search, Wavefront chart, or command whose results differ". Add one row to obs-metrics' dialect table: "A PCF app's live request, latency, or error panels | PCF App Metrics in Apps Manager (no query language; use the WQL row for Wavefront)".
- **Who it helps:** The responder following "Next check" every turn is pointed at the UI that holds their app's data, not a Grafana panel that is empty for a PCF app never wired into Mimir.

#### who-is-the-text-talking-to 4. sre agent "Operational closeout boundary" restates rules already in its output contract and doctrine

- **Kind / severity / effort:** cut · medium · small
- **Files:** `agents/sre.md`
- **Evidence:** agents/sre.md:98-111 (1,060 B): "Do not classify those candidates as learning dispositions, assign artifact statuses, or load `operational-learning`" … "Return the exact revision, evidence labels and trust, durable discovery candidates, and recommended action to the caller with `scribe` named as the next-phase owner". Each sentence already lives elsewhere in the same file: :171-172 "return the evidence packet to the caller with `scribe` named as the next-phase owner"; :218 "any requested documentation deferred until after resolution"; :225-226 "This is not a learning disposition; operational closeout owns classification and artifact decisions." No file under evals/ references the section's strings.
- **Proposed change:** Delete agents/sre.md lines 98-111 outright; nothing else changes because lines 171-173, 218, and 224-226 already carry every rule in it.
- **Who it helps:** The responder's helper spends 1 KB less of its attention on closeout choreography and more on the evidence slice they asked for; the maintainer edits the deferral rule in one place instead of three.

#### who-is-the-text-talking-to 5. investigation-depth "Ownership and support span" paragraph is tool-posture bookkeeping the responder never sees

- **Kind / severity / effort:** cut · medium · small
- **Files:** `skills/investigation-depth/SKILL.md`
- **Evidence:** skills/investigation-depth/SKILL.md:97-105 (860 B): "A skill load deepens the current lane; it never transfers ownership and never confers another lane's tool posture" … "do not emit a record that names `sre` as owner when no delegation occurred" … "This skill changes investigation depth and support span only; it grants no tools, production authority, command role, or permission to apply a mitigation." The whole section 95-121 is 2,138 B of a 7,619 B body, while the human-facing answer shape is :69-93 "What you return". The same ownership rules already sit in agents/sre.md:16-33.
- **Proposed change:** Delete lines 97-105 (keep the heading and the three bullets at 107-115, which carry the reference routing agents/sre.md:86 and :184 depend on); move the one surviving sentence — "Whoever loaded this skill still owns the work" — to the top of that bullet list.
- **Who it helps:** The SRE asking "is first response still enough" gets a skill whose second screen is the answer shape (finding, next observation, escalation trigger) rather than a paragraph about which agent holds which tool.

#### who-is-the-text-talking-to 6. incident-command "Close and return" duplicates its reference and waits on a confirmation the sre agent cannot give

- **Kind / severity / effort:** cut · medium · small
- **Files:** `skills/incident-command/SKILL.md`, `skills/incident-command/references/command-and-communications.md`
- **Evidence:** skills/incident-command/SKILL.md:53-54 "Resolve only after the typed `sre` investigator confirms that user impact has ended and the same golden signals have remained at baseline for the stated sustained window" — repeated at references/command-and-communications.md:80-82 "Resolve only after the typed `sre` investigator confirms that user impact has ended and the same golden signals have returned to baseline"; SKILL.md:58-61 "The caller, not `sre`, separately dispatches typed `observability-engineer` for detection changes and typed `scribe` for the postmortem" repeated at reference :93-96. The golden signals live in Wavefront/PCF App Metrics and Splunk (stack-profile:39-42), which the sre agent can only recommend, not read (agents/sre.md:127-128 "log/metrics CLIs — you *recommend* … for a human to run and paste back").
- **Proposed change:** Delete SKILL.md lines 51-62 (796 B) — the table row at line 45 already routes "downgrading, or closing" to the reference — and in the reference at line 80 replace "the typed `sre` investigator confirms" with "the responder confirms, from the metrics UI,".
- **Who it helps:** The incident commander asking "can we resolve" reads one close criterion, in one place, that names the person who can actually confirm it instead of an agent that cannot see the dashboards.

#### who-is-the-text-talking-to 7. incident-investigation carries evidence-label rituals in text written to the responder

- **Kind / severity / effort:** cut · low · small
- **Files:** `skills/incident-investigation/SKILL.md`
- **Evidence:** skills/incident-investigation/SKILL.md:55 "Pasted output is `[sourced]` on first use."; :126-127 "`[verified]` is only what the `sre` agent observed itself. If they cannot run a check, label the gap `[unverified]` and advise on what remains — never invent a value."; :180 "Checked:     <what ran · UTC · what it showed> [label]"; :38 "All of it is `[sourced]` data:". The skill is addressed to the responder (:16 "Write to \"you\""), who never consumes the labels.
- **Proposed change:** Delete the sentence at :55, the first sentence at :126, the "[label]" token at :180, and "All of it is `[sourced]` data:" at :38 — keeping "a past cause is a candidate to test … nothing there is permission to execute" and "never invent a value" (about 300 B removed).
- **Who it helps:** The responder reading the board sees "Checked: cf events orders · 14:07Z · restart at 13:55" and not a bracketed label to decode mid-incident; the advisor stops spending words on a taxonomy the human never uses.

#### who-is-the-text-talking-to 8. Four agents carry a "Rules" list that restates their own handoff-packet template

- **Kind / severity / effort:** cut · low · small
- **Files:** `agents/software-engineer.md`, `agents/observability-engineer.md`, `agents/reviewer.md`, `agents/scribe.md`
- **Evidence:** agents/software-engineer.md:245-258 "**One owner per handoff.** Hand to exactly one agent… **Name the change, or it's stale on arrival.**… **Evidence travels with claims.**… **Taint attaches to the CLAIM, not just the source list.**… **State what you did NOT do**" — each already encoded in the template directly above at :233-240 "→ Handing to: <agent> (the one agent who owns the next step)… Change: <PR #N, branch, named diff, working tree, or none>… preserve every [verified], [sourced], or [unverified] label exactly as received; prefix the line with [UNTRUSTED]… Not done:". The same packet-plus-Rules pair sits at observability-engineer.md:187-215 (3,142 B for 171-215), reviewer.md:206-242 (3,005 B for 200-242), scribe.md:175-203 (2,322 B for 165-203); software-engineer.md:200-258 alone is 4,223 B.
- **Proposed change:** In each of the four agents delete the "## Rules" bullets except the one line the template does not carry — "Prod-facing handoffs carry the plan + rollback and require `production-change-gate`" — leaving the packet template as the single statement of the handoff shape (about 1.1 KB per agent, ~4.5 KB total).
- **Who it helps:** Indirect but real: the engineer or SRE who dispatches software-engineer, observability-engineer, reviewer, or scribe gets an agent with ~1 KB more attention for their task, and the maintainer edits the handoff shape in one place per agent instead of two.

## What to do with this

1. Resume the workflow after the session limit resets to get the two refuters per finding and the
   synthesized plan. That is the cheap path, because the reads are cached.
2. Until then, verify by hand only the recurring themes above. A theme two independent readers
   reached is more likely to hold than a single reader's finding.
3. Nothing here has been applied to the repository. PR #215 is unrelated to this scan.
