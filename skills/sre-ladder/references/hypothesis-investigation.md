# Hypothesis investigation — prove the cause

Use this mode when the symptom is confirmed, first response is no longer enough, and the next work
is to distinguish candidate causes with evidence. Stabilize user impact first when a safe human-
executed mitigation is available; do not turn a plausible story into root cause.

## Use this mode when

- First response has stabilized the situation or cannot do so, and the cause is still unknown.
- Recent changes must be correlated with the incident timeline.
- Competing causes can be separated by predictions and observations.
- The observed scope is still one service or otherwise bounded; systemic breadth is not yet proven.

Return to [first response](./first-response.md) if the symptom matches a documented procedure and no
causal investigation is needed. Move to [systemic failure](./systemic-failure.md) only when evidence
shows a distributed or self-sustaining mechanism.

## Investigation loop

1. **Characterize precisely.** Establish exact start time, blast radius, severity, and trend. Read
   [signal characterization](./signal-characterization.md) if the incident record lacks them.
2. **Build a UTC timeline.** Align the symptom with deploys, releases, config or feature-flag
   changes, platform events, dependency incidents, traffic shifts, and certificate or credential
   expiries.
3. **Write the differential.** For each candidate cause, state a prediction that would be observed
   if it were true.
4. **Test to eliminate.** Use the typed `sre` lane's authorized logs, metrics, traces, events, and
   network evidence to confirm or reject predictions. Load `root-cause` for the causal-testing loop:
   - Splunk or Loki logs for error spikes, stack traces, and correlation IDs;
   - Wavefront, Prometheus, or Grafana metrics for latency, errors, traffic, and saturation per
     application or instance;
   - ThousandEyes evidence for network, DNS, and dependency reachability; and
   - Moogsoft clustering or correlation for related alerts and platform events.
5. **Separate trigger from mechanism.** Use five whys past the proximate cause. A bad deploy may be
   the trigger; the missing test, rollout guard, or containment boundary may be the systemic cause.
6. **Conclude at the evidence level.** Record a supported cause and confidence, or the remaining
   candidates and the exact observation that would distinguish them.

## Common application-operations failure modes

- **Bad deploy or config:** errors begin at the change time; compare release, revision, instance,
  and configuration evidence.
- **Memory or quota saturation:** correlate `cf events` with memory evidence. Diego may append
  `(out of memory)` to status 137 when Garden reports OOM, while bare status 137 also has non-OOM
  causes and can still represent OOM on some containerd foundations. Do not infer the cause from
  the exit code alone. *[sourced: cloudfoundry/executor `run_step.go`; garden-runc-release issue
  #112]*
- **Slow or failing dependency:** upstream latency and timeout errors rise together; confirm the
  affected path.
- **Connection or thread-pool exhaustion:** saturation leads latency, then errors.
- **Certificate, credential, or secret expiry:** failures begin sharply at an expiry boundary.

## Return to the incident record

Preserve severity, blast radius, the UTC timeline, every tested hypothesis with evidence for and
against, the current cause/confidence, and mitigation performed by a human or recommended for human
execution. Durable code, detection, and documentation work remains proposed next-phase work until
the active incident reaches its terminal recovery state.

Ownership map only—not a load: mitigation goes to the human release owner; durable code changes go
to `software-engineer`; later signal and alert work goes to `observability-engineer`; a proven
systemic or distributed mechanism changes this skill's mode to systemic failure.
