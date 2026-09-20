# Tier 2 approval example

Read only when the caller explicitly asks for a worked example/template or is preparing a Tier 2/3
approval-request packet. Never load this file merely to evaluate an already-prepared real change
packet. The parent `SKILL.md` owns classification, blockers, the verdict, and execution authority.
This example is `[unverified]` shape, not evidence from a foundation and not approval for any real
action. All observations, limits, and thresholds below are fictional, not defaults.

> **Requesting approval for a human release owner to apply a Tier 2 change.**
>
> **Target**: `checkout` app, `prod` space, foundation `pcf-east`.
> **Why scale**: during the same five-minute window, all four web instances reached their worker
> limit and queued requests grew; 502s reached 2% and request p95 reached 600 ms. Sampled downstream
> calls held p95 at 100 ms, and the dependency owner confirmed tested throughput headroom for six
> app instances. This supports app capacity as a mitigation target; 502s alone would not.
> **Change**: scale from 4 -> 6 instances to absorb the 502 burst while the root cause is investigated.
> **Exact command**: Apps Manager -> the `checkout` app's **Overview** page -> **Scale**, instances
> 4 -> 6 (`cf scale checkout -i 6` where the CLI is installed).
> **Valid until**: `<UTC>` — after this deadline the change re-enters approval.
> **Blast radius**: no restart of existing instances (`-i` only adds); ~40s until new instances pass
> health checks in the supplied rehearsal. No config or code changes.
> **Verification**: the **Overview** instance table shows 6 running (`cf app checkout` shows
> `6/6 running`) within 3 min; for the affected routes, 502s stay below 0.1% and request p95 below
> 300 ms for 10 continuous minutes. Running instances alone do not establish recovery.
> **Abort/hold**: stop further scaling and escalate if 6 healthy instances are not established in
> 3 min or recovery is not established within 15 min. If 502s exceed 3% or downstream p95 exceeds
> 150 ms for 2 continuous minutes, the human release owner uses the approved rollback below and
> checks the same signals; missing telemetry leaves recovery unknown and stops further changes.
> **Rollback**: **Scale** back to 4 instances (`cf scale checkout -i 4`) — this restores the desired
> instance count; it does not reverse in-flight requests, external effects, or transient rebalancing.
>
> This is Tier 2 (reversible live change), so a human release owner needs explicit approval for this
> specific apply. Immediately before execution, that owner rechecks the target, command, actor, and
> current configuration identity against the approval. After the attempt, the owner returns an
> `executed`, `not executed`, or `UNKNOWN` receipt.
> I do not apply live changes or perform the reconciliation query.
> Meanwhile I'll continue the Tier 0 investigation of what changed, which needs no approval.
