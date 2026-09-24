# Tier 2 approval example

Read only when the caller explicitly asks for a worked example/template or is preparing a Tier 2/3
approval-request packet. Never load this file merely to evaluate an already-prepared real change
packet. The parent `SKILL.md` owns classification, blockers, the verdict, and execution authority.
This example is `[unverified]` shape, not evidence from a foundation and not approval for any real
action. All observations, limits, and thresholds below are fictional, not defaults.

> **Requesting approval for a human release owner to apply a Tier 2 change.** No declared incident,
> so the full production checklist applies.
>
> **Target**: `order-router` app, `prod` space, foundation `pcf-east`.
> **Why scale**: during the same five-minute window, all four web instances reached their worker
> limit and queued requests grew; 502s reached 2% and request p95 reached 600 ms. Sampled downstream
> calls held p95 at 100 ms, and the dependency owner confirmed tested throughput headroom for six
> app instances. This supports app capacity as a mitigation target; 502s alone would not.
> **Change**: scale from 4 -> 6 instances to absorb the 502 burst while the root cause is investigated.
> **Exact command**: Apps Manager -> the `order-router` app's **Overview** page -> **Scale**, instances
> 4 -> 6 (`cf scale order-router -i 6` where the CLI is installed).
> **Valid until**: `<UTC>` — after this deadline the change re-enters approval.
> **Execution boundary**: `<named release owner>` holds the least-privilege `prod` space role that
> can scale `order-router`; `<evidence: role assignment record>`. I hold no role that can apply it.
> **Change record**: `<change system and ID, per stack-profile>`.
> **Blast radius**: no restart of existing instances (`-i` only adds); ~40s until new instances pass
> health checks in the supplied rehearsal. No config or code changes.
> **Verification**: the **Overview** instance table shows 6 running (`cf app order-router` shows
> `instances: 6/6`) within 3 min; for the affected routes, 502s stay below 0.1% and request p95 below
> 300 ms for 10 continuous minutes. Running instances alone do not establish recovery.
> **Abort/hold**: stop further scaling and escalate if 6 healthy instances are not established in
> 3 min or recovery is not established within 15 min. If 502s exceed 3% or downstream p95 exceeds
> 150 ms for 2 continuous minutes, the human release owner uses the approved rollback below and
> checks the same signals; missing telemetry leaves recovery unknown and stops further changes.
> **Rollback**: **Scale** back to 4 instances (`cf scale order-router -i 4`) — this restores the desired
> instance count; it does not reverse in-flight requests, external effects, or transient rebalancing.
> **Watching**: `<named human>` on 502 rate, request p95, and instance health for the whole window.
> **Timing/comms**: outside the market-open peak and any freeze; on-call and the owning team are
> told before and after.
>
> This is Tier 2 (reversible live change), so a human release owner needs explicit approval for this
> specific apply. Immediately before execution, that owner rechecks the target, command, actor, and
> current configuration identity against the approval. After the attempt, the owner returns an
> `executed`, `not executed`, or `UNKNOWN` receipt.
> I do not apply live changes. A read-only readback I run after the attempt is evidence for the
> reconciliation owner, who alone resolves `UNKNOWN` and grants any retry.
> Meanwhile I'll continue the Tier 0 investigation of what changed, which needs no approval.
